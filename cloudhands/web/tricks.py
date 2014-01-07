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
