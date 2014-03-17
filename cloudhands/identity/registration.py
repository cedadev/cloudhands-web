#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import uuid
from cloudhands.common.fsm import MembershipState

import cloudhands.common.schema
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User


def handle_from_email(addrVal):
    return ' '.join(
        i.capitalize() for i in addrVal.split('@')[0].split('.'))


class Password:
    """
    Adds a password to a user account
    """
    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd

    def __call__(self, session):
        if self.subs.changes[-1].state.name != "prepass":
            return None

        active = session.query(
            SubscriptionState).filter(
            SubscriptionState.name=="active").one()
        now = datetime.datetime.utcnow()
        act = Touch(
            artifact=self.subs, actor=self.actor, state=active, at=now)
        self.subs.changes.append(act)
        session.commit()
        return act
