#!/usr/bin/env python
from setuptools import setup

setup(
    name="reflex",
    version="0.1.0",
    author="Bright.md",
    author_email="support@bright.md",
    description=("Release automation for Bright.md."),
    license='MIT',
    install_requires=[
        'click',
    ],
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
