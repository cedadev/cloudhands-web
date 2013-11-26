#!/usr/bin/env python3
# encoding: UTF-8

import datetime
from collections.abc import Callable
from collections.abc import MutableMapping
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

from cloudhands.web.model import Facet
from cloudhands.web.model import HostFacet
from cloudhands.web.model import Page
from cloudhands.web.model import InfoRegion
from cloudhands.web.model import EmailIsUntrusted
from cloudhands.web.model import EmailIsTrusted
from cloudhands.web.model import EmailHasExpired
from cloudhands.web.model import EmailWasWithdrawn


class TestHostFacet(unittest.TestCase):

    def test_host_validation_mandatory(self):
        h = HostFacet()
        self.assertTrue(h.invalid)
        self.assertTrue(any(i in h.invalid if i.name == "hostname"))
        
        h = HostFacet(hostname="goodname")
        self.assertFalse(h.invalid)
    
    def test_hostname_validation_length(self):
        h = HostFacet(hostname="a" * (Host.name.type.length + 1))
        self.assertTrue(h.invalid)
    
class TestRegion(unittest.TestCase):

    def test_pushed_region_returns_unnamed_dictionary(self):
        region = InfoRegion().name("test region")
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")
        rv = region.push(status, ("resource", "up"))
        self.assertTrue(rv)
        self.assertIsInstance(rv, MutableMapping)
        self.assertIsInstance(rv.name, Callable)


class TestPage(unittest.TestCase):

    def test_push_simple_use(self):
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")
        p = Page()
        p.info.push(status)
        self.assertIn(status.uuid, str(dict(p.termination())))

    def test_info_region_makes_unique_names(self):
        page = Page()
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")

        n = 10000
        for i in range(n):
            facet = page.info.push(status, ("resource", "up"))

        self.assertTrue(all(isinstance(i, Facet) for i in page.info))
        output = dict(page.termination())
        names = {i.name for i in page.info}
        self.assertEqual(n + 1, len(names))  # Version information is in info

    def test_hostspage_hateoas(self):
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
        hostsPage = Page()
        for h in hosts:
            hostsPage.items.push(h)
        self.assertEqual(10, len(dict(hostsPage.termination())["items"]))
