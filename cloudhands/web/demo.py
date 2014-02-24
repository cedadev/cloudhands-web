#!/usr/bin/env python
# encoding: UTF-8

import argparse
from configparser import ConfigParser
import datetime
import logging
import platform
import sqlite3
import sys
import uuid

from cloudhands.burst.membership import handle_from_email
from cloudhands.burst.subscription import Online

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.discovery import providers
from cloudhands.common.discovery import settings
from cloudhands.common.fsm import MembershipState
from cloudhands.common.fsm import SubscriptionState

from cloudhands.common.schema import Archive
from cloudhands.common.schema import Component
from cloudhands.common.schema import Directory
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Provider
from cloudhands.common.schema import Subscription
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

    subscriptions = [
        ("MARMITE", "cloudhands.jasmin.vcloud.phase01.cfg"),
        ("MARMITE", "cloudhands.jasmin.vcloud.phase02.cfg"),
    ]

    def demo_email(req=None):
        return "ben.campbell@universityoflife.ac.uk"


    def create_subscriptions(session):
        maintenance = session.query(
            SubscriptionState).filter(
            SubscriptionState.name=="maintenance").one()
        actor = session.query(Component).filter(
            Component.handle=="burst.controller").one()
        #if not actor:
        #    actor = Component(handle="Demo", uuid=uuid.uuid4().hex)
        #    session.add(actor)

        for orgName, providerName in WebFixture.subscriptions:
            org = session.query(Organisation).filter(
                Organisation.name==orgName).first()
            if not org:
                org = Organisation(
                    uuid=uuid.uuid4().hex,
                    name=orgName)

            provider = session.query(Provider).filter(
                Provider.name==providerName).first()
            if not provider:
                provider = Provider(
                    name=providerName, uuid=uuid.uuid4().hex)
                session.add(provider)

            subs = Subscription(
                uuid=uuid.uuid4().hex,
                model=cloudhands.common.__version__,
                organisation=org,
                provider=provider)
            subs.changes.append(
                Touch(
                    artifact=subs, actor=actor, state=maintenance,
                    at=datetime.datetime.utcnow())
                )
            try:
                session.add(subs)
                session.commit()
            except Exception as e:
                session.rollback()
            finally:
                session.flush()
            act = Online(actor, subs)(session)

    def grant_admin_memberships(session, user):
        active = session.query(MembershipState).filter(
            MembershipState.name == "active").one()

        for name, provider in WebFixture.subscriptions:
            org = session.query(Organisation).filter(
                Organisation.name == name).one()
            mship = Membership(
                uuid=uuid.uuid4().hex,
                model=cloudhands.common.__version__,
                organisation=org,
                role="admin")
            ea = EmailAddress(
                value=WebFixture.demo_email())

            now = datetime.datetime.utcnow()
            act = Touch(artifact=mship, actor=user, state=active, at=now)
            ea.touch = act
            mship.changes.append(act)
            try:
                session.add(ea)
                session.commit()
                yield act
            except Exception as e:
                session.rollback()
            finally:
                session.flush()


    def add_subscribed_resources(session, user):
        for name, provider in WebFixture.subscriptions:
            org = session.query(Organisation).filter(
                Organisation.name == name).one()
            grant = session.query(Touch).join(Membership).join(User).filter(
                Membership.organisation_id == org.id).filter(
                User.id == user.id).first()
            mship = grant.artifact
            for subs in org.subscriptions:
                now = datetime.datetime.utcnow()
                if isinstance(subs.provider, Archive):
                    d = Directory(
                        provider=subs.provider,
                        description="CIDER data archive",
                        mount_path="/{mount}/panfs/cider")
                    act = Touch(
                        artifact=mship, actor=user, state=grant.state, at=now)
                    d.touch = act
                    mship.changes.append(act)
                    try:
                        session.add_all((d, act))
                        session.commit()
                        yield act
                    except Exception as e:
                        session.rollback()
                    finally:
                        session.flush()


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

    WebFixture.create_subscriptions(session)
    user = User(
        handle=handle_from_email(WebFixture.demo_email()),
        uuid=uuid.uuid4().hex)
    for t in WebFixture.grant_admin_memberships(session, user):
        log.info("{} activated as admin for {}".format(
            t.actor.handle,
            t.artifact.organisation.name))

    user = session.query(User).filter(User.handle == user.handle).one()
    for t in WebFixture.add_subscribed_resources(session, user):
        for r in t.resources:
            log.info("{} permitted access to a {} resource ({}).".format(
                t.actor.handle,
                r.provider.name,
                getattr(r, "description", "?")))


    cloudhands.web.main.authenticated_userid = WebFixture.demo_email

    app = cloudhands.web.main.wsgi_app(args)
    cloudhands.web.main.serve(
        app, host=platform.node(), port=args.port, url_scheme="http")
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
