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

"""
 ldappasswd -D " cn=Nick
Aurelius-Haddock,ou=jasmin,ou=People,o=hpc,dc=rl,dc=ac,dc=uk " -w
"<your_password>" -H ldap://ldap-test.jc.rl.ac.uk  -A -S
"cn=nahaddock,ou=ceda,ou=People,o=hpc,dc=rl,dc=ac,dc=uk"
"""

def main(args):
    rv = subprocess.call(["ldappasswd", "-h"])
    return rv

    
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
