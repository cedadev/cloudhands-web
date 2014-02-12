#!/usr/bin/env python3
# encoding: UTF-8

from collections import namedtuple
import unittest
import uuid

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from chameleon import PageTemplate

from cloudhands.common.types import NamedDict

from cloudhands.web.hateoas import Aspect
from cloudhands.web.hateoas import PageBase
from cloudhands.web.hateoas import Parameter
from cloudhands.web.hateoas import Region

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
<ul>
<li tal:repeat="(itemId, item) items.items()"
tal:attributes="
id 'items-{}'.format(itemId);
">
<div tal:omit-tag="" tal:repeat="aspect item.get('_links', [])">
<dl tal:attributes="
id item['uuid']" >
</dl>
</div>
</li>
</ul>
""")

SimpleType = namedtuple("SimpleType", ["uuid", "name"])

class ObjectView(NamedDict):
    pass


class InfoRegion(Region):

    @singledispatch
    def present(obj):
        return None


class ItemsRegion(Region):

    @singledispatch
    def present(obj):
        return None

    @present.register(SimpleType)
    def present_objects(obj):
        item = {k: getattr(obj, k) for k in ("uuid", "name")}
        return ObjectView(item)


class OptionsRegion(Region):

    @singledispatch
    def present(obj):
        return None

class TestPage(PageBase):

    plan = [
        ("info", InfoRegion),
        ("items", ItemsRegion),
        ("options", OptionsRegion)]

class TestsZPTForHTML5Presentation(unittest.TestCase):

    def test_simplerender(self):
        objects = [
            SimpleType(uuid.uuid4().hex, "object-{:03}".format(n))
            for n in range(6)]
        p = TestPage()
        for o in objects:
            p.layout.items.push(o)
        rv = _viewMacro(**dict(p.termination()))
        self.fail(rv)
