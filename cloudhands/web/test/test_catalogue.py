#!/usr/bin/env python3
# encoding: UTF-8

import unittest

import cloudhands.web.catalogue
from cloudhands.common.discovery import catalogue


class DiscoveryTest(unittest.TestCase):

    def test_default_catalogue_item(self):
        self.assertIn(cloudhands.web.catalogue.CatalogItemView, catalogue)
