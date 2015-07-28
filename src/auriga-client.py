#!/usr/bin/env python
import socket, sys, argparse
from usi import *
from usiserver import *

ARGS = None

def read_head(sock):
    head_data = sock.recv(PARAM_HEAD_SIZE)
    if not head_data: return 0
    (pkg_keyword, pkg_size, pkg_type) = unpack_head(head_data)
    print "Receiving %s bytes" % (pkg_size)
    return pkg_size

def read_time(sock):
    time_block = sock.recv(VALUES_TIME_SIZE)
    return time_block is not None

def client(cmd_buff, server, port, output_func = None, finite_responce = True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server, port))
    print "Sending (%s bytes)" % (len(cmd_buff))
    sock.send(cmd_buff)
    reply = ''
    if output_func:
        pkg_size = read_head(sock)
        if finite_responce:
            reply = sock.recv(pkg_size)
            output_func(reply)
        else:
            while pkg_size:
                if not read_time(sock): return
                data = sock.recv(pkg_size)
                if not data: break
                output_func(data)
                reply += data
                pkg_size = read_head(sock)
    sock.close()
    return reply

def main():
    parser = argparse.ArgumentParser(usage='%(prog)s [options]')
    parser.add_argument('-V', '--version', action='version', version='auriga %s' % VER)
    parser.add_argument('-s', '--server', type=str, default="localhost", help='host to attach')
    parser.add_argument('-p', '--port', type=int, default=USI_PORT_DEFAULT, help='port to listen')
    parser.add_argument('-c', '--code', type=str, default=CODE_GVM_DRAW, help='USI server code')
    parser.add_argument('usifile', nargs='?', type=argparse.FileType('rb'), default=sys.stdin, help='USI/USL file')
    ARGS = parser.parse_args()
    usi_loader = UsiDataLoader(None)
    usi_loader.set_file(ARGS.usifile)
    usi_data = usi_loader.do_load()
    telemetry = usi_data.telemetries[1]
    output_func = lambda x : sys.stdout.write(str(x) + '\n')
    print "Subscribe with params"
    params_used = [p.param for p in telemetry.params]
    subscribe_request = param_list_request(ARGS.code, params_used)
    client(subscribe_request, ARGS.server, ARGS.port, lambda x: output_func(subscribe_unpack(x, params_used)))
    print "Delete param"
    delete_request = param_delete_request(ARGS.code, [telemetry.params[0].param.index])
    client(delete_request, ARGS.server, ARGS.port, False)
    print "Receive param values"
    value_request = param_values_request(ARGS.code)
    try:
        client(value_request, ARGS.server, ARGS.port, lambda x: output_func(value_unpack(x, telemetry.params)), False)
    except KeyboardInterrupt:
        print "Client exit"

if __name__ == "__main__":
    main()