#!/usr/bin/env python
import SocketServer, sys, argparse
from threading import Timer, Thread, Event
from time import strftime, localtime, sleep
from usi import *
from usiserver import *

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
                self.server.user_data[user_host] = { 'params' : set(new_params), 'code' : self.server.code, 'iter_index' : 0 }
                self.request.send(param_list_responce(self.server.code, new_params))
        elif pkg_type == PARAM_VALUES:
            if user_host not in self.server.user_data:
                timeprint('Attempt to get values from unsubscribed host %s' % user_host)
                self.do_error()
            else:
                timeprint('Request for values from %s' % user_host)
                timer_delay = self.server.delay / 1000
                self.server.user_data[user_host]['request'] = self.request
                self.server.user_data[user_host]['iter_index']  = 0
                telemetries_len = len(self.server.usi_data.telemetries)
                while self.server.user_data[user_host]['iter_index'] < telemetries_len:
                    try:
                        timeprint('Sending telemetry #%03d to %s' % (self.server.user_data[user_host]['iter_index'], user_host))
                        self.request.send(param_values_responce(self.server.code, self.server.usi_data.telemetries[self.server.user_data[user_host]['iter_index']], self.server.is_inner_time))
                        sleep(timer_delay)
                    except Exception as ex:
                        timeprint('Communication breakdown with %s' % user_host)
                        return
                    self.server.user_data[user_host]['iter_index'] += 1
                    if self.server.user_data[user_host]['iter_index']  >= telemetries_len: #and do_repeat:
                        self.server.user_data[user_host]['iter_index'] = 0
                is_derived_close = True
        elif pkg_type == PARAM_INFO:
            #not implemented. accissuble only in db.
            pass
        elif pkg_type == PARAM_CHECKCONNECT:
            timeprint("Connection check request")
            self.request.send('connected')
        elif pkg_type == PARAM_ADD:
            timeprint("Request for adding subscriptions")
            if pkg_size:
                data = self.request.recv(pkg_size)
                new_params = params_from_ask(data, self.server.usi_data.params)
                if user_host in self.server.user_data:
                    map(lambda p : self.server.user_data[user_host]['params'].add(p), new_params)
                else:
                    self.server.user_data[user_host] = { params : set(new_params), iter_index : 0, request : None }
        elif pkg_type == PARAM_DEL:
            timeprint("Request for deleting subscriptions")
            if pkg_size and user_host in self.server.user_data:
                data = self.request.recv(pkg_size)
                new_params = params_from_ask_index(data, self.server.usi_data.params)
                map(lambda p : self.server.user_data[user_host]['params'].remove(p), new_params)
        elif pkg_type == PARAM_ERROR:
            timeprint('An error occured in client app at host %s' % user_host)
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
        if 'request' in self.user_data[user_host] and self.user_data[user_host]['request'] is not None:
            try:
                self.user_data[user_host]['request'].send(disconnect_msg(self.user_data[user_host]['code']))
                self.user_data[user_host]['request'].close()
            except Exception:
                print "User %s is left. The disconnect message wasn't sent." % user_host
            self.user_data[user_host]['request'] = None

    def del_user_host(self, user_host):
        del self.user_data[user_host]

    def clean_up(self):
        for user_host in self.user_data:
            self.cancel_user_host(user_host)

def callback_test_timer(string):
    print string

def main():
    parser = argparse.ArgumentParser(usage='%(prog)s [options]')
    parser.add_argument('-V', '--version', action='version', version='auriga %s' % VER)
    parser.add_argument('-o', '--output', action='store_true', default=False, help='just output usi file, without starting server')
    parser.add_argument('-u', '--output_params', action='store_true', default=False, help='just output params of loaded usi file, without starting server')
    parser.add_argument('-s', '--server', type=str, default="localhost", help='host to attach')
    parser.add_argument('-p', '--port', type=int, default=USI_PORT_DEFAULT, help='port to listen')
    parser.add_argument('-r', '--repeat', action='store_true', default=False, help='repeat USI')
    parser.add_argument('-t', '--time', action='store_true', default=False, help='add inner time')
    parser.add_argument('-d', '--delay', type=int, default=1000, help='delay of timer in msec')
    parser.add_argument('-c', '--code', type=str, default=CODE_GVM_DRAW, help='USI server code')
    parser.add_argument('usifile', nargs='?', type=argparse.FileType('rb'), default=sys.stdin, help='USI/USL file')
    ARGS = parser.parse_args()

    usi_loader = UsiDataLoader(None)
    usi_loader.set_file(ARGS.usifile)
    usi_data = usi_loader.do_load()

    if ARGS.output_params:
        for param in usi_data.params: print ("%s %s\n" % (param.name, param.param_type))
        print ""
        return
    if ARGS.output:
        print usi_data
        return
    try:
        server = ThreadedTCPServer((ARGS.server, ARGS.port), TCPHandle)
    except Exception:
        sys.stderr.write('Socket %s:%s is already occupied. Unable to run Auriga server.\n' % (ARGS.server, ARGS.port))
        quit()
    server.usi_data = usi_data
    server.code = ARGS.code
    server.repeat = ARGS.repeat
    server.delay = ARGS.delay
    server.is_inner_time = ARGS.time
    server.user_data = {}

    print "*  *"
    print "    *  Auriga USI Server %s" % VER
    print "*      (c)Rikki Mongoose (http://github.com/rikkimongoose/auriga), 2015."
    print "    *  Auriga application started on %s:%s." % (ARGS.server, ARGS.port)
    print " *     Ctrl+C to shutdown server; call with --help for options."
    try:
       server.serve_forever()
    except KeyboardInterrupt:
        server.clean_up()

if __name__ == "__main__":
    main()