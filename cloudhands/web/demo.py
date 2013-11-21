#!/usr/bin/env python
# encoding: UTF-8

import argparse
from configparser import ConfigParser
import datetime
import logging
import sqlite3
import sys
import uuid

from cloudhands.burst.test.fixtures import BurstFixture

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

import cloudhands.web.main
import cloudhands.common.schema
from cloudhands.web.test.fixtures import WebFixture

__doc__ = """
    select a.uuid, s.name, n.name, ips.value, t.at from touches as t
        join resources as r on r.id = t.id
        join artifacts as a on t.artifact_id = a.id
        join states as s on t.state_id = s.id
        left outer join ipaddresses as ips on ips.id = r.id
        left outer join nodes as n on n.id = r.id;
"""

DFLT_DB = ":memory:"


def main(args):
    rv = 1
    log = logging.getLogger("cloudhands.burst")
    session = cloudhands.web.main.configure(args)

    WebFixture.create_organisations(session)
    user = WebFixture.grant_user_membership(session)
    WebFixture.load_hosts_for_user(session, user)
    BurstFixture.load_resources_for_user(session, user, WebFixture.nodes)

    cloudhands.web.main.authenticated_userid = WebFixture.demo_email

    app = cloudhands.web.main.wsgi_app()
    cloudhands.web.main.serve(
        app, host="localhost", port=args.port, url_scheme="http")
    return rv


def parser(description=__doc__):
    rv = cloudhands.web.main.parser(description)
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()
