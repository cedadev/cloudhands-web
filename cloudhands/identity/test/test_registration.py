#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import sqlite3
import unittest
import uuid

from cloudhands.identity.registration import NewPassword

import cloudhands.common
from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

from cloudhands.common.fsm import RegistrationState

from cloudhands.common.schema import BcryptedPassword
from cloudhands.common.schema import Component
from cloudhands.common.schema import Provider
from cloudhands.common.schema import Registration
from cloudhands.common.schema import State
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User


class RegistrationLifecycleTests(unittest.TestCase):

    def setUp(self):
        self.session = Registry().connect(sqlite3, ":memory:").session
        initialise(self.session)
        self.reg = Registration(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__)
        self.session.add(self.reg)
        self.session.commit()

    def tearDown(self):
        Registry().disconnect(sqlite3, ":memory:")


class NewPasswordTests(RegistrationLifecycleTests):

    def setUp(self):
        super().setUp()
        self.system = Component(handle="System", uuid=uuid.uuid4().hex)
        self.user = User(handle=None, uuid=uuid.uuid4().hex)
        prepass = self.session.query(
            RegistrationState).filter(
            RegistrationState.name=="prepass").one()
        now = datetime.datetime.utcnow()
        act = Touch(artifact=self.reg, actor=self.system, state=prepass, at=now)
        self.session.add_all((act, self.system, self.user))
        self.session.commit()

    def test_bring_registration_to_confirmation(self):
        self.assertEqual("prepass", self.reg.changes[-1].state.name)
        password = "existsinmemory"
        act = NewPassword(self.user, password, self.reg)(self.session)
        self.session.add(act)
        self.session.commit()
        self.assertEqual("preconfirm", self.reg.changes[-1].state.name)

    @unittest.skip("TBD")
    def test_confirmation_from_invalid_state(self):
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
            act = NewPassword(actor, subs)(self.session)
            self.assertIs(None, act)
