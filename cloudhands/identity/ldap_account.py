#!/usr/bin/env python
# encoding: UTF-8

import argparse
import logging
import subprocess
import sys

import ldap3

from cloudhands.common.discovery import providers
from cloudhands.common.discovery import settings
from cloudhands.identity.registration import from_pool
from cloudhands.web import __version__

__doc__ = """
Command line tool to change LDAP passwords.
"""

DFLT_DB = ":memory:"

def discover_uids(config=None):
    log = logging.getLogger("cloudhands.identity.discovery")
    config = config or next(iter(settings.values()))
    s = ldap3.Server(
        config["ldap.search"]["host"],
        port=int(config["ldap.search"]["port"]),
        get_info=ldap3.GET_ALL_INFO)
    c = ldap3.Connection(
        s, auto_bind=True, client_strategy=ldap3.STRATEGY_SYNC)
    log.info("Opening LDAP connection to {}.".format(
        config["ldap.search"]["host"]))

    c.search(config["ldap.match"]["query"], "(objectclass=posixAccount)",
        ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
        attributes=["uidNumber"])
    return {
        int(n) for n in (
            i["attributes"].get("uidNumber", None) for i in c.response
        ) if n is not None
    }


def next_uidnumber(taken=None, provider=None):
    taken = taken or set()
    provider = provider or next(reversed(providers["vcloud"]))
    start = int(provider["uidnumbers"]["start"])
    stop = int(provider["uidnumbers"]["stop"])
    pool = set(range(start, stop))
    try:
        taken = taken.union(discover_uids())
    except TimeoutError:
        return None
    else:
        return next(from_pool(pool, taken))


def change_password(cn, pwd, config=None, timeout=10):
    config = config or next(iter(settings.values()))
    shellArgs = ["ldappasswd",
    "-Z",
    "-h", config["ldap.match"]["host"],
    "-D", config["ldap.creds"]["user"],
    "-w", config["ldap.creds"]["password"],
    "-s", pwd,
    "cn={},ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk".format(cn)]
    try:
        rv = subprocess.call(shellArgs, timeout=timeout)
    except subprocess.TimeoutExpired:
        rv = None
    return rv


def main(args):
    print(next_uidnumber())
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
    rv.add_argument(
        "--db", default=DFLT_DB,
        help="Set the path to the database [{}]".format(DFLT_DB))
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
