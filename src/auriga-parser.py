#!/usr/bin/env python
# -*- coding: utf-8 -*-

# USI Viewer 0.2
# Copyright 2015 Rikki Mongoose (http://github.com/rikkimongoose)
# This software is licensed under the "GNU GPL" License. The terms are also available at
# http://www.gnu.org/licenses/gpl.html
import os, sys, getopt, ctypes, codecs
from usi import *

SETTINGS = {}

def setup_console(sys_enc="utf-8"):
    reload(sys)
    try:
        # для win32 вызываем системную библиотечную функцию
        if sys.platform.startswith("win"):
            import ctypes
            enc = "cp%d" % ctypes.windll.kernel32.GetOEMCP() #TODO: проверить на win64/python64
        else:
            # для Linux всё, кажется, есть и так
            enc = (sys.stdout.encoding if sys.stdout.isatty() else
                        sys.stderr.encoding if sys.stderr.isatty() else
                            sys.getfilesystemencoding() or sys_enc)

        # кодировка для sys
        sys.setdefaultencoding(sys_enc)

        # переопределяем стандартные потоки вывода, если они не перенаправлены
        if sys.stdout.isatty() and sys.stdout.encoding != enc:
            sys.stdout = codecs.getwriter(enc)(sys.stdout, 'replace')

        if sys.stderr.isatty() and sys.stderr.encoding != enc:
            sys.stderr = codecs.getwriter(enc)(sys.stderr, 'replace')

    except:
        pass # Ошибка? Всё равно какая - работаем по-старому...

# Main code
def main():
    #reload(sys)
    #sys.setdefaultencoding('utf-8')
    #setup_console()
    try:
        OPTS, ARGS = getopt.getopt(sys.argv[1:], "fhp", ["file_name", "help", "print"])
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % str(err))
        sys.exit(2)
    OPTS = dict(OPTS)
    if '--help' in OPTS or '-h' in OPTS:
        show_help()
        sys.exit(0)
    if '--print' in OPTS or '-p' in OPTS:
        SETTINGS["print"] = True
    else:
        SETTINGS["print"] = False
    if '--file' in OPTS:
        SETTINGS["file_name"] = OPTS['--file_name']
    elif len(ARGS) > 0:
        SETTINGS["file_name"] = ARGS[0]
    else:
        sys.stderr.write('Filename isn\'t defined.\n')
        show_help()
        sys.exit(0)
    SETTINGS["debug_output"] = False
    do_usi_parse(SETTINGS["file_name"])

class UsiServerController:
    def __init__(self, usi_info):
        self.usi_info = usi_info

    def show_menu(self):
        self.menu_header()
        self.menu_text()
        while True:
            cmd = raw_input('Choose command: ').strip()
            if   cmd == "0" : break;
            elif cmd == "1" : self.show_params()
            elif cmd == "2" : self.show_params_with_telemetry()

    def menu_header(self):
        print("File is loaded.")
        print("====")

    def menu_text(self):
        print ("1 - show params list")
        print ("2 - show params and telemetry")
        print ("")
        print ("0 - exit")

    def show_params(self):
        for param in self.usi_info.params: print ("%s %s\n" % (param.name, param.param_type))
        print ""

    def show_params_with_telemetry(self):
        sys.stdout.write(str(self.usi_info))

def do_usi_parse(file_name):
    """ Parse USI file
    """
    if not os.path.exists(SETTINGS["file_name"]):
        sys.stderr.write("File '%s' doesn't exists.\n" % SETTINGS["file_name"])
        sys.exit(2)
    usi_loader = UsiDataLoader(SETTINGS["file_name"])
    usi_info = usi_loader.do_load()
    if SETTINGS["print"]:
        sys.stdout.write(str(usi_info))
    else:
        sys.stdout.write("File %s is loaded\n" % file_name)
        usi_server = UsiServerController(usi_info)
        usi_server.show_menu()


def show_help():
    """ Show the help about the possible command line options
    """
    sys.stdout.write("""MISATO mock USI data server 0.2
    Show USI file. Usage:
    python usi_parser.py opts [%file_name%]
    -h, --help - show help
    -f, --file_name [%file_name%] - load [%file_name%]
    -p, --print [%file_name%] - print [%file_name%]
    [%file_name%] - file to read
    """)

if __name__ == "__main__":
    main()