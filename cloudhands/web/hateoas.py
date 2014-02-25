#!/usr/bin/env python3
# encoding: UTF-8

from collections import OrderedDict
from collections import namedtuple
import functools
from math import ceil
from math import log10

from cloudhands.common.types import NamedDict
from cloudhands.common.types import NamedList


Aspect = namedtuple(
    "Aspect", ["name", "rel", "typ", "ref", "method", "parameters", "action"])
Parameter = namedtuple("Parameter", ["name", "required", "regex", "values"])


class Validating:

    @property
    def parameters(self):
        return []

    @property
    def invalid(self):
        missing = [i for i in self.parameters
                   if i.required and i.name not in self]
        return missing or [
            i for i in self.parameters
            if i.name in self and not i.regex.match(self[i.name])]


class Contextual:

    def configure(self, session=None, user=None):
        return self


class Region(NamedList):

    @staticmethod
    def present(obj):
        return None

    def push(self, obj, session=None, user=None, **kwargs):
        view = self.__class__.present(obj, **kwargs)
        if isinstance(view, Contextual):
            view.configure(session, user)
        if view:
            self.append(view)
        return view


class PageBase:

    plan = []

    def __init__(self, session=None, user=None, paths={}):
        Layout = namedtuple("Layout", [n for n, c in self.plan])
        self.layout = Layout(
            **{name: typ().name(name) for name, typ in self.plan})

        # Bake in session and user to regions
        for region in self.layout:
            region.push = functools.partial(
                region.push, session=session, user=user)

    def termination(self, **kwargs):
        for region in self.layout:
            size = kwargs.get(region.name, len(region))
            for n, facet in enumerate(region):
                try:
                    template = "{{:0{0}}}_{{:0{0}}}".format(ceil(log10(size)))
                    facet.name(template.format(n + 1, size))
                except TypeError:
                    continue

            yield (region.name,
                   OrderedDict([(facet.name, facet) for facet in region]))
