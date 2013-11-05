#!/usr/bin/env python3
# encoding: UTF-8

from collections import OrderedDict
from functools import singledispatch

import cloudhands.common
from cloudhands.common.schema import DCStatus
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


class Region(NamedList):

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

class Page(object):

    _navi = {}
    _info = {
        ("resource", "unknown"): [DCStatusUnknown],
        ("resource", "down"): [DCStatusSaidDown],
        ("resource", "up"): [DCStatusSaidUp],
    }
    _user = {
        ("credential", "untrusted"): [EmailIsUntrusted],
        ("credential", "trusted"): [EmailIsTrusted],
        ("credential", "expired"): [EmailHasExpired],
        ("credential", "withdrawn"): [EmailWasWithdrawn],
    }
    _evts = {}

    def __init__(self):
        self.navi = Region().name("navi")
        self.info = Region([
            VersionsAreVisible().name("versions")
        ]).name("info")
        self.user = Region().name("user")
        self.evts = Region().name("evts")

    def push(self, artifact, state=None):
        for region in [
            self.navi, self.info, self.user, self.evts]:
            widget = region.present(artifact, state)
            if widget:
                region.append(widget)

    def dump(self):
        return [(region.name, OrderedDict([(widget.name, widget)
                for widget in region]))
                for region in (self.navi, self.info, self.user, self.evts)]
