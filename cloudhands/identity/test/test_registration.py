#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import sqlite3
import unittest
import uuid

from cloudhands.identity.registration import NewPassword
from cloudhands.identity.registration import from_pool

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


class UidNumberTests(unittest.TestCase):

    def test_pool_allocation(self):
        pool = set(range(0, 10))
        taken = {0, 1, 2, 9 }
        self.assertEqual(3, next(from_pool(pool, taken)))

    def test_pool_allocation_none_taken(self):
        pool = {7, 5, 9 }
        self.assertEqual(5, next(from_pool(pool)))

    def test_pool_exactly_taken(self):
        pool = set(range(0, 10))
        taken = pool
        self.assertRaises(StopIteration, next, from_pool(pool, taken))

    def test_pool_over_taken(self):
        pool = set(range(0, 10))
        taken = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}
        self.assertRaises(StopIteration, next, from_pool(pool, taken))


class NewPasswordTests(RegistrationLifecycleTests):

    def setUp(self):
        super().setUp()
        self.system = Component(handle="System", uuid=uuid.uuid4().hex)
        self.user = User(handle=None, uuid=uuid.uuid4().hex)
        preconfirm = self.session.query(
            RegistrationState).filter(
            RegistrationState.name=="pre_registration_inetorgperson").one()
        now = datetime.datetime.utcnow()
        act = Touch(artifact=self.reg, actor=self.system, state=preconfirm, at=now)
        self.session.add_all((act, self.system, self.user))
        self.session.commit()

    def test_bring_registration_to_confirmation(self):
        self.assertEqual("pre_registration_inetorgperson", self.reg.changes[-1].state.name)
        password = "existsinmemory"
        op = NewPassword(self.user, password, self.reg)
        act = op(self.session)
        self.assertEqual("pre_registration_person", self.reg.changes[-1].state.name)
        self.assertTrue(self.session.query(BcryptedPassword).count())
        self.assertTrue(op.match(password))
        self.assertFalse(op.match(str(reversed(password))))

    def test_registration_from_any_state(self):
        self.test_bring_registration_to_confirmation()
        password = "existsinmemory"
        op = NewPassword(self.user, password, self.reg)
        act = op(self.session)
        self.assertIsInstance(act, Touch)
