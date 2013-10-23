#!/usr/bin/env python
# encoding: UTF-8

from setuptools import setup
import os.path

import cloudhands.common

__doc__ = open(os.path.join(os.path.dirname(__file__), "README.rst"),
               "r").read()

setup(
    name="cloudhands-common",
    version=cloudhands.common.__version__,
    description="Common definitions for cloudhands PaaS",
    author="D Haynes",
    author_email="david.e.haynes@stfc.ac.uk",
    url="http://pypi.python.org/pypi/cloudhands-common",
    long_description=__doc__,
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License"
    ],
    namespace_packages=["cloudhands"],
    packages=["cloudhands.common"],
    package_data={"cloudhands.common": []},
    install_requires=[],
    entry_points={
        "console_scripts": [
        ],
    },
    zip_safe=False
)
