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

import cloudhands.common

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

from cloudhands.common.fsm import HostState

from cloudhands.common.schema import Host
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Node
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import OSImage
from cloudhands.common.schema import Registration
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.common.types import NamedDict

from cloudhands.web.indexer import create as create_index
from cloudhands.web.indexer import indexer
from cloudhands.web.indexer import people
from cloudhands.web.indexer import Person
from cloudhands.web.model import GenericRegion
from cloudhands.web.model import HostView
from cloudhands.web.model import RegistrationView
from cloudhands.web.model import Page


class TestHostView(unittest.TestCase):

    def test_host_validation_mandatory(self):
        h = HostView()
        self.assertTrue(h.invalid)
        self.assertTrue(any(i for i in h.invalid if i.name == "name"))

        h = HostView(name="goodname")
        self.assertTrue(h.invalid)

        h = HostView(name="goodname", jvo="nodeparent", image="CentOS_6.4")
        self.assertFalse(h.invalid)

    def test_hostname_validation_length(self):
        h = HostView(
            jvo="nodeparent",
            name="a" * (Host.name.type.length + 1))
        self.assertTrue(h.invalid)

        h = HostView(jvo="nodeparent", name="a" * 7, image="CentOS_6.5")
        self.assertTrue(h.invalid)

        h = HostView(jvo="nodeparent", name="a" * 8, image="CentOS_6.5")
        self.assertFalse(h.invalid)

        h = HostView(
            jvo="nodeparent",
            image="CentOS_6.5",
            name="a" * Host.name.type.length)
        self.assertFalse(h.invalid)

    def test_organisation_validation_length(self):
        h = HostView(
            name="hostname",
            image="CentOS_6.5",
            jvo="a" * (Organisation.name.type.length + 1))
        self.assertTrue(h.invalid)

        h = HostView(name="hostname", jvo="a" * 5, image="CentOS_6.5")
        self.assertTrue(h.invalid)

        h = HostView(name="hostname", jvo="a" * 7, image="CentOS_6.5")
        self.assertFalse(h.invalid)

        h = HostView(
            name="hostname",
            image="CentOS_6.5",
            jvo="a" * Organisation.name.type.length)
        self.assertFalse(h.invalid)

    def test_image_validation_length(self):
        h = HostView(
            name="hostname",
            jvo="marmite",
            image="a" * (OSImage.name.type.length + 1))
        self.assertTrue(h.invalid)

        h = HostView(name="hostname", jvo="marmite", image="a" * 5)
        self.assertTrue(h.invalid)

        h = HostView(name="hostname", jvo="marmite", image="a" * 7)
        self.assertFalse(h.invalid)

        h = HostView(
            name="hostname",
            jvo="marmite",
            image="a" * OSImage.name.type.length)
        self.assertFalse(h.invalid)

    def test_image_permitted_characters(self):
        h = HostView(
            name="hostname",
            jvo="marmite",
            image="has space")
        self.assertFalse(h.invalid)


class TestGenericRegion(unittest.TestCase):

    def test_pushed_region_returns_unnamed_dictionary(self):
        region = GenericRegion().name("test region")
        rv = region.push(Person(*(None,) * 5))
        self.assertTrue(rv)
        self.assertIsInstance(rv, MutableMapping)
        self.assertIsInstance(rv.name, Callable)


class TestGenericPage(unittest.TestCase):

    def test_push_simple_use(self):
        id = uuid.uuid4().hex
        p = Page()
        p.layout.info.push(Person(id, 0, [0], "me", []))
        self.assertIn(id, str(dict(p.termination())))

    def test_info_region_makes_unique_names(self):
        page = Page()

        n = 10000
        for i in range(n):
            facet = page.layout.info.push(
                Person("P{0:5}".format(n), n, [n], "", []))

        self.assertTrue(
            all(isinstance(i, NamedDict) for i in page.layout.info))
        output = dict(page.termination())
        names = {i.name for i in page.layout.info}
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
            hostsPage.layout.items.push(h)
        self.assertEqual(10, len(dict(hostsPage.termination())["items"]))


class TestRegistrationPage(unittest.TestCase):

    def test_registration_email_validation(self):
        r = RegistrationView(
            username="username",
            email="somebody_somewhere.com",
            password="1A_" + "a" * 5)
        self.assertTrue(r.invalid)

    def test_registration_password_length_validation(self):
        r = RegistrationView(
            username="username",
            email="somebody@somewhere.com",
            password="1A_" + "a" * 4)
        self.assertTrue(r.invalid)

        r = RegistrationView(
            username="username",
            email="somebody@somewhere.com",
            password="1A_" + "a" * 18)
        self.assertTrue(r.invalid)

        r = RegistrationView(
            username="username",
            email="somebody@somewhere.com",
            password="1A_" + "a" * 5)
        self.assertFalse(r.invalid)

        r = RegistrationView(
            username="username",
            email="somebody@somewhere.com",
            password="1A_" + "a" * 17)
        self.assertFalse(r.invalid)

    def test_registration_password_validation(self):
        r = RegistrationView(
            username="username",
            email="somebody@somewhere.com",
            password="a" * 8)
        self.assertTrue(r.invalid)

        r = RegistrationView(
            username="username",
            email="somebody@somewhere.com",
            password="1" * 8)
        self.assertTrue(r.invalid)

        r = RegistrationView(
            username="username",
            email="somebody@somewhere.com",
            password="_" * 8)
        self.assertTrue(r.invalid)

        r = RegistrationView(
            username="username",
            email="somebody@somewhere.com",
            password="a" * 4 + "A" * 4)
        self.assertTrue(r.invalid)

        r = RegistrationView(
            username="username",
            email="somebody@somewhere.com",
            password="a" * 4 + "1" * 4)
        self.assertTrue(r.invalid)


class TestPeoplePage(unittest.TestCase):

    def test_people_data_comes_from_index(self):

        with tempfile.TemporaryDirectory() as td:
            ix = create_index(td, descr=whoosh.fields.TEXT(stored=True))
            wrtr = ix.writer()

            for i in range(10):
                wrtr.add_document(id=str(i), descr="User {}".format(i))
            wrtr.commit()

            ppl = list(people(td, "User", "descr"))
            self.assertEqual(10, len(ppl))

            peoplePage = Page()
            for p in ppl:
                peoplePage.layout.items.push(p)

            output = dict(peoplePage.termination())
            self.assertEqual(10, len(output["items"]))


class TestCataloguePage(unittest.TestCase):

    def test_catalogueitem_view_finds_logo(self):
        self.fail()
