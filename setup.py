#!/usr/bin/env python
# -*- coding: utf-8 -*-


from setuptools import setup

requirements = [
    'bottle',
    'sh',
    'argh',
    'sqlalchemy',
    'crate',
    'jinja2'
]


setup(
    install_requires=requirements,
    name='paperstore',
    entry_points={
        'console_scripts': [
            'paperstore = paperstore:main'
        ]
    }
)
