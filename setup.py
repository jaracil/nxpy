# -*- coding: utf-8 -*-
##############################################################################
#
#    pynexus, a Python library for easy playing with Nexus
#    Copyright (C) 2016 by the pynexus team
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from os import path
from setuptools import setup

exec(open('pynexus/version.py').read())

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='pynexus',
    version=__version__,
    description='A Python library for easy playing with Nexus',
    long_description=long_description,
    url='https://github.com/jaracil/nxpy',
    author='Javier Sancho',
    author_email='jsancho@nayarsystems.com',
    license='LGPLv3+',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='nexus distributed microservices',
    packages=['pynexus'],
    install_requires=[
        'srvlookup',
        'websocket-client',
    ],
)
