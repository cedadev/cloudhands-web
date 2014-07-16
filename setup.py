#!/usr/bin/env python
# encoding: UTF-8

import ast
from setuptools import setup
import os.path


try:
    import cloudhands.web.__version__ as version
except ImportError:
    # Pip evals this file prior to running setup.
    # This causes ImportError in a fresh virtualenv.
    version = str(ast.literal_eval(
                open(os.path.join(os.path.dirname(__file__),
                "cloudhands", "web", "__init__.py"),
                'r').read().split("=")[-1].strip()))

__doc__ = open(os.path.join(os.path.dirname(__file__), "README.rst"),
               "r").read()

setup(
    name="cloudhands-web",
    version=version,
    description="Web portal for cloudhands PaaS",
    author="D Haynes",
    author_email="david.e.haynes@stfc.ac.uk",
    url="https://github.com/cedadev/cloudhands-web.git",
    long_description=__doc__,
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License"
    ],
    namespace_packages=["cloudhands"],
    packages=[
        "cloudhands.web",
        "cloudhands.web.templates",
        "cloudhands.web.test",
        "cloudhands.identity",
        "cloudhands.identity.test"],
    package_data={
        "cloudhands.web": [
            "templates/*.pt",
            "static/css/*.css",
            "static/js/*.js",
            "static/img/*.jpg",
            "static/img/*.png",
            ],
        "cloudhands.web.test": []
        },
    install_requires=[
        "asyncio>=0.4.1",
        "cloudhands-common>=0.24",
        "singledispatch>=3.4.0.2",
        "pyramid>=1.4.0",
        "pyramid_authstack>=1.0.1",
        "pyramid_chameleon>=0.1",
        "pyramid_macauth>=0.3.0",
        "pyramid-persona>=1.5",
        "waitress>=0.8.7",
        "python3-ldap>=0.9.1",
        "Whoosh>=2.5.5",
        "py-bcrypt>=0.4",
        ],
    entry_points={
        "console_scripts": [
            "cloud-webserve = cloudhands.web.main:run",
            "cloud-demoserve = cloudhands.web.demo:run",
            "cloud-index = cloudhands.web.indexer:run",
            "cloud-identity = cloudhands.identity.main:run",
        ],
        "jasmin.portal.catalogue": [
        ],
    },
    zip_safe=False
)
