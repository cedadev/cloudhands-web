#!/usr/bin/env python3
# encoding: UTF-8

from collections import OrderedDict
from collections import namedtuple
from math import ceil
from math import log10
import re

import cloudhands.common
from cloudhands.common.schema import DCStatus
from cloudhands.common.schema import Host
from cloudhands.common.schema import Membership
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Node

from cloudhands.common.types import NamedDict
from cloudhands.common.types import NamedList

import cloudhands.web


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

    def load(self, session=None):
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


class Region(NamedList):

    def base_handler(*args, **kwargs):
        return None

    def push(self, obj, session=None):
        rv = None
        handler = self.handlers.get(type(obj), self.base_handler)
        facet = handler(self, obj, session)
        if facet:
            rv = facet.load(session)
            self.append(rv)
        return rv

    handlers = {}


class InfoRegion(Region):

    def handle_dcstatus(self, obj, session=None):
        return DCStatusUnknown(vars(obj))

    def handle_pathinfo(self, obj, session=None):
        return obj.name("paths")

    handlers = {
        PathInfo: handle_pathinfo,
        DCStatus: handle_dcstatus}


class ItemsRegion(Region):

    def handle_host(self, artifact, state, session=None):
        resources = [r for i in artifact.changes for r in i.resources]
        item = {k: getattr(artifact, k) for k in ("uuid", "name")}
        item["states"] = [artifact.changes[-1].state]
        item["data"] = {
            "nodes": [i.name for i in resources if isinstance(i, Node)],
            "ips": [i.value for i in resources if isinstance(i, IPAddress)]
        }
        item["_links"] = [
            # TODO: 'Start' or 'stop' actions
            Link("Edit", "self", "/host/{}", artifact.uuid, "get", [], "edit"),
            Link("Settings", "parent", "/organisation/{}",
                 artifact.organisation.name, "get", [], "settings")
        ]
        return HostData(item)

    handlers = {Host: handle_host}


class OptionsRegion(Region):

    def handle_membership(self, artifact, session=None):
        item = {}
        item["data"] = {
            "role": artifact.role,
            "organisation": artifact.organisation.name
        }
        hf = HostData(organisation=artifact.organisation.name).load(session)
        item["_links"] = [
            Link(
                artifact.organisation.name, "collection",
                "/organisation/{}/hosts", artifact.organisation.name, "post",
                hf.parameters, "Add")
        ]

        return MembershipIsUntrusted(item)

    handlers = {Membership: handle_membership}


class Page(object):

    def __init__(self):
        self.info = InfoRegion(
            [VersionInfo().name("versions")]).name("info")
        self.items = ItemsRegion().name("items")
        self.options = OptionsRegion().name("options")

    def termination(self, info=None, paths=None, items=None, options=None):
        for region, size in (
            (self.info, info), (self.items, items), (self.options, options)
        ):

            for n, facet in enumerate(region):
                size = size if size is not None else len(region)
                try:
                    template = "{{:0{0}}}_{{:0{0}}}".format(ceil(log10(size)))
                    facet.name(template.format(n + 1, size))
                except TypeError:
                    continue

            yield (region.name,
                   OrderedDict([(facet.name, facet) for facet in region]))
