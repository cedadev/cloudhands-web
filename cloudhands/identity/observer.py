#!/usr/bin/env python
# encoding: UTF-8

import argparse
import asyncio
import datetime
import logging
import platform
import sqlite3
import sys
import time

from sqlalchemy import desc

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.schema import Component
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import LDAPAttribute
from cloudhands.common.schema import Membership
from cloudhands.common.schema import PosixUId
from cloudhands.common.schema import PosixUIdNumber
from cloudhands.common.schema import PublicKey
from cloudhands.common.schema import Registration
from cloudhands.common.schema import State
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User
from cloudhands.common.states import MembershipState
from cloudhands.common.states import RegistrationState

from cloudhands.identity.ldap import LDAPProxy
from cloudhands.identity.ldap import LDAPRecord
from cloudhands.identity.ldap import RecordPatterns

__doc__ = """
This process performs tasks to process Registrations to the JASMIN cloud.
"""


class Observer:

    _shared_state = {}

    def __init__(self, emailQ, ldapQ, args, config):
        self.__dict__ = self._shared_state
        if not hasattr(self, "tasks"):
            self.emailQ = emailQ
            self.ldapQ = ldapQ
            self.args = args
            self.tasks = [
                asyncio.Task(self.mailer()),
                asyncio.Task(self.publish_userhandle()),
                asyncio.Task(self.publish_uidnumber()),
                asyncio.Task(self.publish_sshpublickey()),
                asyncio.Task(self.publish_user_membership()),
                asyncio.Task(self.publish_uuid())
            ]

    @asyncio.coroutine
    def mailer(self):
        log = logging.getLogger(__name__ + ".mailer")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        invited = session.query(MembershipState).filter(
            RegistrationState.name == "invited").one()
        while True:
            unsent = [
                i for i in session.query(Membership).all()
                if i.changes[-1].state.name == "created"]
            for mship in unsent:
                try:
                    user = mship.changes[-1].actor
                    email = session.query(EmailAddress).join(Touch).join(User).filter(
                        User.id == user.id).order_by(desc(Touch.at)).first().value
                    host = "http://{}:8080".format(platform.node()) #  FIXME
                except Exception as e:
                    log.error(e)
                    break
                else:
                    msg = (email, host, mship.uuid)
                    log.debug(msg)
                    now = datetime.datetime.utcnow()
                    act = Touch(artifact=mship, actor=actor, state=invited, at=now)
                    yield from self.emailQ.put(msg)
                    try:
                        session.add(act)
                        session.commit()
                    except Exception as e:
                        log.error(e)
                        session.rollback()
                        break

            log.debug("Waiting for {}s".format(self.args.interval))
            yield from asyncio.sleep(self.args.interval)

    @asyncio.coroutine
    def publish_userhandle(self):
        log = logging.getLogger(__name__ + ".name")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        while True:
            try:
                unpublished = [
                    r for r in session.query(Registration).all() if (
                    r.changes[-1].state.name ==
                    "pre_registration_inetorgperson")]

                for reg in unpublished:
                    user = reg.changes[0].actor
                    surname = user.surname or "UNKNOWN"
                    record = LDAPRecord(
                        dn={("cn={},ou=jasmin2,"
                        "ou=People,o=hpc,dc=rl,dc=ac,dc=uk").format(user.handle)},
                        objectclass={"top", "person", "organizationalPerson",
                            "inetOrgPerson"},
                        description={"cluster:jasmin-login"},
                        cn={user.handle},
                        sn={surname},
                    )
                    resources = [
                        r for i in reg.changes for r in i.resources
                        if isinstance(r, EmailAddress)]
                    if resources:
                        record["mail"].add(resources[0].value)
                    msg = LDAPProxy.WriteCommonName(record, reg.uuid)
                    yield from self.ldapQ.put(msg)
                    session.expire(reg)
            except Exception as e:
                log.error(e)

            log.debug("Waiting for {}s".format(self.args.interval))
            yield from asyncio.sleep(self.args.interval)

    @asyncio.coroutine
    def publish_uuid(self):
        log = logging.getLogger(__name__ + ".uuid")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        while True:
            try:
                unpublished = [
                    r for r in session.query(Registration).all() if (
                    r.changes[-1].state.name ==
                    "pre_user_inetorgperson_dn")]

                for reg in unpublished:
                    # TODO: Get latest PosixUId resource
                    try:
                        uid = next(r for c in reversed(reg.changes)
                            for r in c.resources if isinstance(r, PosixUId))
                    except StopIteration:
                        continue
                    log.debug(uid)
                    user = reg.changes[0].actor
                    surname = user.surname or "UNKNOWN"
                    record = LDAPRecord(
                        dn={("cn={},ou=jasmin2,"
                        "ou=People,o=hpc,dc=rl,dc=ac,dc=uk").format(reg.uuid)},
                        objectclass={"top", "person", "organizationalPerson",
                            "inetOrgPerson"},
                        description={"cluster:jasmin-login"},
                        cn={reg.uuid},
                        sn={surname},
                    )
                    resources = [
                        r for i in reg.changes for r in i.resources
                        if isinstance(r, EmailAddress)]
                    if resources:
                        record["mail"].add(resources[0].value)
                    msg = LDAPProxy.WriteCommonName(record, reg.uuid)
                    yield from self.ldapQ.put(msg)
                    session.expire(reg)
            except Exception as e:
                log.error(e)
            finally:
                log.debug("Waiting for {}s".format(self.args.interval))
                yield from asyncio.sleep(self.args.interval)

    @asyncio.coroutine
    def publish_uidnumber(self):
        log = logging.getLogger(__name__ + ".uidnumber")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        while True:
            try:
                unpublished = [
                    r for r in session.query(Registration).all() if (
                    r.changes[-1].state.name ==
                    "user_posixaccount")]

                for reg in unpublished:
                    user = reg.changes[0].actor
                    surname = user.surname or "UNKNOWN"
                    resources = [r for c in reversed(reg.changes)
                                 for r in c.resources]

                    emailAddr = next(i for i in resources
                                     if isinstance(i, EmailAddress))
                    uid = next(i for i in resources if isinstance(i, PosixUId))
                    uidNumber = next(i for i in resources
                                     if isinstance(i, PosixUIdNumber))
                    record = LDAPRecord(
                        dn={("cn={},ou=jasmin2,"
                        "ou=People,o=hpc,dc=rl,dc=ac,dc=uk").format(uid.value)},
                        objectclass={"top", "person", "organizationalPerson",
                            "inetOrgPerson", "posixAccount"},
                        description={"cluster:jasmin-login"},
                        cn={uid.value},
                        sn={surname},
                        uid={uid.value},
                        uidNumber={uidNumber.value},
                        gidNumber={uidNumber.value},
                        gecos={"{} <{}>".format(uid.value, emailAddr.value)},
                        homeDirectory={"/home/{}".format(uid.value)},
                        loginShell={"/bin/bash"},
                        mail={emailAddr.value}
                    )
                    log.debug(record)
                    msg = LDAPProxy.WriteUIdNumber(record, reg.uuid)
                    yield from self.ldapQ.put(msg)
                    session.expire(reg)
            except Exception as e:
                log.error(e)
            finally:
                log.debug("Waiting for {}s".format(self.args.interval))
                yield from asyncio.sleep(self.args.interval)

    @asyncio.coroutine
    def publish_sshpublickey(self):
        log = logging.getLogger(__name__ + ".sshpublickey")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        while True:
            try:
                unpublished = [
                    r for r in session.query(Registration).all() if (
                    r.changes[-1].state.name ==
                    "pre_user_ldappublickey")]

                for reg in unpublished:
                    user = reg.changes[0].actor
                    resources = [r for c in reversed(reg.changes)
                                 for r in c.resources]

                    key = next(
                        (i for i in resources if isinstance(i, PublicKey)),
                        None)

                    if key is None:
                        continue

                    uid = next(i for i in resources if isinstance(i, PosixUId))
                    record = LDAPRecord(
                        dn={("cn={},ou=jasmin2,"
                        "ou=People,o=hpc,dc=rl,dc=ac,dc=uk").format(uid.value)},
                        objectclass={"ldapPublicKey"},
                        sshPublicKey={key.value},
                    )
                    log.debug(record)
                    msg = LDAPProxy.WriteSSHPublicKey(record, reg.uuid)
                    yield from self.ldapQ.put(msg)
                    session.expire(reg)
            except Exception as e:
                log.error(e)
            finally:
                log.debug("Waiting for {}s".format(self.args.interval))
                yield from asyncio.sleep(self.args.interval)

    @asyncio.coroutine
    def publish_user_membership(self):
        log = logging.getLogger(__name__ + ".publish_user_membership")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        while True:
            try:
                # Unwieldy, but left outer joins seem not to work with table
                # inheritance.
                unpublished = [
                    mship for mship in session.query(Membership).join(
                    Touch).join(State, State.name == "accepted").all()
                    if not any(isinstance(r, LDAPAttribute)
                        for c in mship.changes for r in c.resources)]

                for mship in unpublished:
                    user = mship.changes[1].actor
                    record = LDAPRecord(
                        dn={
                            ("cn={},ou=Groups,ou=jasmin2,"
                            "ou=People,o=hpc,dc=rl,dc=ac,dc=uk").format(
                            mship.organisation.name.lower() + "_vcloud-admins")
                        },
                        memberUId={user.handle},
                    )
                    msg = LDAPProxy.WriteLDAPAttribute(record, mship.uuid)
                    yield from self.ldapQ.put(msg)
                    session.expire(mship)
            except Exception as e:
                log.error(e)

            log.debug("Waiting for {}s".format(self.args.interval))
            yield from asyncio.sleep(self.args.interval)

