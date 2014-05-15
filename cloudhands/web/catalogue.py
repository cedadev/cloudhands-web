#!/usr/bin/env python3
# encoding: UTF-8

import re
import uuid

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from pyramid.httpexceptions import HTTPForbidden

from cloudhands.common.schema import CatalogueItem
from cloudhands.common.types import NamedDict

from cloudhands.web.hateoas import Aspect
from cloudhands.web.hateoas import Contextual
from cloudhands.web.hateoas import Parameter
from cloudhands.web.hateoas import Validating

from cloudhands.web.model import GenericRegion



class CatalogueItemView(Validating, NamedDict):

    @property
    def public(self):
        return ["name", "description", "note"]

    @property
    def parameters(self):
        return [
            Parameter(
                "name", True, re.compile("\\w{2,32}$"),
                [self["name"]] if "name" in self else [], "")
        ]


@GenericRegion.present.register(CatalogueItem)
def present_catalogueitem(obj):
    item = CatalogueItemView(
        name=obj.name,
        description=obj.description,
        note=obj.note,
        uuid=uuid.uuid4().hex,
    )
    item["_links"] = [
        Aspect("Configure appliance", "create-form", "#", "",  # FIXME
        "post", item.parameters, "Ok")]
    return item
