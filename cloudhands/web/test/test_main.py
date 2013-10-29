#!/usr/bin/env python3
# encoding: UTF-8

import re
import unittest

import cloudhands.web
from cloudhands.web.main import parser
from cloudhands.web.main import top_page


class TopLevelTests(unittest.TestCase):

    def test_version_option(self):
        p = parser()
        rv = p.parse_args(["--version"])
        self.assertTrue(rv.version)

    def test_version_json(self):
        self.assertEqual(
            cloudhands.web.__version__,
            top_page(None)["versions"]["cloudhands.web"])

if __name__ == "__main__":
    unittest.main()
