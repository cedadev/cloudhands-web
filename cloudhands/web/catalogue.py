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



class CatalogItemView(NamedDict):

    @property
    def public(self):
        return ["name", "description", "note"]


@GenericRegion.present.register(CatalogueItem)
def present_catalogueitem(obj):
    # TODO: Get View Class from provider, item name
    item = WhatKindOfView(
        name=obj.value,
        uuid=uuid.uuid4().hex,
    )
    item["_links"] = [
        Aspect("Select account name", "create-form", "#", "",  # FIXME
        "post", item.parameters, "Ok")]
    return item
