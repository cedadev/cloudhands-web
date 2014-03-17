#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import sqlite3
import unittest
import uuid

from cloudhands.identity.registration import Password

import cloudhands.common
from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

from cloudhands.common.fsm import RegistrationState

from cloudhands.common.schema import BcryptedPassword
from cloudhands.common.schema import Component
from cloudhands.common.schema import Provider
from cloudhands.common.schema import Registration
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User


class RegistrationLifecycleTests(unittest.TestCase):

    def setUp(self):
        self.session = Registry().connect(sqlite3, ":memory:").session
        initialise(self.session)
        self.session.commit()

    def tearDown(self):
        Registry().disconnect(sqlite3, ":memory:")


class PasswordTests(RegistrationLifecycleTests):

    def setUp(self):
        super().setUp()
        self.user = User(handle=None, uuid=uuid.uuid4().hex)
        self.session.add(self.user)
        self.session.commit()

    def test_bring_registration_to_confirmation(self):
        actor = Component(handle="Maintenence", uuid=uuid.uuid4().hex)
        prepass = self.session.query(
            RegistrationState).filter(
            RegistrationState.name=="prepass").one()
        offline = [i for i in self.org.subscriptions
            if i.changes[-1].state is prepass]
        self.assertEqual(1, len(offline))
        for subs in offline:
            act = Password(actor, subs)(self.session)
            self.assertIs(self.subs, act.artifact)
            self.assertEqual("unchecked", act.state.name)

    def test_confirmation_from_invalid_state(self):
        actor = Component(handle="Maintenence", uuid=uuid.uuid4().hex)
        prepass = self.session.query(
            RegistrationState).filter(
            RegistrationState.name=="prepass").one()
        preconfirm = self.session.query(
            RegistrationState).filter(
            RegistrationState.name=="preconfirm").one()
        offline = [i for i in self.org.subscriptions
            if i.changes[-1].state is prepass]
        self.assertEqual(1, len(offline))
        now = datetime.datetime.utcnow()
        self.session.add(
            Touch(artifact=offline[0], actor=actor, state=preconfirm, at=now))
        self.session.commit()
        for subs in offline:
            act = Password(actor, subs)(self.session)
            self.assertIs(None, act)
