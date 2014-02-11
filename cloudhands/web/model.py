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
from cloudhands.common.schema import Host
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Membership
from cloudhands.common.schema import Node
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import Resource
from cloudhands.common.schema import State
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.common.types import NamedDict
from cloudhands.common.types import NamedList

import cloudhands.web
from cloudhands.web.indexer import Person


Link = namedtuple(
    "Link", ["name", "rel", "typ", "ref", "method", "parameters", "action"])
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


class VersionInfo(NamedDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update({i.__name__: i.__version__
                    for i in [cloudhands.web, cloudhands.common]})


class PathInfo(NamedDict):
    pass


class HostView(Contextual, Validating, NamedDict):

    @property
    def parameters(self):
        return [
            Parameter("name", True, re.compile("\\w{8,128}$"), []),
            Parameter(
                "jvo", True, re.compile("\\w{6,64}$"),
                [self["organisation"]] if "organisation" in self else []),
            Parameter("description", False, re.compile("\\w{8,128}$"), []),
            Parameter(
                "cpu", False, re.compile("\\w{8,128}$"),
                ["1", "2", "3", "4"]),
            Parameter(
                "ram", False, re.compile("\\w{8,128}$"),
                [1024]),
        ]

    def configure(self, session, user=None):
        state = self["states"][0].name
        self["_links"] = []

        if state == "up":
            self["_links"].append(Link(
                "Send", "self", "/host/{}/commands", self["uuid"],
                "post", [], "stop"))
        elif state == "down":
            self["_links"].append(Link(
                "Send", "self", "/host/{}/commands", self["uuid"],
                "post", [], "start"))
        self["_links"].append(Link(
            "Settings", "parent", "/organisation/{}",
            self["data"]["organisation"], "get", [], "settings"))
        return self


class MembershipView(Contextual, NamedDict):

    def configure(self, session, user=None):
        hf = HostView(organisation=self["data"]["organisation"])  # FIXME
        # Create new host, etc belongs in membership view
        self["_links"] = [
            Link(
                self["data"]["organisation"], "collection",
                "/organisation/{}/hosts", self["data"]["organisation"], "post",
                hf.parameters, "Create")
        ]
        return self


class OrganisationView(Contextual, NamedDict):
    """
    TODO: consider folding this into MembershipView?
    """

    def configure(self, session, user):
        prvlg = session.query(Membership).join(Organisation).join(
            Touch).join(User).filter(
            User.id == user.id).filter(
            Organisation.name == self["data"]["name"]).filter(
            Membership.role == "admin").first()
        if not prvlg or not prvlg.changes[-1].state.name == "active":
            return self

        self["_links"] = [
            Link(
                "Invitation to {}".format(self["data"]["name"]), "self",
                "/organisation/{}/memberships", self["data"]["name"], "post",
                [], "Create")
        ]
        return self


class PersonView(Contextual, Validating, NamedDict):
    """
    Used for free-text search of contacts list
    """

    @property
    def parameters(self):
        return [
            Parameter(
                "description", True, re.compile("\\w{2,}$"),
                [self["description"]] if "description" in self else []),
            Parameter(
                "designator", True, re.compile("\\w{8,}$"),
                [self["designator"]] if "designator" in self else [])
        ]

    def configure(self, sn, user):
        """
        Add links to Memberships in 'invited' state created by this user
        """
        try:
            m = sn.query(Membership).join(Touch).join(User).join(State).filter(
                User.id == user.id).filter(
                State.fsm == "membership").filter(
                State.name == "invite").first()
        except AttributeError:
            # Lack session or user
            pass
        else:
            if m is not None:
                self["_links"] = [
                    Link(
                        m.organisation.name, "parent",
                        "/membership/{}", m.uuid, "post",
                        self.parameters, "Invite")
                ]
        finally:
            return self


class ResourceView(NamedDict):
    pass


class Region(NamedList):

    @singledispatch
    def present(obj):
        return None

    def push(self, obj, session=None, user=None):
        view = Region.present(obj)
        if isinstance(view, Contextual):
            view.configure(session, user)
        if view:
            self.append(view)
        return view

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
        return HostView(item)

    @present.register(Membership)
    def present_membership(artifact):
        item = {}
        item["states"] = [artifact.changes[-1].state]
        item["data"] = {
            "modified": artifact.changes[-1].at,
            "role": artifact.role,
            "organisation": artifact.organisation.name
        }
        return MembershipView(item)

    @present.register(Organisation)
    def present_organisation(obj):
        item = {}
        item["data"] = {
            "name": obj.name,
        }
        return OrganisationView(item)

    @present.register(PathInfo)
    def present_pathinfo(obj):
        return obj.name("paths")

    @present.register(Person)
    def present_person(obj):
        item = {k: getattr(obj, k) for k in ("designator", "description")}
        item["data"] = {
            "keys": obj.keys,
        }
        return PersonView(item)

    @present.register(Resource)
    def present_resource(obj):
        item = {k: getattr(obj, k, "") for k in ("name", "value", "uri")}
        item["data"] = {
            "type": type(obj).__name__
        }
        return ResourceView(item)

    @present.register(VersionInfo)
    def present_pathinfo(obj):
        return obj.name("versions")


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


class Page(PageBase):

    plan = [("info", Region), ("items", Region), ("options", Region)]

    def __init__(self, session=None, user=None, paths={}):
        super().__init__(session, user)

        self.layout.info.push(VersionInfo())
        self.layout.info.push(PathInfo(paths))


class PeoplePage(Page):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        link = Link(
            "Find people", "self",
            "/people", "people", "get",
            PersonView().parameters, "Search")
        self.layout.options.append(NamedDict({"_links": [link]}))
