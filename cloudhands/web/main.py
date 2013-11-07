#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
import logging
import platform
import sys
import sqlite3

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.config import Configurator
from pyramid.exceptions import Forbidden
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import authenticated_userid

from pyramid_authstack import AuthenticationStackPolicy
from pyramid_macauth import MACAuthenticationPolicy

from waitress import serve

from cloudhands.common.connectors import Initialiser
from cloudhands.common.connectors import Session
from cloudhands.common.schema import DCStatus
from cloudhands.common.schema import Touch
#import cloudhands.common
import cloudhands.web
from cloudhands.web import __version__
from cloudhands.web.model import Page

DFLT_PORT = 8080
DFLT_DB = ":memory:"

CRED_TABLE = {}


class Connection(Initialiser):

    def __init__(self, path=DFLT_DB):
        self.engine = self.connect(sqlite3, path=path)
        self.session = Session()
        

def top_page(request):
    #userId = authenticated_userid(request)
    #if userId is None:
    #    raise Forbidden()

    con = Connection()
    status = con.session.query(
        DCStatus).join(Touch).order_by(Touch.at.desc()).first()
    
    p = Page()
    if status:
        state = status.changes[-1].state
        p.push(status, (state.fsm, state.name))

    return dict(p.dump())


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
    # Configuration to be done programmatically so
    # that settings can be shared with, eg: Nginx config
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
        renderer="json", accept="application/json", xhr=True)
    config.add_view(
        top_page, route_name="top", request_method="GET",
        renderer="cloudhands.web:templates/base.pt")

    config.add_route("creds", "/creds")
    config.add_view(
        macauth_creds, route_name="creds", request_method="GET",
        renderer="json", accept="application/json")
        #renderer="cloudhands.web:templates/creds.pt")

    config.add_static_view(name="css", path="topicmob.web:static/css")
    #config.add_static_view(name="js", path="topicmob.web:static/js")
    config.add_static_view(name="img", path="topicmob.web:static/img")

    policy = AuthenticationStackPolicy()
    policy.add_policy(
        "email",
        AuthTktAuthenticationPolicy(
            settings["persona.secret"],
            callback=None)
        )
    policy.add_policy(
        "apimac",
        MACAuthenticationPolicy(
            settings["macauth.master_secret"],
        ))
    config.set_authentication_policy(policy)
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


def parser():
    rv = argparse.ArgumentParser(description=__doc__)
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
