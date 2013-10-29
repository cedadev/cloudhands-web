#!/usr/bin/env python3
# encoding: UTF-8

import operator

class Widget(object):

    def __init__(self, session):
        self.session = session

#TODO Widgets are diictionaries?
class EmailIsUntrusted(Widget):
    pass

class EmailIsTrusted(Widget):
    pass

class EmailHasExpired(Widget):
    pass

class EmailWasWithdrawn(Widget):
    pass

class Page(object):

    _navi = {}
    _info = {}
    _user = {
        ("credential", "untrusted"): [EmailIsUntrusted],
        ("credential", "trusted"): [EmailIsTrusted],
        ("credential", "expired"): [EmailHasExpired],
        ("credential", "withdrawn"): [EmailWasWithdrawn],
    }
    _evts = {}

    def __init__(self):
        self.navi = {}
        self.info = {}
        self.user = {}
        self.evts = {}
        self.configured = []

    def configure(self, fsm, value):
        fsmName = operator.itemgetter(0)
        for policy, picked in [
            (self._navi, self.navi), (self._info, self.info),
            (self._user, self.user), (self._evts, self.evts)]:

            if (fsm, value) in policy:
                picked[(fsm, value)] = policy[(fsm, value)]
