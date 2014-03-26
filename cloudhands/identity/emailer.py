#!/usr/bin/env python
# encoding: UTF-8

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
import sqlite3
import sys
import textwrap


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
        while True:
            dst, url = yield from self.q.get()
            src = self.config["smtp.src"]["from"]

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
            log.info("Notification {} to {}".format(url, dst))
