#!/usr/bin/python
from __future__ import print_function
import mmap
import numpy as np
import h5py
import os.path

import numpy as np
import h5py
import struct, sys, os
import PYlog
import transformations as trans
import json
import copy
#from PYlog import sdlog2_pp

import multiprocessing as mp
import scipy
from scipy import signal, misc
from numpy.linalg import inv



import struct, sys

if sys.hexversion >= 0x030000F0:
	runningPython3 = True
	def _parseCString(cstr):
		return str(cstr, 'ascii').split('\0')[0]
else:
	runningPython3 = False
	def _parseCString(cstr):
		return str(cstr).split('\0')[0]

class sdlog2_pp:	
	def __init__(self):
		self.BLOCK_SIZE = 8192
		self.MSG_HEADER_LEN = 3
		self.MSG_HEAD1 = 0xA3
		self.MSG_HEAD2 = 0x95
		self.MSG_FORMAT_PACKET_LEN = 89
		self.MSG_FORMAT_STRUCT = "BB4s16s64s"
		self.MSG_TYPE_FORMAT = 0x80
		self.FORMAT_TO_STRUCT = {
			"b": ("b", None),
			"B": ("B", None),
			"h": ("h", None),
			"H": ("H", None),
			"i": ("i", None),
			"I": ("I", None),
			"f": ("f", None),
			"d": ("d", None),
			"n": ("4s", None),
			"N": ("16s", None),
			"Z": ("64s", None),
			"c": ("h", 0.01),
			"C": ("H", 0.01),
			"e": ("i", 0.01),
			"E": ("I", 0.01),
			"L": ("i", 0.0000001),
			"M": ("b", None),
			"q": ("q", None),
			"Q": ("Q", None),
		}
		self.csv_delim = ","
		self.csv_null = ""
		self.msg_filter = []
		self.time_msg = 'TIME'
		self.debug_out = False
		self.correct_errors = True
		self.file_name = None
		self.file = None
		self.k = True

		return
	
	def reset(self):
		self.msg_descrs = {}	  # message descriptions by message type map
		self.msg_structs = {}	 # precompiled struct objects per message type
		self.msg_labels = {}	  # message labels by message name map
		self.msg_names = []	   # message names in the same order as FORMAT messages
		self.buffer = bytearray() # buffer for input binary data
		self.ptr = 0			  # read pointer in buffer
		self.csv_columns = []	 # CSV file columns in correct order in format "MSG.label"
		self.csv_data = {}		# current values for all columns
		self.log_data = {}		# values for all columns
		self.csv_updated = False
		self.msg_filter_map = {}  # filter in form of map, with '*" expanded to full list of fields
		self.params = {}
	
	def setCSVDelimiter(self, csv_delim):
		self.csv_delim = csv_delim
	
	def setCSVNull(self, csv_null):
		self.csv_null = csv_null
	
	def setMsgFilter(self, msg_filter):
		self.msg_filter = msg_filter
	
	def setTimeMsg(self, time_msg):
		self.time_msg = time_msg

	def setDebugOut(self, debug_out):
		self.debug_out = debug_out

	def setCorrectErrors(self, correct_errors):
		self.correct_errors = correct_errors

	def setFileName(self, file_name):
		self.file_name = file_name
		if file_name != None:
			self.file = open(file_name, 'w+')
		else:
			self.file = None

	
	def process(self, fn):
		self.reset()
		if self.debug_out:
			# init msg_filter_map
			for msg_name, show_fields in self.msg_filter:
				self.msg_filter_map[msg_name] = show_fields
		first_data_msg = True
		#filename = ntpath.basename(fn).split('.')[-2] + '.hdf5'
		#filename = fn.split('.')[-2] + '.hdf5'
		filename = os.path.splitext(fn)[0] + '.hdf5'
		# check if file exists
		if (os.path.isfile(filename)):
			os.remove(filename)
			print("Removed previous %s" % filename)
		g = h5py.File(filename,'w')
		index = 0;
		precent_read = 0
		p_percent_read = 0
		with open(fn, "rb") as f:
			m = mmap.mmap(f.fileno(), 0, prot=mmap.PROT_READ, offset=0) #File is open read-only
			bytes_read = 0
			size = m.size()
			print("Input Logfile %s: %d MB" % (os.path.basename(fn), int(size/1000000)))
			# local variable acces is faster than global 
			_BUFF_ = self.buffer
			_BLOCK_SIZE_ = self.BLOCK_SIZE
			_PTR_ = self.ptr
			_CSV_DATA_ = self.csv_data
			_CSV_COLS_ = self.csv_columns
			_TIME_MSG_ = self.time_msg
			while True:
				chunk = m.read(_BLOCK_SIZE_)
				if len(chunk) == 0:
					break
				_BUFF_ = _BUFF_[_PTR_:] + chunk
				_PTR_ = 0

				# Status update
				index = index + _BLOCK_SIZE_
				precent_read = int(index * 100.0 / size)
				#sys.stdout.write('\ \r')
				#sys.stdout.flush()
				if (precent_read != p_percent_read):
					sys.stdout.write('Read %d \r' % precent_read)
					#print(precent_read)
					sys.stdout.flush()
					p_percent_read = precent_read

				while (len(_BUFF_) - _PTR_) >= 3:
					head1 = _BUFF_[_PTR_]
					head2 = _BUFF_[_PTR_+1]
					if (head1 != 0xA3 or head2 != 0x95):
						if self.correct_errors:
							_PTR_ += 1
							continue
						else:
							raise Exception("Invalid header at %i (0x%X): %02X %02X, must be %02X %02X" % (bytes_read + _PTR_, bytes_read + _PTR_, head1, head2, self.MSG_HEAD1, self.MSG_HEAD2))
					msg_type = _BUFF_[_PTR_+2]
					if msg_type == 0x80:
						# parse FORMAT message
						if (len(_BUFF_) - _PTR_) < 89:
							break
						#self.parseMsgDescr()
						if runningPython3:
							data = struct.unpack("BB4s16s64s", _BUFF_[_PTR_ + 3 : _PTR_ + 89])
						else:
							data = struct.unpack("BB4s16s64s", str(_BUFF_[_PTR_ + 3 : _PTR_ + 89]))
						msg_type1 = data[0]
						if msg_type1 != 0x80:
							msg_length1 = data[1]
							msg_name1 = _parseCString(data[2])
							msg_format1 = _parseCString(data[3])
							msg_labels1 = _parseCString(data[4]).split(",")
							# Convert msg_format to struct.unpack format string
							msg_struct1 = ""
							msg_mults1 = []
							for c in msg_format1:
								try:
									f1 = self.FORMAT_TO_STRUCT[c]
									msg_struct1 += f1[0]
									msg_mults1.append(f1[1])
								except KeyError as e:
									raise Exception("Unsupported format char: %s in message %s (%i)" % (c, msg_name1, msg_type1))
							msg_struct1 = "<" + msg_struct1   # force little-endian
							self.msg_structs[msg_name1] = struct.Struct(msg_struct1).unpack
							self.msg_descrs[msg_type1] = (msg_length1, msg_name1, msg_format1, msg_labels1, msg_struct1, msg_mults1)
							self.msg_labels[msg_name1] = msg_labels1
							self.msg_names.append(msg_name1)
							_PTR_ += 89
					else:
						# parse data message
						try:
							msg_descr = self.msg_descrs[msg_type]
							# if msg_descr == None:
							#	 raise Exception("Unknown msg type: %i" % msg_type)
						except KeyError as e:
							pass

						msg_length1 = msg_descr[0]
						msg_name1 = msg_descr[1]
						msg_labels1 = msg_descr[3]
						msg_mults1 = msg_descr[5]

						if (len(_BUFF_) - _PTR_) < msg_length1:
							break
						if first_data_msg:
							# build CSV columns and init data map
							self.initCSV()
							first_data_msg = False
						if _TIME_MSG_ != None and msg_name1 == _TIME_MSG_ and self.csv_updated:
							# self.printCSVRow()
							# self.updateLogData()
							for full_label in _CSV_COLS_:
								v = _CSV_DATA_[full_label]
								if v == None:
									v = 0
								self.log_data[full_label].append(v)
							self.csv_updated = False
						show_fields = self.filterMsg(msg_name1)
						if (show_fields != None):
							if runningPython3:
								data = list(self.msg_structs[msg_name1](_BUFF_[_PTR_+3:_PTR_+msg_length1]))
							else:
								try:
									data = list(self.msg_structs[msg_name1](str(_BUFF_[_PTR_+3:_PTR_+msg_length1])))
								except:
									pass
							for i in range(len(data)):
								if type(data[i]) is str:
									data[i] = str(data[i]).split('\0')[0]
								try:
									m1 = msg_mults1[i]
								except:
									pass
								if m1 != None:
									data[i] = data[i] * m1

								label = msg_labels1[i]
								if label in show_fields:
									_CSV_DATA_[msg_name1 + "_" + label] = data[i]
									#self.log_data[msg_name + "_" + label].append(data[i])
									if _TIME_MSG_ != None and msg_name1 != _TIME_MSG_:
										self.csv_updated = True
							# If we are parsing through PARM msg, write values to a file
							if show_fields == ['Name', 'Value']:
								self.params[str(data[0])] = float(data[1])
						_PTR_ += msg_length1
				bytes_read += _PTR_
				if _TIME_MSG_ != None and self.csv_updated:
					# self.printCSVRow()
					# self.updateLogData()
					pass
			m.close()
			del m
		print("Writing file %s" % filename)
		for full_label in self.csv_columns:
			v = self.log_data[full_label]
			g.create_dataset(full_label, data=v, compression="lzf")
		# write params
		for key in self.params:
			g.create_dataset(key, data=self.params[key])
		g.close()
		del g
	
	def filterMsg(self, msg_name):
		show_fields = "*"
		if len(self.msg_filter_map) > 0:
			show_fields = self.msg_filter_map.get(msg_name)
		return show_fields
	
	def initCSV(self):
		if len(self.msg_filter) == 0:
			for msg_name in self.msg_names:
				self.msg_filter.append((msg_name, "*"))
		for msg_name, show_fields in self.msg_filter:
			if show_fields == "*":
				show_fields = self.msg_labels.get(msg_name, [])
			self.msg_filter_map[msg_name] = show_fields
			for field in show_fields:
				full_label = msg_name + "_" + field
				self.csv_columns.append(full_label)
				self.csv_data[full_label] = None
				self.log_data[full_label] = []
		if self.file != None:
			#print(self.csv_delim.join(self.csv_columns), file=self.file)
			pass
		else:
			#print(self.csv_delim.join(self.csv_columns))
			pass

	def updateLogData(self):
		for full_label in self.csv_columns:
			v = self.csv_data[full_label]
			if v == None:
				v = 0
			self.log_data[full_label].append(v)

	def parseMsgDescr(self):
		if runningPython3:
			data = struct.unpack(self.MSG_FORMAT_STRUCT, self.buffer[self.ptr + 3 : self.ptr + self.MSG_FORMAT_PACKET_LEN])
		else:
			data = struct.unpack(self.MSG_FORMAT_STRUCT, str(self.buffer[self.ptr + 3 : self.ptr + self.MSG_FORMAT_PACKET_LEN]))
		msg_type = data[0]
		if msg_type != self.MSG_TYPE_FORMAT:
			msg_length = data[1]
			msg_name = _parseCString(data[2])
			msg_format = _parseCString(data[3])
			msg_labels = _parseCString(data[4]).split(",")
			# Convert msg_format to struct.unpack format string
			msg_struct = ""
			msg_mults = []
			for c in msg_format:
				try:
					f = self.FORMAT_TO_STRUCT[c]
					msg_struct += f[0]
					msg_mults.append(f[1])
				except KeyError as e:
					raise Exception("Unsupported format char: %s in message %s (%i)" % (c, msg_name, msg_type))
			msg_struct = "<" + msg_struct   # force little-endian
			self.msg_structs[msg_name] = struct.Struct(msg_struct).unpack
			self.msg_descrs[msg_type] = (msg_length, msg_name, msg_format, msg_labels, msg_struct, msg_mults)
			self.msg_labels[msg_name] = msg_labels
			self.msg_names.append(msg_name)
			if self.debug_out:
				if self.filterMsg(msg_name) != None:
					print("MSG FORMAT: type = %i, length = %i, name = %s, format = %s, labels = %s, struct = %s, mults = %s" % (
								msg_type, msg_length, msg_name, msg_format, str(msg_labels), msg_struct, msg_mults))
		self.ptr += self.MSG_FORMAT_PACKET_LEN

def procS(file_name):
	parser = PYlog.sdlog2_pp()
	parser.process(file_name)
	del parser

def get_session_number(filename):
	ret = -1
	filename_list = filename.split('/')
	for i in reversed(filename_list):
		if 'sess' in i:
			try:
				ret = int(i[4:])
				break
			except Exception as e:
				print('-------------------')
				print(e)

	return ret

def set_parser_params(parser):
	debug_out = False
	correct_errors = True
	msg_filter = []
	csv_null = ""
	csv_delim = ","
	time_msg = "TIME"
	file_name = None
	opt = None
	for arg in sys.argv[2:]:
		if opt != None:
			if opt == "d":
				csv_delim = arg
			elif opt == "n":
				csv_null = arg
			elif opt == "t":
				time_msg = arg
			elif opt == "f":
				file_name = arg
			elif opt == "m":
				show_fields = "*"
				a = arg.split("_")
				if len(a) > 1:
					show_fields = a[1].split(",")
				msg_filter.append((a[0], show_fields))
			opt = None
		else:
			if arg == "-v":
				debug_out = True
			elif arg == "-e":
				correct_errors = True
			elif arg == "-d":
				opt = "d"
			elif arg == "-n":
				opt = "n"
			elif arg == "-m":
				opt = "m"
			elif arg == "-t":
				opt = "t"
			elif arg == "-f":
				opt = "f"

	if csv_delim == "\\t":
		csv_delim = "\t"
	
	parser.setCSVDelimiter(csv_delim)
	parser.setCSVNull(csv_null)
	parser.setMsgFilter(msg_filter)
	parser.setTimeMsg(time_msg)
	parser.setFileName(file_name)
	parser.setDebugOut(debug_out)
	parser.setCorrectErrors(correct_errors)
	return parser

def main(root_dir):
	cal_param_list = ['session_number', 'CAL_MAG0_ODX', 'CAL_MAG0_ODY', 'CAL_MAG0_ODZ', 'CAL_MAG0_ROT', 'CAL_MAG0_XOFF', 'CAL_MAG0_XSCALE', 'CAL_MAG0_YOFF', 'CAL_MAG0_YSCALE', 'CAL_MAG0_ZOFF', 'CAL_MAG0_ZSCALE']
	cal_param_dict = {}

	if (os.path.isdir(root_dir)):
		datafilenameList = []
		logfilenameList = []
		processes = []
		poo = mp.Pool(processes=7,maxtasksperchild=10)
		# is directory, look for all files inside it
		for root, dirs, files in os.walk(root_dir):
			for file in files:
				if file.endswith('.px4log'):
					fname =os.path.join(root, file)
					if 'preflight' in fname:
						pass
					else:
						fn = os.path.join(root, file)
						datafilename = os.path.splitext(fn)[0] + '.hdf5'
						logfilename = os.path.splitext(fn)[0] + '.px4log'

						# check logfile size
						statinfo = os.stat(logfilename)
						if (statinfo.st_size < 1000000): # < 1MB
							print('Filesize too small %s' % logfilename)
							break

						if (os.path.isfile(datafilename)):
							pass
						else:
							parser = sdlog2_pp()
							debug_out = False
							correct_errors = True
							msg_filter = []
							csv_null = ""
							csv_delim = ","
							time_msg = "TIME"
							file_name = None
							opt = None
							for arg in sys.argv[2:]:
								if opt != None:
									if opt == "d":
										csv_delim = arg
									elif opt == "n":
										csv_null = arg
									elif opt == "t":
										time_msg = arg
									elif opt == "f":
										file_name = arg
									elif opt == "m":
										show_fields = "*"
										a = arg.split("_")
										if len(a) > 1:
											show_fields = a[1].split(",")
										msg_filter.append((a[0], show_fields))
									opt = None
								else:
									if arg == "-v":
										debug_out = True
									elif arg == "-e":
										correct_errors = True
									elif arg == "-d":
										opt = "d"
									elif arg == "-n":
										opt = "n"
									elif arg == "-m":
										opt = "m"
									elif arg == "-t":
										opt = "t"
									elif arg == "-f":
										opt = "f"

							if csv_delim == "\\t":
								csv_delim = "\t"

							parser.setCSVDelimiter(csv_delim)
							parser.setCSVNull(csv_null)
							parser.setMsgFilter(msg_filter)
							parser.setTimeMsg(time_msg)
							parser.setFileName(file_name)
							parser.setDebugOut(debug_out)
							parser.setCorrectErrors(correct_errors)
							print('Processing %s ' % logfilename)
							try:
								parser.process(logfilename)
							except Exception as e:
								print(e)
							print('Done Processing %s' % logfilename)
							del parser

						# print('Processing file %s' % fn)
						current_session_number = get_session_number(datafilename)
						# print('current sess number %s' % current_session_number)
						try:
							M = h5py.File(datafilename)
						except Exception as e:
							print(e)
							break

						# print M.keys()
						if 'AIRCRAFT_ID' in M.keys():
							if M['AIRCRAFT_ID'].value in cal_param_dict.keys():
								old_session_number = cal_param_dict[M['AIRCRAFT_ID'].value][cal_param_list.index('session_number')]
								if old_session_number > current_session_number:
									# print('Ignoring old session logfile for %s' % datafilename)
									break
								else:
									# print current_session_number
									cal_param_dict[M['AIRCRAFT_ID'].value] = [current_session_number]
							else:
								# print current_session_number
								cal_param_dict[M['AIRCRAFT_ID'].value] = [current_session_number]

							for key in cal_param_list:
								try:
									if 'CAL_' in key:
										if key in M.keys():
											cal_param_dict[M['AIRCRAFT_ID'].value].append(M[key].value)
										else:
											if (key == 'CAL_MAG0_ODX') and ('CAL_MAG0_ODX1' in M.keys()):
												cal_param_dict[M['AIRCRAFT_ID'].value].append(M['CAL_MAG0_ODX1'].value)
											elif  (key == 'CAL_MAG0_ODY') and ('CAL_MAG0_ODY1' in M.keys()):
												cal_param_dict[M['AIRCRAFT_ID'].value].append(M['CAL_MAG0_ODY1'].value)
											elif  (key == 'CAL_MAG0_ODZ') and ('CAL_MAG0_ODZ1' in M.keys()):
												cal_param_dict[M['AIRCRAFT_ID'].value].append(M['CAL_MAG0_ODZ1'].value)
											else:
												print('Key: %s' % key)
												print('Couldnt find a key in file %s' % datafilename)
												cal_param_dict.pop(M['AIRCRAFT_ID'].value, None)
												break
								except:
									print('Key: %s' % key)
									print('Failed to find a key in file %s' % datafilename)
									cal_param_dict.pop(M['AIRCRAFT_ID'].value, None)
									break
						else:
							print('AIRCRAFT_ID not found in file %s' % datafilename)
	return cal_param_list, cal_param_dict


def reject_outliers(data, m = 2.):
	d = np.abs(data - np.median(data))
	mdev = np.median(d)
	s = d/mdev if mdev else 0.
	return np.ma.masked_where(s>m, data)


def inverse_cal(root_dir, stat_dict):
	ret_dict = {}
	ret_list = ['session_number', 'mag_norm_orig', 'mag_norm_orig_diff', 'mag_norm_raw', 'mag_norm_raw_diff', 'mag_norm_inv', 'mag_norm_inv_diff']
	if (os.path.isdir(root_dir)):
		# is directory, look for all files inside it
		for root, dirs, files in os.walk(root_dir):
			for file in files:
				if file.endswith('.px4log'):
					fname =os.path.join(root, file)
					if 'preflight' in fname:
						pass
					else:
						fn = os.path.join(root, file)
						datafilename = os.path.splitext(fn)[0] + '.hdf5'
						logfilename = os.path.splitext(fn)[0] + '.px4log'

						# check logfile size
						statinfo = os.stat(logfilename)
						if (statinfo.st_size < 1000000): # < 1MB
							print('Filesize too small %s' % logfilename)
							break

						if (os.path.isfile(datafilename)):
							pass
						else:
							parser = sdlog2_pp()
							debug_out = False
							correct_errors = True
							msg_filter = []
							csv_null = ""
							csv_delim = ","
							time_msg = "TIME"
							file_name = None
							opt = None
							for arg in sys.argv[2:]:
								if opt != None:
									if opt == "d":
										csv_delim = arg
									elif opt == "n":
										csv_null = arg
									elif opt == "t":
										time_msg = arg
									elif opt == "f":
										file_name = arg
									elif opt == "m":
										show_fields = "*"
										a = arg.split("_")
										if len(a) > 1:
											show_fields = a[1].split(",")
										msg_filter.append((a[0], show_fields))
									opt = None
								else:
									if arg == "-v":
										debug_out = True
									elif arg == "-e":
										correct_errors = True
									elif arg == "-d":
										opt = "d"
									elif arg == "-n":
										opt = "n"
									elif arg == "-m":
										opt = "m"
									elif arg == "-t":
										opt = "t"
									elif arg == "-f":
										opt = "f"

							if csv_delim == "\\t":
								csv_delim = "\t"

							parser.setCSVDelimiter(csv_delim)
							parser.setCSVNull(csv_null)
							parser.setMsgFilter(msg_filter)
							parser.setTimeMsg(time_msg)
							parser.setFileName(file_name)
							parser.setDebugOut(debug_out)
							parser.setCorrectErrors(correct_errors)
							print('Processing %s ' % logfilename)
							try:
								parser.process(logfilename)
							except Exception as e:
								print(e)
							print('Done Processing %s' % logfilename)
							del parser

						current_session_number = get_session_number(datafilename)

						try:
							M = h5py.File(datafilename)

							"""
							X_mask = reject_outliers(M['IMU_MagX'][3:], 100.0)
							Y_mask = reject_outliers(M['IMU_MagY'][3:], 100.0)
							Z_mask = reject_outliers(M['IMU_MagZ'][3:], 100.0)
							IMU_MagX = []
							IMU_MagY = []
							IMU_MagZ = []
							for i in range(len(X_mask.data)):
								if np.ma.getmaskarray(X_mask)[i] or np.ma.getmaskarray(Y_mask)[i] or np.ma.getmaskarray(Z_mask)[i]:
									print('Outlier')
									pass
								else:
									IMU_MagX.append(X_mask.data[i])
									IMU_MagY.append(Y_mask.data[i])
									IMU_MagZ.append(Z_mask.data[i])
							IMU_MagX = np.array(IMU_MagX)
							IMU_MagY = np.array(IMU_MagY)
							IMU_MagZ = np.array(IMU_MagZ)
							"""

							IMU_MagX = scipy.signal.medfilt(M['IMU_MagX'][3:],7)
							IMU_MagY = scipy.signal.medfilt(M['IMU_MagY'][3:],7)
							IMU_MagZ = scipy.signal.medfilt(M['IMU_MagZ'][3:],7)
							mag_meas = np.matrix([IMU_MagX, IMU_MagY, IMU_MagZ])


							x_off_orig = M['CAL_MAG0_XOFF'].value
							y_off_orig = M['CAL_MAG0_YOFF'].value
							z_off_orig = M['CAL_MAG0_ZOFF'].value

							x_scale_orig = M['CAL_MAG0_XSCALE'].value
							y_scale_orig = M['CAL_MAG0_YSCALE'].value
							z_scale_orig = M['CAL_MAG0_ZSCALE'].value

							off_diag_param_list = ['CAL_MAG0_ODX', 'CAL_MAG0_ODY', 'CAL_MAG0_ODZ']
							for elem in off_diag_param_list:
								if elem in M.keys():
									if (elem == 'CAL_MAG0_ODX'):
										x_off_diag_orig = M[elem].value
									elif (elem == 'CAL_MAG0_ODY'):
										y_off_diag_orig = M[elem].value
									elif (elem == 'CAL_MAG0_ODZ'):
										z_off_diag_orig = M[elem].value

								else:
									if (elem == 'CAL_MAG0_ODX') and ('CAL_MAG0_ODX1' in M.keys()):
										x_off_diag_orig = M['CAL_MAG0_ODX1'].value
									elif  (elem == 'CAL_MAG0_ODY') and ('CAL_MAG0_ODY1' in M.keys()):
										y_off_diag_orig = M['CAL_MAG0_ODY1'].value
									elif  (elem == 'CAL_MAG0_ODZ') and ('CAL_MAG0_ODZ1' in M.keys()):
										z_off_diag_orig = M['CAL_MAG0_ODZ1'].value
									else:
										print('Key: %s' % elem)
										print('Couldnt find a key in file %s' % datafilename)
										break

							mag_norm_orig = np.sqrt(IMU_MagX**2 + IMU_MagY**2 + IMU_MagZ**2)
							mag_norm_orig_diff = np.max(mag_norm_orig) - np.min(mag_norm_orig)
							if mag_norm_orig_diff > 2:
								break
							# print(mag_norm_orig_diff)

							# get calib matrix
							mat_cal_orig = np.array([[x_scale_orig, x_off_diag_orig, y_off_diag_orig], [x_off_diag_orig, y_scale_orig, z_off_diag_orig], [y_off_diag_orig, z_off_diag_orig, z_scale_orig]])
							mat_cal_orig_inv = inv(mat_cal_orig)
							off_cal_orig = np.matrix([x_off_orig, y_off_orig, z_off_orig]).transpose()

							# get raw measurements
							mag_raw_meas = np.matrix(np.zeros(mag_meas.shape))
							for i in range(len(IMU_MagX)):
								mag_raw_meas[:, i] = mat_cal_orig_inv.dot(mag_meas[:, i]) + off_cal_orig

							mag_x_raw = np.array(mag_raw_meas[0, :])[0]
							mag_y_raw = np.array(mag_raw_meas[1, :])[0]
							mag_z_raw = np.array(mag_raw_meas[2, :])[0]
							mag_norm_raw = np.sqrt(mag_x_raw**2 + mag_y_raw**2 + mag_z_raw**2)
							mag_norm_raw_diff = np.max(mag_norm_raw) - np.min(mag_norm_raw)


							#  prepare mean matrix
							mat_cal_stat = np.array([[stat_dict['x_scale'], stat_dict['x_off_diag'], stat_dict['y_off_diag']], [stat_dict['x_off_diag'], stat_dict['y_scale'], stat_dict['z_off_diag']], [stat_dict['y_off_diag'], stat_dict['z_off_diag'], stat_dict['z_scale']]])
							# mat_cal_stat = np.array([[x_scale_orig, stat_dict['x_off_diag'], stat_dict['y_off_diag']], [stat_dict['x_off_diag'], y_scale_orig, stat_dict['z_off_diag']], [stat_dict['y_off_diag'], stat_dict['z_off_diag'], z_scale_orig]])
							off_cal_stat = np.matrix([stat_dict['x_offset'], stat_dict['y_offset'], stat_dict['z_offset']]).transpose()

							# get inverse calculated measurements
							mag_inv_meas = np.matrix(np.zeros(mag_meas.shape))
							for i in range(len(IMU_MagX)):
								# mag_inv_meas[:, i] = mat_cal_orig.dot(mag_raw_meas[:, i] - off_cal_orig)
								# mag_inv_meas[:, i] = mat_cal_orig.dot(mag_raw_meas[:, i]) - off_cal_orig
								
								# mag_inv_meas[:, i] = mat_cal_stat.dot(mag_raw_meas[:, i] - off_cal_orig)
								# mag_inv_meas[:, i] = mat_cal_stat.dot(mag_raw_meas[:, i]) - off_cal_orig
								
								mag_inv_meas[:, i] = mat_cal_stat.dot(mag_raw_meas[:, i] - off_cal_stat)

							mag_x_inv = np.array(mag_inv_meas[0, :])[0]
							mag_y_inv = np.array(mag_inv_meas[1, :])[0]
							mag_z_inv = np.array(mag_inv_meas[2, :])[0]
							mag_norm_inv = np.sqrt(mag_x_inv**2 + mag_y_inv**2 + mag_z_inv**2)
							mag_norm_inv_diff = np.max(mag_norm_inv) - np.min(mag_norm_inv)


						except Exception as e:
							print(e)
							break

						# print M.keys()
						if 'AIRCRAFT_ID' in M.keys():
							if M['AIRCRAFT_ID'].value in ret_dict.keys():
								old_session_number = ret_dict[M['AIRCRAFT_ID'].value][ret_list.index('session_number')]
								if old_session_number > current_session_number:
									# print('Ignoring old session logfile for %s' % datafilename)
									break
								else:
									# print current_session_number
									ret_dict[M['AIRCRAFT_ID'].value] = [current_session_number]
							else:
								# print current_session_number
								ret_dict[M['AIRCRAFT_ID'].value] = [current_session_number]

							ret_dict[M['AIRCRAFT_ID'].value].append(mag_norm_orig)
							ret_dict[M['AIRCRAFT_ID'].value].append(mag_norm_orig_diff)
							ret_dict[M['AIRCRAFT_ID'].value].append(mag_norm_raw)
							ret_dict[M['AIRCRAFT_ID'].value].append(mag_norm_raw_diff)
							ret_dict[M['AIRCRAFT_ID'].value].append(mag_norm_inv)
							ret_dict[M['AIRCRAFT_ID'].value].append(mag_norm_inv_diff)

						else:
							print('AIRCRAFT_ID not found in file %s' % datafilename)
	return ret_list, ret_dict

def get_field(field, src_list, src_dict):
	ret = []

	indx = src_list.index(field)
	for key in np.sort(src_dict.keys()):
		ret.append(src_dict[key][indx])
	return ret

def stat_mag_cal(cal_list, cal_dict):
	mag_x_off = get_field('CAL_MAG0_XOFF', cal_list, cal_dict)
	mag_y_off = get_field('CAL_MAG0_YOFF', cal_list, cal_dict)
	mag_z_off = get_field('CAL_MAG0_ZOFF', cal_list, cal_dict)
	
	mag_x_scale = get_field('CAL_MAG0_XSCALE', cal_list, cal_dict)
	mag_y_scale = get_field('CAL_MAG0_YSCALE', cal_list, cal_dict)
	mag_z_scale = get_field('CAL_MAG0_ZSCALE', cal_list, cal_dict)
	
	mag_x_off_diag = get_field('CAL_MAG0_ODX', cal_list, cal_dict)
	mag_y_off_diag = get_field('CAL_MAG0_ODY', cal_list, cal_dict)
	mag_z_off_diag = get_field('CAL_MAG0_ODZ', cal_list, cal_dict)

	mean_mx_off = np.mean(mag_x_off)
	std_mx_off = np.std(mag_x_off)
	mean_my_off = np.mean(mag_y_off)
	std_my_off = np.std(mag_y_off)
	mean_mz_off = np.mean(mag_z_off)
	std_mz_off = np.std(mag_z_off)

	ret_offset = [mean_mx_off, std_mx_off, mean_my_off, std_my_off, mean_mz_off, std_mz_off]

	mean_mx_scale = np.mean(mag_x_scale)
	std_mx_scale = np.std(mag_x_scale)
	mean_my_scale = np.mean(mag_y_scale)
	std_my_scale = np.std(mag_y_scale)
	mean_mz_scale = np.mean(mag_z_scale)
	std_mz_scale = np.std(mag_z_scale)

	ret_scale = [mean_mx_scale, std_mx_scale, mean_my_scale, std_my_scale, mean_mz_scale, std_mz_scale]

	mean_mx_off_diag = np.mean(mag_x_off_diag)
	std_mx_off_diag = np.std(mag_x_off_diag)
	mean_my_off_diag = np.mean(mag_y_off_diag)
	std_my_off_diag = np.std(mag_y_off_diag)
	mean_mz_off_diag = np.mean(mag_z_off_diag)
	std_mz_off_diag = np.std(mag_z_off_diag)

	ret_off_diag = [mean_mx_off_diag, std_mx_off_diag, mean_my_off_diag, std_my_off_diag, mean_mz_off_diag, std_mz_off_diag]

	return ret_offset, ret_scale, ret_off_diag

def stat_mag_cal_median(cal_list, cal_dict):
	mag_x_off = get_field('CAL_MAG0_XOFF', cal_list, cal_dict)
	mag_y_off = get_field('CAL_MAG0_YOFF', cal_list, cal_dict)
	mag_z_off = get_field('CAL_MAG0_ZOFF', cal_list, cal_dict)
	
	mag_x_scale = get_field('CAL_MAG0_XSCALE', cal_list, cal_dict)
	mag_y_scale = get_field('CAL_MAG0_YSCALE', cal_list, cal_dict)
	mag_z_scale = get_field('CAL_MAG0_ZSCALE', cal_list, cal_dict)
	
	mag_x_off_diag = get_field('CAL_MAG0_ODX', cal_list, cal_dict)
	mag_y_off_diag = get_field('CAL_MAG0_ODY', cal_list, cal_dict)
	mag_z_off_diag = get_field('CAL_MAG0_ODZ', cal_list, cal_dict)

	median_mx_off = np.median(mag_x_off)
	std_mx_off = np.std(mag_x_off)
	median_my_off = np.median(mag_y_off)
	std_my_off = np.std(mag_y_off)
	median_mz_off = np.median(mag_z_off)
	std_mz_off = np.std(mag_z_off)

	ret_offset = [median_mx_off, std_mx_off, median_my_off, std_my_off, median_mz_off, std_mz_off]

	median_mx_scale = np.median(mag_x_scale)
	std_mx_scale = np.std(mag_x_scale)
	median_my_scale = np.median(mag_y_scale)
	std_my_scale = np.std(mag_y_scale)
	median_mz_scale = np.median(mag_z_scale)
	std_mz_scale = np.std(mag_z_scale)

	ret_scale = [median_mx_scale, std_mx_scale, median_my_scale, std_my_scale, median_mz_scale, std_mz_scale]

	median_mx_off_diag = np.median(mag_x_off_diag)
	std_mx_off_diag = np.std(mag_x_off_diag)
	median_my_off_diag = np.median(mag_y_off_diag)
	std_my_off_diag = np.std(mag_y_off_diag)
	median_mz_off_diag = np.median(mag_z_off_diag)
	std_mz_off_diag = np.std(mag_z_off_diag)

	ret_off_diag = [median_mx_off_diag, std_mx_off_diag, median_my_off_diag, std_my_off_diag, median_mz_off_diag, std_mz_off_diag]

	return ret_offset, ret_scale, ret_off_diag

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print("Usage: python mag_analysis.py <log.hdf5>\n")
		sys.exit()

	cal_list, cal_dict = main(sys.argv[1])
	ret_offset, ret_scale, ret_off_diag = stat_mag_cal(cal_list, cal_dict)
	stat_dict = {}
	stat_dict['x_offset'] = ret_offset[0]
	stat_dict['y_offset'] = ret_offset[2]
	stat_dict['z_offset'] = ret_offset[4]

	stat_dict['x_scale'] = ret_scale[0]
	stat_dict['y_scale'] = ret_scale[2]
	stat_dict['z_scale'] = ret_scale[4]

	stat_dict['x_off_diag'] = ret_off_diag[0]
	stat_dict['y_off_diag'] = ret_off_diag[2]
	stat_dict['z_off_diag'] = ret_off_diag[4]
	
	ret_list, ret_dict = inverse_cal(sys.argv[1], stat_dict)
