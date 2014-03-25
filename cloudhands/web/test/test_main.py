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

import bcrypt

from pyramid import testing
from pyramid.exceptions import Forbidden
from pyramid.exceptions import NotFound
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.httpexceptions import HTTPNotFound

from cloudhands.burst.membership import Invitation

import cloudhands.common
from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

from cloudhands.common.fsm import MembershipState
from cloudhands.common.fsm import RegistrationState

from cloudhands.common.schema import BcryptedPassword
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Provider
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Registration
from cloudhands.common.schema import Resource
from cloudhands.common.schema import State
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

import cloudhands.web
from cloudhands.web.indexer import create as create_index
from cloudhands.web.indexer import indexer
from cloudhands.web.indexer import ldap_types
from cloudhands.web.main import authenticate_user
from cloudhands.web.main import parser
from cloudhands.web.main import top_read
from cloudhands.web.main import membership_read
from cloudhands.web.main import membership_update
from cloudhands.web.main import organisation_read
from cloudhands.web.main import organisation_memberships_create
from cloudhands.web.main import people_read
from cloudhands.web.main import register
from cloudhands.web.main import registration_create


@unittest.skip("Not doing it yet")
class ACLTests(unittest.TestCase):

    def test_access_control(self):
        raise NotImplementedError


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

    @staticmethod
    def make_test_user(session):
        valid = session.query(RegistrationState).filter(
            RegistrationState.name == "valid").one()
        reg = Registration(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__)
        user = User(handle="Test User", uuid=uuid.uuid4().hex)
        hash = bcrypt.hashpw("TestPassw0rd", bcrypt.gensalt(12))
        now = datetime.datetime.utcnow()
        act = Touch(artifact=reg, actor=user, state=valid, at=now)
        pwd = BcryptedPassword(touch=act, value=hash)
        ea = EmailAddress(
            touch=act,
            value=cloudhands.web.main.authenticated_userid())
        session.add_all((pwd, ea))
        session.commit()
        return act

    @staticmethod
    def make_test_user_role_user(session):
        user = ServerTests.make_test_user(session).actor
        org = Organisation(
            uuid=uuid.uuid4().hex,
            name="TestOrg")
        provider = Provider(
            name="testcloud.io", uuid=uuid.uuid4().hex)
        userMp = Membership(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            organisation=org,
            role="user")

        # Make the authenticated user an admin
        active = session.query(
            MembershipState).filter(MembershipState.name == "active").one()
        now = datetime.datetime.utcnow()
        act = Touch(artifact=userMp, actor=user, state=active, at=now)
        session.add(act)
        session.commit()
        return act

    @staticmethod
    def make_test_user_role_admin(session):
        admin = ServerTests.make_test_user(session).actor
        org = Organisation(
            uuid=uuid.uuid4().hex,
            name="TestOrg")
        provider = Provider(
            name="testcloud.io", uuid=uuid.uuid4().hex)
        adminMp = Membership(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            organisation=org,
            role="admin")

        # Make the authenticated user an admin
        active = session.query(
            MembershipState).filter(MembershipState.name == "active").one()
        now = datetime.datetime.utcnow()
        act = Touch(artifact=adminMp, actor=admin, state=active, at=now)
        session.add(act)
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
            top_read(self.request)["info"]["versions"]["cloudhands.web"])
        self.assertEqual(
            cloudhands.common.__version__,
            top_read(self.request)["info"]["versions"]["cloudhands.common"])

class MembershipPageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.config.add_route("membership", "/membership")
        self.config.add_route("organisation", "/organisation")
        self.config.add_route("people", "/people")

    def test_authenticate_nonuser_raises_not_found(self):
        request = testing.DummyRequest()
        self.assertRaises(NotFound, authenticate_user, request)

    def test_authenticate_nonuser_attaches_userid(self):
        request = testing.DummyRequest()
        try:
            authenticate_user(request)
        except NotFound as e:
            self.assertEqual(
                cloudhands.web.main.authenticated_userid(), e.userId)

    def test_nonuser_membership_read_creates_user(self):

        def newuser_email(request=None):
            return "someone.new@somewhere.else.org"

        # Create an admin
        self.assertEqual(0, self.session.query(User).count())
        self.assertEqual(0, self.session.query(Membership).count())
        act = ServerTests.make_test_user_role_admin(self.session)
        org = act.artifact.organisation
        self.assertEqual(1, self.session.query(User).count())
        self.assertEqual(1, self.session.query(Membership).count())

        # Create a new invite
        request = testing.DummyRequest()
        request.matchdict.update({"org_name": org.name})
        self.assertRaises(HTTPFound, organisation_memberships_create, request)
        self.assertEqual(1, self.session.query(User).count())
        self.assertEqual(2, self.session.query(Membership).count())
        mship = self.session.query(
            Membership).join(Touch).join(State).join(Organisation).filter(
            Organisation.id == org.id).filter(State.name == "invite").one()

        testuser_email, cloudhands.web.main.authenticated_userid = (
            cloudhands.web.main.authenticated_userid, newuser_email)
        try:
            # New person visits membership
            request = testing.DummyRequest()
            request.matchdict.update({"mship_uuid": mship.uuid})
            reply = membership_read(request)

            # Check new user added
            self.assertEqual(2, self.session.query(User).count())
            self.assertTrue(self.session.query(EmailAddress).filter(
                EmailAddress.value == newuser_email()).first())
        finally:
            cloudhands.web.main.authenticated_userid = testuser_email

    def test_user_membership_update_post_returns_forbidden(self):
        act = ServerTests.make_test_user_role_user(self.session)
        mship = act.artifact
        request = testing.DummyRequest()
        request.matchdict.update({"mship_uuid": mship.uuid})
        self.assertRaises(Forbidden, membership_update, request)

    def test_admin_membership_update_post_adds_resources(self):
        dn = "cn=testadmin,ou=ceda,ou=People,o=hpc,dc=rl,dc=ac,dc=uk"
        uid = "2345"
        gid = "6200"
        key = "tu3+" * 100
        with tempfile.TemporaryDirectory() as td:
            Args = namedtuple("Arguments", ["index"])
            self.config.add_settings({"args": Args(td)})

            ix = create_index(td, **ldap_types)
            wrtr = ix.writer()
            wrtr.add_document(id=dn, uidNumber=uid, gidNumber=gid,
                              sshPublicKey=key)
            wrtr.commit()

            act = ServerTests.make_test_user_role_admin(self.session)
            self.assertEqual(2, self.session.query(Resource).count())
            mship = act.artifact
            request = testing.DummyRequest(post={"designator": dn})
            request.matchdict.update({"mship_uuid": mship.uuid})
            # NB: admin is updating his own membership here
            self.assertRaises(
                HTTPFound, membership_update, request)

            n = self.session.query(
                Resource).join(Touch).join(Membership).filter(
                Membership.id == mship.id).count()
            self.assertEqual(3, n)


class OrganisationPageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.config.add_route("organisation", "/organisation")

    def test_nonadmin_user_cannot_add_membership(self):
        act = ServerTests.make_test_user_role_user(self.session)
        org = act.artifact.organisation
        request = testing.DummyRequest()
        request.matchdict.update({"org_name": org.name})
        page = organisation_read(request)
        options = page["options"].values()
        mships = [i for i in options if "role" in i]
        self.assertTrue(mships)
        self.assertEqual(org.name, mships[0]["organisation"])
        invite = list(i for o in options if "_links" in o
                      for i in o["_links"] if i.name.startswith("Invit"))
        self.assertFalse(invite)

    def test_admin_user_can_add_membership(self):
        act = ServerTests.make_test_user_role_admin(self.session)
        admin = act.actor
        org = act.artifact.organisation
        request = testing.DummyRequest()
        request.matchdict.update({"org_name": org.name})
        page = organisation_read(request)
        options = page["options"].values()
        mships = [i for i in options if "role" in i]
        self.assertTrue(mships)
        self.assertEqual(org.name, mships[0]["organisation"])
        invite = next(i for o in options if "_links" in o
                      for i in o["_links"] if i.name.startswith("Invit"))
        self.assertTrue(invite)
        self.assertEqual(
            "/organisation/{}/memberships".format(org.name),
            invite.typ.format(invite.ref))

    def test_user_memberships_post_returns_forbidden(self):
        act = ServerTests.make_test_user_role_user(self.session)
        org = act.artifact.organisation
        request = testing.DummyRequest()
        request.matchdict.update({"org_name": org.name})
        self.assertRaises(Forbidden, organisation_memberships_create, request)

    def test_admin_memberships_post_returns_artifact_created(self):
        self.config.add_route("membership", "/membership")
        self.config.add_route("people", "/people")
        act = ServerTests.make_test_user_role_admin(self.session)
        org = act.artifact.organisation
        request = testing.DummyRequest()
        request.matchdict.update({"org_name": org.name})
        self.assertRaises(HTTPFound, organisation_memberships_create, request)


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
            people_read, self.request)

    def test_read_regions(self):
        create_index(self.td.name, **ldap_types)
        page = people_read(self.request)
        self.assertIn("info", page)
        self.assertIn("items", page)
        self.assertIn("options", page)
        self.assertIn("paths", page["info"])

    def test_search_form(self):
        create_index(self.td.name, **ldap_types)
        page = people_read(self.request)
        self.assertEqual(1, len(page["options"]))

    def test_user_search(self):
        ix = create_index(self.td.name, **ldap_types)
        wrtr = ix.writer()

        for i in range(10):
            wrtr.add_document(id=str(i), gecos="User {}".format(i))
        wrtr.commit()

        request = testing.DummyRequest({"description": "Loser"})
        page = people_read(request)
        self.assertEqual(0, len(page["items"]))

        request = testing.DummyRequest({"description": "User"})
        page = people_read(request)
        self.assertEqual(10, len(page["items"]))

    def test_user_items_offer_open_invitation(self):
        act = ServerTests.make_test_user_role_admin(self.session)
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
        page = people_read(request)
        items = page["items"].values()
        self.assertTrue(all("_links" in i for i in items))

class RegistrationPageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.config.add_route("register", "/register")
        self.config.add_route("registration", "/registration")

    def test_register_form(self):
        request = testing.DummyRequest()
        rv = register(request)
        options = [i for i in rv.get("options", {}).values() if "_links" in i]
        self.assertEqual(
            1, len([i for o in options for i in o["_links"]
            if i.rel == "create-form"]))

    def test_registration_create(self):
        request = testing.DummyRequest(
            {"handle": "newuser", "password": "th!swillb3myPa55w0rd",
            "email": "somebody@some.ac.uk"})
        self.assertRaises(HTTPFound, registration_create, request)

if __name__ == "__main__":
    unittest.main()
