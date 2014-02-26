#!/usr/bin/env python3
# encoding: UTF-8

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

import cloudhands.web
from cloudhands.web.hateoas import Aspect
from cloudhands.web.hateoas import Contextual
from cloudhands.web.hateoas import PageBase
from cloudhands.web.hateoas import Parameter
from cloudhands.web.hateoas import Region
from cloudhands.web.hateoas import Validating
from cloudhands.web.indexer import Person


class VersionInfo(NamedDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update({i.__name__: i.__version__
                    for i in [cloudhands.web, cloudhands.common]})


class PathInfo(NamedDict):
    pass


class OrganisationInfo(NamedDict):
    pass


class HostView(Contextual, Validating, NamedDict):

    @property
    def parameters(self):
        return [
            Parameter("name", True, re.compile("\\w{8,128}$"), []),
            Parameter(
                "jvo", True, re.compile("\\w{6,64}$"),
                [self["organisation"]] if "organisation" in self else []),
            Parameter(
                "image", True, re.compile("\\S{6,64}$"), []),
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
            self["_links"].append(Aspect(
                "Send", "self", "/host/{}/commands", self["uuid"],
                "post", [], "stop"))
        elif state == "down":
            self["_links"].append(Aspect(
                "Send", "self", "/host/{}/commands", self["uuid"],
                "post", [], "start"))
        self["_links"].append(Aspect(
            "Settings", "parent", "/organisation/{}",
            self["data"]["organisation"], "get", [], "settings"))
        return self


class MembershipView(Contextual, NamedDict):

    @property
    def public(self):
        return ["organisation", "role"]


    def configure(self, session, user=None):
        hf = HostView(organisation=self["organisation"])
        #hf.configure(session, user)
        # Create new host, etc belongs in membership view
        self["_links"] = [
            Aspect(
                "New VM", "collection",
                "/organisation/{}/hosts", self["organisation"], "post",
                hf.parameters, "Create")]
        if self["role"] == "admin":
            self["_links"].append(
                Aspect(
                    "Invitation to {}".format(self["organisation"]),
                    "create-form",
                    "/organisation/{}/memberships", self["organisation"],
                    "post", [], "Create")
            )
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
            Aspect(
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
                    Aspect(
                        m.organisation.name, "parent",
                        "/membership/{}", m.uuid, "post",
                        self.parameters, "Invite")
                ]
        finally:
            return self


class ResourceView(NamedDict):
    pass

class GenericRegion(Region):

    @singledispatch
    def present(obj):
        return None

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
        item = {
            "modified": artifact.changes[-1].at,
            "organisation": artifact.organisation.name,
            "role": artifact.role,
            "states": [artifact.changes[-1].state],
            "uuid": artifact.uuid,
        }
        return MembershipView(item)

    @present.register(Organisation)
    def present_organisation(obj, isSelf=False):
        item = {k: getattr(obj, k) for k in ("uuid", "name")}
        rel = "self" if isSelf else "canonical"
        item["_links"] = [
            Aspect(obj.name, rel, "/organisation/{}", obj.name,
            "get", [], "View")]
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


class NavRegion(Region):

    @singledispatch
    def present(obj):
        return None

    @present.register(Organisation)
    def present_organisation(obj, isSelf=False):
        item = {k: getattr(obj, k) for k in ("uuid", "name")}
        rel = "self" if isSelf else "canonical"
        item["_links"] = [
            Aspect(obj.name, rel, "/organisation/{}", obj.name,
            "get", [], "View")]
        return OrganisationInfo(item)


class Page(PageBase):

    plan = [
        ("info", GenericRegion),
        ("nav", NavRegion),
        ("items", GenericRegion),
        ("options", GenericRegion)]

    def __init__(self, session=None, user=None, paths={}):
        super().__init__(session, user)

        self.layout.info.push(VersionInfo())
        self.layout.info.push(PathInfo(paths))


class PeoplePage(Page):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        link = Aspect(
            "Find people", "self",
            "/people", "people", "get",
            PersonView().parameters, "Search")
        self.layout.options.append(NamedDict({"_links": [link]}))
