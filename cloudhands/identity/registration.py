#!/usr/bin/env python3
# encoding: UTF-8

import datetime
import uuid

import bcrypt

import cloudhands.common.schema
from cloudhands.common.schema import BcryptedPassword
from cloudhands.common.schema import Membership
from cloudhands.common.schema import PosixUIdNumber
from cloudhands.common.schema import PublicKey
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.common.states import RegistrationState


__doc__ = """


.. graphviz::

   digraph registration {
    center = true;
    compound = true;
    nodesep = 0.6;
    edge [decorate=true,labeldistance=3,labelfontname=helvetica,
        labelfontsize=10,labelfloat=false];

    subgraph cluster_web {
        label = "Web";
        style = filled;
        labeljust = "l";
        node [shape=ellipse];
        "Set LDAP password" [shape=circle,width=0.8,fixedsize=true];
        PRE_USER_LDAPPUBLICKEY [shape=box];
        PRE_REGISTRATION_INETORGPERSON_CN [shape=box];
        PRE_REGISTRATION_INETORGPERSON_CN -> "Set LDAP password" [style=invis];
        "Set LDAP password" -> "BcryptedPassword" [style=invis];
        "BcryptedPassword" -> "PosixUIdNumber" [style=invis];
        "PosixUIdNumber" -> "PosixGIdNumber" [style=invis];
        "PosixGIdNumber" -> PRE_USER_LDAPPUBLICKEY [style=invis];
         PRE_USER_LDAPPUBLICKEY -> "PublicKey"[style=invis];
        "PublicKey" -> PRE_USER_LDAPPUBLICKEY [style=invis];
    }

    subgraph cluster_identity {
        label = "LDAP client";
        node [shape=box];
        "PosixUId" [shape=ellipse];
        "Write CN" [shape=circle,width=0.8,fixedsize=true];
        "Write key" [shape=circle,width=0.8,fixedsize=true];
        "Write CN" -> "PosixUId" [style=invis];
        "PosixUId" -> PRE_USER_POSIXACCOUNT [style=invis];
        PRE_USER_POSIXACCOUNT -> "Write key" [style=invis];
        "Write key" -> VALID [style=invis];
    }

    subgraph cluster_observer {
        label = "Observer";
        node [shape=box];
        "Monitor" [shape=circle];
        "PublicKey ?" [shape=diamond];
        "Monitor" -> PRE_REGISTRATION_INETORGPERSON [style=invis];
        "Monitor" -> "PublicKey ?" [style=invis];
    }

    subgraph cluster_emailer {
        label = "Emailer";
        "TimeInterval" [shape=ellipse];
        "Send" [shape=circle,width=0.5,fixedsize=true];
        "TimeInterval" -> "Send" [style=invis];
    }

    subgraph cluster_admin {
        label = "Admin";
        style = filled;
        labeljust = "l";
        node [shape=ellipse];
        PRE_REGISTRATION_PERSON [shape=box];
        "User" -> "Registration" [style=invis];
        "Registration" -> "EmailAddress" [style=invis];
        "EmailAddress" -> PRE_REGISTRATION_PERSON [style=invis];
    }

    "Start" [shape=point];
    "Guest" [shape=circle];
    "Start" -> User [style=solid,arrowhead=odot];
    "User" -> "Registration" [style=solid,arrowhead=odot];
    "Registration" -> "EmailAddress" [style=solid,arrowhead=odot];
    "EmailAddress" -> PRE_REGISTRATION_PERSON [style=solid,arrowhead=tee];
    PRE_REGISTRATION_PERSON -> "Monitor" [style=dashed,arrowhead=vee];
    PRE_REGISTRATION_INETORGPERSON_CN -> "Write CN"
        [style=dashed,arrowhead=vee];
    "Write CN" -> "PosixUId" [style=solid,arrowhead=odot];
    "PosixUId" -> PRE_USER_POSIXACCOUNT [style=solid,arrowhead=tee];
    PRE_USER_POSIXACCOUNT -> "PosixUIdNumber"
        [taillabel="[POST /login]",style=dashed,arrowhead=odot];
    "Set LDAP password" -> "BcryptedPassword"
        [style=solid,arrowhead=odot];
    "PosixUIdNumber" -> "PosixGIdNumber" [style=solid,arrowhead=odot];
    "PosixGIdNumber" -> PRE_USER_LDAPPUBLICKEY [style=solid,arrowhead=tee];
    PRE_USER_LDAPPUBLICKEY -> "Monitor" [style=dashed,arrowhead=vee];
    PRE_USER_LDAPPUBLICKEY -> "PublicKey"
        [taillabel="[POST /registration/{uuid}/keys]",style=dashed,arrowhead=odot];
    "PublicKey" -> PRE_USER_LDAPPUBLICKEY [style=dashed,arrowhead=tee];
    "Monitor" -> "PublicKey ?" [style=solid,arrowhead=vee];
    "PublicKey ?" -> "Write key" [taillabel="Y",style=solid,arrowhead=vee];
    "Write key" -> VALID [style=solid,arrowhead=vee];
    "Monitor" -> PRE_REGISTRATION_INETORGPERSON  [style=solid,arrowhead=tee];
    PRE_REGISTRATION_INETORGPERSON -> "TimeInterval"
        [style=solid,arrowhead=odot];
    "TimeInterval" -> "Send" [style=solid,arrowhead=none];
    "Send" -> "Guest" [style=dotted,arrowhead=vee];
    "Guest" -> PRE_REGISTRATION_INETORGPERSON_CN
        [taillabel="[GET /registration/{uuid}]",style=dotted,arrowhead=tee];
    "Guest" -> "Set LDAP password"
        [taillabel="[POST /registration/{uuid}/passwords]",style=dotted,arrowhead=tee];
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

    def match(self, attempt):
        return bcrypt.checkpw(attempt, self.hash)

    def __call__(self, session):
        newreg = session.query(
            RegistrationState).filter(
            RegistrationState.name=="pre_registration_inetorgperson").one()
        ts = datetime.datetime.utcnow()
        act = Touch(
            artifact=self.reg, actor=self.user, state=newreg, at=ts)
        resource = BcryptedPassword(touch=act, value=self.hash)
        session.add(resource)
        session.commit()
        return act


class NewAccount:
    """
    Adds a posix account to a user registration
    """
    def __init__(self, user, uidNumber:int, reg):
        self.user = user
        self.uidNumber = uidNumber
        self.reg = reg

    def __call__(self, session):
        nextState = "user_posixaccount"
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
