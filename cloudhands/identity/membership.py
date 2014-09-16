#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import uuid

import cloudhands.common.factories
import cloudhands.common.schema
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.common.states import MembershipState


def handle_from_email(addrVal):
    return ' '.join(
        i.capitalize() for i in addrVal.split('@')[0].split('.'))


class Invitation():
    """
    :param object user: A :py:func:`cloudhands.common.schema.User` object.
    :param object org: A :py:func:`cloudhands.common.schema.Organisation`.
    """
    def __init__(self, user, org, handle, surname, emailAddr):
        self.user = user
        self.org = org
        self.handle = handle
        self.surname = surname
        self.emailAddr = emailAddr

    def __call__(self, session):
        """
        Attempts to create a new membership record for the organisation.

        If the `user` attribute is not privileged in the organisation, the
        operation will fail and `None` will be returned.

        :param object session:  A SQLALchemy database session.
        :returns: a :py:func:`cloudhands.common.schema.Touch` object.
        """
        prvlg = session.query(Membership).join(Touch).join(User).filter(
            User.id == self.user.id).filter(
            Membership.organisation == self.org).filter(
            Membership.role == "admin").first()
        if not prvlg or not prvlg.changes[-1].state.name == "active":
            return None

        mship = Membership(
            uuid=uuid.uuid4().hex,
            model=cloudhands.web.__version__,
            organisation=self.org,
            role="user")
        invite = session.query(MembershipState).filter(
            MembershipState.name == "created").one()
        now = datetime.datetime.utcnow()
        act = Touch(artifact=mship, actor=self.user, state=invite, at=now)
        session.add(act)

        guest = session.merge(cloudhands.common.factories.user(
            session, self.handle, self.surname))
        now = datetime.datetime.utcnow()
        act = Touch(artifact=mship, actor=guest, state=invite, at=now)
        session.add(act)
        session.commit()

        reg = cloudhands.common.factories.registration(
            session, guest, self.emailAddr, cloudhands.common.__version__)

        return act


class Activation():
    """
    :param object user: A :py:func:`cloudhands.common.schema.User` object.
    :param object mship: A :py:func:`cloudhands.common.schema.Membership`.
    :param object eAddr: A :py:func:`cloudhands.common.schema.EmailAddress`.
    """
    def __init__(self, mship, user=None):
        self.mship = mship
        self.user = user

    def __call__(self, session):
        """
        Activates the membership record for the organisation.

        :param object session:  A SQLALchemy database session.
        :returns: a :py:func:`cloudhands.common.schema.Touch` object.
        """
        active = session.query(
            MembershipState).filter(MembershipState.name == "active").one()
        now = datetime.datetime.utcnow()

        user = session.merge(self.user or self.mship.changes[1].actor)
        act = Touch(artifact=self.mship, actor=user, state=active, at=now)
        session.add(act)
        session.commit()
        return act


class MembershipAgent():
    pass
