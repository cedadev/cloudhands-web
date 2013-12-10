#!/usr/bin/env python3
# encoding: UTF-8

import datetime
from collections.abc import Callable
from collections.abc import MutableMapping
import sqlite3
import tempfile
import unittest
import uuid

import whoosh.fields
from whoosh.query import Or
from whoosh.query import Term

import cloudhands.common

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

from cloudhands.common.fsm import CredentialState
from cloudhands.common.fsm import HostState

from cloudhands.common.schema import DCStatus
from cloudhands.common.schema import Host
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Node
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.web.indexer import create as create_index
from cloudhands.web.indexer import indexer
from cloudhands.web.model import Fragment
from cloudhands.web.model import HostData
from cloudhands.web.model import Page
from cloudhands.web.model import InfoRegion
from cloudhands.web.model import EmailIsUntrusted
from cloudhands.web.model import EmailIsTrusted
from cloudhands.web.model import EmailHasExpired
from cloudhands.web.model import EmailWasWithdrawn


class TestHostData(unittest.TestCase):

    def test_host_validation_mandatory(self):
        h = HostData()
        self.assertTrue(h.invalid)
        self.assertTrue(any(i for i in h.invalid if i.name == "hostname"))
        
        h = HostData(hostname="goodname")
        self.assertTrue(h.invalid)
    
        h = HostData(hostname="goodname", organisation="nodeparent")
        self.assertFalse(h.invalid)
    
    def test_hostname_validation_length(self):
        h = HostData(
            organisation="nodeparent",
            hostname="a" * (Host.name.type.length + 1))
        self.assertTrue(h.invalid)

        h = HostData(organisation="nodeparent",hostname="a" * 7)
        self.assertTrue(h.invalid)
 
        h = HostData(organisation="nodeparent",hostname="a" * 8)
        self.assertFalse(h.invalid)

        h = HostData(
            organisation="nodeparent",
            hostname="a" * Host.name.type.length)
        self.assertFalse(h.invalid)


    def test_organisation_validation_length(self):
        h = HostData(
            hostname="hostname",
            organisation="a" * (Organisation.name.type.length + 1))
        self.assertTrue(h.invalid)

        h = HostData(hostname="hostname", organisation="a" * 5)
        self.assertTrue(h.invalid)
 
        h = HostData(hostname="hostname", organisation="a" * 7)
        self.assertFalse(h.invalid)

        h = HostData(
            hostname="hostname",
            organisation="a" * Organisation.name.type.length)
        self.assertFalse(h.invalid)


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


class TestGenericPage(unittest.TestCase):

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

        self.assertTrue(all(isinstance(i, Fragment) for i in page.info))
        output = dict(page.termination())
        names = {i.name for i in page.info}
        self.assertEqual(n + 1, len(names))  # Version information is in info


class TestHostsPage(unittest.TestCase):

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


class TestUsersPage(unittest.TestCase):

    def test_people_data_comes_from_index(self):

        with tempfile.TemporaryDirectory() as td:
            ix = create_index(td, descr=whoosh.fields.TEXT(stored=True))
            wrtr = ix.writer()

            for i in range(10):
                wrtr.add_document(id=str(i), descr="User {}".format(i))
            wrtr.commit()

            srch = ix.searcher()
            query = Or([Term("id", "0"), Term("id", "9")])
            people = srch.search(query)
            peoplePage = Page()
            for p in people:
                peoplePage.items.push(p)
            self.assertEqual(2, len(dict(peoplePage.termination())["items"]))

