#!/usr/bin/env python
# encoding: UTF-8

import asyncio
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
import sqlite3
import sys
import textwrap

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.fsm import RegistrationState
from cloudhands.common.schema import Component
from cloudhands.common.schema import Registration
from cloudhands.common.schema import Touch


class Emailer:

    _shared_state = {}

    TEXT = textwrap.dedent("""
    Your action is required.

    Please visit this link to confirm your registration:
    {url}
    """).strip()

    HTML = textwrap.dedent("""
    <html>
    <head></head>
    <body>
    <h1>Your action is required</h1>
    <p>Please visit this link to confirm your registration.</p>
    <p><a href="{url}">{url}</a></p>
    </body>
    </html>
    """).strip()

    def __init__(self, q, args, config):
        self.__dict__ = self._shared_state
        if not hasattr(self, "task"):
            self.q = q
            self.args = args
            self.config = config
            self.task = asyncio.Task(self.notify())

    @asyncio.coroutine
    def notify(self):
        log = logging.getLogger("cloudhands.identity.emailer")
        session = Registry().connect(sqlite3, self.args.db).session
        initialise(session)
        actor = session.query(Component).filter(
            Component.handle=="identity.controller").one()
        postconfirm = session.query(RegistrationState).filter(
            RegistrationState.name == "postconfirm").one()
        while True:
            dst, host, reg_uuid = yield from self.q.get()
            path = "registration/{}".format(reg_uuid)
            url = '/'.join((host, path))
            src = self.config["smtp.src"]["from"]

            reg = session.query(Registration).filter(
                Registration.uuid == reg_uuid).first()
            now = datetime.datetime.utcnow()
            act = Touch(artifact=reg, actor=actor, state=postconfirm, at=now)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = self.config["smtp.src"]["subject"]
            msg["From"] = src
            msg["To"] = dst

            text = Emailer.TEXT.format(url=url)
            html = Emailer.HTML.format(url=url)
            for i in (MIMEText(text, "plain"), MIMEText(html, "html")):
                msg.attach(i)

            s = smtplib.SMTP(self.config["smtp.mta"]["host"])
            s.sendmail(src, dst, msg.as_string())
            s.quit()

            try:
                session.add(act)
                session.commit()
            except Exception as e:
                log.error(e)
                session.rollback()
                continue
            else:
                log.debug(act)
