#!/usr/bin/env python
import os
from struct import *
from usi import *

CODE_GVM_DRAW   = "GVM_DRAW70"
CODE_SEA_LAUNCH = "SEA_LAUN53"

USI_PORT_DEFAULT = 0x3131

PARAM_LIST         = 0
PARAM_VALUES       = 1
PARAM_INFO         = 2
PARAM_CHECKCONNECT = 3
PARAM_ADD          = 4
PARAM_DEL          = 5
PARAM_ERROR        = 101
PARAM_DISCONNECT   = 102

PACK_HEAD_SIZE = 0xE

ASK_PARAM_SIZE = 0x23

PARAM_HEAD_STRUCT = '<10sHH'

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
    return pack('<Hb32s', param.index, param.param_type_num, param.name[:32])

def params_from_ask(ask_params_data, params):
    param_titles = []
    offset = 0
    while offset < len(ask_params_data):
        ask_param_data = ask_params_data[offset : offset + ASK_PARAM_SIZE]
        index, param_type_num, name = unpack('<Hb32s', ask_param_data)
        name = strip_c_str(name)
        if filter(lambda p: p.name == name, params):
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

def param_values_responce(code, telemetry):
    params_buff = ''
    for param_value in telemetry.params:
        data_buff = None
        if param_value.param.param_type_num == PARAM_TYPE_SIGNAL:
            data_buff = pack('<Hb', param_value.param.index, param_value.value)
        elif param_value.param.param_type_num == PARAM_TYPE_FUNCTION:
            data_buff = pack('<Hf', param_value.param.index, param_value.value)
        elif param_value.param.param_type_num == PARAM_TYPE_FUNCTION_DOUBLE:
            data_buff = pack('<Hd', param_value.param.index, param_value.value)
        elif param_value.param.param_type_num == PARAM_TYPE_CODE:
            data_buff = pack('<HH', param_value.param.index, param_value.value)
        elif param_value.param.param_type_num == PARAM_TYPE_CODE_LONG:
            data_buff = pack('<Hl', param_value.param.index, param_value.value)
        elif param_value.param.param_type_num == PARAM_TYPE_STRING:
            val = value[:63]
            str_len = len(val)
            data_buff = pack('<Hc%ss' % str_len, param_value.param.index, str_len, val)
        elif param_value.param.param_type_num == PARAM_TYPE_COMPLEX:
            data_buff = pack('<HHff', param_value.param.index, param_value.value, param_value.percent, param_value.physical)
        if data_buff is None: continue
        params_buff += data_buff
    prefix_buff = pack(PARAM_HEAD_STRUCT, code, len(params_buff) + 4, PARAM_VALUES)
    time_buff = pack('<i', telemetry.time)
    return prefix_buff + time_buff + params_buff

def checkconnect_msg(code):
    return pack(PARAM_HEAD_STRUCT, code, 0, PARAM_CHECKCONNECT)

def error_msg(code):
    return pack(PARAM_HEAD_STRUCT, code, 0, PARAM_ERROR)

def disconnect_msg(code):
    return pack(PARAM_HEAD_STRUCT, code, 0, PARAM_DISCONNECT)

if __name__ == "__main__":
    print "PyUSI server algorithms module"