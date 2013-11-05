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
    def configure(self, artifact, state=None):
        return False

    @configure.register(DCStatus)
    def configure(self, artifact, state=None):
        return True

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
        self.navi = NamedList().name("navi")
        self.info = NamedList([
            VersionsAreVisible().name("versions")
        ]).name("info")
        self.user = NamedList().name("user")
        self.evts = NamedList().name("evts")

    def configure(self, fsm, value, session=None, *args, **kwargs):
        for spec, picked in [
            (self._navi, self.navi), (self._info, self.info),
            (self._user, self.user), (self._evts, self.evts)
        ]:
            try:
                picked.extend([
                    class_(*args, **kwargs).name(fsm).load(session)
                    for class_ in spec[(fsm, value)]])
            except KeyError:
                pass

    def push(self, artifact, state):
        for region in [
            self.navi, self.info, self.user, self.evts]:
            pass

    def dump(self):
        return [(region.name, OrderedDict([(facet.name, facet)
                for facet in region]))
                for region in (self.navi, self.info, self.user, self.evts)]
