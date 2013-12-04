#!/usr/bin/env python3
#   encoding: UTF-8

import datetime
import logging
import uuid

import cloudhands.common
from cloudhands.common.fsm import HostState
from cloudhands.common.schema import Host
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User
from cloudhands.common.tricks import create_user_from_email
from cloudhands.common.tricks import handle_from_email


class WebFixture(object):

    nodes = [
        ("METAFOR", "portal", "up", "130.246.184.156"),
        ("METAFOR", "worker_01", "up", "192.168.1.3"),
        ("METAFOR", "worker_02", "up", "192.168.1.4"),
        ("METAFOR", "worker_03", "down", "192.168.1.5"),
        ("METAFOR", "worker_04", "down", "192.168.1.6"),
        ("METAFOR", "worker_05", "up", "192.168.1.7"),
        ("METAFOR", "worker_06", "up", "192.168.1.8"),
        ("METAFOR", "worker_07", "up", "192.168.1.9"),
        ("METAFOR", "worker_08", "up", "192.168.1.10"),
        ("METAFOR", "worker_09", "up", "192.168.1.11"),
        ("METAFOR", "worker_10", "down", "192.168.1.12"),
        ("METAFOR", "worker_11", "up", "192.168.1.13"),
        ("METAFOR", "worker_12", "up", "192.168.1.14"),
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
        invitation = Membership(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            organisation=org,
            role="user")
        handle = handle_from_email(WebFixture.demo_email())
        return (create_user_from_email(
            session, WebFixture.demo_email(), handle, invitation) or
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
