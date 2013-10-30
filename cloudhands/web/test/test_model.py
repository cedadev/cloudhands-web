#!/usr/bin/env python3
# encoding: UTF-8

import unittest

from cloudhands.common.fsm import CredentialState

from cloudhands.web.model import Page
from cloudhands.web.model import EmailIsUntrusted
from cloudhands.web.model import EmailIsTrusted
from cloudhands.web.model import EmailHasExpired
from cloudhands.web.model import EmailWasWithdrawn


class TestPage(unittest.TestCase):

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
