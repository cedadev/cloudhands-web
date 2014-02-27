#!/usr/bin/env python3
# encoding: UTF-8

from collections import namedtuple
import json
import re
import unittest
import uuid

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from chameleon import PageTemplate
import pkg_resources

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

"""

item_macro = PageTemplate(pkg_resources.resource_string(
    "cloudhands.web.templates", "item_list.pt"))
nav_macro = PageTemplate(pkg_resources.resource_string(
    "cloudhands.web.templates", "nav_list.pt"))
option_macro = PageTemplate(pkg_resources.resource_string(
    "cloudhands.web.templates", "option_list.pt"))

Ownership = namedtuple("Ownership", ["uuid", "limit", "level"])
SimpleType = namedtuple("SimpleType", ["uuid", "name"])


class TypesEncoder(json.JSONEncoder):

    def default(self, obj):
        try:
            return obj.pattern
        except AttributeError:
            return json.JSONEncoder.default(self, obj)

class ObjectView(NamedDict):

    @property
    def public(self):
        return ["name"]


class OwnershipView(NamedDict):

    @property
    def public(self):
        return ["level"]


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


class NavRegion(Region):

    @singledispatch
    def present(obj):
        return None

    @present.register(SimpleType)
    def present_objects(obj, isSelf=False):
        item = {k: getattr(obj, k) for k in ("uuid", "name")}
        rel = "self" if isSelf else "canonical"
        item["_links"] = [
            Aspect(obj.name, rel, "/object/{}", obj.uuid,
            "get", [], "View")]
        return ObjectView(item)


class OptionsRegion(Region):

    @singledispatch
    def present(obj):
        return None

    @present.register(Ownership)
    def present_objects(obj):
        item = vars(obj)
        item["_links"] = [
            # NB: Parameters drawn from View object if validating
            Aspect("New object", "create-form", "/bag", None, "post",
            [Parameter("name", True, re.compile("\\w{8,128}$"), [])],
            "Create")]
        return OwnershipView(item)


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
        rv = item_macro(**dict(p.termination()))
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
        rv = item_macro(**dict(p.termination()))
        self.assertTrue(re.search('<dl[^>]+class="objectview"', rv))
        self.assertTrue(re.search('<dl[^>]+id="[a-f0-9]{32}"', rv))

    def test_definition_list_contains_public_attributes(self):
        objects = [
            SimpleType(uuid.uuid4().hex, "object-{:03}".format(n))
            for n in range(6)]
        p = TestItemListTemplate.TestPage()
        for o in objects:
            p.layout.items.push(o)
        rv = item_macro(**dict(p.termination()))
        self.assertEqual(6, len(re.findall("<dt[^>]*>name</dt>", rv)))
        self.assertEqual(6, len(re.findall("<dd[^>]*>", rv)))

    def test_list_items_have_aspects(self):
        objects = [
            SimpleType(uuid.uuid4().hex, "object-{:03}".format(n))
            for n in range(6)]
        p = TestItemListTemplate.TestPage()
        for o in objects:
            p.layout.items.push(o)
        rv = item_macro(**dict(p.termination()))
        self.assertEqual(
            6, len(re.findall('<form[^>]+action="/object/[a-f0-9]{32}"', rv)))


class TestNavListTemplate(unittest.TestCase):

    class TestPage(PageBase):

        plan = [("nav", NavRegion)]

    def test_nav_section_exists(self):
        p = TestNavListTemplate.TestPage()
        p.layout.nav.push(SimpleType(uuid.uuid4().hex, "MARMITE"))
        rv = nav_macro(**dict(p.termination()))
        self.assertTrue(re.search(
            '<nav[^>]+class="pure-menu pure-menu-open"', rv))


    def test_menu_contains_each_element(self):
        p = TestNavListTemplate.TestPage()
        p.layout.nav.push(SimpleType(uuid.uuid4().hex, "MARMITE"))
        p.layout.nav.push(SimpleType(uuid.uuid4().hex, "BRANSTON"))
        rv = nav_macro(**dict(p.termination()))
        self.assertEqual(2, rv.count('<a rel="canonical" href="/object/'))
        self.assertIn(">MARMITE</a>", rv)
        self.assertIn(">BRANSTON</a>", rv)


    def test_self_link_shows_visited(self):
        p = TestNavListTemplate.TestPage()
        p.layout.nav.push(SimpleType(uuid.uuid4().hex, "MARMITE"))
        p.layout.nav.push(
            SimpleType(uuid.uuid4().hex, "BRANSTON"), isSelf=True)
        rv = nav_macro(**dict(p.termination()))
        self.assertEqual(1, rv.count('<a rel="canonical" href="/object/'))
        self.assertIn("pure-menu-selected", rv)


class TestOptionListTemplate(unittest.TestCase):

    class TestPage(PageBase):

        plan = [("options", OptionsRegion)]

    def test_definition_list_has_class_and_id(self):
        p = TestItemListTemplate.TestPage()
        p.layout.options.push(Ownership(uuid.uuid4().hex, 256, 18))
        rv = option_macro(**dict(p.termination()))
        self.assertTrue(re.search('<dl[^>]+class="ownershipview"', rv))
        self.assertTrue(re.search('<dl[^>]+id="[a-f0-9]{32}"', rv))

    def test_definition_list_contains_public_attributes(self):
        p = TestItemListTemplate.TestPage()
        p.layout.options.push(Ownership(uuid.uuid4().hex, 256, 18))
        rv = option_macro(**dict(p.termination()))
        self.assertEqual(1, rv.count("<dt>level</dt>"))
        self.assertEqual(1, rv.count("<dd>"))

    def test_list_items_have_aspects(self):
        p = TestItemListTemplate.TestPage()
        p.layout.options.push(Ownership(uuid.uuid4().hex, 256, 18))
        rv = option_macro(**dict(p.termination()))
        self.assertEqual(
            1, len(re.findall('<form[^>]+action="/bag"', rv)))

    def test_print_render(self):
        p = TestItemListTemplate.TestPage()
        p.layout.options.push(Ownership(uuid.uuid4().hex, 256, 18))
        data = dict(p.termination())
        rv = option_macro(**data)
        #print(rv)
        #print(json.dumps(data, cls=TypesEncoder))
