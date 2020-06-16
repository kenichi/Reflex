#!/usr/bin/env python
from inspect import cleandoc

from setuptools import setup


__version__ = '0.2.0'


setup(
    name='brightmd.reflex',
    packages=['reflex', 'reflex.test'],
    version=__version__,
    description='Repository release automation',
    author='Bright.md',
    author_email='support@bright.md',
    url='https://github.com/brightmd/reflex',
    keywords=['git', 'flow', 'automation'],
    classifiers=[],
    license='MIT',
    install_requires=cleandoc('''
    click>=5.0,<8.0
    ''').split(),
    extras_require={
        'dev': [
            'awscli',
            'mock',
            'pytest',
            'pytest-coverage',
            's3pypi',
            'tox',
        ]
    },
    entry_points={
        'console_scripts': [
            'reflex = reflex.cli:main',
        ]
    },
)
