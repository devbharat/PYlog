#!/usr/bin/env python

from __future__ import print_function
import mmap
import numpy as np
import h5py
import os.path

"""Dump binary log generated by PX4's sdlog2 or APM as CSV
    
Usage: python sdlog2_dump.py <log.bin> [-v] [-e] [-d delimiter] [-n null] [-m MSG[.field1,field2,...]]
    
    -v  Use plain debug output instead of CSV.
    
    -e    Recover from errors.
    
    -d  Use "delimiter" in CSV. Default is ",".
    
    -n  Use "null" as placeholder for empty values in CSV. Default is empty.
    
    -m MSG[.field1,field2,...]
        Dump only messages of specified type, and only specified fields.
        Multiple -m options allowed."""

author  = "Anton Babushkin"
version = "1.2"

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
        self.msg_descrs = {}      # message descriptions by message type map
        self.msg_structs = {}     # precompiled struct objects per message type
        self.msg_labels = {}      # message labels by message name map
        self.msg_names = []       # message names in the same order as FORMAT messages
        self.buffer = bytearray() # buffer for input binary data
        self.ptr = 0              # read pointer in buffer
        self.csv_columns = []     # CSV file columns in correct order in format "MSG.label"
        self.csv_data = {}        # current values for all columns
        self.log_data = {}        # values for all columns
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
                        msg_descr = self.msg_descrs[msg_type]
                        if msg_descr == None:
                            raise Exception("Unknown msg type: %i" % msg_type)
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

def _main():
    if len(sys.argv) < 2:
        print("Usage: python sdlog2_dump.py <log.bin> [-v] [-e] [-d delimiter] [-n null] [-m MSG[.field1,field2,...]] [-t TIME_MSG_NAME]\n")
        print("\t-v\tUse plain debug output instead of CSV.\n")
        print("\t-e\tRecover from errors.\n")
        print("\t-d\tUse \"delimiter\" in CSV. Default is \",\".\n")
        print("\t-n\tUse \"null\" as placeholder for empty values in CSV. Default is empty.\n")
        print("\t-m MSG[.field1,field2,...]\n\t\tDump only messages of specified type, and only specified fields.\n\t\tMultiple -m options allowed.")
        print("\t-t\tSpecify TIME message name to group data messages by time and significantly reduce duplicate output.\n")
        print("\t-fPrint to file instead of stdout")
        return
    fn = sys.argv[1]
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
    parser = sdlog2_pp()
    parser.setCSVDelimiter(csv_delim)
    parser.setCSVNull(csv_null)
    parser.setMsgFilter(msg_filter)
    parser.setTimeMsg(time_msg)
    parser.setFileName(file_name)
    parser.setDebugOut(debug_out)
    parser.setCorrectErrors(correct_errors)

    parser.process(fn)
    del parser
    # Pickle it
    #with open('company_data.pkl', 'wb') as output:
    #    pickle.dump(parser, output, pickle.HIGHEST_PROTOCOL)

if __name__ == "__main__":
    _main()
