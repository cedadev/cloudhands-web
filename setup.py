#!/usr/bin/env python
# encoding: UTF-8

from setuptools import setup
import os.path

import cloudhands.web

__doc__ = open(os.path.join(os.path.dirname(__file__), "README.rst"),
               "r").read()

setup(
    name="cloudhands-web",
    version=cloudhands.web.__version__,
    description="Web portal for cloudhands PaaS",
    author="D Haynes",
    author_email="david.e.haynes@stfc.ac.uk",
    url="http://pypi.python.org/pypi/cloudhands-web",
    long_description=__doc__,
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License"
    ],
    namespace_packages=["cloudhands"],
    packages=["cloudhands.web"],
    package_data={"cloudhands.web": []},
    install_requires=[
        "pyramid>=1.4.0",
        "pyramid-persona>=1.5",
        "waitress>=0.8.7",
        ],
    entry_points={
        "console_scripts": [
        "chweb-serve = cloudhands.web.main:run"
        ],
    },
    zip_safe=False
)
