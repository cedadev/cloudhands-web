#!/usr/bin/env python
# encoding: UTF-8

import argparse
import logging
import subprocess
import sys

from cloudhands.web import __version__

__doc__ = """
Command line tool to change LDAP passwords.
"""


def change_password(cn, pwd):
    shellArgs = ["ldappasswd",
    "-h", "ldap-test.jc.rl.ac.uk",
    "-D", "cn=dehaynes,ou=ceda,ou=People,o=hpc,dc=rl,dc=ac,dc=uk",
    "-w", "password",
    "-s", pwd,
    "cn={},ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk".format(cn)]
    rv = subprocess.call(shellArgs)
    return rv


def main(args):
    return change_password("pjk12345", "firstpwd")

    
def parser(descr=__doc__):
    rv = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=descr)
    rv.add_argument(
        "--version", action="store_true", default=False,
        help="Print the current version number")
    rv.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = 0
    if args.version:
        sys.stdout.write(__version__ + "\n")
    else:
        rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()
