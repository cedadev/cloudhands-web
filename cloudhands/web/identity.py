#!/usr/bin/env python3
# encoding: UTF-8

import ldap3

__doc__ = """
ldapsearch -x -H ldap://homer.esc.rl.ac.uk -s sub -b
'ou=ceda,ou=People,o=hpc,dc=rl,dc=ac,dc=uk'
'(&(objectclass=posixAccount)(objectclass=ldapPublicKey))'
"""

s = ldap3.server.Server(
    "homer.esc.rl.ac.uk",
    port=389,
    getInfo=ldap3.GET_ALL_INFO)
c = ldap3.connection.Connection(
    s, autoBind=True, clientStrategy=ldap3.STRATEGY_SYNC)
result = c.search(
    "ou=ceda,ou=People,o=hpc,dc=rl,dc=ac,dc=uk",
    "(&(objectclass=posixAccount)(objectclass=ldapPublicKey))",
    ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
    attributes = ["cn", "gecos", "uid", "uidNumber", "gidNumber", "sshPublicKey"])

if result:
    for r in c.response:
        print(r['dn'], r['attributes']) # for unicode attributes
else:
    print('result', c.result)
c.unbind()
