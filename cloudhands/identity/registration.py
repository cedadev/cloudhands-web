#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import uuid

from cloudhands.common.fsm import RegistrationState

import cloudhands.common.schema
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User


def handle_from_email(addrVal):
    return ' '.join(
        i.capitalize() for i in addrVal.split('@')[0].split('.'))


class NewPassword:
    """
    Adds a password to a user account
    """
    def __init__(self, user, passwd, reg):
        self.user = user
        self.passwd = passwd
        self.reg = reg

    def __call__(self, session):
        if self.reg.changes[-1].state.name != "prepass":
            return None

        preconfirm = session.query(
            RegistrationState).filter(
            RegistrationState.name=="preconfirm").one()
        now = datetime.datetime.utcnow()
        act = Touch(
            artifact=self.reg, actor=self.user, state=preconfirm, at=now)
        #self.reg.changes.append(act)
        session.commit()
        return act
