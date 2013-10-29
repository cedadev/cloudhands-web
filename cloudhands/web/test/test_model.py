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
        widgets = [i for v in p.user.values() for i in v]
        self.assertIn(EmailIsUntrusted, widgets)
        self.assertNotIn(EmailIsTrusted, widgets)
        self.assertNotIn(EmailHasExpired, widgets)
        self.assertNotIn(EmailWasWithdrawn, widgets)

    def test_credential_trusted_emailistrusted(self):
        p = Page()
        p.configure(CredentialState.table, "trusted")
        widgets = [i for v in p.user.values() for i in v]
        self.assertNotIn(EmailIsUntrusted, widgets)
        self.assertIn(EmailIsTrusted, widgets)
        self.assertNotIn(EmailHasExpired, widgets)
        self.assertNotIn(EmailWasWithdrawn, widgets)
