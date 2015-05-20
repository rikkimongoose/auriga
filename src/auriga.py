#!/usr/bin/env python
import SocketServer, sys, argparse
from time import strftime, localtime
from threading import Thread
from usi import *
from usiserver import *

VER = "1.0"

def callback_send_values(do_repeat, user_data_record = None, usi_data = None):
    if user_data_record.iter_index >= len(USI_DATA.telemetries):
        if do_repeat:
            user_data_record['iter_index'] = 0
        else:
            user_data_record['request'].close()
            user_data_record['timer'].cancel()
    telemetry = usi_data.telemetries[user_data_record['iter_index']]
    user_data_record.request.send(param_values_responce(user_data_record['code'], telemetry))

def timeprint(string):
    print "[%s] %s" % (strftime("%Y-%m-%d %H:%M:%S", localtime()), string)

class TCPHandle(SocketServer.BaseRequestHandler):
    def do_error(self):
        self.request.send(error_msg(self.server.code))

    def handle(self):
        is_derived_close = False
        data = self.request.recv(PACK_HEAD_SIZE)
        pkg_keyword, pkg_size, pkg_type = unpack_head(data)
        user_host = self.client_address[0]
        timeprint("Request from %s with %s keyword, package size: %s" % (user_host, pkg_keyword, pkg_size))
        if pkg_type == PARAM_LIST:
            if pkg_size:
                data = self.request.recv(pkg_size)
                timeprint("Subscribe request")
                new_params = params_from_ask(data, self.server.usi_data.params)
                self.server.user_data[user_host] = { 'params' : set(new_params), 'code' : self.server.code, 'iter_index' : 0, 'timer' : None, 'request' : None }
                self.request.send(param_list_request(self.server.code, new_params))
        elif pkg_type == PARAM_VALUES:
            if user_host not in self.server.user_data:
                timeprint('Attempt to get values from unsubsribed host %s' % user_host)
                self.do_error()
            else:
                timerThread = Timer(self.server.delay, callback_send_values, self.server.repeat, {'user_data_record' : self.server.user_data[user_host], 'usi_data' : self.server.usi_data})
                self.server.user_data[user_host].request = self.request
                self.server.user_data[user_host].timer = timerThread
                timerThread.start()
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
                new_params = params_from_ask(data, self.server.usi_data.params)
                if user_host in self.server.user_data:
                    map(lambda p : self.server.user_data[user_host].params.add(p), new_params)
                else:
                    self.server.user_data[user_host] = { params : set(new_params), iter_index : 0, timer : None, request : None }
        elif pkg_type == PARAM_DEL:
            if pkg_size and user_host in self.server.user_data:
                data = self.request.recv(pkg_size)
                new_params = params_from_ask(data, self.server.usi_data.params)
                map(lambda p : self.server.user_data[user_host].params.remove(p), new_params)
        elif pkg_type == PARAM_ERROR:
            timeprint('An error occuured in client app at host %s' % user_host)
            self.server.cancel_user_host(user_host)
            self.server.del_user_host(user_host)
            is_derived_close = True
        elif pkg_type == PARAM_DISCONNECT:
            timeprint('Host %s has been disconnected' % user_host)
            self.server.cancel_user_host(user_host)
            self.server.del_user_host(user_host)
            is_derived_close = True
        if not is_derived_close:
            timeprint("Responce closed")
            self.request.close()

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def cancel_user_host(self, user_host):
        if user_host not in self.user_data: return
        if self.user_data[user_host]['timer'] is not None: self.user_data[user_host]['timer'].cancel()
        if self.user_data[user_host]['request'] is not None:  self.user_data[user_host]['request'].close()

    def del_user_host(self, user_host):
        del self.user_data[user_host]

    def clean_up(self):
        for user_host in self.user_data:
            self.cancel_user_host(user_host)

def main():
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
    usi_data = usi_loader.do_load()

    server = ThreadedTCPServer((ARGS.server, ARGS.port), TCPHandle)
    server.usi_data = usi_data
    server.code = ARGS.code
    server.repeat = ARGS.repeat
    server.delay = ARGS.delay
    server.user_data = {}

    print "*  *"
    print "    *  Auriga USI Server %s" % VER
    print "*      (c)Rikki Mongoose (http://github.com/rikkimongoose/auriga), 2015"
    print "    *  Auriga application started on %s:%s" % (ARGS.server, ARGS.port)
    print " *     Ctrl+C to shutdown server; call with --help for options"
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.clean_up()

if __name__ == "__main__":
    main()