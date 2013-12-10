#!/usr/bin/env python3
# encoding: UTF-8

import tempfile
import unittest

import whoosh.fields
from whoosh.query import Or
from whoosh.query import FuzzyTerm
from whoosh.query import Term

from cloudhands.web.indexer import create as create_index
from cloudhands.web.indexer import indexer
from cloudhands.web.indexer import ldap_types
from cloudhands.web.indexer import people
from cloudhands.web.indexer import Person


class TestIndexer(unittest.TestCase):

    def test_custom_search(self):

        with tempfile.TemporaryDirectory() as td:
            ix = create_index(td, descr=whoosh.fields.TEXT(stored=True))
            wrtr = ix.writer()

            for i in range(10):
                wrtr.add_document(id=str(i), descr="User {}".format(i))
            wrtr.commit()

            srch = ix.searcher()
            query = Or([Term("id", "0"), Term("id", "9")])
            hits = srch.search(query)
            self.assertEqual(2, len(hits))

    def test_simple_people_search(self):

        with tempfile.TemporaryDirectory() as td:
            ix = create_index(td, **ldap_types)
            wrtr = ix.writer()

            for i in range(10):
                wrtr.add_document(id=str(i), gecos="User {}".format(i))
            wrtr.commit()

            ppl = list(people(td, "User"))
            self.assertEqual(10, len(ppl))
            self.assertTrue(all(isinstance(i, Person) for i in ppl))

    def test_custom_people_search(self):

        with tempfile.TemporaryDirectory() as td:
            ix = create_index(td, descr=whoosh.fields.TEXT(stored=True))
            wrtr = ix.writer()

            for i in range(10):
                wrtr.add_document(id=str(i), descr="User {}".format(i))
            wrtr.commit()

            ppl = list(people(td, "User", "descr"))
            self.assertEqual(10, len(ppl))
