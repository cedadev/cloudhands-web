#!/usr/bin/env python3
# encoding: UTF-8

from collections import OrderedDict
from collections import namedtuple
from math import ceil
from math import log10

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


class Facet(NamedDict):

    def load(self, session=None):
        return self


class VersionInfo(Facet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update({i.__name__: i.__version__
                    for i in [cloudhands.web, cloudhands.common]})


class PathInfo(Facet):
    pass


class DCStatusUnknown(Facet):
    pass


class DCStatusSaidUp(Facet):
    pass


class DCStatusSaidDown(Facet):
    pass


# TODO: Tidy up
class EmailIsUntrusted(Facet):
    pass


class EmailIsTrusted(Facet):
    pass


class EmailHasExpired(Facet):
    pass


class EmailWasWithdrawn(Facet):
    pass


class MembershipIsUntrusted(Facet):
    pass


class MembershipIsTrusted(Facet):
    pass


class MembershipHasExpired(Facet):
    pass


class MembershipWasWithdrawn(Facet):
    pass


class HostIsDown(Facet):
    pass


class HostIsUnknown(Facet):
    pass


class HostIsUp(Facet):
    pass


class Region(NamedList):

    def base_handler(*args, **kwargs):
        return None

    def push(self, obj, state=None, session=None):
        rv = None
        handler = self.handlers.get(type(obj), self.base_handler)
        facet = handler(self, obj, state, session)
        if facet:
            rv = facet.load(session)
            self.append(rv)
        return rv

    handlers = {}


class InfoRegion(Region):

    def handle_dcstatus(self, obj, state, session=None):
        if not state:
            rv = DCStatusUnknown(vars(obj))
        elif state[1] == "down":
            rv = DCStatusSaidDown(vars(obj))
        elif state[1] == "up":
            rv = DCStatusSaidUp(vars(obj))
        else:
            rv = DCStatusUnknown(vars(obj))

        return rv

    def handle_pathinfo(self, obj, state=None, session=None):
        return obj.name("paths")

    handlers = {
        PathInfo: handle_pathinfo,
        DCStatus: handle_dcstatus}


class ItemsRegion(Region):

    def handle_host(self, artifact, state, session=None):
        try:
            value = state[1]
            facet = {
                "down": HostIsDown,
                "up": HostIsUp,
            }.get(value, HostIsUnknown)

        except TypeError:
            facet = HostIsUnknown

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
        return facet(item)

    handlers = {Host: handle_host}


class OptionsRegion(Region):

    def handle_membership(self, artifact, state, session=None):
        try:
            value = state[1]
            facet = {
                "granted": MembershipIsTrusted,
                "expired": MembershipHasExpired,
                "withdrawn": MembershipWasWithdrawn,
            }.get(value, MembershipIsUntrusted)

        except TypeError:
            facet = MembershipIsUntrusted

        item = {}
        item["data"] = {
            "role": artifact.role,
            "organisation": artifact.organisation.name
        }
        item["_links"] = [
            Link(
                "New host", "collection", "/organisation/{}/hosts",
                artifact.organisation.name, "post",
                [
                    Parameter("hostname", True, "", []),
                ], "Add")
        ]

        return facet(item)

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
