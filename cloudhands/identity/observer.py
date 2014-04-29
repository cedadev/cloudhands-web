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

__doc__ = """
This process performs tasks to process Registrations to the JASMIN cloud.
"""


class Observer:

    _shared_state = {}

    def __init__(self, q, args, config):
        self.__dict__ = self._shared_state
        if not hasattr(self, "task"):
            self.q = q
            self.args = args
            self.task = asyncio.Task(self.monitor())

    @asyncio.coroutine
    def monitor(self):
        log = logging.getLogger(__name__)
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
                    yield from self.q.put(msg)
                    try:
                        session.add(act)
                        session.commit()
                    except Exception as e:
                        log.error(e)
                        session.rollback()
                        break

            log.debug("Waiting for {}s".format(self.args.interval))
            yield from asyncio.sleep(self.args.interval)
