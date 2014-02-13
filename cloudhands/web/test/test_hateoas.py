#!/usr/bin/env python3
# encoding: UTF-8

from collections import namedtuple
import re
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
<metal:item_list define-macro="item_list">
<ul>
<li tal:repeat="(itemId, item) items.items()"
tal:attributes="
id 'items-{}'.format(itemId);
">
<dl
tal:define="class_ item.__class__.__name__.lower()"
tal:condition="item['_links'] | None"
tal:attributes="
id item['uuid'];
class class_">
<div tal:omit-tag="" tal:repeat="key item.public">
<dt tal:content="key"></dt>
<dd tal:content="item[key]"></dd>
</div>
</dl>
<div tal:omit-tag="" tal:repeat="aspect item.get('_links', [])">
<a tal:content="aspect.action"
tal:attributes="
rel aspect.rel;
href aspect.typ.format(aspect.ref);
"></a>
</div>
</li>
</ul>
</metal:item_list>
""")

SimpleType = namedtuple("SimpleType", ["uuid", "name"])

class ObjectView(NamedDict):

    @property
    def public(self):
        return ["name"]


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
        item["_links"] = [
            Aspect(obj.name, "canonical", "/object/{}", obj.uuid,
            "get", [], "View")]
        return ObjectView(item)


class OptionsRegion(Region):

    @singledispatch
    def present(obj):
        return None


class PlainRegion(Region):

    @singledispatch
    def present(obj):
        return None

    @present.register(SimpleType)
    def present_objects(obj):
        item = {k: getattr(obj, k) for k in ("uuid", "name")}
        return ObjectView(item)


class TestFundamentals(unittest.TestCase):

    class TestPage(PageBase):

        plan = [("items", PlainRegion)]

    def test_views_without_links_are_not_displayed(self):
        objects = [
            SimpleType(uuid.uuid4().hex, "object-{:03}".format(n))
            for n in range(6)]
        p = TestFundamentals.TestPage()
        for o in objects:
            p.layout.items.push(o)
        rv = _viewMacro(**dict(p.termination()))
        self.assertNotIn("object-0", rv)


class TestItemListTemplate(unittest.TestCase):

    class TestPage(PageBase):

        plan = [
            ("info", InfoRegion),
            ("items", ItemsRegion),
            ("options", OptionsRegion)]

    def test_definition_list_has_class_and_id(self):
        objects = [
            SimpleType(uuid.uuid4().hex, "object-{:03}".format(n))
            for n in range(6)]
        p = TestItemListTemplate.TestPage()
        for o in objects:
            p.layout.items.push(o)
        rv = _viewMacro(**dict(p.termination()))
        self.assertTrue(re.search('<dl[^>]+class="objectview"', rv))
        self.assertTrue(re.search('<dl[^>]+id="[a-f0-9]{32}"', rv))

    def test_definition_list_contains_public_attributes(self):
        objects = [
            SimpleType(uuid.uuid4().hex, "object-{:03}".format(n))
            for n in range(6)]
        p = TestItemListTemplate.TestPage()
        for o in objects:
            p.layout.items.push(o)
        rv = _viewMacro(**dict(p.termination()))
        self.assertEqual(6, rv.count("<dt>name</dt>"))
        self.assertEqual(6, rv.count("<dd>"))

    def test_list_items_have_aspects(self):
        objects = [
            SimpleType(uuid.uuid4().hex, "object-{:03}".format(n))
            for n in range(6)]
        p = TestItemListTemplate.TestPage()
        for o in objects:
            p.layout.items.push(o)
        rv = _viewMacro(**dict(p.termination()))
        self.assertEqual(
            6, len(re.findall('<a[^>]+href="/object/[a-f0-9]{32}"', rv)))

    def test_print_render(self):
        objects = [
            SimpleType(uuid.uuid4().hex, "object-{:03}".format(n))
            for n in range(6)]
        p = TestItemListTemplate.TestPage()
        for o in objects:
            p.layout.items.push(o)
        rv = _viewMacro(**dict(p.termination()))
        print(rv)
