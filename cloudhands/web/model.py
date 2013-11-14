#!/usr/bin/env python3
# encoding: UTF-8

from collections import OrderedDict
try:
    from functools import singledispatch  # Python 3.4
except ImportError:
    from singledispatch import singledispatch

import cloudhands.common
from cloudhands.common.schema import DCStatus
from cloudhands.common.schema import Host
from cloudhands.common.types import NamedDict
from cloudhands.common.types import NamedList

import cloudhands.web


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

    @singledispatch
    def present(self, artifact, session=None, state=None):
        return None

    @present.register(DCStatus)
    def present(self, artifact, state, session=None):
        if not state:
            rv = DCStatusUnknown(vars(artifact))
        elif state[1] == "down":
            rv = DCStatusSaidDown(vars(artifact))
        elif state[1] == "up":
            rv = DCStatusSaidUp(vars(artifact))
        else:
            rv = DCStatusUnknown(vars(artifact))

        return rv.name("{}_{:05}".format(self.name, len(self))).load(session)


class HostCollection(Region):

    @singledispatch
    def present(self, artifact, session=None, state=None):
        return None

    @present.register(Host)
    def present(self, artifact, state, session=None):
        try:
            value = state[1]
            facet = {
                "down": HostIsDown,
                "up": HostIsUp,
            }.get(value, HostIsUnknown)

        except TypeError:
            facet = HostIsUnknown

        rv = facet(vars(artifact))
        return self.load_facet(rv, session)


class Page(object):

    def __init__(self):
        self.regions = [
            Region([
                VersionsAreVisible().name("versions")
            ]).name("info"),
            HostCollection().name("items"),
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
