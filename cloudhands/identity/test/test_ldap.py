#!/usr/bin/env python3
#   encoding: UTF-8


from collections import UserDict
import textwrap
import unittest

import ldap3

class LDAPRecord(UserDict):

    @classmethod
    def from_ldif(cls, val, **kwargs):
        rv = cls(**kwargs)
        lines = val.splitlines()
        while len(lines):
            line = lines.pop(0)
            try:
                if lines[0].startswith(" "):
                    line = line + lines.pop(0).lstrip()
            except IndexError:
                pass

            try:
                k, v = line.split(":", maxsplit=1)
            except ValueError:
                if line.isspace():
                    continue
            else:
                rv[k.strip()].add(v.strip())
        return rv

    def __getitem__(self, key):
        try:
            rv = self.data[self.__keytransform__(key)]
        except KeyError:
            rv = self.data[self.__keytransform__(key)] = set()
        finally:
            return rv

    def __delitem__(self, key):
        del self.store[self.__keytransform__(key)]

    def __eq__(self, other):
        keyDiff = set(self.keys()) ^ set(other.keys())
        return len(keyDiff) == 0 and all(
           self[i] == other[i] for i in sorted(self.keys()))

    def __keytransform__(self, key):
        return key.lower()

    def __setitem__(self, key, value):
        self.data[self.__keytransform__(key)] = value


class RecordPatterns:

    registration_person = 1
    registration_inetorgperson = 2
    registration_inetorgperson_sn = 3
    user_inetorgperson_dn = 4
    user_posixaccount = 5
    user_ldappublickey = 6

    @staticmethod
    def identify(val):
        return None

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

class TestLDAPRecord(unittest.TestCase):

    def test_missing_key(self):
        a = LDAPRecord()
        self.assertTrue(isinstance(a["new"], set))

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
        ldif = LDAPRecord.from_ldif(expect, version={"1"}, changetype={"add"})
        result = ldap_membership(self.connection, uuid_).response
        self.assertEqual(
            ldif,
            LDAPRecord.from_ldif(result))
        self.assertEqual(
            RecordPatterns.registration_person,
            RecordPatterns.identify(ldif))

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

