#!/usr/bin/env python
# encoding: UTF-8

import asyncio
from collections import UserDict
import functools

import ldap3


@functools.total_ordering
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

    def __gt__(self, other):
        return (
            sum(len(i) for i in self.values())
            > sum(len(i) for i in other.values()))

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
        obj = LDAPRecord.from_ldif(val)
        ref = LDAPRecord(
            version=obj["version"], changetype=obj["changetype"],
            dn=obj["dn"], cn=obj["cn"], sn=obj["sn"],
            description=obj["description"],
            objectclass={"top", "person"})
        if obj == ref:
            return RecordPatterns.registration_person
        else:
            ref["objectclass"].add("organizationalPerson")
            ref["objectclass"].add("inetOrgPerson")
            ref.update({"ou": obj["ou"], "mail": obj["mail"]})

        if obj == ref:
            if obj["sn"] == {"UNKNOWN"}:
                return RecordPatterns.registration_inetorgperson
            elif any(i for i in obj["cn"] if len(i) == 8):
                return RecordPatterns.user_inetorgperson_dn
            else:
                return RecordPatterns.registration_inetorgperson_sn
        else:
            ref["objectclass"].add("posixAccount")
            ref.update({
                "uid": obj["uid"], "uidNumber": obj["uidNumber"],
                "gidNumber": obj["gidNumber"],
                "homeDirectory": obj["homeDirectory"],
                "userPassword": obj["userPassword"],
            })

        if obj == ref:
            return RecordPatterns.user_posixaccount
        else:
            ref["objectclass"].add("ldapPublicKey")
            ref.update({"sshPublicKey": obj["sshPublicKey"]})

        if obj == ref:
            return RecordPatterns.user_ldappublickey
        else:
            return None

    @staticmethod
    def next_mutator(pattern=None):
        transitions = {
            None: RecordPatterns.add_registration_person,
        }
        return transitions[pattern]

    # TODO: arg is an LDAPRecord
    def add_registration_person(con, uuid):
        con.add(
            "cn={},ou=jasmin2,ou=People,o=hpc,dc=rl,dc=ac,dc=uk".format(uuid),
            ["top", "person"], {
                "objectClass": ["top", "person"],
                "description": "JASMIN2 vCloud registration",
                "cn": uuid,
                "sn": "UNKNOWN"}
        )
        return con


