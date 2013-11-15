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


Link = namedtuple("Link", ["rel", "typ", "ref"])

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

    def load_facet(self, obj, session):
        return obj.name("{}_{:05}".format(self.name, len(self))).load(session)

    def present(self, artifact, state=None, session=None):
        return self.presenters.get(
            type(artifact), self.present_none)(self, artifact, state, session)

    def present_none(self, *args, **kwargs):
        return None


class InfoCollection(Region):

    def present_dcstatus(self, artifact, state, session=None):
        if not state:
            rv = DCStatusUnknown(vars(artifact))
        elif state[1] == "down":
            rv = DCStatusSaidDown(vars(artifact))
        elif state[1] == "up":
            rv = DCStatusSaidUp(vars(artifact))
        else:
            rv = DCStatusUnknown(vars(artifact))

        return self.load_facet(rv, session)

    presenters = {DCStatus: present_dcstatus}


class HostCollection(Region):

    def present_host(self, artifact, state, session=None):
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
        item["ips"] = [i.value for i in resources if isinstance(i, IPAddress)]
        item["nodes"] = [i.name for i in resources if isinstance(i, Node)]
        item["_links"] = [
            Link("self", "/host", artifact.uuid),
            Link("parent", "/organisation", artifact.organisation.name)]
        return self.load_facet(facet(item), session)

    presenters = {Host: present_host}


class Page(object):

    def __init__(self):
        self.regions = [
            InfoCollection([
                VersionsAreVisible().name("versions")
            ]).name("info")
        ]

    def push(self, artifact, state=None):
        for region in self.regions:
            widget = region.present(artifact, state)
            if widget:
                region.append(widget)

    def dump(self):
        return [(region.name, OrderedDict([(widget.name, widget)
                for widget in region]))
                for region in self.regions]


class HostsPage(Page):

    def __init__(self):
        self.regions = [
            InfoCollection([
                VersionsAreVisible().name("versions")
            ]).name("info"),
            HostCollection().name("items"),
        ]

