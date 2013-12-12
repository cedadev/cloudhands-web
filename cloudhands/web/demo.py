#!/usr/bin/env python
# encoding: UTF-8

import argparse
from configparser import ConfigParser
import datetime
import logging
import sqlite3
import sys
import uuid

from cloudhands.burst.membership import handle_from_email

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.discovery import settings
from cloudhands.common.fsm import MembershipState

from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

import cloudhands.web.indexer
import cloudhands.web.main
import cloudhands.common.schema

__doc__ = """
This program creates a fictional scenario for the purpose
of demonstrating the JASMIN web portal.
"""

DFLT_DB = ":memory:"


class WebFixture(object):

    organisations = [
        ("MARMITE", "vcloud"),
    ]

    def demo_email(req=None):
        return "ben.campbell@universityoflife.ac.uk"

    def create_organisations(session):
        for name, provider in WebFixture.organisations:
            org = Organisation(name=name)
            try:
                session.add(org)
                session.commit()
            except Exception as e:
                session.rollback()

    def grant_admin_memberships(session, user):
        active = session.query(MembershipState).filter(
            MembershipState.name == "active").one()
        for name, provider in WebFixture.organisations:
            org = session.query(Organisation).filter(
                Organisation.name == name).one()
            mship = Membership(
                uuid=uuid.uuid4().hex,
                model=cloudhands.common.__version__,
                organisation=org,
                role="admin")
            ea = EmailAddress(
                value=WebFixture.demo_email(),
                provider=provider)

            now = datetime.datetime.utcnow()
            act = Touch(artifact=mship, actor=user, state=active, at=now)
            ea.touch = act
            mship.changes.append(act)
            session.add(ea)
            session.commit()
            yield act


def main(args):
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s|%(message)s")
    log = logging.getLogger("cloudhands.web.demo")

    args.interval = None
    args.query = None
    log.info("Generating index at {}".format(args.index))
    cloudhands.web.indexer.main(args)

    session = cloudhands.web.main.configure(args)

    WebFixture.create_organisations(session)
    user = User(handle=handle_from_email(WebFixture.demo_email()),
                 uuid=uuid.uuid4().hex)
    for t in WebFixture.grant_admin_memberships(session, user):
        log.info("{} activated as admin for {}".format(
            t.actor.handle,
            t.artifact.organisation.name))

    cloudhands.web.main.authenticated_userid = WebFixture.demo_email

    app = cloudhands.web.main.wsgi_app(args)
    cloudhands.web.main.serve(
        app, host="localhost", port=args.port, url_scheme="http")
    return 0


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
