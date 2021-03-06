#!/usr/bin/env python3
# encoding: UTF-8

from collections import OrderedDict
import datetime
import re
import uuid

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from pyramid.httpexceptions import HTTPForbidden

import cloudhands.common
from cloudhands.common.schema import Appliance
from cloudhands.common.schema import BcryptedPassword
from cloudhands.common.schema import CatalogueChoice
from cloudhands.common.schema import EmailAddress
from cloudhands.common.schema import Host
from cloudhands.common.schema import Label
from cloudhands.common.schema import IPAddress
from cloudhands.common.schema import Membership
from cloudhands.common.schema import NATRouting
from cloudhands.common.schema import Node
from cloudhands.common.schema import Organisation
from cloudhands.common.schema import PosixGId
from cloudhands.common.schema import PosixUIdNumber
from cloudhands.common.schema import PosixUId
from cloudhands.common.schema import ProviderReport
from cloudhands.common.schema import PublicKey
from cloudhands.common.schema import Registration
from cloudhands.common.schema import Resource
from cloudhands.common.schema import State
from cloudhands.common.schema import Subscription
from cloudhands.common.schema import Touch
from cloudhands.common.schema import User

from cloudhands.common.types import NamedDict

import cloudhands.web
from cloudhands.web.hateoas import Action
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


class PageInfo(NamedDict):

    @property
    def public(self):
        return ["title", "refresh"]


class PathInfo(NamedDict):
    pass


class ResourceInfo(OrderedDict, NamedDict):

    @property
    def public(self):
        return [i for i in self.keys() if i != "uuid"]


class EventInfo(NamedDict):

    @property
    def public(self):
        return ["at", "user", "event", "resources"]


class FlashInfo(NamedDict):

    @property
    def public(self):
        return ["comment", "exception", "message"]


class OrganisationInfo(NamedDict):
    pass


class PublicKeyInfo(ResourceInfo): pass


class ApplianceView(Contextual, Validating, NamedDict):

    @property
    def public(self):
        return ["name", "latest", "ips"]

    @property
    def parameters(self):
        return [
            Parameter("name", True, re.compile("\\w{8,128}$"), [], ""),
            Parameter(
                "jvo", True, re.compile("\\w{6,64}$"),
                [self["organisation"]] if "organisation" in self else [], ""),
            Parameter(
                "image", True, re.compile("[\\S ]{6,64}$"),
                getattr(self, "images", []), ""),
            Parameter("description", False, re.compile("\\w{8,128}$"), [], ""),
        ]

    def configure(self, session, user=None):
        self["_links"] = []

        subs = session.query(Subscription).join(Organisation).filter(
            Organisation.name==self["organisation"]).first()
        if subs:
           self.images = [i.name for i in subs.changes[-1].resources]

        try:
            state = self["latest"].state.name
        except KeyError:
            # Not a live object
            return self

        if state in ("requested", "configuring"):
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_delete").parameters,
                "Cancel"))
        elif state in (
            "pre_provision", "provisioning", "pre_operational",
            "pre_start", "pre_check",
        ):
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_check").parameters,
                "Check"))
        elif state in (
            "operational",
        ):
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_check").parameters,
                "Check"))
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_start").parameters,
                "Start"))
        elif state in (
            "running",
        ):
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_check").parameters,
                "Check"))
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_stop").parameters,
                "Stop"))
        elif state in (
            "pre_stop", "stopped"
        ):
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_check").parameters,
                "Check"))
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_delete").parameters,
                "Delete"))
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_start").parameters,
                "Start"))
        elif state in ("pre_delete", "deleting"):
            self["_links"].append(Action(
                "_hidden", "canonical", "/appliance/{}", self["uuid"],
                "post", StateView(fsm="appliance", name="pre_check").parameters,
                "Check"))
        return self


class BcryptedPasswordView(Validating, NamedDict):

    @property
    def public(self):
        return []

    @property
    def parameters(self):
        return [
            Parameter(
                "password", True, re.compile(
                    "^(?=.*\\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[^a-zA-Z0-9])"
                    "(?!.*\\s).{8,20}$"
                ),[],
                """
                Passwords are between 8 and 20 characters in length.
                They must contain:
                <ul>
                <li>at least one lowercase letter</li>
                <li>at least one uppercase letter</li>
                <li>at least one numeric digit</li>
                <li>at least one special character</li>
                </ul>
                They cannot contain whitespace.
                """),
        ]

class HostView(Contextual, Validating, NamedDict):

    @property
    def public(self):
        return ["name", "latest", "ips"]

    @property
    def parameters(self):
        return [
            Parameter("name", True, re.compile("\\w{8,128}$"), [], ""),
            Parameter(
                "jvo", True, re.compile("\\w{6,64}$"),
                [self["organisation"]] if "organisation" in self else [], ""),
            Parameter(
                "image", True, re.compile("[\\S ]{6,64}$"),
                getattr(self, "images", []), ""),
            Parameter("description", False, re.compile("\\w{8,128}$"), [], ""),
            Parameter(
                "cpu", False, re.compile("\\d{1,2}$"),
                ["1", "2", "3", "4"], ""),
            Parameter(
                "ram", False, re.compile("\\d{3,4}$"),
                ["1024"], ""),
        ]

    def configure(self, session, user=None):
        self["_links"] = []

        subs = session.query(Subscription).join(Organisation).filter(
            Organisation.name==self["organisation"]).first()
        if subs:
           self.images = [i.name for i in subs.changes[-1].resources]

        try:
            state = self["latest"].state.name
        except KeyError:
            # Not a live object
            return self

        if state == "requested":
            self["_links"].append(Action(
                "Command", "canonical", "/host/{}", self["uuid"],
                "post", StateView(fsm="host", name="deleting").parameters,
                "cancel"))
        elif state == "scheduling":
            self["_links"].append(Action(
                "Command", "canonical", "/host/{}", self["uuid"],
                "get", [], "check"))
        elif state == "unknown":
            self["_links"].append(Action(
                "Command", "canonical", "/host/{}", self["uuid"],
                "post", StateView(fsm="host", name="deleting").parameters,
                "stop"))
        elif state == "up":
            self["_links"].append(Action(
                "Command", "canonical", "/host/{}", self["uuid"],
                "post", [], "stop"))
        elif state == "deleting":
            self["_links"].append(Action(
                "Command", "canonical", "/host/{}", self["uuid"],
                "get", [], "check"))
        elif state == "down":
            self["_links"].append(Action(
                "Command", "canonical", "/host/{}", self["uuid"],
                "post", [], "start"))
        return self


class LabelView(Validating, NamedDict):

    @property
    def public(self):
        return ["name", "description"]

    @property
    def parameters(self):
        return [
            Parameter(
                "name", True, re.compile("[\\w-]{2,}$"),
                [self["name"]] if "name" in self else [], ""),
            Parameter(
                "description", True, re.compile("[\\w ]{8,}$"),
                [self["description"]] if "description" in self else [], ""),
        ]


class MembershipView(Contextual, Validating, NamedDict):

    @property
    def public(self):
        return ["organisation", "role"]

    @property
    def parameters(self):
        return [
            Parameter(
                "username", True, re.compile("\\w{8,10}$"),
                [self["username"]] if self.get("username", None) else [],
                """
                Please choose a name 8 to 10 characters long.
                """),
            Parameter(
                "surname", True, re.compile("\\w{2,32}$"),
                [self["surname"]] if self.get("surname", None) else [],
                ""),
            Parameter(
                "email", True, re.compile("[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]"
                "+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\\.[a-zA-Z0-9]"
                "(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+"
                # http://www.w3.org/TR/html5/forms.html#valid-e-mail-address
                ),
                [self["email"]] if self.get("email", None) else [],
                """
                We will send instructions to this address to activate the account.
                """),
        ]

    def configure(self, session, user=None):
        #hf = HostView(organisation=self["organisation"])
        #hf.configure(session, user)
        # Create new host, etc belongs in membership view
        self["_links"] = []
        if self["role"] == "admin":
            self["_links"].append(
                Action(
                    "Invitation to {}".format(self["organisation"]),
                    "create-form",
                    "/organisation/{}/memberships", self["organisation"],
                    "post", self.parameters, "Create")
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
        if not prvlg or prvlg.changes[-1].state.name in (
            "created", "invited", "expired", "withdrawn"
        ):
            return self

        self["_links"] = [
            Action(
                "Invitation to {}".format(self["data"]["name"]), "self",
                "/organisation/{}/memberships", self["data"]["name"], "post",
                [], "Create")
        ]
        return self


class PosixUIdView(Contextual, Validating, NamedDict):

    @property
    def public(self):
        return ["name"]

    @property
    def parameters(self):
        return [
            Parameter(
                "name", True, re.compile("\\w{8,}$"), [], ""
            )
        ]

    def configure(self, session, user):
        self["_links"] = []
        if not self["name"]:
            self["_links"].append(
                Action("Select account name", "create-form", "#", "",
                "post", self.parameters, "Ok"))


class PersonView(Validating, NamedDict):
    """
    Used for free-text search of contacts list
    """

    @property
    def parameters(self):
        return [
            Parameter(
                "description", True, re.compile("\\w{2,}$"),
                [self["description"]] if "description" in self else [], ""),
            Parameter(
                "designator", True, re.compile("\\w{8,}$"),
                [self["designator"]] if "designator" in self else [], "")
        ]


class PublicKeyView(Validating, NamedDict):

    @property
    def public(self):
        return []

    @property
    def parameters(self):
        return [
            Parameter(
                "value", True, re.compile(
                    "ssh-rsa AAAA[0-9A-Za-z+/]+[=]{0,3} ([^@]+@[^@]+)"),
                [self["value"]] if "value" in self else [], ""),
        ]


class RegistrationView(Validating, NamedDict):

    @property
    def public(self):
        return []

    @property
    def parameters(self):
        return [
            Parameter(
                "username", True, re.compile("\\w{8,10}$"),
                [self["username"]] if self.get("username", None) else [],
                """
                User names are 8 to 10 characters long.
                """),
            Parameter(
                "password", True, re.compile(
                    "^(?=.*\\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[^a-zA-Z0-9])"
                    "(?!.*\\s).{8,20}$"
                ),[],
                """
                Passwords are between 8 and 20 characters in length.
                They must contain:
                <ul>
                <li>at least one lowercase letter</li>
                <li>at least one uppercase letter</li>
                <li>at least one numeric digit</li>
                <li>at least one special character</li>
                </ul>
                They cannot contain whitespace.
                """),
        ]


class LoginView(RegistrationView):

    @property
    def public(self):
        return []


class ResourceView(NamedDict):

    @property
    def public(self):
        return ["name", "value"]


class CatalogueChoiceView(ResourceView):

    @property
    def public(self):
        return ["template", "purpose"]

class StateView(Validating, NamedDict):

    @property
    def public(self):
        return ["fsm", "name"]

    @property
    def parameters(self):
        return [
            Parameter(
                "fsm", True, re.compile("\\w{3,32}$"),
                [self["fsm"]] if "fsm" in self else [], ""),
            Parameter(
                "name", True, re.compile("\\w{2,64}$"),
                [self["name"]] if "name" in self else [], "")
        ]


class NavRegion(Region):

    @singledispatch
    def present(obj):
        return None

    @present.register(Organisation)
    def present_organisation(obj, isSelf=False):
        item = {k: getattr(obj, k) for k in ("uuid", "name")}
        item["_type"] = "organisation"
        rel = "self" if isSelf else "canonical"
        item["_links"] = [
            Action(obj.name, rel, "/organisation/{}", obj.name,
            "get", [], "View")]
        return OrganisationInfo(item)

    @present.register(Registration)
    def present_registration(artifact):
        latest = artifact.changes[-1] if artifact.changes else None 
        resources = [r for i in artifact.changes for r in i.resources]
        hndl = latest.actor.handle if (
            latest and isinstance(latest.actor, User)) else ""
        item = {
            "username": hndl,
            "modified": latest.at if latest else None,
            "uuid": artifact.uuid,
        }
        item["_links"] = [
            Action(
                "Account",
                "canonical",
                "/account/{}", item["uuid"],
                "get", [], "View")
        ]
        return RegistrationView(item)


class ItemRegion(Region):

    @singledispatch
    def present(obj):
        return None

    @present.register(Appliance)
    def present_appliance(artifact):
        resources = [r for i in artifact.changes for r in i.resources]
        names = {i.name for i in resources if isinstance(i, Label)}
        item = {
            "uuid": artifact.uuid,
            "name": names.pop() if names else None,
            "organisation": artifact.organisation.name,
            "nodes": [i.name for i in resources if isinstance(i, Node)],
            "ips": ', '.join(
                [i.ip_ext for i in resources if isinstance(i, NATRouting)] +
                [i.value for i in resources if isinstance(i, IPAddress)]
            ),
            "latest":  artifact.changes[-1],
        }
        return ApplianceView(item)

    @present.register(BcryptedPassword)
    def present_bcryptedpassword(obj):
        now = datetime.datetime.utcnow()
        age = now - obj.touch.at
        hrs = age.seconds // 3600
        mins = (age.seconds % 3600) // 60
        return ResourceInfo((
            ("password", "********"),
            ("set", "{0} days, {1} hrs, {2} mins ago".format(
                age.days, hrs, mins)),
            ("uuid", uuid.uuid4().hex),
        ))

    @present.register(EmailAddress)
    def present_emailaddress(obj):
        return ResourceInfo(
            email=obj.value,
            uuid=uuid.uuid4().hex,
        )

    @present.register(CatalogueChoice)
    def present_catalogue_choice(obj):
        item = {
            "template": obj.name,
            "purpose": obj.description,
            "uuid": uuid.uuid4().hex,
            "_type": "cataloguechoice",
        }
        item["_links"] = [
            Action("Catalogue", "collection", "#", "",  # FIXME
            "get", [], "Ok")]
        return CatalogueChoiceView(item)

    @present.register(HTTPForbidden)
    def present_forbidden(exception):
        item = {
            "comment": exception.comment,
            "exception": exception.detail,
            "message": exception.message,
        }
        return FlashInfo(item)

    @present.register(Host)
    def present_host(artifact):
        resources = [r for i in artifact.changes for r in i.resources]
        item = {
            "uuid": artifact.uuid,
            "name": artifact.name,
            "organisation": artifact.organisation.name,
            "nodes": [i.name for i in resources if isinstance(i, Node)],
            "ips": [i.value for i in resources if isinstance(i, IPAddress)],
            "latest":  artifact.changes[-1],
        }
        return HostView(item)

    @present.register(Label)
    def present_label(obj):
        item = LabelView(
            name = obj.name,
            description = obj.description,
            uuid = uuid.uuid4().hex,
            _type = "label"
        )
        try:
            ref = obj.touch.artifact.uuid
        except AttributeError:
            ref = obj.uuid
        item["_links"] = [Action(
            name="General information",
            rel="edit-form",
            typ="/appliance/{}",
            ref=ref,
            method="post",
            parameters=item.parameters,
            prompt="OK")]
        return item

    @present.register(PosixUId)
    def present_posixuid(obj):
        item = ResourceInfo(
            name=obj.value,
            uuid=uuid.uuid4().hex,
        )
        return item

    @present.register(PosixUIdNumber)
    def present_posixuidnumber(obj):
        return ResourceInfo(
            uid=obj.value,
            uuid=uuid.uuid4().hex,
        )

    @present.register(PosixGId)
    def present_posixgid(obj):
        return ResourceInfo(
            gid=obj.value,
            uuid=uuid.uuid4().hex,
        )

    @present.register(PublicKey)
    def present_publickey(obj):
        return PublicKeyInfo({
            "Public key": obj.value,
            "uuid": uuid.uuid4().hex,
        })

    @present.register(PageInfo)
    def present_pageinfo(obj):
        return obj.name("page")

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
        item["uuid"] = uuid.uuid4().hex
        item["_type"] = type(obj).__name__.lower()
        return ResourceView(item)

    @present.register(Touch)
    def present_forbidden(act):
        item = {
            "at": act.at,
            "event": act.artifact.typ,
            "resources": act.resources,
            "user": act.actor.handle,
            "uuid": uuid.uuid4().hex,
        }
        item["_links"] = [
            Action(act.artifact.typ, "collection", "/user/{}", act.actor.uuid,
            "get", [], "View")]
        return EventInfo(item)

    @present.register(VersionInfo)
    def present_pathinfo(obj):
        return obj.name("versions")


class OptionRegion(Region):

    @singledispatch
    def present(obj):
        return None

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

    @present.register(PosixUId)
    def present_posixuid(obj):
        item = PosixUIdView(
            name=obj.value,
            uuid=uuid.uuid4().hex,
        )
        return item

    @present.register(BcryptedPassword)
    def present_bcryptedpassword(obj):
        item = BcryptedPasswordView(
            uuid=uuid.uuid4().hex,
        )
        item["_links"] = [Action(
            name="Set your password",
            rel="edit-form",
            typ="/registration/{}/passwords",
            ref=obj.uuid,
            method="post",
            parameters=item.parameters,
            prompt="Change")]
        return item

    @present.register(PublicKey)
    def present_publickey(obj):
        item = PublicKeyView(
            value=obj.value,
            uuid=uuid.uuid4().hex,
        )
        item["_links"] = [Action(
            name="Paste your key",
            rel="edit-form",
            typ="/registration/{}/keys",
            ref=obj.uuid,
            method="post",
            parameters=item.parameters,
            prompt="Add")]
        return item

    @present.register(Registration)
    def present_registration(artifact):
        latest = artifact.changes[-1] if artifact.changes else None 
        resources = [r for i in artifact.changes for r in i.resources]
        hndl = latest.actor.handle if (
            latest and isinstance(latest.actor, User)) else ""
        item = {
            "username": hndl,
            "modified": latest.at if latest else None,
            "uuid": artifact.uuid,
        }
        return RegistrationView(item)

    @present.register(User)
    def present_user(obj):
        item = LoginView({
            "uuid": uuid.uuid4().hex,
            "username": obj.handle,
            "email": None})
        item["_links"] = [
            Action("User login", "login", "/login", "",
            "post", item.parameters, "Log in")]
        return item


class Page(PageBase):

    plan = [
        ("info", ItemRegion),
        ("nav", NavRegion),
        ("items", ItemRegion),
        ("options", OptionRegion)]

    def __init__(self, session=None, user=None, paths={}):
        super().__init__(session, user)

        self.layout.info.push(VersionInfo())
        self.layout.info.push(PathInfo(paths))


class PeoplePage(Page):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        link = Action(
            "Find people", "self",
            "/people", "people", "get",
            PersonView().parameters, "Search")
        self.layout.options.append(NamedDict({"_links": [link]}))
