#!/usr/bin/env python
# encoding: UTF-8

import argparse
import asyncio
import logging
import sys

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry
from cloudhands.common.discovery import settings
from cloudhands.identity.emailer import Emailer
from cloudhands.identity.observer import Observer

__doc__ = """
This process performs tasks to process Registrations to the JASMIN cloud.
"""

DFLT_DB = ":memory:"

def main(args):
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s|%(message)s")
    log = logging.getLogger("cloudhands.identity.main")

    portalName, config = next(iter(settings.items()))

    loop = asyncio.get_event_loop()
    q = asyncio.Queue(loop=loop)
    emailer = Emailer(q, args, config)
    observer = Observer(q, args, config)
    #emailer.q.put_nowait(
    #    ("david.e.haynes@stfc.ac.uk",
    #    "http://jasmin-cloud.jc.rl.ac.uk:8080/"
    #    "registration/1a3c37c3a2f646eea4447e0b629ba899"))

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
        "--interval", default=3, type=int,
        help="Set the monitoring interval (s)")
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
