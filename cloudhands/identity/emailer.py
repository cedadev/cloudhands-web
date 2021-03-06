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
from cloudhands.common.schema import Component
from cloudhands.common.schema import Membership
from cloudhands.common.schema import TimeInterval
from cloudhands.common.schema import Touch


class Emailer:

    _shared_state = {}

    TEXT = textwrap.dedent("""
    Your action is required.

    Please visit this link to confirm your membership:
    {url}
    """).strip()

    HTML = textwrap.dedent("""
    <html>
    <head></head>
    <body>
    <h1>Your action is required</h1>
    <p>Please visit this link to confirm your membership.</p>
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
        while True:
            dst, host, mship_uuid = yield from self.q.get()
            path = "membership/{}".format(mship_uuid)
            url = '/'.join((host, path))
            src = self.config["smtp.src"]["from"]

            mship = session.query(Membership).filter(
                Membership.uuid == mship_uuid).first()
            latest = mship.changes[-1]
            now = datetime.datetime.utcnow()
            end = now + datetime.timedelta(hours=24)
            act = Touch(artifact=mship, actor=actor, state=latest.state, at=now)
            limit = TimeInterval(end=end, touch=act) 

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
                session.add(limit)
                session.commit()
            except Exception as e:
                log.error(e)
                session.rollback()
                continue
            else:
                log.info(
                    "{0.touch.artifact.uuid} {0.touch.state.name} "
                    "until {0.end:%Y-%m-%dT%H:%M:%S}".format(limit))
