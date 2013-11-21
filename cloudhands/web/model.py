#!/usr/bin/env python3
# encoding: UTF-8

from collections import OrderedDict
from collections import namedtuple

import cloudhands.common
from cloudhands.common.schema import DCStatus
from cloudhands.common.schema import Host
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Node

from cloudhands.common.types import NamedDict
from cloudhands.common.types import NamedList

import cloudhands.web


Link = namedtuple("Link", ["rel", "typ", "ref", "method", "parameters"])

class Facet(NamedDict):

    def load(self, session=None):
        return self


class VersionsAreVisible(Facet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update({i.__name__: i.__version__
                    for i in [cloudhands.web, cloudhands.common]})


class DCStatusUnknown(Facet):
    pass


class DCStatusSaidUp(Facet):
    pass


class DCStatusSaidDown(Facet):
    pass


class EmailIsUntrusted(Facet):
    pass


class EmailIsTrusted(Facet):
    pass


class EmailHasExpired(Facet):
    pass


class EmailWasWithdrawn(Facet):
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

    handlers = {DCStatus: handle_dcstatus}


class PathsRegion(Region):

    def handle_dict(self, obj, state=None, session=None):
        return Facet(obj)

    handlers = {dict: handle_dict}

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
            Link("self", "/host", artifact.uuid, "get", []),
            Link("parent", "/organisation",
                 artifact.organisation.name, "get", [])
        ]
        return facet(item)

    handlers = {Host: handle_host}

class OptionsRegion(Region):
    pass

# TODO: class HostControl

class Page(object):

    def __init__(self):
        self.info = InfoRegion([
                VersionsAreVisible().name("versions")
            ]).name("info")
        self.paths = PathsRegion().name("paths")
        self.items = ItemsRegion().name("items")
        self.options = OptionsRegion().name("options")

    def termination(self, info=None, paths=None, items=None, options=None):
        for region, size in ((self.info, info), (self.paths, paths),
                             (self.items, items), (self.options, options)):

            for n, facet in enumerate(region):
                size = size if size is not None else len(region)
                try:
                    facet.name("{:05}_{:05}".format(n + 1, size))
                except TypeError:
                    continue

            yield (region.name,
                   OrderedDict([(facet.name, facet) for facet in region]))
