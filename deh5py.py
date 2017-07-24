#!/usr/bin/python

import numpy as np
import h5py
import struct, sys, os
import PYlog
import transformations as trans
#from PYlog import sdlog2_pp

import multiprocessing as mp

def procS(file_name):
	parser = PYlog.sdlog2_pp()
	parser.process(file_name)
	del parser

def _main():
	pass


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("Usage: python deh5py.py <log.hdf5>\n")
		sys.exit()

	if (os.path.isdir(sys.argv[1])):
		datafilenameList = []
		logfilenameList = []
		processes = []
		poo = mp.Pool(processes=3,maxtasksperchild=10)
		# is directory, look for all files inside it
		for root, dirs, files in os.walk(sys.argv[1]):
			for file in files:
				if file.endswith('.px4log'):
					#print(os.path.join(root, file))
					fn = os.path.join(root, file)
					print('Processing file %s' % fn)
					datafilename = os.path.splitext(fn)[0] + '.hdf5'
					logfilename = os.path.splitext(fn)[0] + '.px4log'
					if (os.path.isfile(datafilename)):
						pass
					else:
						datafilenameList.append(datafilename)
						logfilenameList.append(logfilename)
						#poo.apply(procS, (logfilename,))
		"""
		for i in range(len(logfilenameList)):
			processes.append(mp.Process(target=procS, args=(logfilenameList[i],)))

		# Run processes
		for p in processes:
		    p.start()

		# Exit the completed processes
		for p in processes:
		    p.join()
		"""
		poo.map(procS, logfilenameList)
		poo.close()
		poo.join()

	elif(os.path.isfile(sys.argv[1])):
		fn = sys.argv[1]
		datafilename = os.path.splitext(fn)[0] + '.hdf5'
		logfilename = os.path.splitext(fn)[0] + '.px4log'
		if (os.path.isfile(datafilename)):
			pass
		else:
			parser = PYlog.sdlog2_pp()
			parser.process(logfilename)

	M = h5py.File(datafilename)
	for label in M.keys():
		try:
			exec('%s = M["%s"][3:]' % (label, label))
		except:
			try:
				exec('%s = M["%s"].value' % (label, label))
			except:
				print('Error executing %s = M["%s"][3:]' % (label, label))
	# Turn quat to Rotation matrix for quick postprocess
	try:
		quat=np.array([M["ATT_qw"][3:], M["ATT_qx"][3:], M["ATT_qy"][3:], M["ATT_qz"][3:]])
		R = []
		ATT_PitchHov = []
		for i in range(np.size(quat, 1)):
			m = trans.quaternion_matrix(quat[:,i])
			roll, pitch, yaw = trans.euler_from_matrix(m)
			ATT_PitchHov.append(pitch)
			R.append(m)
		ATT_PitchHov = np.array(ATT_PitchHov) - np.pi / 2.0
	except:
		e = sys.exc_info()[0]
		print( "<p>Error: %s</p>" % e )
		pass
	_main()
