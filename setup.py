# -*- coding: utf-8 -*-
# setup.py
from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='empiar-depositor',
    version='1.6b25',
    packages=find_packages(),
    author="Andrii Iudin",
    author_email="andrii@ebi.ac.uk, andrii.iudin@gmail.com",
    description="Script for depositing the data into EMPIAR using EMPIAR API",
    long_description=long_description,
    license="Apache License",
    keywords="EMPIAR, deposition, microscopy",
    include_package_data=True,
    install_requires=["requests"],
    classifiers=[
        # maturity
        'Development Status :: 4 - Beta',
        # environment
        'Environment :: Console',
        # audience
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        # license
        'License :: OSI Approved :: Apache Software License',
        # python version
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points={
        'console_scripts': ['empiar-depositor = empiar_depositor.empiar_depositor:main'],
    }
)
