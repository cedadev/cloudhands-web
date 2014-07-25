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

from cloudhands.web.hateoas import Action
from cloudhands.web.hateoas import Contextual
from cloudhands.web.hateoas import Parameter
from cloudhands.web.hateoas import Validating

from cloudhands.web.model import ItemRegion



class CatalogueItemView(Validating, NamedDict):

    @property
    def public(self):
        return ["name", "description", "note"]

    @property
    def parameters(self):
        return [
            Parameter(
                "uuid", True, re.compile("\\w{32}$"),
                self["uuid"] if "uuid" in self else "", "")
        ]


@ItemRegion.present.register(CatalogueItem)
def present_catalogueitem(obj):
    item = CatalogueItemView(
        name=obj.name,
        description=obj.description,
        note=obj.note,
        uuid=obj.uuid,
    )
    item["_links"] = [
        Action("Configure appliance", "create-form",
        "/organisation/{}/appliances", obj.organisation.name,
        "post", item.parameters, "Ok")]
    return item
