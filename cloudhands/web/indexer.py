#!/usr/bin/env python3
# encoding: UTF-8

import argparse
import functools
import logging
import os
import sched
import sys

import ldap3
import whoosh.fields
import whoosh.index
import whoosh.qparser
import whoosh.query
import whoosh.writing

__doc__ = """
ldapsearch -x -H ldap://homer.esc.rl.ac.uk -s sub -b
'ou=ceda,ou=People,o=hpc,dc=rl,dc=ac,dc=uk'
'(&(objectclass=posixAccount)(objectclass=ldapPublicKey))'
"""

DFLT_IX = "cloudhands.wsh"
DFLT_IVAL_S = 1800

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

ldap_types = {
    "cn": whoosh.fields.ID(stored=True),
    "gecos": whoosh.fields.TEXT(stored=True),
    "uid": whoosh.fields.KEYWORD(stored=True),
    "uidNumber": whoosh.fields.NUMERIC(stored=True),
    "gidNumber": whoosh.fields.KEYWORD(stored=True),
    "sshPublicKey": whoosh.fields.STORED(),
}

def main(args):
    rv = 0

    try:
        os.mkdir(args.index)
    except OSError:
        pass

    schema = whoosh.fields.Schema(dn=whoosh.fields.ID(),
        **{k: v for k, v in ldap_types.items() if ldap_attributes[k]})

    ix = whoosh.index.create_in(args.index, schema=schema)
    ix = whoosh.index.open_dir(args.index)

    s = ldap3.server.Server(
        ldap_search["host"],
        port=int(ldap_search["port"]),
        getInfo=ldap3.GET_ALL_INFO)
    c = ldap3.connection.Connection(
        s, autoBind=True, clientStrategy=ldap3.STRATEGY_SYNC)

    search = functools.partial(
        c.search, ldap_search ["query"], ldap_search["filter"],
        ldap3.SEARCH_SCOPE_WHOLE_SUBTREE,
        attributes=[k for k, v in ldap_attributes.items() if v])

    def pager(size=128):
        cookie = True
        result = search(pagedSize=size)
        yield from c.response
        while result and cookie:
            cookie = c.result["controls"]["1.2.840.113556.1.4.319"]["value"]["cookie"]
            result = search(pagedSize=size, pagedCookie=cookie)
            yield from c.response

    writer = ix.writer()
    print("Indexing fields: {}".format(ix.schema.names()))
    for n, i in enumerate(pager()):
        writer.add_document(
            dn=i["dn"], **{k: v[0] if v else None for k, v in i["attributes"].items()})
    writer.commit(mergetype=whoosh.writing.CLEAR)

    c.unbind()

    qp = whoosh.qparser.QueryParser(
        "gecos", schema=ix.schema, termclass=whoosh.query.FuzzyTerm)
    q = qp.parse("David")
    with ix.searcher() as searcher:
        print("Searching {} records".format(searcher.doc_count()))
        #print(list(searcher.lexicon("gecos")))
        results = searcher.search(q, limit=20)
        print("Found {} hits".format(results.estimated_length()))
        print(*[i.fields() for i in results], sep="\n")

    return rv


def parser(descr=__doc__):
    rv = argparse.ArgumentParser(description=descr)
    rv.add_argument(
        "--version", action="store_true", default=False,
        help="Print the current version number")
    rv.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
    rv.add_argument(
        "--index", default=DFLT_IX,
        help="Set the path to the index directory [{}]".format(DFLT_IX))
    rv.add_argument(
        "--interval", default=DFLT_IVAL_S,
        help="Set the indexing interval (s) [{}]".format(DFLT_IVAL_S))


    return rv


def run():
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)

if __name__ == "__main__":
    run()
