#!/usr/bin/env python
# encoding: UTF-8

import argparse
from configparser import ConfigParser
import datetime
import logging
import sqlite3
import sys
import uuid

from cloudhands.common.connectors import Initialiser
from cloudhands.common.connectors import Session

DFLT_DB = ":memory:"

nodes = [
("METAFOR", "portal" "up", "130.246.184.156"),
("METAFOR", "worker 01" "up", "192.168.1.3"),
("METAFOR", "worker 02" "up", "192.168.1.4"),
("METAFOR", "worker 03" "down", "192.168.1.5"),
("METAFOR", "worker 04" "down", "192.168.1.6"),
("METAFOR", "worker 05" "up", "192.168.1.7"),
("METAFOR", "worker 06" "up", "192.168.1.8"),
("METAFOR", "worker 07" "up", "192.168.1.9"),
("METAFOR", "worker 08" "up", "192.168.1.10"),
("METAFOR", "worker 09" "up", "192.168.1.11"),
("METAFOR", "worker 10" "down", "192.168.1.12"),
("METAFOR", "worker 11" "up", "192.168.1.13"),
("METAFOR", "worker 12" "up", "192.168.1.14"),
]

class DemoLoader(Initialiser):

    def __init__(self, config, path=DFLT_DB):
        self.config = config
        self.engine = self.connect(sqlite3, path=path)
        self.session = Session()


    def dump(self):
        print(*self.engine.iterdump(), sep="\n")

def main(args):
    rv = 1
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s|%(message)s")
    log = logging.getLogger("cloudhands.burst")

    ldr = DemoLoader(config=ConfigParser(), path=args.db)

    return rv


def parser():
    rv = argparse.ArgumentParser(description=__doc__)
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
