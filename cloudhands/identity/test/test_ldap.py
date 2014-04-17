#!/usr/bin/env python3
#   encoding: UTF-8


import unittest

class LDAPRecordTests(unittest.TestCase):

    complete = """
    dn: cn=dehaynes,ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
    objectclass: top
    objectclass: person
    objectclass: organizationalPerson
    objectclass: posixAccount
    objectclass: ldapPublicKey
    description: JASMIN2 vCloud account
    userPassword: {SHA}0LXhFAsrBWEEQ
    cn: dehaynes
    sn: Haynes
    uid: dehaynes
    uidNumber: 1034
    gidNumber: 100
    homeDirectory: /home/dehaynes
    sshPublicKey: ssh-dss AAAAB3...
    sshPublicKey: ssh-dss AAAAM5...
    """

    def test_state_one(self):
        expect = """
        dn: cn=3dceb7f3dc9947b78345f864972ee31f,ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        cn: 3dceb7f3dc9947b78345f864972ee31f
        sn: UNKNOWN
        """
        self.fail(expect)

    def test_state_two(self):
        expect = """
        dn: cn=dehaynes,ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk
        objectclass: top
        objectclass: person
        objectclass: organizationalPerson
        objectclass: posixAccount
        objectclass: ldapPublicKey
        description: JASMIN2 vCloud account
        userPassword: {SHA}0LXhFAsrBWEEQ
        cn: dehaynes
        sn: Haynes
        uid: dehaynes
        uidNumber: 1034
        gidNumber: 100
        homeDirectory: /home/dehaynes
        sshPublicKey: ssh-dss AAAAB3...
        sshPublicKey: ssh-dss AAAAM5...
        """
