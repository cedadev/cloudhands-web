#!/usr/bin/env python3
# encoding: UTF-8

from collections import namedtuple
import re
import sqlite3
import tempfile
import unittest

from pyramid import testing

import cloudhands.common
from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

import cloudhands.web
from cloudhands.web.indexer import create as create_index
from cloudhands.web.indexer import indexer
from cloudhands.web.indexer import ldap_types
from cloudhands.web.main import parser
from cloudhands.web.main import top_page
from cloudhands.web.main import people_page


class ACLTests(unittest.TestCase):

    def test_access_control(self):
        self.fail("Not doing it yet")


class ServerTests(unittest.TestCase):

    @classmethod
    def setUpClass(class_):

        def testuser_email(req=None):
            return "testuser@unittest.python"

        class_.auth_unpatch = cloudhands.web.main.authenticated_userid
        cloudhands.web.main.authenticated_userid = testuser_email
        if class_.auth_unpatch is cloudhands.web.main.authenticated_userid:
            class_.skipTest("Authentication badly patched")

    @classmethod
    def teardownClass(class_):
        cloudhands.web.main.authenticated_userid = class_.auth_unpatch

    def setUp(self):
        session = Registry().connect(sqlite3, ":memory:").session
        initialise(session)
        self.request = testing.DummyRequest()
        self.config = testing.setUp(request=self.request)
        self.config.add_static_view(
            name="css", path="cloudhands.web:static/css")
        self.config.add_static_view(
            name="js", path="cloudhands.web:static/js")
        self.config.add_static_view(
            name="img", path="cloudhands.web:static/img")

    def tearDown(self):
        Registry().disconnect(sqlite3, ":memory:")

class VersionInfoTests(ServerTests):

    def test_version_option(self):
        p = parser()
        rv = p.parse_args(["--version"])
        self.assertTrue(rv.version)

    def test_version_json(self):
        self.assertEqual(
            cloudhands.web.__version__,
            top_page(self.request)["info"]["versions"]["cloudhands.web"])
        self.assertEqual(
            cloudhands.common.__version__,
            top_page(self.request)["info"]["versions"]["cloudhands.common"])

class PeoplePageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.td = tempfile.TemporaryDirectory()
        Args = namedtuple("Arguments", ["index"])
        self.config.add_settings({"args": Args(self.td.name)})

    def tearDown(self):
        self.td.cleanup()
        super().tearDown()

    def test_user_search(self):
        ix = create_index(self.td.name, **ldap_types)
        wrtr = ix.writer()

        for i in range(10):
            wrtr.add_document(id=str(i), gecos="User {}".format(i))
        wrtr.commit()

        self.fail(people_page(self.request))

if __name__ == "__main__":
    unittest.main()
