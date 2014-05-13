#!/usr/bin/env python3
# encoding: UTF-8

from collections import OrderedDict
import unittest

from cloudhands.common.discovery import catalogue


class DiscoveryTest(unittest.TestCase):

    def test_default_catalogue_item(self):
        self.assertIsInstance(catalogue, OrderedDict)
