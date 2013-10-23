#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
import logging
import sys

from pyramid.config import Configurator

from waitress import serve

import cloudhands.web
from cloudhands.web import __version__

DFLT_PORT = 8080


def top_page(request):
    return {"versions": {i.__name__: i.__version__ for i in [cloudhands.web]}}


def wsgi_app():
    # Configuration to be done programmatically so
    # that settings can be shared with, eg: Nginx config
    settings = {
        }
    config = Configurator(settings=settings)
    #config.add_static_view(name="css", path="cloudhands.web:static/css")
    #config.add_static_view(name="js", path="cloudhands.web:static/js")
    #config.add_static_view(name="img", path="cloudhands.web:static/img")
    config.add_route("top", "/")
    config.add_view(
        top_page, route_name="top", request_method="GET",
        renderer="json")
        #renderer="cloudhands.web:templates/top.pt")
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
