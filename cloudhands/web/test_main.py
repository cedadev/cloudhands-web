#!/usr/bin/env python3
# encoding: UTF-8

import re
import unittest

from cloudhands.web.main import parser

class TopLevelTests(unittest.TestCase):

    def test_trivial(self):
        p = parser()
        rv = p.parse_args(["--version"])
        self.assertTrue(rv.version)

if __name__ == "__main__":
    unittest.main()
