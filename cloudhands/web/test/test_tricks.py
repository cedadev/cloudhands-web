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
from cloudhands.common.schema import Host
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import State
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.web.tricks import allocate_ip


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
        handle = "Test User"
        hName = "mynode.test.org"
        ipAddr = "192.168.1.1"

        user = User(handle=handle, uuid=uuid.uuid4().hex)
        org = session.query(Organisation).one()
        session.add_all((user, org))
        session.commit()

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