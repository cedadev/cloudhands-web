#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
import sys

from cloudhands.web import __version__

def parser():
    rv = argparse.ArgumentParser(description=__doc__)
    rv.add_argument("--version", action="store_true", default=False,
    help="Print the current version number")
    return rv

def run():
    p = parser()
    args = p.parse_args()
    if args.version:
        sys.stdout.write(__version__)
        rv = 0
    else:
        rv = main(args)
    sys.exit(rv)

if __name__  == "__main__":
    run()
