#!/usr/bin/env python3
#   encoding: UTF-8

import datetime
import logging
import uuid

from cloudhands.common.fsm import MembershipState

import cloudhands.common.schema
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Host
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Resource
from cloudhands.common.schema import State
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

__doc__ = """
Common functions for interacting with the schema.
"""


def handle_from_email(addrVal):
    return ' '.join(
        i.capitalize() for i in addrVal.split('@')[0].split('.'))


def create_user_from_email(session, addrVal, handle, invitation):
    """
    Creates a new user account from an email address and an invitation.
    The sequence of operations is:

    1.  Create a User record.
    2.  Create an EmailAddress resource
    3.  Touch the invitation with the user, the email, and a state of `active`.

    :param object session:  A SQLALchemy database session.
    :param string addrVal:   The user's email address.
    :param string handle:   Becomes the user's handle. If not supplied,
                            handle is constructed from the `addrVal`.
    :param object invitation: A Membership object.
    :returns: The newly created User object.
    """
    log = logging.getLogger("cloudhands.common.tricks")

    user = User(handle=handle, uuid=uuid.uuid4().hex)
    try:
        session.add(user)
        session.commit()
    except Exception as e:
        session.rollback()
        log.warning("User with handle '{}' exists".format(handle))
        return None

    active = session.query(
        MembershipState).filter(MembershipState.name == "active").one()
    now = datetime.datetime.utcnow()

    activation = Touch(artifact=invitation, actor=user, state=active, at=now)
    invitation.changes.append(activation)
    ea = EmailAddress(
        value=addrVal, touch=activation, provider=addrVal.split('@')[1])
    session.add(ea)
    session.commit()
    return user


def allocate_ip(session, host, ipAddr, provider="unknown"):
    session.query(IPAddress).filter(IPAddress.value == ipAddr).delete()

    now = datetime.datetime.utcnow()
    recent = host.changes[-1]
    act = Touch(artifact=host, actor=recent.actor, state=recent.state, at=now)
    host.changes.append(act)
    ip = IPAddress(value=ipAddr, touch=act, provider=provider)
    session.add(ip)
    session.commit()
    return ip
