#!/usr/bin/env python

import sys, argparse
from usi import *

VER = "1.0"

# Main code
def main():
    parser = argparse.ArgumentParser(usage='%(prog)s [options]')
    parser.add_argument('-V', '--version', action='version', version='auriga parser %s' % VER)
    parser.add_argument('-p', '--params', action='store_true', default=False, help='print params only')
    parser.add_argument('usifile', nargs='?', type=argparse.FileType('rb'), default=sys.stdin, help='USI/USL file')
    ARGS = parser.parse_args()
    usi_loader = UsiDataLoader(None)
    usi_loader.set_file(ARGS.usifile)
    USI_DATA = usi_loader.do_load()
    if ARGS.params:
        for param in USI_DATA.params: print ("%s %s\n" % (param.name, param.param_type))
        print ""
    else:
        print USI_DATA

if __name__ == "__main__":
    main()