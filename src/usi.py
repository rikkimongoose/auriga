#!/usr/bin/env python
# -*- coding: utf-8 -*-

from struct import *
import os, sys

SERVICE_INFO, SERVICE_INFO_HEAD = 1, 2
FILETYPE_USI, FILETYPE_USL = 1, 2

TYPE_ERROR_CODE = -1

PARAM_EMPTY        = 0x7FFF #=32767
PARAM_EMPTY_SIGNAL = 0x2    #=b10
PARAM_EMPTY_STR    = ''

PARSE_STAT_ERROR            = TYPE_ERROR_CODE
PARSE_STAT_TIED             = 0x1
PARSE_STAT_DECOMMUNICATED   = 0x2
PARSE_STAT_PHYSICAL         = 0x4
PARSE_STAT_COMPRESSED       = 0x64

PARAM_TYPE_ERROR            = TYPE_ERROR_CODE
PARAM_TYPE_SIGNAL           = 0
PARAM_TYPE_FUNCTION         = 1
PARAM_TYPE_FUNCTION_DOUBLE  = 4
PARAM_TYPE_CODE             = 2
PARAM_TYPE_CODE_LONG        = 3
PARAM_TYPE_STRING           = 5
PARAM_TYPE_COMPLEX          = 6

PARAM_ADD_TYPE_ERROR          = TYPE_ERROR_CODE
PARAM_ADD_TYPE_SIGNAL         = 0
PARAM_ADD_TYPE_ANALOG         = 1
PARAM_ADD_TYPE_DIGIT          = 2
PARAM_ADD_TYPE_SIT            = 3
PARAM_ADD_TYPE_CIM            = 4
PARAM_ADD_TYPE_DESH           = 5
PARAM_ADD_TYPE_SIGNAL_CONTROL = 6

def strip_c_str(string):
    return string.strip(chr(0x0))

class UsiInfo:
    def __init__(self):
        self.service_info = None
        self.sub_header = None
        self.params = []
        self.telemetries = []
        self.service_info_type = SERVICE_INFO

    def __str__(self):
        str_out = str(self.service_info) + "\n" + str(self.sub_header) + "\n"
        for param in self.params: str_out += str(param)
        for telemetry in self.telemetries: str_out += str(telemetry)
        return str_out

class UsiServiceInfo:
    def __init__(self):
        self.keyword = ""
        self.title = ""
        self.num = ""
        self.test_section = ""
        self.drawing_num = ""
        self.file_start = 0
        self.file_finish = 0
        self.fcreation_time = ""

    def __str__(self):
        return """### SERVICE INFO
KEYWORD\t: %s
TITLE\t: %s
NUM\t: %s
TEST SECTION\t: %s
DRAWING NUM\t: %s
FILE START\t: %f
FILE FINISH\t: %f
CREATION TIME\t: %s
===""" % (self.keyword, self.title, self.num, self.test_section, self.drawing_num, self.file_start, self.file_finish, self.creation_time)
UsiServiceInfo.STRUCT_SIZE = 0x54

class UsiServiceInfoHead:
    def __init__(self):
        self.code = 0
        self.description = ""

    def __str__(self):
        return """### SERVICE INFO (HEAD)
CODE\t: %s
DESCRIPTION\t: %s
===""" % (self.code, self.description)
UsiServiceInfoHead.HEAD_SIZE = 0x4
UsiServiceInfoHead.HEAD_TAG = "HEAD"

class UsiSubHeader:
    def __init__(self):
        self.stat = []
        self.unknown_byte = 0 # not mentioned in standard
        self.time_scale = 0
        self.params_count = 0
        self.buff_length = 0

    def __str__(self):
        return """### SUBHEADER
UNKNOWN BYTE\t: %x
STAT\t: %s
TIME SCALE\t: %s
PARAMS COUNT\t: %s
BUFF LENGTH\t: %s
===""" % (self.unknown_byte, self.stat, self.time_scale, self.params_count, self.buff_length)
UsiSubHeader.STRUCT_SIZE = 0xA

class UsiParam:
    def __init__(self):
        self.index = 0
        self.index_str = "0"
        self.name = ""
        self.param_type = ""
        self.in_address = 0
        self.out_address = 0
        self.param_additional_type = ""
        self.algorithm_num = 0
        self.bit_num = 0
        self.local_num = 0
        self.dimension = "" #= reserv

    def __str__(self):
        return """### USI PARAM %s
NAME\t: %s
PARAM TYPE\t: %s
IN ADDRESS\t: %s
OUT ADDRESS\t: %s
ADDITIONAL TYPE\t: %s
ALGO NUM\t: %s
BIT NUM\t: %s
LOCAL NUM\t: %s
DIMENSION\t: %s
===""" % (self.index, self.name, self.param_type, self.in_address, self.out_address, self.param_additional_type, self.algorithm_num, self.bit_num, self.local_num, self.dimension)
UsiParam.STRUCT_SIZE = 0x20


class UslParam(UsiParam):
    def __init__(self):
        UsiParam.__init__(self)
        self.description = ""
        self.reserved = ""

    def __str__(self):
        return """### USI PARAM %s
NAME\t: %s
PARAM TYPE\t: %s
IN ADDRESS\t: %s
OUT ADDRESS\t: %s
ADDITIONAL TYPE\t: %s
ALGO NUM\t: %s
BIT NUM\t: %s
LOCAL NUM\t: %s
DIMENSION\t: %s
DESCRIPTION\t: %s
RESERVED\t: %s
===""" % (self.index, self.name, self.param_type, self.in_address, self.out_address, self.param_additional_type, self.algorithm_num, self.bit_num, self.local_num, self.dimension, self.description, self.reserved)

UslParam.STRUCT_SIZE = 0x100

class UsiTelemetry:
    def __init__(self):
        self.time = 0
        self.buff_length = 0
        self.file_pos = 0
        self.params = []

    def __str__(self):
        as_str = """### TELEMETRY
TIME\t: %.3f sec
BUFF LENGTH\t: %s
FILE POS\t: %x
===""" % (self.time, self.buff_length, self.file_pos)
        if(len(self.params)): as_str += "\n"
        for param in self.params: as_str += str(param) + "\n"
        return as_str
UsiTelemetry.STRUCT_HEAD_SIZE = 0x6

class UsiTelemetryParam:
    def __init__(self, param = None, size = 0, value = 0):
        self.param = param
        self.size = size
        self.value = value

        # reserved for complex ones
        self.percent = 0
        self.physical = 0
    def __str__(self):
        if self.param is None: return ""
        return "%s (%s) = %s" % (self.param.name, self.size, self.value)

class UsiDataLoader:
    def out(self, obj):
        if self.debug_output: print obj

    def _get_service_info_type(self):
        service_info_type = SERVICE_INFO
        chunk = self.file.read(UsiServiceInfoHead.HEAD_SIZE)
        self.file.seek(0)
        head_tag = strip_c_str(unpack('<4s', chunk)[0])
        if head_tag == UsiServiceInfoHead.HEAD_TAG:
            return SERVICE_INFO_HEAD
        return SERVICE_INFO

    def _read_service_info(self):
        self.usi_info.service_info_type = self._get_service_info_type()
        service_info = None
        if self.usi_info.service_info_type == SERVICE_INFO:
            service_info = UsiServiceInfo()
            chunk = self.file.read(UsiServiceInfo.STRUCT_SIZE)
            keyword, title, num, test_section, drawing_num, file_start, file_finish, creation_time = unpack('<10s11s11s17s11sff16s', chunk)
            service_info.keyword = strip_c_str(keyword)
            service_info.title = strip_c_str(title)
            service_info.num = strip_c_str(num)
            service_info.test_sectio = strip_c_str(test_section)
            service_info.drawing_num = strip_c_str(drawing_num)
            service_info.file_start = file_start
            service_info.file_finish = file_finish
            service_info.creation_time = strip_c_str(creation_time)
        elif self.usi_info.service_info_type == SERVICE_INFO_HEAD:
            service_info = UsiServiceInfoHead()
            self.file.seek(UsiServiceInfoHead.HEAD_SIZE)
            chunk = self.file.read(UsiServiceInfo.STRUCT_SIZE - UsiServiceInfoHead.HEAD_SIZE)
            code, description = unpack('<B79s', chunk)
            service_info.code = code
            service_info.description = strip_c_str(description)
        self.out(service_info)
        return service_info

    def _read_subheader_data(self):
        chunk = self.file.read(UsiSubHeader.STRUCT_SIZE)
        sub_header = UsiSubHeader()
        unknown_byte, stat, time_scale, params_count, buff_length = unpack('<BBIHH', chunk)
        sub_header.unknown_byte = unknown_byte
        sub_header.stat = self._parse_stat(stat)
        sub_header.time_scale = time_scale
        sub_header.params_count = params_count
        sub_header.buff_length = buff_length
        self.out(sub_header)
        return sub_header

    def _read_param_usi(self, index):
        param_data = UsiParam()
        chunk = self.file.read(UsiParam.STRUCT_SIZE)
        name, param_type, in_address, out_address, param_additional_type, algorithm_num, bit_num, local_num, dimension = unpack('<10sHHHHBBH10s', chunk)
        param_data.index = index
        param_data.index_str = str(index)
        param_data.name = strip_c_str(name)
        param_data.param_type_num = param_type
        param_data.param_type = self._get_param_type_title(param_type)
        param_data.in_address = in_address
        param_data.out_address = out_address
        param_data.param_additional_type_num = param_additional_type
        param_data.param_additional_type = self._get_param_additional_type_title(param_additional_type)
        param_data.algorithm_num = algorithm_num
        param_data.bit_num = bit_num
        param_data.local_num = local_num
        param_data.dimension = strip_c_str(dimension)
        self.out(param_data)
        return param_data

    def _read_param_usl(self, index):
        param_data = UslParam()
        chunk = self.file.read(UslParam.STRUCT_SIZE)
        name, dimension, description, param_type, in_address, out_address, param_additional_type, algorithm_num, bit_num, local_num, reserved = unpack('<32s32s32sHHHHBBH148s', chunk)
        param_data.index = index
        param_data.index_str = str(index)
        param_data.name = strip_c_str(name)
        param_data.param_type_num = param_type
        param_data.param_type = self._get_param_type_title(param_type)
        param_data.in_address = in_address
        param_data.out_address = out_address
        param_data.param_additional_type_num = param_additional_type
        param_data.param_additional_type = _get_param_additional_type_title(param_additional_type)
        param_data.algorithm_num = algorithm_num
        param_data.bit_num = bit_num
        param_data.local_num = local_num
        param_data.dimension = strip_c_str(dimension)
        
        param_data.description = strip_c_str(description)
        param_data.reserved = strip_c_str(reserv)
        self.out(param_data)
        return param_data

    def _read_telemetry(self):
        chunk = self.file.read(UsiTelemetry.STRUCT_HEAD_SIZE)
        if not chunk: return None
        telemetry_data = UsiTelemetry()
        telemetry_time, buff_length = unpack('<LH', chunk)

        telemetry_data.time = self._get_telemetry_time(telemetry_time)
        telemetry_data.buff_length = buff_length
        telemetry_data.file_pos = self.file.tell()

        chunk = self.file.read(buff_length)
        if not chunk:
            sys.stderr.write("File is abrupted")
            return None;
        for param in self.usi_info.params:
            size_for_param = self._get_telemetry_size_for_param(param.param_type)
            subchunk = chunk[param.out_address : param.out_address + size_for_param]
            value = 0
            if size_for_param == 2: value = unpack('<H', subchunk)[0]
            elif size_for_param == 4: value = unpack('<f', subchunk)[0]
            elif size_for_param == 8: value = unpack('<d', subchunk)[0]
            else: sys.stderr.write("Unknown type of param\t: %s" % param.param_type)
            if param.param_type_num == PARAM_TYPE_SIGNAL:
                if 1 << param.bit_num & value: value = 1
                else: value = 0
            if param.index_str not in self.params_loaded or self.params_loaded[param.index_str] != value:
                self.params_loaded[param.index_str] = value
                usi_telemetry_param = UsiTelemetryParam()
                usi_telemetry_param.param = param
                usi_telemetry_param.size = size_for_param
                usi_telemetry_param.value = value
                telemetry_data.params.append(usi_telemetry_param)
        self.out(telemetry_data)
        return telemetry_data

    def do_load_head(self):
        self.usi_info = UsiInfo()
        self.usi_info.service_info = self._read_service_info()
        self.usi_info.sub_header = self._read_subheader_data()

    def do_load_params(self):
        do_read_param = None
        if self.filetype == FILETYPE_USL:
            do_read_param = self._read_param_usl
        else:
            do_read_param = self._read_param_usi
        map(lambda i : self.usi_info.params.append(do_read_param(i)), range(0, self.usi_info.sub_header.params_count))

    def do_load_telemetry(self):
        telemetry_data = self._read_telemetry()
        if telemetry_data is not None:
            self.usi_info.telemetries.append(telemetry_data)
            while telemetry_data is not None:
                self.usi_info.telemetries.append(telemetry_data)
                telemetry_data = self._read_telemetry()

    def get_empty_for_param(self, param_type):
        if   param_type in [PARAM_TYPE_SIGNAL]:
            return PARAM_EMPTY_SIGNAL
        elif param_type in [PARAM_TYPE_FUNCTION, PARAM_TYPE_FUNCTION_DOUBLE, PARAM_TYPE_CODE, PARAM_TYPE_CODE_LONG]:
            return PARAM_EMPTY
        elif param_type in [PARAM_TYPE_STRING]:
            return PARAM_EMPTY_STR
        else:
            return 0

    def do_load_zero_telemetry(self):
        telemetry_data = UsiTelemetry()
        telemetry_data.time = 0
        telemetry_data.buff_length = 0
        telemetry_data.file_pos = 0
        for param in self.usi_info.params:
            value = self.get_empty_for_param(param.param_type)
            self.params_loaded[param.index_str] = value
            usi_telemetry_param = UsiTelemetryParam()
            usi_telemetry_param.param = param
            usi_telemetry_param.size = self._get_telemetry_size_for_param(param.param_type)
            usi_telemetry_param.value = value
            telemetry_data.params.append(usi_telemetry_param)
        self.usi_info.telemetries.append(telemetry_data)
        self.out(telemetry_data)
        return telemetry_data

    def do_load_opened(self):
        self.do_load_head()
        self.do_load_params()
        self.params_loaded = {}
        if self.zero_telemetry:
            self.do_load_zero_telemetry()
        self.do_load_telemetry()
        self._close()
        self.file = None
        return self.usi_info

    def do_load(self):
        if self.file is None:
            self._open()
        return self.do_load_opened()

    def set_file(self, file_stream):
        self.file = file_stream
        if file_stream is None:
            self.filetype = self.usi_file_type_by_name(file_stream.name)
        else:
            self.filetype = FILETYPE_USI

    def usi_file_type_by_name(self, filename):
        if(filename.strip().lower().endswith('usl')):
            return FILETYPE_USL
        else:
            return FILETYPE_USI

    def _from_oem_str(self, oem_str):
        return oem_str#.decode("cp866").encode()

    def _parse_code(self, codeType, code, dictCode):
        if code in dictCode:
            return dictCode[code]
        sys.stderr.write("Unknown %s code: %s\n" % (codeType, code))
        return dictCode[TYPE_ERROR_CODE]

    def _parse_stat(self, code):
        return self._parse_code("USI file stat" , code, {
                PARSE_STAT_ERROR : "ERROR",
                PARSE_STAT_TIED : "tied",
                PARSE_STAT_DECOMMUNICATED : "decommunicated",
                PARSE_STAT_PHYSICAL : "physical",
                #0x8 : RESERVED,
                #0x16 : RESERVED,
                #0x32 : RESERVED,
                PARSE_STAT_COMPRESSED : "compressed"
            })

    def _get_param_type_title(self, code):
        return self._parse_code("param type", code, {
                    PARAM_TYPE_ERROR : "ERROR",
                    PARAM_TYPE_SIGNAL : "Signal",
                    PARAM_TYPE_FUNCTION : "Function",
                    PARAM_TYPE_CODE : "Code",
                    PARAM_TYPE_CODE_LONG : "Code (Long)",
                    PARAM_TYPE_FUNCTION_DOUBLE : "Function (Double)",
                    PARAM_TYPE_STRING : "String",
                    PARAM_TYPE_COMPLEX : "Complex"
                })

    def _get_param_additional_type_title(self, code):
        return self._parse_code("additional param type", code, {
                    PARAM_ADD_TYPE_ERROR : "ERROR",
                    PARAM_ADD_TYPE_SIGNAL : "Signal",
                    PARAM_ADD_TYPE_ANALOG : "Analog",
                    PARAM_ADD_TYPE_DIGIT : "Digit",
                    PARAM_ADD_TYPE_SIT : "SIT",
                    PARAM_ADD_TYPE_CIM : "CIM",
                    PARAM_ADD_TYPE_DESH : "DESH",
                    PARAM_ADD_TYPE_SIGNAL_CONTROL : "SignalControl"
                })

    def _get_telemetry_size_for_param(self, param_code):
        if param_code in ["Signal", "Code"]: return 2
        if param_code in ["Function", "Code (Long)"]: return 4
        if param_code in ["Function (Double)"]: return 8
        else: return 0

    def _get_telemetry_time(self, telemetry_time):
        return (telemetry_time * 1.0) / self.usi_info.sub_header.time_scale

    def __init__(self, file_stream):
        self.zero_telemetry = True
        self.file = None
        self.usi_info = None
        self.debug_output = False
        self.set_file(file_stream)

    def _open(self):
        if self.file is None: self.file = open(self.filename, 'rb')

    def _close(self):
        if self.file is not None: self.file.close()

if __name__ == "__main__":
    print "PyUSI class module"