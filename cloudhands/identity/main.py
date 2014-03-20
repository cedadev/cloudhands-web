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
import time

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.discovery import settings

__doc__ = """
This process performs tasks to administer hosts in the JASMIN cloud.

It makes state changes to Host artifacts in the JASMIN database. It
operates in a round-robin loop with a specified interval.
"""

DFLT_DB = ":memory:"


class Handler:

    #@singledispatch
    @staticmethod
    def call(obj):
        print("Nope")

    #@call.register(int)
    @staticmethod
    def call_int(obj):
        print("Yup")

h = Handler()
Handler.call(5)

class Emailer:

    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state

    @asyncio.coroutine
    def notify(self, future):
        portalName, config = next(iter(settings.items()))
        src = config["smtp.src"]["from"]
        dst = "david.e.haynes@stfc.ac.uk"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = config["smtp.src"]["subject"]
        msg["From"] = src
        msg["To"] = dst

        # Create the body of the message (a plain-text and an HTML version).
        text = "Hi!\nSent by lovely Python."
        html = """\
        <html>
          <head></head>
          <body>
            <p>Hi!<br>
               Sent by lovely <a href="http://www.python.org">Python</a> you wanted.
            </p>
          </body>
        </html>
        """

        # Record the MIME types of both parts - text/plain and text/html.
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(part1)
        msg.attach(part2)

        # Send the message via local SMTP server.
        s = smtplib.SMTP(config["smtp.mta"]["host"])

        # sendmail function takes 3 arguments: sender's address, recipient's address
        # and message to send - here it is sent as one string.
        s.sendmail(src, dst, msg.as_string())
        s.quit()
        future.set_result(True)
        return future

def main(args):
    rv = 1
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s|%(message)s")

    session = Registry().connect(sqlite3, args.db).session
    initialise(session)

    emailer = Emailer()

    #tasks = [
    #    asyncio.Task(emailer.factorial("A", 2)),
    #    asyncio.Task(emailer.factorial("B", 3)),
    #    asyncio.Task(emailer.factorial("C", 4))]

    loop = asyncio.get_event_loop()
    future = asyncio.Future()
    asyncio.Task(emailer.notify(future))
    loop.run_until_complete(future)
    loop.close()

    return rv


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
