#!/usr/bin/env python
import socket, sys, argparse
from usi import *
from usiserver import *

ARGS = None
VER = "1.0"

def client(string, server, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #sock.setblocking(0)
    sock.connect((server, port))
    print "Sending: " + string
    sock.send(string)
    reply = sock.recv(16384)  # limit reply to 16K
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
    subscribe_request = param_list_request(ARGS.code, [param.param for param in telemetry.params])
    print client(subscribe_request, ARGS.server, ARGS.port)

if __name__ == "__main__":
    main()