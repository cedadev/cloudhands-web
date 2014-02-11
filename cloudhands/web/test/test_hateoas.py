#!/usr/bin/env python3
# encoding: UTF-8

from collections import namedtuple
import unittest

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from chameleon import PageTemplate

from cloudhands.common.types import NamedDict

from cloudhands.web.model import Page
from cloudhands.web.model import Region

"""
info
====

self: The 'self' link for the primary object
names: A mapping of object types to URLS (even python://collections.abc.Sequence)
paths: A mapping of root paths to URLS
versions: Versions of backend packages

nav
===

Links to other objects with a relationship

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

TestType = namedtuple("TestType", ["uuid", "name"])

class TestView(NamedDict):
    pass


class TestRegion(Region):

    @singledispatch
    def present(obj):
        return None

    @present.register(TestType)
    def present_test_type(artifact):
        item = {k: getattr(artifact, k) for k in ("uuid", "name")}
        return TestView(item)


class TestPage(Page):

    plan = [
        ("info", TestRegion),
        ("items", TestRegion),
        ("options", TestRegion)]

class TestsZPTForHTML5Presentation(unittest.TestCase):

    def test_simplerender(self):
        self.fail(_viewMacro(**{"name": None}))
