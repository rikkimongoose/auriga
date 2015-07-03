#!/usr/bin/env python
import os
from struct import *
from usi import *

VER = "1.2"

(CODE_GVM_DRAW53, CODE_GVM_DRAW, CODE_SEA_LAUNCH) = ("GVM_DRAW53", "GVM_DRAW70", "SEA_LAUN53")

USI_PORT_DEFAULT = 0x3131

VALUES_TIME_SIZE = 0x4
INNER_TIME_MASK = 0x100000
VALUE_INDEX_SIZE = 0x2
VALUE_TIME_SIZE = 0x2
VALUE_STRING_MAX = 63

PARAM_LIST         = 0
PARAM_VALUES       = 1
PARAM_INFO         = 2
PARAM_CHECKCONNECT = 3
PARAM_ADD          = 4
PARAM_DEL          = 5
PARAM_ERROR        = 101
PARAM_DISCONNECT   = 102

PACK_HEAD_SIZE = 0xE

ASK_PARAM_STRUCT = '<Hb32s'
ASK_PARAM_SIZE = 0x23
ASK_PARAM_INDEX_SIZE = 0x2

PARAM_HEAD_STRUCT = '<10sHH'
PARAM_HEAD_SIZE = 0x0E

class UsiParam:
    def __init__(self, name, index, param_type_num):
        self.name = name
        self.index = index
        self.param_type_num = param_type_num

    def __str__(self):
        return self.name

def unpack_head(data):
    pkg_keyword, pkg_size, pkg_type = unpack(PARAM_HEAD_STRUCT, data)
    pkg_keyword = strip_c_str(pkg_keyword)
    return (pkg_keyword, pkg_size, pkg_type)

def param_to_ask(param):
    return pack(ASK_PARAM_STRUCT, param.index, param.param_type_num, param.name[:32])

def param_from_ask_index(ask_params_data, params):
    param_titles = []
    offset = 0
    while offset < len(ask_params_data):
        ask_param_data = ask_params_data[offset : offset + ASK_PARAM_INDEX_SIZE]
        index = unpack('<H', ask_param_data)
        if filter(lambda p: p.index == index, params):
            param_titles.append(UsiParam(name, index, param_type_num))
        offset += ASK_PARAM_INDEX_SIZE
    return param_titles

def params_from_ask(ask_params_data, params = None):
    param_titles = []
    offset = 0
    while offset < len(ask_params_data):
        ask_param_data = ask_params_data[offset : offset + ASK_PARAM_SIZE]
        index, param_type_num, name = unpack(ASK_PARAM_STRUCT, ask_param_data)
        name = strip_c_str(name)
        if params is None:
            param_titles.append(name)
        elif filter(lambda p: p.name == name, params):
            param_titles.append(UsiParam(name, index, param_type_num))
        offset += ASK_PARAM_SIZE
    return param_titles

def param_info_pack(param_info):
    return pack('<H32s32sffff46b', param_info.index, param_info.measure, param_info.description, param_info.min_val, param_info.max_val, param_info.min_diap, param_info.max_diap, chr(0) * 46)

def param_list_pack(code, params, lambda_param_convert, param_cmd):
    params_buff = ''
    for param in params:
        params_buff += lambda_param_convert(param)
    prefix_buff = pack(PARAM_HEAD_STRUCT, code, len(params_buff), param_cmd)
    return prefix_buff + params_buff

def param_list_request(code, params):
    return param_list_pack(code, params, lambda param: param_to_ask(param),  PARAM_LIST)

def param_list_responce(code, params):
    return param_list_pack(code, params, lambda param: param_to_ask(param), PARAM_LIST)

def param_add_request(code, params):
    return param_list_pack(code, params, lambda param: param_to_ask(param), PARAM_ADD)

def param_add_responce(code, params):
    return param_list_pack(code, params, lambda param: param_to_ask(param), PARAM_ADD)

def param_delete_request(code, indexes):
    return param_list_pack(code, indexes, lambda index: pack('<H', index), PARAM_DEL)

def param_info_request(code, indexes):
    return param_list_pack(code, indexes, lambda index: pack('<H', index), PARAM_INFO)

def param_info_responce(code, param_infos):
    return param_list_pack(code, param_infos, lambda param_info: param_info_pack(param_info), PARAM_INFO)

def param_values_request(code):
    return pack(PARAM_HEAD_STRUCT, code, 0, PARAM_VALUES)

def subscribe_unpack(data):
    return  "\n".join(params_from_ask(data))

def _read_masked_index(index):
    if index & INNER_TIME_MASK:
        return (index ^ INNER_TIME_MASK, True)
    return (index, False)

def _struct_by_type_num(key):
    stat_dict = {
        PARAM_TYPE_SIGNAL : ('<b', 1),
        PARAM_TYPE_FUNCTION : ('<f', 4),
        PARAM_TYPE_FUNCTION_DOUBLE : ('<d', 8),
        PARAM_TYPE_CODE : ('<H', 2),
        PARAM_TYPE_CODE_LONG : ('<l', 4),
        PARAM_TYPE_STRING : ('<c%ss', 0),
        PARAM_TYPE_COMPLEX : ('<Hff', 10)
    }
    return stat_dict[key]

def value_unpack(data, params):
    telemetry_values_str = ""
    telemetry_value_format = "%s\t= %s"
    offset = 0
    while offset < len(data):
        value_data = data[offset : offset + VALUE_INDEX_SIZE]
        if len(value_data) < VALUE_INDEX_SIZE: break
        offset += VALUE_INDEX_SIZE
        value_data_index, has_local_time = _read_masked_index(unpack('<H', value_data)[0])
        local_time = 0
        if has_local_time:
            value_data = data[offset : offset + VALUE_TIME_SIZE]
            offset += VALUE_TIME_SIZE
            local_time = unpack('<H', value_data)
        telemetry_param = (filter(lambda p: p.param.index == value_data_index, params) or [None])[0]
        if telemetry_param is None: continue
        struct_code, struct_size = _struct_by_type_num(telemetry_param.param.param_type_num)
        if struct_size:
            value_data = data[offset : offset + struct_size]
            offset += struct_size
            if struct_size < 10:
                param_value_num = unpack(struct_code, value_data)[0]
                param_value_str = telemetry_value_format % (telemetry_param.param.name, param_value_num)
            else:
                param_value_num, param_value_percent, param_value_physical = unpack(struct_code, value_data)
                param_value_str = telemetry_value_format % (telemetry_param.param.name, "%s (%s%) %s" % (param_value_num, param_value_percent, param_value_physical))
        else:
            struct_size = unpack(struct_code, data[offset : offset + 1])
            param_value_str = unpack('<%ss' % struct_size, data[offset + 1 : struct_size])
            offset += struct_size + 1
            param_value_str = telemetry_value_format % (telemetry_param.param.name, param_value_str)
        telemetry_values_str += param_value_str + '\n'
    return telemetry_values_str

def param_values_responce(code, telemetry, append_inner_time = False):
    DEFAULT_LOCAL_TIME = 1
    params_buff = ''
    for param_value in telemetry.params:
        if append_inner_time:
            data_buff = pack('<HH', param_value.param.index & INNER_TIME_MASK, DEFAULT_LOCAL_TIME)
        else:
            data_buff = pack('<H', param_value.param.index)
        struct_code = _struct_by_type_num(param_value.param.param_type_num)[0]
        if param_value.param.param_type_num in [PARAM_TYPE_SIGNAL, PARAM_TYPE_FUNCTION, PARAM_TYPE_FUNCTION_DOUBLE, PARAM_TYPE_CODE, PARAM_TYPE_CODE_LONG, PARAM_TYPE_STRING, PARAM_TYPE_COMPLEX]:
            data_buff += pack(struct_code, param_value.value)
        elif param_value.param.param_type_num == PARAM_TYPE_STRING:
            val = value[:VALUE_STRING_MAX]
            str_len = len(val)
            data_buff += pack(struct_code % str_len, str_len, val)
        elif param_value.param.param_type_num == PARAM_TYPE_COMPLEX:
            data_buff += pack(struct_code, param_value.value, param_value.percent, param_value.physical)
        else: continue
        params_buff += data_buff
    time_buff = pack('<i', telemetry.time)
    prefix_buff = pack(PARAM_HEAD_STRUCT, code, len(params_buff) + VALUES_TIME_SIZE, PARAM_VALUES)
    return prefix_buff + time_buff + params_buff

def checkconnect_msg(code):
    return pack(PARAM_HEAD_STRUCT, code, 0, PARAM_CHECKCONNECT)

def error_msg(code):
    return pack(PARAM_HEAD_STRUCT, code, 0, PARAM_ERROR)

def disconnect_msg(code):
    return pack(PARAM_HEAD_STRUCT, code, 0, PARAM_DISCONNECT)

if __name__ == "__main__":
    print "PyUSI server algorithms module"