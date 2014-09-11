#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import uuid

import bcrypt

from cloudhands.common.fsm import RegistrationState

import cloudhands.common.schema
from cloudhands.common.schema import BcryptedPassword
from cloudhands.common.schema import Membership
from cloudhands.common.schema import PosixUIdNumber
from cloudhands.common.schema import PublicKey
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User


__doc__ = """


.. graphviz::

   digraph registration {
    center = true;
    compound = true;
    nodesep = 0.6;
    edge [decorate,labeldistance=3,labelfontname=helvetica,
        labelfontsize=10,labelfloat=false];

    subgraph cluster_web {
        label = "Web";
        node [shape=box];
        PRE_PROVISION_INETORGPERSON_CN -> "Set LDAP password" [style=invis];
        "Set LDAP password" -> "PublicKey ?" [style=invis];
        "PublicKey ?" -> PRE_USER_LDAPPUBLICKEY [style=invis];
    }

    subgraph cluster_identity {
        label = "Identity";
        style = filled;
        node [shape=box];
        "Write CN" -> "PosixUId" [style=invis];
        "PosixUId" -> PRE_USER_POSIXACCOUNT [style=invis];
        PRE_USER_POSIXACCOUNT -> "Write UId" [style=invis];
        "Write UId" -> VALID [style=invis];
    }

    subgraph cluster_observer {
        label = "Observer";
        style = filled;
        node [shape=box];
        "Monitor" -> PRE_REGISTRATION_INETORGPERSON [style=invis];
    }

    subgraph cluster_emailer {
        label = "Emailer";
        style = filled;
        "TimeInterval" [shape=ellipse];
        "Send email" [shape=circle];
        "TimeInterval" -> "Send email" [style=invis];
    }

    subgraph cluster_admin {
        label = "Admin";
        style = filled;
        node [shape=ellipse];
        PRE_REGISTRATION_PERSON [shape=box];
        "User" -> "Registration" [style=invis];
        "Registration" -> "EmailAddress" [style=invis];
        "EmailAddress" -> PRE_REGISTRATION_PERSON [style=invis];
    }

    PRE_PROVISION_INETORGPERSON_CN -> "Write CN" [taillabel="GET",style=dashed,arrowhead=none];
   }
"""

def handle_from_email(addrVal):
    return ' '.join(
        i.capitalize() for i in addrVal.split('@')[0].split('.'))


def from_pool(pool:set, taken:set=set()):
    return iter(sorted(pool - taken))


class NewPassword:
    """
    Adds a new password to a user registration
    """
    def __init__(self, user, passwd, reg):
        self.user = user
        self.hash = bcrypt.hashpw(passwd, bcrypt.gensalt(12))
        self.reg = reg
        self.offset = datetime.timedelta()

    def match(self, attempt):
        return bcrypt.checkpw(attempt, self.hash)

    def __call__(self, session):
        newreg = session.query(
            RegistrationState).filter(
            RegistrationState.name=="pre_registration_person").one()
        ts = datetime.datetime.utcnow() - self.offset
        act = Touch(
            artifact=self.reg, actor=self.user, state=newreg, at=ts)
        resource = BcryptedPassword(touch=act, value=self.hash)
        session.add(resource)
        session.commit()
        return act

#TODO: remove (bad idea)
class AgedPassword(NewPassword):

    def __init__(self, user, passwd, reg, offset):
        super().__init__()
        self.offset = offset


class NewAccount:
    """
    Adds a posix account to a user registration
    """
    def __init__(self, user, uidNumber:int, reg):
        self.user = user
        self.uidNumber = uidNumber
        self.reg = reg

    def __call__(self, session):
        nextState = "valid" if any(
            r for c in self.reg.changes for r in c.resources
            if isinstance(r, PublicKey)) else "pre_user_ldappublickey"
        state = session.query(
            RegistrationState).filter(
            RegistrationState.name == nextState).one()

        now = datetime.datetime.utcnow()
        act = Touch(
            artifact=self.reg, actor=self.user, state=state, at=now)
        resource = PosixUIdNumber(value=self.uidNumber, touch=act, provider=None)
        session.add(resource)
        session.commit()
        return act
