#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
import logging
import os.path
import platform
import sqlite3
import sys

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.exceptions import Forbidden
from pyramid.exceptions import NotFound
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.renderers import JSON
from pyramid.security import authenticated_userid

from pyramid_authstack import AuthenticationStackPolicy
from pyramid_macauth import MACAuthenticationPolicy

from waitress import serve

from cloudhands.common.fsm import MembershipState
from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.schema import DCStatus
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Host
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Resource
from cloudhands.common.schema import Serializable
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User
#import cloudhands.common
import cloudhands.web
from cloudhands.web import __version__
from cloudhands.web.model import Page
from cloudhands.web.model import PathInfo

DFLT_PORT = 8080
DFLT_DB = ":memory:"

CRED_TABLE = {}


def registered_connection():
    r = Registry()
    return r.connect(*next(iter(r.items)))


def paths(request):
    return {p: os.path.dirname(request.static_url(
        "cloudhands.web:static/{}/{}".format(p, f)))
        for p, f in (
            ("css", "any.css"), ("js", "any.js"), ("img", "any.png"))}


def record_adapter(obj, request):
    rv = obj.as_dict()
    try:
        del rv["id"]
    except KeyError:
        pass
    return rv


def top_page(request):
    userId = authenticated_userid(request)
    if userId is None:
        raise Forbidden()

    con = registered_connection()
    status = con.session.query(
        DCStatus).join(Touch).order_by(Touch.at.desc()).first()

    page = Page()
    if status:
        state = status.changes[-1].state
        page.items.push(status, (state.fsm, state.name))

    page.info.push(PathInfo(paths(request)))

    return dict(page.termination())


def hosts_page(request):
    log = logging.getLogger("cloudhands.web.hosts")
    userId = authenticated_userid(request)
    if userId is None:
        raise Forbidden()

    con = registered_connection()
    user = con.session.query(User).join(Touch).join(
        EmailAddress).filter(EmailAddress.value == userId).first()
    if not user:
        # TODO: create
        raise NotFound("User not found for {}".format(userId))

    memberships = con.session.query(Membership).join(Touch).join(User).filter(
        User.id == user.id).all()
    log.info(memberships)

    # FIXME!
    #hosts = con.session.query(Host).join(Touch).join(User).filter(
    #    User == user).all() # JVOs are containers for hosts
    hosts = con.session.query(Host).all()
    page = Page()
    page.info.push(PathInfo(paths(request)))
    for h in hosts:
        page.items.push(h)
    for m in memberships:
        page.options.push(m)

    return dict(page.termination())


def macauth_creds(request):
    userId = authenticated_userid(request)
    if userId is None:
        raise Forbidden()

    # Get a reference to the MACAuthenticationPolicy plugin.
    stack = request.registry.getUtility(IAuthenticationPolicy)
    policy = stack.policies["apimac"]

    try:
        id, key = CRED_TABLE[userId]
    except KeyError:
        id, key = policy.encode_mac_id(request, userId)
        CRED_TABLE[userId] = (id, key)

    return {"id": id, "key": key}


def wsgi_app():
    # TODO: pick up settings by discovery
    settings = {
        "persona.secret": "FON85B9O3VCMQ90517Z1",
        "persona.audiences": [
            "http://{}:80".format(platform.node()),
            "http://localhost:8080"],
        "macauth.master_secret": "MU3D133C4FC4M0EDWHXK",
        }
    config = Configurator(settings=settings)
    config.include("pyramid_chameleon")
    config.include("pyramid_persona")

    hateoas = JSON(indent=4)
    hateoas.add_adapter(Serializable, record_adapter)
    config.add_renderer("hateoas", hateoas)

    config.add_route("top", "/")
    config.add_view(
        top_page, route_name="top", request_method="GET",
        renderer="cloudhands.web:templates/base.pt")

    config.add_route("hosts", "/hosts")
    #config.add_view(
    #    hosts_page, route_name="hosts", request_method="GET",
    #    renderer="hateoas", accept="application/json", xhr=None)
    config.add_view(
        hosts_page, route_name="hosts", request_method="GET",
        renderer="cloudhands.web:templates/hosts.pt")

    config.add_route("creds", "/creds")
    config.add_view(
        macauth_creds, route_name="creds", request_method="GET",
        renderer="json", accept="application/json")
        #renderer="cloudhands.web:templates/creds.pt")

    config.add_static_view(name="css", path="cloudhands.web:static/css")
    config.add_static_view(name="js", path="cloudhands.web:static/js")
    config.add_static_view(name="img", path="cloudhands.web:static/img")

    authn_policy = AuthenticationStackPolicy()
    authn_policy.add_policy(
        "email",
        AuthTktAuthenticationPolicy(
            settings["persona.secret"],
            callback=None)
        )
    authn_policy.add_policy(
        "apimac",
        MACAuthenticationPolicy(
            settings["macauth.master_secret"],
        ))
    authz_policy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authn_policy)
    config.set_authorization_policy(authz_policy)
    config.scan()

    app = config.make_wsgi_app()
    return app


def configure(args):
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s|%(message)s")
    r = Registry()
    session = r.connect(sqlite3, args.db).session
    initialise(session)
    return session


def main(args):
    session = configure(args)
    app = wsgi_app()
    serve(app, host="localhost", port=args.port, url_scheme="http")
    return 1


def parser(description=__doc__):
    rv = argparse.ArgumentParser(description)
    rv.add_argument(
        "--version", action="store_true", default=False,
        help="Print the current version number")
    rv.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
    rv.add_argument(
        "--port", type=int, default=DFLT_PORT,
        help="Set the port number [{}]".format(DFLT_PORT))
    rv.add_argument(
        "--db", default=DFLT_DB,
        help="Set the path to the database [{}]".format(DFLT_DB))
    return rv


def run():
    p = parser()
    args = p.parse_args()
    if args.version:
        sys.stdout.write(__version__ + "\n")
        rv = 0
    else:
        rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()
