#!/usr/bin/env python3
# encoding: UTF-8

import datetime
from collections.abc import MutableMapping
from collections.abc import Sequence
import unittest
import uuid

import cloudhands.common
from cloudhands.common.fsm import CredentialState
from cloudhands.common.fsm import HostState

from cloudhands.common.schema import DCStatus
from cloudhands.common.schema import Host
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Node
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.web.model import Page
from cloudhands.web.model import HostCollection
from cloudhands.web.model import HostsPage
from cloudhands.web.model import InfoCollection
from cloudhands.web.model import EmailIsUntrusted
from cloudhands.web.model import EmailIsTrusted
from cloudhands.web.model import EmailHasExpired
from cloudhands.web.model import EmailWasWithdrawn


class TestRegion(unittest.TestCase):

    def test_info_region_returns_named_dict(self):
        region = InfoCollection().name("test region")
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")
        rv = region.present(status, ("resource", "up"))
        self.assertTrue(rv)
        self.assertIsInstance(rv, MutableMapping)
        self.assertIsInstance(rv.name, Sequence)

    def test_info_region_makes_unique_names(self):
        region = InfoCollection().name("test region")
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")

        n = 10000
        for i in range(n):
            widget = region.present(status, ("resource", "up"))
            region.append(widget)

        names = {i.name for i in region}
        self.assertEqual(n, len(names))


class TestPage(unittest.TestCase):

    def test_push_simple_use(self):
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")
        p = Page()
        p.push(status)
        self.assertIn(status.uuid, str(p.dump()))

    def test_hateoas_hosts(self):
        user = User(handle="Sam Guy", uuid=uuid.uuid4().hex)
        org = Organisation(name="TestOrg")
        state = HostState(name="requested")
        hosts = [Host(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            organisation=org,
            name="host_{:02}".format(i)
            ) for i in range(10)]
        for n, h in enumerate(hosts):
            now = datetime.datetime.utcnow()
            t = Touch(artifact=h, actor=user, state=state, at=now)
            ip = IPAddress(value="192.168.1.{}".format(n), touch=t)
            node = Node(name="vm{:05}".format(n), touch=t)
            t.resources.extend([ip, node])
            h.changes.append(t)
        p = HostsPage()
        for h in hosts:
            p.push(h)
        self.assertEqual(10, len(dict(p.dump())["items"]))
        for i in p.dump():
            print(i)
