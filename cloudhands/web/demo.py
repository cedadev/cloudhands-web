#!/usr/bin/env python
# encoding: UTF-8

import argparse
from configparser import ConfigParser
import datetime
import logging
import platform
import sqlite3
import sys
import textwrap
import uuid

from cloudhands.burst.membership import handle_from_email
from cloudhands.burst.subscription import Online

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.discovery import providers
from cloudhands.common.discovery import settings
from cloudhands.common.fsm import MembershipState
from cloudhands.common.fsm import RegistrationState
from cloudhands.common.fsm import SubscriptionState

from cloudhands.common.schema import Archive
from cloudhands.common.schema import CatalogueItem
from cloudhands.common.schema import Component
from cloudhands.common.schema import Directory
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import PosixUId
from cloudhands.common.schema import Provider
from cloudhands.common.schema import Registration
from cloudhands.common.schema import Subscription
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.identity.registration import NewPassword

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
        ("EOSCloud", "cloudhands.jasmin.vcloud.phase03.cfg"),
        ("NERC-EW", "cloudhands.jasmin.vcloud.phase03.cfg"),
        #("MARMITE", "cloudhands.jasmin.vcloud.phase02.cfg"),  # FIXME: SSL cert
    ]

    @staticmethod
    def demo_email(req=None):
        return "ben.campbell@universityoflife.ac.uk"

    @staticmethod
    def demo_password(req=None):
        return "IWannaS33TheDemo!"

    @staticmethod
    def create_subscriptions(session):
        log = logging.getLogger("cloudhands.web.demo.subscriptions")
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
                session.add(org)

            provider = session.query(Provider).filter(
                Provider.name==providerName).first()
            if not provider:
                provider = Provider(
                    name=providerName, uuid=uuid.uuid4().hex)
                session.add(provider)

            if session.query(Subscription).join(Organisation).join(
                Provider).filter(Organisation.id==org.id).filter(
                Provider.id==provider.id).count():
                yield None
            else:

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
                act = Online(actor, subs)(session)
                subs.changes.append(act)
                try:
                    session.add(subs)
                    session.commit()
                    yield act
                except Exception as e:
                    log.debug(e)
                    session.rollback()
                finally:
                    session.flush()

    @staticmethod
    def create_catalogue(session):
        org = session.query(Organisation).first()
        try:
            session.add_all((
                CatalogueItem(
                    name="Bastion-host",
                    description="Headless VM for admin tasks",
                    note=textwrap.dedent("""
                        <p>This VM runs OpenSSH on CentOS 6.5.
                        It is used for administration and monitoring tasks.</p>
                        """),
                    logo="headless",
                    organisation=org,
                    uuid=uuid.uuid4().hex,
                ),
                CatalogueItem(
                    name="nfs-client",
                    description="Headless VM for file transfer operations",
                    note=textwrap.dedent("""
                        <p>This VM runs CentOS 6.5 with a minimal amount of RAM and
                        no X server. It is used for file transfer operations from the
                        command line.</p>
                        """),
                    logo="headless",
                    organisation=org,
                    uuid=uuid.uuid4().hex,
                ),
                CatalogueItem(
                    name="NFS-client-server",
                    description="Headless VM for file transfer operations",
                    note=textwrap.dedent("""
                        <p>This VM runs NFS services on CentOS 6.5.</p>
                        """),
                    logo="headless",
                    organisation=org,
                    uuid=uuid.uuid4().hex,
                ),
                CatalogueItem(
                    name="Web-Server",
                    description="Headless VM with Web server",
                    note=textwrap.dedent("""
                        <p>This VM runs Apache on CentOS 6.5.
                        It has 8GB RAM and 4 CPU cores.
                        It is used for hosting websites and applications with a
                        Web API.</p>
                        """),
                    logo="headless",
                    organisation=org,
                    uuid=uuid.uuid4().hex,
                ),
                CatalogueItem(
                    name="steve-pasco",
                    description="JASMIN Analysis Platform",
                    note=textwrap.dedent("""
                        <p>This VM runs IPython notebook.
                        It has a wide range of uses for research and analysis.</p>
                        """),
                    logo="headless",
                    organisation=org,
                    uuid=uuid.uuid4().hex,
                )
            ))
            session.commit()
        except Exception as e:
            session.rollback()
        finally:
            session.flush()

    @staticmethod
    def create_registration(session, user):
        preconfirm = session.query(RegistrationState).filter(
            RegistrationState.name == "pre_registration_inetorgperson").one()
        reg = Registration(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__)
        act = NewPassword(user, WebFixture.demo_password(), reg)(session)
        ea = EmailAddress(touch=act, value=WebFixture.demo_email())
        try:
            session.add(ea)
            session.commit()
        except Exception as e:
            session.rollback()
        finally:
            session.flush()

        yield act

        confirmed = session.query(RegistrationState).filter(
            RegistrationState.name == "pre_user_posixaccount").one()
        now = datetime.datetime.utcnow()
        act = Touch(artifact=reg, actor=user, state=confirmed, at=now)

        # TODO: Formalise function (wildcard unpacking of forenames?)
        cn = ''.join(i[:n] for i, n in zip(
            reversed(user.handle.split()), (6, 1, 1))).lower()
        uid = PosixUId(value=cn, touch=act)
        # TODO: PosixUIdNumber of 7010001

        try:
            session.add(uid)
            session.commit()
        except Exception as e:
            session.rollback()
        finally:
            session.flush()

        yield act

    @staticmethod
    def grant_admin_memberships(session, user):
        log = logging.getLogger("cloudhands.web.demo.memberships")
        active = session.query(MembershipState).filter(
            MembershipState.name == "active").one()

        for name, provider in WebFixture.subscriptions:
            org = session.query(Organisation).filter(
                Organisation.name == name).one()

            ea = session.query(EmailAddress).filter(
                EmailAddress.value==WebFixture.demo_email()).first()
            if not ea:
                ea = EmailAddress(
                    value=WebFixture.demo_email())
                session.add(ea)

            if session.query(Membership).join(Organisation).join(
                Touch).join(User).filter(Organisation.id==org.id).filter(
                Membership.role=="admin").filter(User.id==user.id).count():
                yield None

            else:
                    
                now = datetime.datetime.utcnow()
                mship = Membership(
                    uuid=uuid.uuid4().hex,
                    model=cloudhands.common.__version__,
                    organisation=org,
                    role="admin")
                act = Touch(artifact=mship, actor=user, state=active, at=now)
                ea.touch = act
                mship.changes.append(act)
                try:
                    session.add(ea)
                    session.commit()
                    yield act
                except Exception as e:
                    log.debug(e)
                    session.rollback()
                finally:
                    session.flush()

    @staticmethod
    def add_subscribed_resources(session, user):
        log = logging.getLogger("cloudhands.web.demo.resources")
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

    cfg, session = cloudhands.web.main.configure(args)

    for t in WebFixture.create_subscriptions(session):
        try:
            log.info("{} subscribed to {}".format(
                t.artifact.organisation.name,
                t.artifact.provider.name))
        except AttributeError:
            log.debug("Subscription pre-exists")

    WebFixture.create_catalogue(session)
    user = User(
        handle=handle_from_email(WebFixture.demo_email()),
        uuid=uuid.uuid4().hex)
    try:
        session.add(user)
        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.flush()


    for t in WebFixture.create_registration(session, user):
        for r in t.resources:
            log.info(r)

    user = session.query(User).filter(User.handle == user.handle).one()
    for t in WebFixture.grant_admin_memberships(session, user):
        try:
            log.info("{} activated as admin for {}".format(
                t.actor.handle,
                t.artifact.organisation.name))
        except AttributeError:
            log.debug("Membership pre-exists for {}".format(user.handle))

    user = session.query(User).filter(User.handle == user.handle).one()
    for t in WebFixture.add_subscribed_resources(session, user):
        for r in t.resources:
            log.info("{} permitted access to a {} resource ({}).".format(
                t.actor.handle,
                r.provider.name,
                getattr(r, "description", "?")))


    cloudhands.web.main.authenticated_userid = WebFixture.demo_email

    app = cloudhands.web.main.wsgi_app(args, cfg)
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
