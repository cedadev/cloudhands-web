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

    def test_info_region(self):
        region = Region().name("test region")
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")
        rv = region.present(status)
        self.assertTrue(rv)
        self.assertIsInstance(rv, MutableMapping)
        self.assertIsInstance(rv.name, Sequence)
        print(rv)

class TestPage(unittest.TestCase):

    def test_push_interface(self):
        status = DCStatus(
            uuid=uuid.uuid4().hex,
            model=cloudhands.common.__version__,
            uri="host.domain",
            name="DC under test")
        p = Page()
        p.push(status, ("resource", "unknown"))

        
    def test_credential_untrusted_emailisuntrusted(self):
        p = Page()
        p.configure(CredentialState.table, "untrusted")
        facet = next(iter(p.user))
        self.assertIsInstance(facet, EmailIsUntrusted)

    def test_credential_trusted_emailistrusted(self):
        p = Page()
        p.configure(CredentialState.table, "trusted")
        facet = next(iter(p.user))
        self.assertIsInstance(facet, EmailIsTrusted)

    def test_credential_expired_emailhasexpired(self):
        p = Page()
        p.configure(CredentialState.table, "expired")
        facet = next(iter(p.user))
        self.assertIsInstance(facet, EmailHasExpired)

    def test_credential_withdrawn_emailwaswithdrawn(self):
        p = Page()
        p.configure(CredentialState.table, "withdrawn")
        facet = next(iter(p.user))
        self.assertIsInstance(facet, EmailWasWithdrawn)
