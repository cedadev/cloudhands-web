#!/usr/bin/env python
# encoding: UTF-8

import argparse
import asyncio
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
import sqlite3
import sys
import textwrap
import time

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.discovery import settings

__doc__ = """
This process performs tasks to process Registrations to the JASMIN cloud.
"""

DFLT_DB = ":memory:"


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

    def __init__(self, q, config):
        self.__dict__ = self._shared_state
        if not hasattr(self, "task"):
            self.q = q
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


def main(args):
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s|%(message)s")
    log = logging.getLogger("cloudhands.identity.main")

    portalName, config = next(iter(settings.items()))
    session = Registry().connect(sqlite3, args.db).session
    initialise(session)

    loop = asyncio.get_event_loop()
    q = asyncio.Queue(loop=loop)
    emailer = Emailer(q, config)
    emailer.q.put_nowait(
        ("david.e.haynes@stfc.ac.uk",
        "http://jasmin-cloud.jc.rl.ac.uk:8080/"
        "registration/1a3c37c3a2f646eea4447e0b629ba899"))

    tasks = asyncio.Task.all_tasks()
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()

    return 0


def parser(descr=__doc__):
    rv = argparse.ArgumentParser(description=descr)
    rv.add_argument(
        "--version", action="store_true", default=False,
        help="Print the current version number")
    rv.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
    rv.add_argument(
        "--db", default=DFLT_DB,
        help="Set the path to the database [{}]".format(DFLT_DB))
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()
