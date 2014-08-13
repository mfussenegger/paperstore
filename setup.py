#!/usr/bin/env python
# -*- coding: utf-8 -*-


from setuptools import setup

requirements = [
    'bottle',
    'sh',
    'argh',
    'whoosh'
]


setup(
    install_requires=requirements,
    name='paperstore'
)
