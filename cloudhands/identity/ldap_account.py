#!/usr/bin/env python
# encoding: UTF-8

import argparse
import logging
import subprocess
import sys

import ldap3

from cloudhands.common.discovery import settings
from cloudhands.web import __version__

__doc__ = """
Command line tool to change LDAP passwords.
"""

def discover_uids(config):
    log = logging.getLogger("cloudhands.identity.discovery")
    s = ldap3.Server(
        config["ldap.search"]["host"],
        port=int(config["ldap.search"]["port"]),
        get_info=ldap3.GET_ALL_INFO)
    c = ldap3.Connection(
        s, auto_bind=True, client_strategy=ldap3.STRATEGY_SYNC)
    log.info("Opening LDAP connection to {}.".format(
        config["ldap.search"]["host"]))

    c.search(config["ldap.search"]["query"], "(objectclass=posixAccount)",
        ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
        attributes=["uidNumber"])
    return set(int(n) for i in c.response for n in i["attributes"].get("uidNumber", []))


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
    provider, config = next(iter(settings.items()))
    print(discover_uids(config).intersection(range(24000, 26000)))
    #return change_password("pjk12345", "firstpwd")

    
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
