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

    def base_presenter(*args, **kwargs):
        return None

    def push(self, obj, session=None, user=None):
        rv = None
        presenter = self.presenters.get(type(obj), self.base_presenter)
        facet = presenter(self, obj)
        if facet:
            rv = facet.configure(session, user)
            self.append(rv)
        return rv

    presenters = {}


class InfoRegion(Region):

    def present_dcstatus(self, obj, session=None):
        return DCStatusUnknown(vars(obj))

    def present_pathinfo(self, obj, session=None):
        return obj.name("paths")

    presenters = {
        PathInfo: present_pathinfo,
        DCStatus: present_dcstatus}


class ItemsRegion(Region):

    def present_host(self, artifact):
        resources = [r for i in artifact.changes for r in i.resources]
        item = {k: getattr(artifact, k) for k in ("uuid", "name")}
        item["states"] = [artifact.changes[-1].state]
        item["data"] = {
            "organisation": artifact.organisation.name,
            "nodes": [i.name for i in resources if isinstance(i, Node)],
            "ips": [i.value for i in resources if isinstance(i, IPAddress)]
        }
        return HostData(item)

    def present_person(self, obj, session=None):
        item = {k: getattr(obj, k) for k in ("designator", "description")}
        item["data"] = {
            "keys": obj.keys,
        }
        return PersonData(item)

    presenters = {
        Host: present_host,
        Person: present_person}


class OptionsRegion(Region):

    def present_membership(self, artifact, session=None):
        item = {}
        item["data"] = {
            "role": artifact.role,
            "organisation": artifact.organisation.name
        }
        # TODO: move to MembershipXXX.load
        hf = HostData(organisation=artifact.organisation.name)
        item["_links"] = [
            Link(
                artifact.organisation.name, "collection",
                "/organisation/{}/hosts", artifact.organisation.name, "post",
                hf.parameters, "Add")
        ]

        return MembershipIsUntrusted(item)

    presenters = {Membership: present_membership}


class Page(object):

    def __init__(self, user=None):
        self.user = user
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
