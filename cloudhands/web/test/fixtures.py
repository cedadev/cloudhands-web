#!/usr/bin/env python3
#   encoding: UTF-8

import datetime
import logging
import uuid

import cloudhands.common
from cloudhands.common.fsm import HostState
from cloudhands.common.schema import Host
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User
from cloudhands.common.tricks import create_user_grant_email_membership
from cloudhands.common.tricks import handle_from_email


class WebFixture(object):

    nodes = [
        ("METAFOR", "portal", "up", "130.246.184.156"),
        ("METAFOR", "worker 01", "up", "192.168.1.3"),
        ("METAFOR", "worker 02", "up", "192.168.1.4"),
        ("METAFOR", "worker 03", "down", "192.168.1.5"),
        ("METAFOR", "worker 04", "down", "192.168.1.6"),
        ("METAFOR", "worker 05", "up", "192.168.1.7"),
        ("METAFOR", "worker 06", "up", "192.168.1.8"),
        ("METAFOR", "worker 07", "up", "192.168.1.9"),
        ("METAFOR", "worker 08", "up", "192.168.1.10"),
        ("METAFOR", "worker 09", "up", "192.168.1.11"),
        ("METAFOR", "worker 10", "down", "192.168.1.12"),
        ("METAFOR", "worker 11", "up", "192.168.1.13"),
        ("METAFOR", "worker 12", "up", "192.168.1.14"),
    ]

    def demo_email(req=None):
        return "ben.campbell@durham.ac.uk"

    def create_organisations(session):
        for name in {i[0] for i in WebFixture.nodes}:
            org = Organisation(name=name)
            try:
                session.add(org)
                session.commit()
            except Exception as e:
                session.rollback()

    def grant_user_membership(session):
        org = session.query(Organisation).one()  # FIXME
        handle = handle_from_email(WebFixture.demo_email())
        return (create_user_grant_email_membership(
            session, org, WebFixture.demo_email(), handle) or
            session.query(User).filter(User.handle == handle).one())

    def load_hosts_for_user(session, user):
        log = logging.getLogger("cloudhands.web.demo")
        for jvo, hostname, status, addr in WebFixture.nodes:
            # 1. User creates a new host
            now = datetime.datetime.utcnow()
            org = session.query(
                Organisation).filter(Organisation.name == jvo).one()
                
            requested = session.query(HostState).filter(
                HostState.name == "requested").one()
            host = Host(
                uuid=uuid.uuid4().hex,
                model=cloudhands.common.__version__,
                organisation=org,
                name=hostname
                )
            host.changes.append(
                Touch(artifact=host, actor=user, state=requested, at=now))
            session.add(host)
            session.commit()



