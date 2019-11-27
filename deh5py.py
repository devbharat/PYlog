#!/usr/bin/python

import numpy as np
import h5py
import struct, sys, os
import PYlog
import transformations as trans
import json
import copy
#from PYlog import sdlog2_pp

import multiprocessing as mp

def get_geotag_data(log_data):
	t = log_data["TIME_StartTime"][3:]
	CAMT_seq = log_data["CAMT_seq"][3:]
	CAMT_timestamp = log_data["CAMT_timestamp"][3:]
	roll = []
	pitch = []
	yaw = []

	try:
		quat=np.array([M["ATT_qw"][3:], M["ATT_qx"][3:], M["ATT_qy"][3:], M["ATT_qz"][3:]])
		R = []
		ATT_PitchHov = []
		for i in range(np.size(quat, 1)):
			m = trans.quaternion_matrix(quat[:,i])
			r, p, y = trans.euler_from_matrix(m)
			roll.append(r)
			pitch.append(p)
			yaw.append(y)
	except:
		e = sys.exc_info()[0]
		print( "<p>Error: %s</p>" % e )
		pass

	GPOS_Lat = log_data["GPOS_Lat"][3:]
	GPOS_Lon = log_data["GPOS_Lon"][3:]
	GPOS_Alt = log_data["GPOS_Alt"][3:]

	# output
	timestamp_approx = []
	timestamp_exact = []
	lat_approx = []
	lon_approx = []
	alt_approx = []
	roll_approx = []
	pitch_appro = []
	yaw_approx = []

	# tmp variable init
	prev_cam_seq = 0

	for i in range(len(CAMT_seq)):
		if (CAMT_seq[i] != prev_cam_seq):
			print CAMT_seq[i],TIME_StartTime[i], CAMT_timestamp[i], GPOS_Lat[i], GPOS_Lon[i], GPOS_Alt[i]
			timestamp_approx.append((TIME_StartTime[i] / 1000.0) + 300)
			timestamp_exact.append((CAMT_timestamp[i] / 1000.0) + 300)
			lat_approx.append(GPOS_Lat[i] / 1.0)
			lon_approx.append(GPOS_Lon[i] / 1.0)
			alt_approx.append(GPOS_Alt[i])
			roll_approx.append(roll[i])
			pitch_appro.append(pitch[i])
			yaw_approx.append(yaw[i])
			prev_cam_seq = CAMT_seq[i]

	ret = [timestamp_approx, timestamp_exact, lat_approx, lon_approx, alt_approx, roll_approx, pitch_appro, yaw_approx]
	return np.array(ret)

def gen_geotag_list(log_data):
	d = get_geotag_data(log_data)

	""" Output format should look like below
	{
		"flights": [
			{
				"geotag": [
					{
						"coordinate": [
							"28.986774492071003",
							"-95.412158025929685",
							"76.668975830078125"
						],
						"hAccuracy": "5",
						"pitch": "-0.052623718060734626",
						"roll": "0.32719370722770691",
						"sequence": "0",
						"timestamp": "1538495464067.603",
						"vAccuracy": "10",
						"version": "1",
						"yaw": "-1.4531420469284058"
					},
					{
						"coordinate": [
							"28.984050026956627",
							"-95.414339015017958",
							"75.263534545898438"
						],
						"hAccuracy": "5",
						"pitch": "0.019284092806098108",
						"roll": "0.57114452123641968",
						"sequence": "1195",
						"timestamp": "1538496873627.0281",
						"vAccuracy": "10",
						"version": "1",
						"yaw": "-1.406010627746582"
					}
				],
				"name": "Raw"
			}
		]
	}

	data = {'flights':[{'geotag':[{'coordinate':['28.986774492071003', '-95.412158025929685', '76.668975830078125'], 'hAccuracy' : '5', 'pitch' : '-0.052623718060734626' , 'roll' : '0.3271937072277069' , 'sequence' : '0' , 'timestamp' : '1538495464067.603' , 'vAccuracy' : '10' , 'version' : '1' , 'yaw' : '-1.406010627746582'}], 'name': 'Raw'}]}
	print json.dumps(data, indent=4)

	"""
	template = {'flights':[{'geotag':[{'coordinate':['', '', ''], 'hAccuracy' : '5', 'pitch' : '' , 'roll' : '' , 'sequence' : '' , 'timestamp' : '' , 'vAccuracy' : '10' , 'version' : '1' , 'yaw' : ''}], 'name': 'Raw'}]}
	geotag_json_string = json.dumps(template, indent=4)
	geotag_json_obj = json.loads(geotag_json_string)

	geotag_list = geotag_json_obj['flights'][0]['geotag']
	geotag_item = geotag_list[0]
	tmp_geotag_item = copy.deepcopy(geotag_item)

	for i in range(np.shape(d)[1]):
		timestamp_approx, timestamp_exact, lat_approx, lon_approx, alt_approx, roll_approx, pitch_appro, yaw_approx = list(d[:,i])

		if (i == 0):
			# lat lon alt
			geotag_item['coordinate'][0] = str(lat_approx).decode('utf8')
			geotag_item['coordinate'][1] = str(lon_approx).decode('utf8')
			geotag_item['coordinate'][2] = str(alt_approx).decode('utf8')
			geotag_item['sequence'] = str(i).decode('utf8')
			geotag_item['pitch'] = str(pitch_appro).decode('utf8')
			geotag_item['roll'] = str(roll_approx).decode('utf8')
			geotag_item['yaw'] = str(yaw_approx).decode('utf8')
			geotag_item['timestamp'] = str(timestamp_exact).decode('utf8')

		else:
			tmp_geotag_item['coordinate'][0] = str(lat_approx).decode('utf8')
			tmp_geotag_item['coordinate'][1] = str(lon_approx).decode('utf8')
			tmp_geotag_item['coordinate'][2] = str(alt_approx).decode('utf8')
			tmp_geotag_item['sequence'] = str(i).decode('utf8')
			tmp_geotag_item['pitch'] = str(pitch_appro).decode('utf8')
			tmp_geotag_item['roll'] = str(roll_approx).decode('utf8')
			tmp_geotag_item['yaw'] = str(yaw_approx).decode('utf8')
			tmp_geotag_item['timestamp'] = str(timestamp_exact).decode('utf8')

			geotag_list.append(tmp_geotag_item)
			tmp_geotag_item = copy.deepcopy(tmp_geotag_item)
	# print json.dumps(geotag_json_obj, indent = 4)
	return geotag_json_obj

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
		poo = mp.Pool(processes=7,maxtasksperchild=10)
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
						if (os.stat(logfilename).st_size > 1000000.0): # > 1MB
							datafilenameList.append(datafilename)
							logfilenameList.append(logfilename)
							poo.apply_async(procS, (logfilename,))
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
		# poo.map(procS, logfilenameList)
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

	gt = gen_geotag_list(M)
	geotag_file_name = datafilename + '.json'
	with open(geotag_file_name, 'w') as outfile:  
		outfile.write(json.dumps(gt, indent = 4))

	_main()
