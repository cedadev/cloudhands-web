#!/usr/bin/env python3
# encoding: UTF-8

from collections.abc import MutableMapping
from collections.abc import Sequence

import unittest
import uuid

import cloudhands.common
from cloudhands.common.fsm import CredentialState
from cloudhands.common.schema import DCStatus

from cloudhands.web.model import Page
from cloudhands.web.model import Region
from cloudhands.web.model import EmailIsUntrusted
from cloudhands.web.model import EmailIsTrusted
from cloudhands.web.model import EmailHasExpired
from cloudhands.web.model import EmailWasWithdrawn


class TestRegion(unittest.TestCase):

    def test_info_region_returns_named_dict(self):
        region = Region().name("test region")
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")
        rv = region.present(status, ("resource", "up"))
        self.assertTrue(rv)
        self.assertIsInstance(rv, MutableMapping)
        self.assertIsInstance(rv.name, Sequence)

    def test_info_region_makes_unique_names(self):
        region = Region().name("test region")
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")

        n = 10000
        for i in range(n):
            widget = region.present(status, ("resource", "up"))
            region.append(widget)

        names = {i.name for i in region}
        self.assertEqual(n, len(names))


class TestPage(unittest.TestCase):

    def test_push_simple_use(self):
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")
        p = Page()
        p.push(status)
