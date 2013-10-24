#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
import logging
import platform
import sys

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.config import Configurator
from pyramid.security import authenticated_userid
from pyramid.exceptions import Forbidden

from waitress import serve

import cloudhands.web
from cloudhands.web import __version__

DFLT_PORT = 8080


def top_page(request):
    userid = authenticated_userid(request)
    if userid is None:
        raise Forbidden()
    return {"versions": {i.__name__: i.__version__ for i in [cloudhands.web]}}


def wsgi_app():
    # Configuration to be done programmatically so
    # that settings can be shared with, eg: Nginx config
    settings = {
        "persona.secret": "FON85B9O3VCMQ90517Z1",
        "persona.audiences":[
            "http://{}:80".format(platform.node()),
            "http://localhost:8080"],
        "macauth.master_secret": "MU3D133C4FC4M0EDWHXK",
        }
    config = Configurator(settings=settings)
    #config.add_static_view(name="css", path="cloudhands.web:static/css")
    #config.add_static_view(name="js", path="cloudhands.web:static/js")
    #config.add_static_view(name="img", path="cloudhands.web:static/img")
    config.add_route("top", "/")
    config.add_view(
        top_page, route_name="top", request_method="GET",
        renderer="json", accept="application/json")
        #renderer="cloudhands.web:templates/top.pt")

    config.include("pyramid_persona")
    policy = AuthTktAuthenticationPolicy(
        settings['persona.secret'],
        callback=None)

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
