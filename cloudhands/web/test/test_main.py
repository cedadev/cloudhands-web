#!/usr/bin/env python3
# encoding: UTF-8

from collections import namedtuple
import datetime
import operator
import re
import sqlite3
import tempfile
import unittest
import uuid

from pyramid import testing
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.httpexceptions import HTTPNotFound

from cloudhands.burst.membership import Invitation

import cloudhands.common
from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

from cloudhands.common.fsm import MembershipState

from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

import cloudhands.web
from cloudhands.web.indexer import create as create_index
from cloudhands.web.indexer import indexer
from cloudhands.web.indexer import ldap_types
from cloudhands.web.main import parser
from cloudhands.web.main import top_page
from cloudhands.web.main import organisation_page
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
        self.session = Registry().connect(sqlite3, ":memory:").session
        initialise(self.session)
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


    def make_test_user_admin(session):
        # Create an organisation, membership of it, and a user
        # for the authenticated email address of this test
        org = Organisation(name="TestOrg")
        adminMp = Membership(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            organisation=org,
            role="admin")
        admin = User(handle="Test Admin", uuid=uuid.uuid4().hex)
        ea = EmailAddress(
            value=cloudhands.web.main.authenticated_userid(),
            provider="test admin's email provider")

        # Make the authenticated user an admin
        active = session.query(
            MembershipState).filter(MembershipState.name == "active").one()
        now = datetime.datetime.utcnow()
        act = Touch(artifact=adminMp, actor=admin, state=active, at=now)
        ea.touch = act
        adminMp.changes.append(act)
        session.add(ea)
        session.commit()
        return act


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


class OrganisationPageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.config.add_route("organisation", "/organisation")

    def test_nonadmin_user_cannot_add_membership(self):
        self.assertRaises(
            HTTPNotFound,
            organisation_page, self.request)

    def test_admin_user_can_add_membership(self):
        act = ServerTests.make_test_user_admin(self.session)
        admin = act.actor
        org = act.artifact.organisation
        request = testing.DummyRequest()
        request.matchdict.update({"org_name": org.name})
        page = organisation_page(request)
        options = page["options"].values()
        data = [i for i in options if "name" in i.get("data", {})]
        self.assertTrue(data)
        self.assertEqual(org.name, data[0]["data"]["name"])
        invite = next(i for o in options if "_links" in o
                      for i in o["_links"] if i.name.startswith("Invit"))
        self.assertTrue(invite)


class PeoplePageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.td = tempfile.TemporaryDirectory()
        Args = namedtuple("Arguments", ["index"])
        self.config.add_settings({"args": Args(self.td.name)})
        self.config.add_route("people", "/people")

    def tearDown(self):
        self.td.cleanup()
        super().tearDown()

    def test_500_error_raised_without_index(self):
        self.assertRaises(
            HTTPInternalServerError,
            people_page, self.request)

    def test_page_regions(self):
        create_index(self.td.name, **ldap_types)
        page = people_page(self.request)
        self.assertIn("info", page)
        self.assertIn("items", page)
        self.assertIn("options", page)
        self.assertIn("paths", page["info"])

    def test_search_form(self):
        create_index(self.td.name, **ldap_types)
        page = people_page(self.request)
        self.assertEqual(1, len(page["options"]))

    def test_user_search(self):
        ix = create_index(self.td.name, **ldap_types)
        wrtr = ix.writer()

        for i in range(10):
            wrtr.add_document(id=str(i), gecos="User {}".format(i))
        wrtr.commit()

        request = testing.DummyRequest({"description": "Loser"})
        page = people_page(request)
        self.assertEqual(0, len(page["items"]))

        request = testing.DummyRequest({"description": "User"})
        page = people_page(request)
        self.assertEqual(10, len(page["items"]))

    def test_user_items_offer_open_invitation(self):

        act = ServerTests.make_test_user_admin(self.session)
        admin = act.actor
        org = act.artifact.organisation

        # Issue an invitation for the organisation
        self.assertIsInstance(
            Invitation(admin, org)(self.session),
            Touch)

        # Populate some people
        ix = create_index(self.td.name, **ldap_types)
        wrtr = ix.writer()

        for i in range(10):
            wrtr.add_document(id=str(i), gecos="Person {}".format(i))
        wrtr.commit()

        request = testing.DummyRequest({"description": "Person"})
        page = people_page(request)
        items = page["items"].values()
        self.assertTrue(all("_links" in i for i in items))

if __name__ == "__main__":
    unittest.main()
