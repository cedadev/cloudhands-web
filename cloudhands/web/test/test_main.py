#!/usr/bin/env python3
# encoding: UTF-8

import re
import sqlite3
import unittest

from pyramid import testing

import cloudhands.common
from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

import cloudhands.web
from cloudhands.web.main import parser
from cloudhands.web.main import top_page


class ACLTests(unittest.TestCase):

    def test_access_control(self):
        self.fail("Not doing it yet")


class TopLevelTests(unittest.TestCase):

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

if __name__ == "__main__":
    unittest.main()
