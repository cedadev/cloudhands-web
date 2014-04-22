#!/usr/bin/env python3
#   encoding: UTF-8


from collections import defaultdict
import unittest

import ldap3

def ldap_membership(con, uuid):
    con.add(
        "cn={},ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk".format(uuid),
        ["top", "person"], {
            "objectClass": ["top", "person"],
            "description": "JASMIN2 vCloud registration",
            "cn": uuid,
            "sn": "UNKNOWN"}
    )
    return con

class LDAPFaker:

    @staticmethod
    def demo():
        connection = ldap3.Connection(
            server=None, client_strategy=ldap3.STRATEGY_LDIF_PRODUCER)
        connection.add(
            "cn=test-add-operation,o=test",
            ["iNetOrgPerson"], {
                "objectClass": ["iNetOrgPerson"],
                "sn": "test-add",
                "cn": "test-add-operation"}
        )
        return connection

class LDAPRecordTests(unittest.TestCase):

    complete = """
    dn: cn=dehaynes,ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
    objectclass: top
    objectclass: person
    objectclass: organizationalPerson
    objectclass: inetOrgPerson
    objectclass: posixAccount
    objectclass: ldapPublicKey
    description: JASMIN2 vCloud account
    userPassword: {SHA}0LXhFAsrBWEEQ
    cn: dehaynes
    sn: Haynes
    ou: jasmin2
    uid: dehaynes
    uidNumber: 1034
    gidNumber: 100
    mail: david.e.haynes@stfc.ac.uk
    homeDirectory: /home/dehaynes
    sshPublicKey: ssh-dss AAAAB3...
    sshPublicKey: ssh-dss AAAAM5...
    """

    def setUp(self):
        self.connection = ldap3.Connection(
            server=None, client_strategy=ldap3.STRATEGY_LDIF_PRODUCER)

    @staticmethod
    def ldif_content2dict(val):
        rv = defaultdict(set)
        for line in (i.strip() for i in val.splitlines()):
            try:
                k, v = line.split(":", maxsplit=1)
            except ValueError:
                if line.isspace():
                    continue
            else:
                rv[k.strip()].add(v.strip())
        return rv

    def test_state_one(self):
        uuid_ = "3dceb7f3dc9947b78345f864972ee31f"
        uuid_ = "3dc9947b78345f864972ee31f"
        expect = """
        dn: cn={uuid},ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        description: JASMIN2 vCloud registration
        cn: {uuid}
        sn: UNKNOWN
        """.format(uuid=uuid_)
        ldif = LDAPRecordTests.ldif_content2dict(expect)
        ldif.update({"version": {'1'}, "changetype": {"add"}})
        result = ldap_membership(self.connection, uuid_).response
        print(result)
        print(set(ldif.values()) - 
            set(LDAPRecordTests.ldif_content2dict(result).values()))

    def test_state_two(self):
        expect = """
        dn: cn=3dceb7f3dc9947b78345f864972ee31f,ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        objectclass: organizationalPerson
        objectclass: inetOrgPerson
        description: JASMIN2 vCloud registration
        cn: 3dceb7f3dc9947b78345f864972ee31f
        sn: UNKNOWN
        ou: jasmin2
        mail: david.e.haynes@stfc.ac.uk
        """

    def test_state_three(self):
        expect = """
        dn: cn=3dceb7f3dc9947b78345f864972ee31f,ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        objectclass: organizationalPerson
        objectclass: inetOrgPerson
        description: JASMIN2 vCloud registration
        cn: 3dceb7f3dc9947b78345f864972ee31f
        sn: Haynes
        ou: jasmin2
        mail: david.e.haynes@stfc.ac.uk
        """

    def test_state_four(self):
        expect = """
        dn: cn=dehaynes,ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        objectclass: organizationalPerson
        objectclass: inetOrgPerson
        description: JASMIN2 vCloud user
        cn: dehaynes
        sn: Haynes
        ou: jasmin2
        mail: david.e.haynes@stfc.ac.uk
        """

    def test_state_five(self):
        expect = """
        dn: cn=dehaynes,ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        objectclass: organizationalPerson
        objectclass: inetOrgPerson
        objectclass: posixAccount
        description: JASMIN2 vCloud account
        userPassword: {SHA}0LXhFAsrBWEEQ
        cn: dehaynes
        sn: Haynes
        ou: jasmin2
        uid: dehaynes
        uidNumber: 1034
        gidNumber: 100
        mail: david.e.haynes@stfc.ac.uk
        homeDirectory: /home/dehaynes
        """

    def test_state_six(self):
        expect = """
        dn: cn=dehaynes,ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        objectclass: organizationalPerson
        objectclass: inetOrgPerson
        objectclass: posixAccount
        objectclass: ldapPublicKey
        description: JASMIN2 vCloud account
        userPassword: {SHA}0LXhFAsrBWEEQ
        cn: dehaynes
        sn: Haynes
        ou: jasmin2
        uid: dehaynes
        uidNumber: 1034
        gidNumber: 100
        mail: david.e.haynes@stfc.ac.uk
        homeDirectory: /home/dehaynes
        sshPublicKey: ssh-dss AAAAB3...
        """

