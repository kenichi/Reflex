#!/usr/bin/env python
from inspect import cleandoc

from setuptools import setup

_version = {}
exec(open('reflex/_version.py').read(), _version)

setup(
    name='reflex',
    packages=['reflex', 'reflex.test'],
    version=_version['__version__'],
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
        'testing': [
            'pytest',
        ]
    },
    entry_points={
        'console_scripts': [
            'reflex = reflex.cli:main',
        ]
    },
)
