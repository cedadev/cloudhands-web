#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import sqlite3
import unittest
import uuid

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

from cloudhands.common.fsm import HostState
from cloudhands.common.fsm import MembershipState

import cloudhands.common.schema
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Host
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import State
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.web.tricks import allocate_ip
from cloudhands.web.tricks import create_user_from_email
from cloudhands.web.tricks import handle_from_email


class TestUserMembership(unittest.TestCase):

    def setUp(self):
        """ Populate test database"""
        session = Registry().connect(sqlite3, ":memory:").session
        session.add_all(
            State(fsm=MembershipState.table, name=v)
            for v in MembershipState.values)
        session.add(Organisation(name="TestOrg"))
        session.commit()

    def tearDown(self):
        """ Every test gets its own in-memory database """
        r = Registry()
        r.disconnect(sqlite3, ":memory:")

    def test_quick_add_user(self):
        session = Registry().connect(sqlite3, ":memory:").session
        oName = "TestOrg"
        eAddr = "my.name@test.org"

        org = session.query(
            Organisation).filter(Organisation.name == oName).one()
        invitation = Membership(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            organisation=org,
            role="user")
        handle = handle_from_email(eAddr)
        user = create_user_from_email(session, eAddr, handle, invitation)
        self.assertIs(user, session.query(User).join(Touch).join(
            EmailAddress).filter(EmailAddress.value == eAddr).first())

    def test_add_duplicate_user(self):
        session = Registry().connect(sqlite3, ":memory:").session
        session.autoflush = False   # http://stackoverflow.com/a/4202016
        oName = "TestOrg"
        eAddr = "my.name@test.org"

        org = session.query(
            Organisation).filter(Organisation.name == oName).one()
        invitation = Membership(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            organisation=org,
            role="user")
        handle = handle_from_email(eAddr)
        user = create_user_from_email(session, eAddr, handle, invitation)
        reInvitation = Membership(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            organisation=org,
            role="user")
        self.assertIsNone(create_user_from_email(
            session, eAddr, handle, reInvitation))


class TestResourceManagement(unittest.TestCase):

    def setUp(self):
        """ Populate test database"""
        session = Registry().connect(sqlite3, ":memory:").session
        session.add_all(
            State(fsm=HostState.table, name=v)
            for v in HostState.values)
        session.add_all(
            State(fsm=MembershipState.table, name=v)
            for v in MembershipState.values)
        session.add(Organisation(name="TestOrg"))
        session.commit()

    def tearDown(self):
        """ Every test gets its own in-memory database """
        r = Registry()
        r.disconnect(sqlite3, ":memory:")

    def test_reallocate_ip(self):
        session = Registry().connect(sqlite3, ":memory:").session
        session.autoflush = False   # http://stackoverflow.com/a/4202016
        oName = "TestOrg"
        eAddr = "my.name@test.org"
        hName = "mynode.test.org"
        ipAddr = "192.168.1.1"

        org = session.query(
            Organisation).filter(Organisation.name == oName).one()
        invitation = Membership(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            organisation=org,
            role="user")
        handle = handle_from_email(eAddr)
        user = create_user_from_email(session, eAddr, handle, invitation)

        scheduling = session.query(HostState).filter(
            HostState.name == "scheduling").one()
        up = session.query(HostState).filter(
            HostState.name == "up").one()
        hosts = [
            Host(
                uuid=uuid.uuid4().hex,
                model=cloudhands.common.__version__,
                organisation=org,
                name=hName),
            Host(
                uuid=uuid.uuid4().hex,
                model=cloudhands.common.__version__,
                organisation=org,
                name=hName),
        ]
        now = datetime.datetime.utcnow()
        hosts[0].changes.append(
            Touch(artifact=hosts[0], actor=user, state=up, at=now))
        hosts[1].changes.append(
            Touch(artifact=hosts[1], actor=user, state=scheduling, at=now))
        session.add_all(hosts)
        session.commit()

        ip = allocate_ip(session, hosts[0], ipAddr)
        self.assertIn(ip, [r for c in hosts[0].changes for r in c.resources])

        ip = allocate_ip(session, hosts[1], ipAddr)
        self.assertNotIn(
            ip, [r for c in hosts[0].changes for r in c.resources])
        self.assertIn(ip, [r for c in hosts[1].changes for r in c.resources])
