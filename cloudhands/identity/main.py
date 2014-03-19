#!/usr/bin/env python
# encoding: UTF-8

import argparse
import asyncio
import datetime
import logging
import sqlite3
import sys
import time

from cloudhands.common.connectors import initialise
from cloudhands.common.connectors import Registry

__doc__ = """
This process performs tasks to administer hosts in the JASMIN cloud.

It makes state changes to Host artifacts in the JASMIN database. It
operates in a round-robin loop with a specified interval.
"""

DFLT_DB = ":memory:"


@asyncio.coroutine
def factorial(name, number):
    f = 1
    for i in range(2, number+1):
        print("Task %s: Compute factorial(%s)..." % (name, i))
        yield from asyncio.sleep(1)
        f *= i
    print("Task %s: factorial(%s) = %s" % (name, number, f))


def main(args):
    rv = 1
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s|%(message)s")

    session = Registry().connect(sqlite3, args.db).session
    initialise(session)

    tasks = [
        asyncio.Task(factorial("A", 2)),
        asyncio.Task(factorial("B", 3)),
        asyncio.Task(factorial("C", 4))]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait(tasks))
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
