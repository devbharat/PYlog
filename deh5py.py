#!/usr/bin/python

import matplotlib.pyplot as plt
import numpy as np
import h5py
import struct, sys, os
from PYlog import sdlog2_pp
import multiprocessing as mp

def graph(data_y, legend_str=''):
	plt.figure()
	plt.plot(t, data_y)
	plt.grid(1)
	plt.xlabel('Time in seconds')
	if (legend_str != ''):
		plt.legend([legend_str])
	plt.show()

def procS(file_name):
	parser = sdlog2_pp()
	parser.process(file_name)

def _main():
	"""
	plt.figure(1)
	plt.plot(TIME_StartTime, CTD1_reg, label='CTD1_reg')
	plt.hold('on')
	plt.plot(TIME_StartTime, ACTR_fSat0, label='ACTR_fSat0')
	plt.plot(TIME_StartTime, ACTR_fSat1, label='ACTR_fSat1')
	plt.plot(TIME_StartTime, -CTD1_eR2*CTD2_kR2, label='-CTD1_eR2*CTD2_kR2')
	plt.plot(TIME_StartTime, -CTD1_eq*CTD2_kRate2, label='-CTD1_eq*CTD2_kRate2')
	plt.plot(TIME_StartTime, FOMO_myInt, label='FOMO_myInt')
	plt.plot(TIME_StartTime, CTD5_MyFF, label='CTD5_MyFF')
	plt.plot(TIME_StartTime, FOMO_my, label='FOMO_my')
	plt.grid('on')
	plt.legend()
	plt.show()

	print(M.keys())
	plt.figure(1)
	plt.plot(M["TIME_StartTime"][:], M["ACTR_fSat0"][:])
	plt.hold('on')
	plt.plot(M["TIME_StartTime"][:], M["ACTR_fSat1"][:])
	plt.plot(M["TIME_StartTime"][:], -M["CTD1_eR2"][:]*M["CTD2_kR2"][:])
	plt.plot(M["TIME_StartTime"][:], -M["CTD1_eq"][:]*M["CTD2_kRate2"][:])
	plt.plot(M["TIME_StartTime"][:], M["FOMO_myInt"][:], 'x')
	plt.plot(M["TIME_StartTime"][:], M["CTD5_MyFF"][:])
	plt.plot(M["TIME_StartTime"][:], M["FOMO_my"][:])
	plt.grid('on')
	plt.show()

	plt.figure(2)
	#Plot pitch, pitch SP and longitudnal velocities
	#graph LPOS.Z ATT.Pitch ATSP.PitchSP LPOS.VX*np.cos(ATT.Yaw)+LPOS.VY*np.sin(ATT.Yaw) LPSP.VX*np.cos(ATT.Yaw)+LPSP.VY*np.sin(ATT.Yaw) LPOS.VX LPOS.VY ATT.Yaw
	plt.plot(TIME_StartTime, CTD1_reg, label='CTD1_reg')
	plt.hold('on')
	plt.plot(TIME_StartTime, LPOS_Z, label='LPOS_Z')
	plt.plot(TIME_StartTime, ATT_Pitch, label='ATT_Pitch')
	plt.plot(TIME_StartTime, ATSP_PitchSP, label='ATSP_PitchSP')
	plt.plot(TIME_StartTime, LPOS_VX*np.cos(ATT_Yaw)+LPOS_VY*np.sin(ATT_Yaw), label='LPOS_VX_body')
	plt.plot(TIME_StartTime, LPSP_VX*np.cos(ATT_Yaw)+LPSP_VY*np.sin(ATT_Yaw), label='LPSP_VX_body')
	plt.plot(TIME_StartTime, LPOS_VZ, label='LPOS_VZ')
	plt.legend()
	plt.grid('on')
	plt.show()


	#Plot various throttle/force contributions to pitch setpoint
	#graph MPCD.t1*np.cos(ATT.Yaw)+MPCD.t2*np.sin(ATT.Yaw) MPCD.tI1*np.cos(ATT.Yaw)+MPCD.tI2*np.sin(ATT.Yaw) -MPCD.dC
	plt.figure(3)
	plt.plot(TIME_StartTime, CTD1_reg, label='CTD1_reg')
	plt.hold('on')
	plt.plot(TIME_StartTime, MPCD_t1*np.cos(ATT_Yaw)+MPCD_t2*np.sin(ATT_Yaw), label='MPCD_t1_body')
	plt.plot(TIME_StartTime, MPCD_tI1*np.cos(ATT_Yaw)+MPCD_tI2*np.sin(ATT_Yaw), label='MPCD_tI1_body')
	plt.plot(TIME_StartTime, -MPCD_dC, label='-MPCD_dC')
	plt.grid('on')
	plt.legend()
	plt.show()

	plt.figure(4)
	plt.plot(TIME_StartTime, CTD1_reg, label='CTD1_reg')
	plt.hold('on')
	plt.plot(TIME_StartTime, MPCD_t3, label='MPCD_t3')
	plt.plot(TIME_StartTime, MPCD_tI3, label='MPCD_tI3')
	plt.plot(TIME_StartTime, MPCD_lC, label='MPCD_lC')
	plt.grid('on')
	plt.legend()
	plt.show()
	"""
	pass


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("Usage: python deh5py.py <log.hdf5>\n")
		sys.exit()

	if (os.path.isdir(sys.argv[1])):
		datafilenameList = []
		logfilenameList = []
		processes = []
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
						#procS(logfilename)
		for i in range(len(logfilenameList)):
			print("BANANAN   %s" % logfilenameList[i])
			processes.append(mp.Process(target=procS, args=(logfilenameList[i],)))

		# Run processes
		for p in processes:
		    p.start()

		# Exit the completed processes
		for p in processes:
		    p.join()

	elif(os.path.isfile(sys.argv[1])):
		fn = sys.argv[1]
		datafilename = os.path.splitext(fn)[0] + '.hdf5'
		logfilename = os.path.splitext(fn)[0] + '.px4log'
		if (os.path.isfile(datafilename)):
			pass
		else:
			parser = sdlog2_pp()
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
	# Shortcuts
	try:
		global t
		t = TIME_StartTime / 1000000.0
		yaw = MPCE_yaw
		pitch = ATT_Pitch
		pitch_sp = ATSP_PitchSP
		t1 = MPCD_t1
		t2 = MPCD_t2
		t3 = MPCD_t3
		fd0 = ACTR_fd0
		fd1 = ACTR_fd1
		fSat0 = ACTR_fSat0
		fSat1 = ACTR_fSat1
		navS = STAT_NavState
		tx_b = MPCD_t1*np.cos(yaw) + MPCD_t2*np.sin(yaw)
		vx_b = LPOS_VX*np.cos(MPCE_yaw) + LPOS_VY*np.sin(MPCE_yaw)
		vx_sp_b = LPSP_VX*np.cos(MPCE_yaw) + LPSP_VY*np.sin(MPCE_yaw)
		vex_b = MPCE_veX*np.cos(yaw) + MPCE_veY*np.sin(yaw)
	except:
		pass
	_main()
