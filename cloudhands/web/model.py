#!/usr/bin/env python3
# encoding: UTF-8

from collections import OrderedDict
from collections import namedtuple
import functools
from math import ceil
from math import log10
import re

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

import cloudhands.common
from cloudhands.common.schema import DCStatus
from cloudhands.common.schema import Host
from cloudhands.common.schema import Membership
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Node

from cloudhands.common.types import NamedDict
from cloudhands.common.types import NamedList

import cloudhands.web
from cloudhands.web.indexer import Person


Link = namedtuple(
    "Link", ["name", "rel", "typ", "ref", "method", "parameters", "action"])
Parameter = namedtuple("Parameter", ["name", "required", "regex", "values"])


class Fragment(NamedDict):

    @property
    def invalid(self):
        missing = [i for i in self.parameters
                   if i.required and i.name not in self]
        return missing or [
            i for i in self.parameters
            if i.name in self and not i.regex.match(self[i.name])]

    @property
    def parameters(self):
        return []

    def configure(self, session=None, user=None):
        return self


class VersionInfo(Fragment):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update({i.__name__: i.__version__
                    for i in [cloudhands.web, cloudhands.common]})


class PathInfo(Fragment):
    pass


class DCStatusUnknown(Fragment):
    pass


class DCStatusSaidUp(Fragment):
    pass


class DCStatusSaidDown(Fragment):
    pass


# TODO: Tidy up
class EmailIsUntrusted(Fragment):
    pass


class EmailIsTrusted(Fragment):
    pass


class EmailHasExpired(Fragment):
    pass


class EmailWasWithdrawn(Fragment):
    pass


class MembershipIsUntrusted(Fragment):
    pass


class MembershipIsTrusted(Fragment):
    pass


class MembershipHasExpired(Fragment):
    pass


class MembershipWasWithdrawn(Fragment):
    pass


class HostData(Fragment):

    @property
    def parameters(self):
        return [
            Parameter("hostname", True, re.compile("\\w{8,128}$"), []),
            Parameter(
                "organisation", True, re.compile("\\w{6,64}$"),
                [self["organisation"]] if "organisation" in self else [])
        ]


    def configure(self, session, user=None):
        state = self["states"][0].name
        self["_links"] = []

        if state == "up":
            self["_links"].append(
                Link("Send", "self", "/host/{}/commands", self["uuid"],
                "post", [], "stop"))
        elif state == "down":
            self["_links"].append(
                Link("Send", "self", "/host/{}/commands", self["uuid"],
                "post", [], "start"))
        self["_links"].append(
            Link("Settings", "parent", "/organisation/{}",
            self["data"]["organisation"], "get", [], "settings"))
        return self


class PersonData(Fragment):
    pass


class Region(NamedList):

    @singledispatch
    def present(obj):
        return None

    def push(self, obj, session=None, user=None):
        rv = None
        facet = Region.present(obj)
        if facet:
            rv = facet.configure(session, user)
            self.append(rv)
        return rv

    @present.register(DCStatus)
    def present_dcstatus(obj):
        return DCStatusUnknown(vars(obj))

    @present.register(PathInfo)
    def present_pathinfo(obj, session=None):
        return obj.name("paths")

    @present.register(Host)
    def present_host(artifact):
        resources = [r for i in artifact.changes for r in i.resources]
        item = {k: getattr(artifact, k) for k in ("uuid", "name")}
        item["states"] = [artifact.changes[-1].state]
        item["data"] = {
            "organisation": artifact.organisation.name,
            "nodes": [i.name for i in resources if isinstance(i, Node)],
            "ips": [i.value for i in resources if isinstance(i, IPAddress)]
        }
        return HostData(item)

    @present.register(Person)
    def present_person(obj):
        item = {k: getattr(obj, k) for k in ("designator", "description")}
        item["data"] = {
            "keys": obj.keys,
        }
        return PersonData(item)

    @present.register(Membership)
    def present_membership(artifact):
        item = {}
        item["data"] = {
            "role": artifact.role,
            "organisation": artifact.organisation.name
        }
        # TODO: move to MembershipXXX.configure
        hf = HostData(organisation=artifact.organisation.name)
        item["_links"] = [
            Link(
                artifact.organisation.name, "collection",
                "/organisation/{}/hosts", artifact.organisation.name, "post",
                hf.parameters, "Add")
        ]

        return MembershipIsUntrusted(item)


class Page(object):

    Layout = namedtuple("Layout", ["info", "items", "options"])

    def __init__(self, session=None, user=None):
        self.layout = Page.Layout(
            info=Region(
                [VersionInfo().name("versions")]).name("info"),
            items=Region().name("items"),
            options=Region().name("options"))
        for region in self.layout:
            region.push = functools.partial(
                region.push, session=session, user=user)

    def termination(self, info=None, items=None, options=None):
        for region, size in zip(self.layout, (info, items, options)):

            for n, facet in enumerate(region):
                size = size if size is not None else len(region)
                try:
                    template = "{{:0{0}}}_{{:0{0}}}".format(ceil(log10(size)))
                    facet.name(template.format(n + 1, size))
                except TypeError:
                    continue

            yield (region.name,
                   OrderedDict([(facet.name, facet) for facet in region]))
