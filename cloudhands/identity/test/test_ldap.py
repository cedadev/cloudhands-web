#!/usr/bin/env python3
#   encoding: UTF-8


import textwrap
import unittest

from cloudhands.identity.ldap import LDAPRecord
from cloudhands.identity.ldap import RecordPatterns

import ldap3


class TestLDAPRecord(unittest.TestCase):

    def test_missing_key(self):
        a = LDAPRecord()
        self.assertTrue(isinstance(a["new"], set))

    def test_remove_key(self):
        a = LDAPRecord()
        a["new"].add(None)
        self.assertEqual(1, len(a))
        del a["new"]
        self.assertEqual(0, len(a))

    def test_equality(self):
        len_ = 20
        a = LDAPRecord((str(n), set(range(0, n))) for n in range(len_))
        b = LDAPRecord((str(n), set(range(0, n))) for n in range(len_))
        self.assertEqual(a, b)

    def test_equality_negative(self):
        len_ = 20
        a = LDAPRecord((str(n), set(range(0, n))) for n in range(len_))
        b = LDAPRecord((str(n), set(range(0, n+1))) for n in range(len_))
        self.assertNotEqual(a, b)

    def test_case_lowered_keys(self):
        a = LDAPRecord()
        b = LDAPRecord()

        a["volume"].add(2)
        b["VOLUME"].add(10)
        self.assertNotEqual(a, b)

        a["volume"].add(10)
        b["VOLUME"].add(2)
        self.assertEqual(a, b)

    def test_instantiation_with_keyword_arguments(self):
        a = {"one": {1}}
        b = {"two": {2}}
        c = LDAPRecord()
        c.update(a)
        c.update(b)

        d = LDAPRecord(a, **b)
        self.assertEqual(c, d)

    def test_ldif_linelength(self):
        uuid_ = "3dceb7f3dc9947b78345f864972ee31f"
        long = textwrap.dedent("""
        dn: cn={uuid},ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        """.format(uuid=uuid_)).strip()

        self.assertEqual(84, len(long.splitlines()[0]))
        ldif = textwrap.wrap(long, width=78)
        self.assertTrue(ldif[1].startswith(",dc=uk"))
        ldif[1] = " " + ldif[1]  # RFC2849 line folding

        short = "objectclass: top"

        r = LDAPRecord.from_ldif('\n'.join(ldif + [short]))
        self.assertEqual({"dn", "objectclass"}, set(r.keys()))
        
class RecordChangeTests(unittest.TestCase):

    sample = """
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

    def test_state_one(self):
        uuid_ = "3dceb7f3dc9947b78345f864972ee31f"
        #uuid_ = "3dc9947b78345f864972ee31f"
        expect = textwrap.dedent("""
        dn: cn={uuid},ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        description: JASMIN2 vCloud registration
        cn: {uuid}
        sn: UNKNOWN
        """.format(uuid=uuid_))
        #ldif = LDAPRecord.from_ldif(expect, version={"1"}, changetype={"add"})
        #result = RecordPatterns.add_registration_person(
        #    self.connection, uuid_).response  # FIXME
        #self.assertEqual(
        #    ldif,
        #    LDAPRecord.from_ldif(result))

        self.assertEqual(
            RecordPatterns.registration_person,
            RecordPatterns.identify(LDAPRecord.from_ldif(expect)))

    def test_state_two(self):
        expect = textwrap.dedent("""
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
        """)
        self.assertEqual(
            RecordPatterns.registration_inetorgperson,
            RecordPatterns.identify(LDAPRecord.from_ldif(expect)))

    def test_state_three(self):
        expect = textwrap.dedent("""
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
        """)
        self.assertEqual(
            RecordPatterns.registration_inetorgperson_sn,
            RecordPatterns.identify(LDAPRecord.from_ldif(expect)))

    def test_state_four(self):
        expect = textwrap.dedent("""
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
        """)
        self.assertEqual(
            RecordPatterns.user_inetorgperson_dn,
            RecordPatterns.identify(LDAPRecord.from_ldif(expect)))

    def test_state_five(self):
        expect = textwrap.dedent("""
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
        """)
        self.assertEqual(
            RecordPatterns.user_posixaccount,
            RecordPatterns.identify(LDAPRecord.from_ldif(expect)))

    def test_state_six(self):
        expect = textwrap.dedent("""
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
        """)
        self.assertEqual(
            RecordPatterns.user_ldappublickey,
            RecordPatterns.identify(LDAPRecord.from_ldif(expect)))

