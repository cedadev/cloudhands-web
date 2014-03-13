#!/usr/bin/env python3
#   encoding: UTF-8

import inspect
import textwrap
import timeit
import unittest

import bcrypt

class BcryptTests(unittest.TestCase):

    @staticmethod
    def setup():
        import bcrypt
        password = "Q1w2E3r4T5y6"
        hash = bcrypt.hashpw(password, bcrypt.gensalt(12))
        valid = password
        invalid = str(reversed(password))
        return (hash, valid, invalid)

    def test_password_valid(self):
        hash, valid, invalid = BcryptTests.setup()
        self.assertTrue(bcrypt.checkpw(valid, hash))

    def test_password_valid(self):
        hash, valid, invalid = BcryptTests.setup()
        self.assertTrue(bcrypt.checkpw(valid, hash))

    def test_complexity_when_password_valid(self):
        number = 3
        setup = ";".join(i.lstrip() for i in 
            inspect.getsource(BcryptTests.setup).splitlines()[2:-1])
        t = timeit.timeit(
            "bcrypt.checkpw(valid, hash)",
            setup=setup,
            number=number)
        self.assertTrue(0.5 < t < 1.0)

    def test_complexity_when_password_invalid(self):
        number = 3
        setup = ";".join(i.lstrip() for i in 
            inspect.getsource(BcryptTests.setup).splitlines()[2:-1])
        t = timeit.timeit(
            "bcrypt.checkpw(invalid, hash)",
            setup=setup,
            number=number)
        self.assertTrue(0.5 < t < 1.0)
