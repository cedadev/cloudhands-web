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

from cloudhands.common.fsm import HostState
from cloudhands.common.fsm import MembershipState

import cloudhands.common.schema
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Host
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Node
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Resource
from cloudhands.common.schema import State
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.common.tricks import create_user_grant_email_membership

import cloudhands.web.main

__doc__ = """
    select a.uuid, s.name, n.name, ips.value, t.at from touches as t
        join resources as r on r.id = t.id
        join artifacts as a on t.artifact_id = a.id
        join states as s on t.state_id = s.id
        left outer join ipaddresses as ips on ips.id = r.id
        left outer join nodes as n on n.id = r.id;
"""

DFLT_DB = ":memory:"


class DemoLoader(Initialiser):

    nodes = [
        ("METAFOR", "portal", "up", "130.246.184.156"),
        ("METAFOR", "worker 01", "up", "192.168.1.3"),
        ("METAFOR", "worker 02", "up", "192.168.1.4"),
        ("METAFOR", "worker 03", "down", "192.168.1.5"),
        ("METAFOR", "worker 04", "down", "192.168.1.6"),
        ("METAFOR", "worker 05", "up", "192.168.1.7"),
        ("METAFOR", "worker 06", "up", "192.168.1.8"),
        ("METAFOR", "worker 07", "up", "192.168.1.9"),
        ("METAFOR", "worker 08", "up", "192.168.1.10"),
        ("METAFOR", "worker 09", "up", "192.168.1.11"),
        ("METAFOR", "worker 10", "down", "192.168.1.12"),
        ("METAFOR", "worker 11", "up", "192.168.1.13"),
        ("METAFOR", "worker 12", "up", "192.168.1.14"),
    ]

    def demo_email(req=None):
        return "ben.campbell@durham.ac.uk"

    def __init__(self, config, path=DFLT_DB):
        self.config = config
        self.con = cloudhands.web.main.Connection(path)

    def create_organisations(self):
        for name in {i[0] for i in DemoLoader.nodes}:
            org = Organisation(name=name)
            try:
                self.con.session.add(org)
                self.con.session.commit()
            except Exception as e:
                self.con.session.rollback()

    def grant_user_membership(self):
        org = self.con.session.query(Organisation).one()  # FIXME
        return create_user_grant_email_membership(
            self.con.session, org, DemoLoader.demo_email())

    def load_hosts_for_user(self, user):
        for jvo, hostname, status, addr in DemoLoader.nodes:
            # 1. User creates a new host
            now = datetime.datetime.utcnow()
            org = self.con.session.query(
                Organisation).filter(Organisation.name == jvo).one()
                
            requested = self.con.session.query(HostState).filter(
                HostState.name == "requested").one()
            host = Host(
                uuid=uuid.uuid4().hex,
                model=cloudhands.common.__version__,
                organisation=org,
                name=hostname
                )
            host.changes.append(
                Touch(artifact=host, actor=user, state=requested, at=now))
            self.con.session.add(host)
            self.con.session.commit()

            now = datetime.datetime.utcnow()
            scheduling = self.con.session.query(HostState).filter(
                HostState.name == "scheduling").one()
            host.changes.append(
                Touch(artifact=host, actor=user, state=scheduling, at=now))
            self.con.session.commit()

            # 2. Burst controller raises a node
            now = datetime.datetime.utcnow()
            act = Touch(artifact=host, actor=user, state=scheduling, at=now)
            host.changes.append(act)
            node = Node(name=host.name, touch=act)
            self.con.session.add(node)
            self.con.session.commit()

            # 3. Burst controller allocates an IP
            now = datetime.datetime.utcnow()
            act = Touch(artifact=host, actor=user, state=scheduling, at=now)
            host.changes.append(act)
            ip = IPAddress(value=addr, touch=act)
            self.con.session.add(ip)
            self.con.session.commit()

            # 4. Burst controller marks Host with operating state
            now = datetime.datetime.utcnow()
            state = self.con.session.query(HostState).filter(
                HostState.name == status).one()
            host.changes.append(
                Touch(artifact=host, actor=user, state=state, at=now))
            self.con.session.commit()


def main(args):
    rv = 1
    model = cloudhands.web.main.configure(args)
    log = logging.getLogger("cloudhands.burst")

    ldr = DemoLoader(config=ConfigParser(), path=args.db)
    ldr.create_organisations()
    user = ldr.grant_user_membership()
    ldr.load_hosts_for_user(user)

    cloudhands.web.main.authenticated_userid = DemoLoader.demo_email

    app = cloudhands.web.main.wsgi_app()
    cloudhands.web.main.serve(
        app, host="localhost", port=args.port, url_scheme="http")
    return rv


def parser(description=__doc__):
    rv = cloudhands.web.main.parser(description)
    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()