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
from pyramid.security import authenticated_userid

from pyramid_authstack import AuthenticationStackPolicy
from pyramid_macauth import MACAuthenticationPolicy

from waitress import serve

from cloudhands.common.fsm import MembershipState
from cloudhands.common.connectors import Initialiser
from cloudhands.common.connectors import Session
from cloudhands.common.schema import DCStatus
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Host
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User
#import cloudhands.common
import cloudhands.web
from cloudhands.web import __version__
from cloudhands.web.model import Page

DFLT_PORT = 8080
DFLT_DB = ":memory:"

CRED_TABLE = {}


class Connection(Initialiser):

    _shared_state = {}

    def __init__(self, path=DFLT_DB):
        self.__dict__ = self._shared_state
        self.engine = self.connect(sqlite3, path=path)
        if not hasattr(self, "session"):
            self.session = Session(autoflush=False)


def paths(request):
    return {p: os.path.dirname(request.static_url(
        "cloudhands.web:static/{}/{}".format(p, f)))
        for p, f in (
            ("css", "any.css"), ("js", "any.js"), ("img", "any.png"))}


def top_page(request):
    userId = authenticated_userid(request)
    if userId is None:
        raise Forbidden()

    con = Connection()
    status = con.session.query(
        DCStatus).join(Touch).order_by(Touch.at.desc()).first()

    p = Page()
    if status:
        state = status.changes[-1].state
        p.push(status, (state.fsm, state.name))

    rv = {"paths": paths(request)}
    rv.update(dict(p.dump()))
    return rv


def hosts_page(request):
    userId = authenticated_userid(request)
    if userId is None:
        raise Forbidden()

    con = Connection()
    user = con.session.query(User).join(Touch).join(
            EmailAddress).filter(EmailAddress.value == userId).first()
    if not user:
        # TODO: create
        raise NotFound("User not found for {}".format(userId))

    p = Page()
    rv = {"paths": paths(request), "user": user.handle}
    rv.update(dict(p.dump()))
    return rv


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

    config.add_route("top", "/")
    config.add_view(
        top_page, route_name="top", request_method="GET",
        renderer="cloudhands.web:templates/base.pt")

    config.add_route("hosts", "/hosts")
    config.add_view(
        top_page, route_name="hosts", request_method="GET",
        renderer="json", accept="application/json", xhr=True)
    config.add_view(
        hosts_page, route_name="hosts", request_method="GET",
        renderer="json", accept="application/json")
        #renderer="cloudhands.web:templates/hosts.pt")

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
    return None


def main(args):
    model = configure(args)
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
