#!/usr/bin/env python
import SocketServer, sys, argparse
from time import strftime, localtime
from threading import Thread
from usi import *
from usiserver import *

VER = "1.0"
ARGS = None
USI_DATA = None
USER_DATA = {}
usi_loader = None

def callback_send_values(do_repeat, user_data_record=None):
    if user_data_record.iter_index >= len(USI_DATA.telemetries):
        if do_repeat:
            user_data_record.iter_index = 0
        else:
            user_data_record.request.close()
            user_data_record.timer.cancel()
    telemetry = USI_DATA.telemetries[user_data_record.iter_index]
    user_data_record.request.send(param_values_responce(ARGS.code, telemetry))

def cancel_user_host(user_host):
    if user_host in USER_DATA:
        if USER_DATA[user_host].timer is not None: USER_DATA[user_host].timer.cancel()
        if USER_DATA[user_host].request is not None: USER_DATA[user_host].request.close()
        del USER_DATA[user_host]

class TCPHandle(SocketServer.BaseRequestHandler):
    def timeprint(string):
        print "[%s] %s" % (strftime("%Y-%m-%d %H:%M:%S", localtime()), string)

    def do_error(self):
        self.request.send(error_msg(ARGS.code))

    def handle(self):
        is_derived_close = False
        data = 'data'
        data = self.request.recv(PACK_HEAD_SIZE)
        pkg_keyword, pkg_size, pkg_type = unpack_head(data)
        user_host = self.client_address[0]
        timeprint("Request from %s with %s keyword" % (user_host, pkg_keyword))
        if pkg_type == PARAM_LIST:
            if pkg_size:
                data = self.request.recv(pkg_size)
                new_params = params_from_ask(data, USI_DATA.params)
                USER_DATA[user_host] = { params : set(new_params), iter_index : 0, timer : None, request : None }
            else:
                if user_host in USER_DATA: del USER_DATA[user_host]
        elif pkg_type == PARAM_VALUES:
            if user_host not in USER_DATA:
                timeprint('Attempt to get values from unsubsribed host %s' % user_host)
                do_error()
            USER_DATA[user_host].request = self.request
            USER_DATA[user_host].timer = Timer(ARGS.delay, callback_send_values, ARGS.repeat, {user_data_record : USER_DATA[user_host]})
            USER_DATA[user_host].timer.start()
            is_derived_close = True
        elif pkg_type == PARAM_INFO:
            #not implemented. accissuble only in db.
            pass
        elif pkg_type == PARAM_CHECKCONNECT:
            timeprint("Connection check request")
            self.request.send('connected')
        elif pkg_type == PARAM_ADD:
            if pkg_size:
                data = self.request.recv(pkg_size)
                new_params = params_from_ask(data, USI_DATA.params)
                if user_host in USER_DATA:
                    for new_param in new_params: USER_DATA[user_host].params.add(new_param)
                else:
                    USER_DATA[user_host] = { params : set(new_params), iter_index : 0, timer : None, request : None }
        elif pkg_type == PARAM_DEL:
            if pkg_size and user_host in USER_DATA:
                data = self.request.recv(pkg_size)
                new_params = params_from_ask(data, USI_DATA.params)
                for new_param in new_params: USER_DATA[user_host].params.remove(new_param)
        elif pkg_type == PARAM_ERROR:
            timeprint('An error occuured in client app at host %s' % user_host)
            cancel_user_host(user_host)
            is_derived_close = True
        elif pkg_type == PARAM_DISCONNECT:
            timeprint('Host %s has been disconnected' % user_host)
            cancel_user_host(user_host)
            is_derived_close = True
        if not is_derived_close:
            timeprint("Responce closed")
            self.request.close()

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

def main():    #define argument options
    parser = argparse.ArgumentParser(usage='%(prog)s [options]')
    parser.add_argument('-V', '--version', action='version', version='auriga %s' % VER)
    parser.add_argument('-s', '--server', type=str, default="localhost", help='host to attach')
    parser.add_argument('-p', '--port', type=int, default=USI_PORT_DEFAULT, help='port to listen')
    parser.add_argument('-r', '--repeat', action='store_true', default=False, help='repeat USI')
    parser.add_argument('-d', '--delay', type=int, default=1000, help='delay of timer in msec')
    parser.add_argument('-c', '--code', type=str, default=CODE_GVM_DRAW, help='USI server code')
    parser.add_argument('usifile', nargs='?', type=argparse.FileType('rb'), default=sys.stdin, help='USI/USL file')
    ARGS = parser.parse_args()

    usi_loader = UsiDataLoader(None)
    usi_loader.set_file(ARGS.usifile)
    USI_DATA = usi_loader.do_load()

    server = ThreadedTCPServer((ARGS.server, ARGS.port), TCPHandle)
    print "*  *"
    print "    *  Auriga USI Server %s" % VER
    print "*      by ZAO Merkury (http://mrcur.ru/), 2015"
    print "    *  Auriga application started on %s:%s" % (ARGS.server, ARGS.port)
    print " *     Ctrl+C to shutdown server; call with --help for options"
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()