#!/usr/bin/env python3
# encoding: UTF-8

from collections import namedtuple
import datetime
import operator
import re
import sqlite3
import tempfile
import textwrap
import unittest
import unittest.mock
import uuid

import bcrypt

from pyramid import testing
from pyramid.exceptions import Forbidden
from pyramid.exceptions import NotFound
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPInternalServerError
from pyramid.httpexceptions import HTTPNotFound

import cloudhands.common
from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

from cloudhands.common.schema import Appliance
from cloudhands.common.schema import BcryptedPassword
from cloudhands.common.schema import CatalogueItem
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Label
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import PosixUId
from cloudhands.common.schema import PosixUIdNumber
from cloudhands.common.schema import Provider
from cloudhands.common.schema import PublicKey
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Registration
from cloudhands.common.schema import Resource
from cloudhands.common.schema import State
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.common.states import MembershipState
from cloudhands.common.states import RegistrationState

import cloudhands.web
from cloudhands.web.indexer import create as create_index
from cloudhands.web.indexer import indexer
from cloudhands.web.indexer import ldap_types
from cloudhands.web.main import appliance_modify
from cloudhands.web.main import appliance_read
from cloudhands.web.main import authenticate_user
from cloudhands.web.main import login_read
from cloudhands.web.main import login_update
from cloudhands.web.main import membership_read
from cloudhands.web.main import membership_update
from cloudhands.web.main import organisation_appliances_create
from cloudhands.web.main import organisation_catalogue_read
from cloudhands.web.main import organisation_memberships_create
from cloudhands.web.main import organisation_read
from cloudhands.web.main import parser
from cloudhands.web.main import people_read
from cloudhands.web.main import register
from cloudhands.web.main import RegistrationForbidden
from cloudhands.web.main import registration_create
from cloudhands.web.main import registration_keys
from cloudhands.web.main import top_read

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
        self.assets = {
            "paths.assets": dict(
                css = "cloudhands.web:static/css",
                html = "cloudhands.web:static/html",
                img = "cloudhands.web:static/img",
                js = "cloudhands.web:static/js")
        }
        self.request = testing.DummyRequest()
        self.request.registry.settings = {"cfg": self.assets}
        self.config = testing.setUp(request=self.request)
        self.config.add_static_view(
            name="css", path="cloudhands.web:static/css")
        self.config.add_static_view(
            name="html", path="cloudhands.web:static/html")
        self.config.add_static_view(
            name="js", path="cloudhands.web:static/js")
        self.config.add_static_view(
            name="img", path="cloudhands.web:static/img")

    def tearDown(self):
        Registry().disconnect(sqlite3, ":memory:")

    @staticmethod
    def make_test_user(session):
        just_registered = session.query(RegistrationState).filter(
            RegistrationState.name == "pre_registration_inetorgperson_cn").one()
        reg = Registration(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__)
        user = User(handle="Test User", uuid=uuid.uuid4().hex)
        hash = bcrypt.hashpw("TestPassw0rd", bcrypt.gensalt(12))
        now = datetime.datetime.utcnow()
        act = Touch(artifact=reg, actor=user, state=just_registered, at=now)
        pwd = BcryptedPassword(touch=act, value=hash)
        ea = EmailAddress(
            touch=act,
            value=cloudhands.web.main.authenticated_userid())
        session.add_all((pwd, ea))
        session.commit()
        return act

    @staticmethod
    def make_test_user_role_user(session):
        session.add(
            Provider(
                name="testcloud.io", uuid=uuid.uuid4().hex)
        )
        user = ServerTests.make_test_user(session).actor
        org = Organisation(
            uuid=uuid.uuid4().hex,
            name="TestOrg")
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


class AppliancePageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.config.add_route(
            "appliance", "/appliance/{app_uuid}")
        self.config.add_route("organisation", "/organisation/{org_name}")
        self.config.add_route(
            "organisation_appliances", "/organisation/{org_name}/appliances")
        act = ServerTests.make_test_user_role_user(self.session)
        org = act.artifact.organisation
        self.session.add_all((
            CatalogueItem(
                uuid=uuid.uuid4().hex,
                name="nfs-client",
                description="Headless VM for file transfer operations",
                note=textwrap.dedent("""
                    <p>This VM runs CentOS 6.5 with a minimal amount of RAM and
                    no X server. It is used for file transfer operations from the
                    command line.</p>
                    """),
                logo="headless",
                organisation=org
            ),
            CatalogueItem(
                uuid=uuid.uuid4().hex,
                name="Web-Server",
                description="Headless VM with Web server",
                note=textwrap.dedent("""
                    <p>This VM runs Apache on CentOS 6.5.
                    It has 8GB RAM and 4 CPU cores.
                    It is used for hosting websites and applications with a
                    Web API.</p>
                    """),
                logo="headless",
                organisation=org
            )
        ))
        self.session.commit()

    def test_organisation_appliances_create(self):
        self.assertEqual(0, self.session.query(Appliance).count())
        org = self.session.query(Organisation).one()
        ci = self.session.query(CatalogueItem).first()
        self.assertIn(ci, org.catalogue)
        request = testing.DummyRequest(post={"uuid": ci.uuid})
        request.matchdict.update({"org_name": org.name})
        self.assertRaises(
            HTTPFound, organisation_appliances_create, request)
        self.assertEqual(1, self.session.query(Appliance).count())

    def test_organisation_appliances_create_then_view_appliance(self):
        self.test_organisation_appliances_create()
        self.assertEqual(1, self.session.query(Appliance).count())
        app = self.session.query(Appliance).one()
        request = testing.DummyRequest()
        request.matchdict.update({"app_uuid": app.uuid})
        page = appliance_read(request)
        items = list(page["items"].values())
        catalogueChoice = items[0]["_links"][0]
        self.assertEqual("collection", catalogueChoice.rel)
        blankLabel = items[1]
        self.assertIn("uuid", blankLabel)

    def test_appliance_read_with_missing_uuid(self):
        request = testing.DummyRequest()
        request.matchdict.update({"app_uuid": uuid.uuid4().hex})
        self.assertRaises(
            HTTPNotFound, appliance_read, request)

    def test_appliance_modify_validates_label(self):
        self.test_organisation_appliances_create()
        self.assertEqual(1, self.session.query(Appliance).count())
        self.assertEqual(0, self.session.query(Label).count())
        app = self.session.query(Appliance).one()
        request = testing.DummyRequest(post={"name": "No blanks"})
        request.matchdict.update({"app_uuid": app.uuid})
        self.assertRaises(
            HTTPBadRequest, appliance_modify, request)
        self.assertEqual("configuring", app.changes[-1].state.name)
 
    def test_appliance_modify_adds_label(self):
        self.test_organisation_appliances_create()
        self.assertEqual(1, self.session.query(Appliance).count())
        self.assertEqual(0, self.session.query(Label).count())
        app = self.session.query(Appliance).one()
        request = testing.DummyRequest(
            post={"name": "Test_name", "description": "Test description"})
        request.matchdict.update({"app_uuid": app.uuid})
        self.assertRaises(
            HTTPFound, appliance_modify, request)
        app = self.session.query(Appliance).one()
        self.assertEqual(1, self.session.query(Label).count())

    def test_appliance_label_permits_hyphens_in_name(self):
        self.test_organisation_appliances_create()
        self.assertEqual(1, self.session.query(Appliance).count())
        self.assertEqual(0, self.session.query(Label).count())
        app = self.session.query(Appliance).one()
        request = testing.DummyRequest(
            post={"name": "Test-name", "description": "Test description"})
        request.matchdict.update({"app_uuid": app.uuid})
        self.assertRaises(
            HTTPFound, appliance_modify, request)
        app = self.session.query(Appliance).one()
        self.assertEqual(1, self.session.query(Label).count())

    def test_appliance_appears_in_organisation(self):
        self.test_organisation_appliances_create()
        self.assertEqual(1, self.session.query(Appliance).count())
        self.assertEqual(0, self.session.query(Label).count())
        app = self.session.query(Appliance).one()
        request = testing.DummyRequest(
            post={"name": "Test_name", "description": "Test description"})
        request.matchdict.update({"app_uuid": app.uuid})
        self.assertRaises(
            HTTPFound, appliance_modify, request)
        app = self.session.query(Appliance).one()
        self.assertEqual(1, self.session.query(Label).count())
        request = testing.DummyRequest()
        request.matchdict.update({"org_name": app.organisation.name})
        page = organisation_read(request)
        self.assertEqual(1, len(page["items"]))


class CataloguePageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.config.add_route(
            "catalogue", "/organisation/{org_name}/catalogue")

    def test_no_options_seen_in_catalogue_view(self):
        act = ServerTests.make_test_user_role_user(self.session)
        org = act.artifact.organisation
        self.session.add_all((
            CatalogueItem(
                uuid=uuid.uuid4().hex,
                name="nfs-client",
                description="Headless VM for file transfer operations",
                note=textwrap.dedent("""
                    <p>This VM runs CentOS 6.5 with a minimal amount of RAM and
                    no X server. It is used for file transfer operations from the
                    command line.</p>
                    """),
                logo="headless",
                organisation=org
            ),
            CatalogueItem(
                uuid=uuid.uuid4().hex,
                name="Web-Server",
                description="Headless VM with Web server",
                note=textwrap.dedent("""
                    <p>This VM runs Apache on CentOS 6.5.
                    It has 8GB RAM and 4 CPU cores.
                    It is used for hosting websites and applications with a
                    Web API.</p>
                    """),
                logo="headless",
                organisation=org
            )
        ))
        self.session.commit()
        request = testing.DummyRequest()
        request.matchdict.update({"org_name": org.name})
        page = organisation_catalogue_read(request)
        self.assertFalse(list(page["options"].values()))
        items = list(page["items"].values())
        self.assertEqual(2, len(items))
        self.assertTrue(any(i["name"] == "nfs-client" for i in items))
        self.assertTrue(any(i["name"] == "Web-Server" for i in items))

 
class LoginAndOutTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.config.add_route("top", "/")

    def test_we_can_read_login_from_test(self):
        request = testing.DummyRequest()
        self.assertTrue(login_read(request))

    def test_we_can_log_in_from_test(self):
        act = ServerTests.make_test_user_role_user(self.session)
        request = testing.DummyRequest(
            post={"username": "Test User", "password": "TestPassw0rd"})
        self.assertRaises(HTTPFound, login_update, request)

    def test_registration_lifecycle_pre_registration_inet_orgperson_cn(self):
        act = ServerTests.make_test_user_role_user(self.session)
        request = testing.DummyRequest(
            post={"username": "Test User", "password": "TestPassw0rd"})
        self.assertRaises(HTTPFound, login_update, request)
        self.assertEqual(1, self.session.query(User).count())
        self.assertEqual(1, self.session.query(Registration).count())
        self.assertEqual(1, self.session.query(BcryptedPassword).count())
        self.assertEqual(1, self.session.query(EmailAddress).count())
        self.assertEqual(0, self.session.query(PosixUId).count())
        self.assertEqual(0, self.session.query(PosixUIdNumber).count())

        reg = self.session.query(Registration).one()
        self.assertEqual(
            "pre_registration_inetorgperson_cn",
            reg.changes[-1].state.name)

    def test_registration_lifecycle_pre_registration_inet_orgperson_cn(self):
        act = ServerTests.make_test_user_role_user(self.session)
        user = act.actor
        prvdr = self.session.query(Provider).one()
        reg = self.session.query(Registration).one()
        
        state = self.session.query(State).filter(
            State.name == "pre_user_posixaccount").one()
        now = datetime.datetime.utcnow()
        act = Touch(artifact=reg, actor=user, state=state, at=now)
        self.session.add(
            PosixUId(value="testuser", touch=act, provider=prvdr))
        self.session.commit()

        request = testing.DummyRequest(
            post={"username": "Test User", "password": "TestPassw0rd"})

        noUidNumber = unittest.mock.patch(
            "cloudhands.web.main.next_uidnumber",
            autospec=True, return_value = 7654321)
        noPasswordChange = unittest.mock.patch(
            "cloudhands.web.main.change_password",
            autospec=True, return_value = 0)
        with noUidNumber, noPasswordChange:
            self.assertRaises(HTTPFound, login_update, request)

        self.assertEqual(1, self.session.query(User).count())
        self.assertEqual(1, self.session.query(Registration).count())
        self.assertEqual(1, self.session.query(BcryptedPassword).count())
        self.assertEqual(1, self.session.query(EmailAddress).count())
        self.assertEqual(1, self.session.query(PosixUId).count())
        self.assertEqual(1, self.session.query(PosixUIdNumber).count())

        self.assertEqual(
            "pre_user_ldappublickey",
            reg.changes[-1].state.name)


class MembershipPageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.config.add_route("membership", "/membership/{mship_uuid}")
        self.config.add_route("registration", "/registration/{reg_uuid}")
        #self.config.add_route("organisation", "/organisation")
        #self.config.add_route("people", "/people")

    def test_authenticate_nonuser_raises_not_found(self):
        request = testing.DummyRequest()
        self.assertRaises(NotFound, authenticate_user, request, NotFound)

    def test_authenticate_nonuser_attaches_userid(self):
        request = testing.DummyRequest()
        try:
            authenticate_user(request)
        except NotFound as e:
            self.assertEqual(
                cloudhands.web.main.authenticated_userid(), e.userId)

    def test_guest_membership_read_activates_membership(self):

        def newuser_email(request=None):
            return "someone.new@somewhere.else.org"

        # Create an admin
        self.assertEqual(0, self.session.query(User).count())
        self.assertEqual(0, self.session.query(Membership).count())
        act = ServerTests.make_test_user_role_admin(self.session)
        admin = act.actor
        org = act.artifact.organisation
        self.assertEqual(1, self.session.query(User).count())
        self.assertEqual(1, self.session.query(Registration).count())
        self.assertEqual(1, self.session.query(Membership).count())

        # Create a new invite
        request = testing.DummyRequest(post={
            "username": "someonew",
            "surname": "New",
            "email": newuser_email()})
        request.registry.settings = {"cfg": self.assets}
        request.matchdict.update({"org_name": org.name})
        self.assertRaises(HTTPFound, organisation_memberships_create, request)
        self.assertEqual(2, self.session.query(User).count())
        self.assertEqual(2, self.session.query(Registration).count())
        self.assertEqual(2, self.session.query(Membership).count())
        mship = self.session.query(
            Membership).join(Touch).join(State).join(Organisation).filter(
            Organisation.id == org.id).filter(State.name == "created").one()

        testuser_email, cloudhands.web.main.authenticated_userid = (
            cloudhands.web.main.authenticated_userid, newuser_email)
        try:
            # Email is sent
            invited = self.session.query(MembershipState).filter(
                MembershipState.name == "invited").one()
            act = Touch(
                artifact=mship, actor=admin, state=invited,
                at=datetime.datetime.utcnow())
            self.session.add(act)
            self.session.commit()

            # New person visits membership
            request = testing.DummyRequest()
            request.matchdict.update({"mship_uuid": mship.uuid})

            self.assertRaises(HTTPFound, membership_read, request)

            # Check new user added
            self.assertEqual("active", mship.changes[-1].state.name)
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
        request = testing.DummyRequest(post={
            "username": "someonew",
            "surname": "New",
            "email": "someone@somewhere.net"})
        request.matchdict.update({"org_name": org.name})
        self.assertRaises(Forbidden, organisation_memberships_create, request)

    def test_admin_memberships_post_returns_artifact_created(self):
        self.config.add_route("membership", "/membership")
        self.config.add_route("people", "/people")
        act = ServerTests.make_test_user_role_admin(self.session)
        org = act.artifact.organisation
        request = testing.DummyRequest(post={
            "username": "someonew",
            "surname": "New",
            "email": "someone@somewhere.net"})
        request.registry.settings = {"cfg": self.assets}
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

class RegistrationPageTests(ServerTests):

    def setUp(self):
        super().setUp()
        self.config.add_route("top", "/")
        self.config.add_route("register", "/registration")
        self.config.add_route("registration", "/registration/{reg_uuid}")
        self.config.add_route(
            "registration_keys", "/registration/{reg_uuid}/key")

    def test_register_form(self):
        request = testing.DummyRequest()
        rv = register(request)
        options = [i for i in rv.get("options", {}).values() if "_links" in i]
        self.assertEqual(
            1, len([i for o in options for i in o["_links"]
            if i.rel == "create-form"]))

    def test_registration_create(self):
        request = testing.DummyRequest(
            {"username": "new_user", "password": "th!swillb3myPa55w0rd",
            "email": "somebody@some.ac.uk"})
        self.assertRaises(HTTPFound, registration_create, request)

    def test_registration_create_duplicate(self):
        request = testing.DummyRequest(
            {"username": "new_user", "password": "th!swillb3myPa55w0rd",
            "email": "somebody@some.ac.uk"})
        try:
            registration_create(request)
        except HTTPFound:
            pass
        self.assertRaises(RegistrationForbidden, registration_create, request)

    def test_registration_key_bad_prefix(self):
        self.assertEqual(0, self.session.query(PublicKey).count())
        act = ServerTests.make_test_user(self.session)
        reg = self.session.query(Registration).one()
        val = textwrap.dedent("""
            AAAAB3NzaC1yc2EAAAABIwAAAQEAuOg/gIR9szQ0IcPjqD1jlY9enJETy
            ppW39MAH0WV1LqR+/ULulG4uBUS/HBwvS7ggu3P6mj4i2hH9Kz9JGwnkuhxMJu3d/
            b/2Z7/1hBkQls5BKTzSoYnPCVYfvPyNXzRHEcRPjyfGcrIYz2CU4g5Ei2f0IgRnga
            mDQrTU33QLosoaJqfw0pvX2SdFyFRmJkY6vH7j66ciXl2bfUUdf1KaoadkD+n59U6
            EiURrholSlaZp0gECjx0dM4mZUD0DqjWGll0NmnM4NIpCl+lTOrFLicJBgPuAnsrq
            p8HjGEHweRoPwFkKpcPkfyV+k0o/bltu3Lyd8KLJrVzYAUXRnLRpw== dehaynes@
            snow.badc.rl.ac.uk""").replace("\n", "")
        request = testing.DummyRequest({"value": val})
        request.matchdict.update({"reg_uuid": reg.uuid})
        self.assertRaises(HTTPBadRequest, registration_keys, request)
        self.assertEqual(0, self.session.query(PublicKey).count())

    def test_registration_key_bad_suffix(self):
        self.assertEqual(0, self.session.query(PublicKey).count())
        act = ServerTests.make_test_user(self.session)
        reg = self.session.query(Registration).one()
        val = textwrap.dedent("""
            ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAuOg/gIR9szQ0IcPjqD1jlY9enJETy
            ppW39MAH0WV1LqR+/ULulG4uBUS/HBwvS7ggu3P6mj4i2hH9Kz9JGwnkuhxMJu3d/
            b/2Z7/1hBkQls5BKTzSoYnPCVYfvPyNXzRHEcRPjyfGcrIYz2CU4g5Ei2f0IgRnga
            mDQrTU33QLosoaJqfw0pvX2SdFyFRmJkY6vH7j66ciXl2bfUUdf1KaoadkD+n59U6
            EiURrholSlaZp0gECjx0dM4mZUD0DqjWGll0NmnM4NIpCl+lTOrFLicJBgPuAnsrq
            p8HjGEHweRoPwFkKpcPkfyV+k0o/bltu3Lyd8KLJrVzYAUXRnLRpw==
            """).replace("\n", "")
        request = testing.DummyRequest({"value": val})
        request.matchdict.update({"reg_uuid": reg.uuid})
        self.assertRaises(HTTPBadRequest, registration_keys, request)
        self.assertEqual(0, self.session.query(PublicKey).count())

    def test_registration_key_valid(self):
        self.assertEqual(0, self.session.query(PublicKey).count())
        act = ServerTests.make_test_user(self.session)
        reg = self.session.query(Registration).one()
        val = textwrap.dedent("""
            ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAuOg/gIR9szQ0IcPjqD1jlY9enJETy
            ppW39MAH0WV1LqR+/ULulG4uBUS/HBwvS7ggu3P6mj4i2hH9Kz9JGwnkuhxMJu3d/
            b/2Z7/1hBkQls5BKTzSoYnPCVYfvPyNXzRHEcRPjyfGcrIYz2CU4g5Ei2f0IgRnga
            mDQrTU33QLosoaJqfw0pvX2SdFyFRmJkY6vH7j66ciXl2bfUUdf1KaoadkD+n59U6
            EiURrholSlaZp0gECjx0dM4mZUD0DqjWGll0NmnM4NIpCl+lTOrFLicJBgPuAnsrq
            p8HjGEHweRoPwFkKpcPkfyV+k0o/bltu3Lyd8KLJrVzYAUXRnLRpw== dehaynes@
            snow.badc.rl.ac.uk""").replace("\n", "")
        request = testing.DummyRequest({"value": val})
        request.matchdict.update({"reg_uuid": reg.uuid})
        self.assertRaises(HTTPFound, registration_keys, request)
        self.assertEqual(1, self.session.query(PublicKey).count())

if __name__ == "__main__":
    unittest.main()
