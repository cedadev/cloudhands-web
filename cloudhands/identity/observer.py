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
from cloudhands.common.fsm import RegistrationState
from cloudhands.common.schema import Component
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Registration
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

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
                asyncio.Task(self.publisher())]

    @asyncio.coroutine
    def mailer(self):
        log = logging.getLogger(__name__ + ".mailer")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        preconfirm = session.query(RegistrationState).filter(
            RegistrationState.name == "pre_registration_inetorgperson").one()
        while True:
            unsent = [
                r for r in session.query(Registration).all()
                if r.changes[-1].state.name == "pre_registration_person"]
            unpublished = [
                r for r in session.query(Registration).all()
                if r.changes[-1].state.name == "pre_registration_person_sn"]
            for reg in unsent:
                try:
                    user = reg.changes[0].actor
                    email = session.query(EmailAddress).join(Touch).join(User).filter(
                        User.id == user.id).order_by(desc(Touch.at)).first().value
                    host = "http://{}:8080".format(platform.node()) #  FIXME
                except Exception as e:
                    log.error(e)
                    break
                else:
                    msg = (email, host, reg.uuid)
                    log.debug(msg)
                    now = datetime.datetime.utcnow()
                    act = Touch(artifact=reg, actor=actor, state=preconfirm, at=now)
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
    def publisher(self):
        log = logging.getLogger(__name__ + ".publisher")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        while True:
            try:
                unpublished = [
                    r for r in session.query(Registration).all() if (
                    r.changes[-1].state.name ==
                    "pre_registration_inetorgperson_sn")]

                for reg in unpublished:
                    # TODO: Build LDAPRecord
                    user = reg.changes[0].actor
                    record = LDAPRecord(
                        dn={("cn={},ou=jasmin2,"
                        "ou=People,o=hpc,dc=rl,dc=ac,dc=uk").format(reg.uuid)},
                        objectclass={"top", "person", "organizationalPerson",
                            "inetOrgPerson"},
                        description={"JASMIN2 vCloud registration"},
                        cn={reg.uuid},
                        sn={"UNKNOWN"},
                    )
                    resources = [
                        r for i in reg.changes for r in i.resources
                        if isinstance(r, EmailAddress)]
                    if resources:
                        record["mail"].add(resources[0].value)
                    msg = (record, reg.uuid)
                    yield from self.ldapQ.put(msg)
                    session.expire(reg)
            except Exception as e:
                log.error(e)

            log.debug("Waiting for {}s".format(self.args.interval))
            yield from asyncio.sleep(self.args.interval)
