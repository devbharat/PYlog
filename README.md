[![Build Status](https://semaphoreci.com/api/v1/devbharat/pylog/branches/master/badge.svg)](https://semaphoreci.com/devbharat/pylog)

PYlog
===============

Quick hackjob based on sdlog2_dump.py from https://github.com/PX4/Firmware/blob/master/Tools/sdlog2/sdlog2_dump.py. 
Instead of dumping the file as CSV, the read binary file is dumped as HDF5 format that is much much faster to load and still well compressed to keep the file size small.

This postprocessing pipeline is ideal for those who

 - Prefer python over matlab
 - Prefer to work with ipython commandline and need loged arrays/params at their fingertips
 - Need to perform array/matrix operations on logged variables(that are for example not possible with MAVExplorer)
 - Need to postprocess the same logfile multiple times(and don't want to waste time parsing the binary each time)
 
Installation
==============

    pip install numpy cython h5py
    python setup.py build_ext --inplace
    python setup.py build
    
You can test the script with the included log files in the test folder

    python deh5py.py test/


Usage
==============

The handiest way to use the script is to run it with python intepreter


    ipython --pylab

    %run deh5py.py /path/to/direcotryWithLogfiles

    # Example
    t=TIME_StartTime/1e06
    plot(t, LPOS_Z)

The first time you run the deh5py.py script, it'll write a .hdf5 file and load the arrays/params to the interpreter. The next time onwards it'll simply read it, so it'll be much faster. You can use TAB for auto  completing array names and param names on the commandline which is also pretty handy.
