# -*- coding: utf-8 -*-

import errno
import subprocess

from distutils.core import setup
from Cython.Build import cythonize

setup(name='sdlog2_pp',
      version='0.0.1',
      description='Python PX4 sdlog2 plotting scripts.',
      author='Bharat Tak',
      ext_modules = cythonize(['src/PYlog.pyx']),
      scripts = ['transformations.py', 'deh5py.py'],
      )

