# -*- coding: utf-8 -*-

import errno
import subprocess

from distutils.core import setup

setup(name='sdlog2_pp',
      version='0.0.1',
      description='Python PX4 sdlog2 plotting scripts.',
      author='Bharat Tak',
      scripts=['src/PYlog.py', 'src/deh5py.py'],
      )

"""
cythonize src/PYlog.py && gcc -shared -pthread -fPIC -fwrapv -O3 -Wall -fno-strict-aliasing -I/usr/include/python2.7 -o PYlog.so src/PYlog.c
"""
