#!/usr/bin/env python3
# encoding: UTF-8

import functools

import ldap3

__doc__ = """
ldapsearch -x -H ldap://homer.esc.rl.ac.uk -s sub -b
'ou=ceda,ou=People,o=hpc,dc=rl,dc=ac,dc=uk'
'(&(objectclass=posixAccount)(objectclass=ldapPublicKey))'
"""

ldap_search = {
    "host": "homer.esc.rl.ac.uk",
    "port": "389",
    "query": "ou=ceda,ou=People,o=hpc,dc=rl,dc=ac,dc=uk",
    "filter": "(&(objectclass=posixAccount)(objectclass=ldapPublicKey))",
}
ldap_attributes = {
    "cn": True,
    "gecos": True,
    "uid": True,
    "uidNumber": True,
    "gidNumber": True,
    "sshPublicKey": True,
}

s = ldap3.server.Server(
    "homer.esc.rl.ac.uk",
    port=389,
    getInfo=ldap3.GET_ALL_INFO)
c = ldap3.connection.Connection(
    s, autoBind=True, clientStrategy=ldap3.STRATEGY_SYNC)

search = functools.partial(
    c.search, ldap_search ["query"], ldap_search["filter"],
    ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
    attributes = [k for k, v in ldap_attributes.items() if v])

def pager(size=128):
    cookie = True
    result = search(pagedSize=size)
    yield from c.response
    while result and cookie:
        cookie = c.result["controls"]["1.2.840.113556.1.4.319"]["value"]["cookie"]
        result = search(pagedSize=size, pagedCookie=cookie)
        yield from c.response

for n, i in enumerate(pager()):
    print(n,i["attributes"])

c.unbind()
