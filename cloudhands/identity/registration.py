#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import uuid

import bcrypt

from cloudhands.common.fsm import RegistrationState

import cloudhands.common.schema
from cloudhands.common.schema import BcryptedPassword
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User


def handle_from_email(addrVal):
    return ' '.join(
        i.capitalize() for i in addrVal.split('@')[0].split('.'))


class NewPassword:
    """
    Adds a new password to a user account
    """
    def __init__(self, user, passwd, reg):
        self.user = user
        self.hash = bcrypt.hashpw(passwd, bcrypt.gensalt(12))
        self.reg = reg

    def match(self, attempt):
        return bcrypt.checkpw(attempt, self.hash)

    def __call__(self, session):
        newreg = session.query(
            RegistrationState).filter(
            RegistrationState.name=="pre_registration_person").one()
        now = datetime.datetime.utcnow()
        act = Touch(
            artifact=self.reg, actor=self.user, state=newreg, at=now)
        resource = BcryptedPassword(touch=act, value=self.hash)
        session.add(resource)
        session.commit()
        return act
