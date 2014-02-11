#!/usr/bin/env python3
# encoding: UTF-8

import unittest

from chameleon import PageTemplate

from cloudhands.web.model import Fragment
from cloudhands.web.model import Page

"""
info
====

self: The 'self' link for the primary object
names: A mapping of object types to URLS (even python://collections.abc.Sequence)
versions: Versions of backend packages
nav: links to other objects with a relationship

items
=====

A sequence of existing objects
Each object has a relationship with the primary object
Each object shows its data
Each object identifies its traits (map to one or more icons)

options
=======
A sequence of available operations
"""

_viewMacro = PageTemplate("""
Hiya!
""")

class TestView(Fragment):
    pass

class TestPage(Page):
    pass

class TestsZPTForHTML5Presentation(unittest.TestCase):

    def test_simplerender(self):
        self.fail(_viewMacro(**{"name": None}))
