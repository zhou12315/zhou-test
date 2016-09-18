#!/usr/bin/env python
# coding=utf-8
__author__ = 'yazhou.zhao'


from optparse import OptionParser
import sys
import os

class hotplug_test_help():
    def __init__(self):
        usage = "./%prog [ -f <filename> ] or [ -n <loops>] -o <on_time> -u <off_time> [ -i <io_type>]"
        self.parser = OptionParser(usage, version="%prog  v1.1")
        self.parser.add_option("-f", "--file", type="string", dest="file_name",
                          help="read case data from FILE,or from console [default: "
                               "read case data from console]",
                          action="store")
        self.parser.add_option("-n", "--number", type="int", dest="test_number",
                          help="total numbers of hotplug test loops,or [default: %default]",
                          default=1000,
                          action="store")
        self.parser.add_option("-o", "--on", type="int", dest="on_time",
                          help="wait time (s) after plug in device,"
                               " if value=0, on_time will be random(15s,360s) [default: %default]",
                          default=0,
                          action="store")
        self.parser.add_option("-u", "--off", type="int", dest="off_time",
                          help="wait time (s) after pull up device,"
                               " if value=0, off_time will be random(5s,15s) [default: %default ]",
                          default=0,
                          action="store")
        self.parser.add_option("-i", "--io",type='int', dest="io_type",
                          help="whether have fio during hotplug test ",
                          action="store")
        (self.options, self.args) = self.parser.parse_args()

        # if len(self.args) == 0:
        #    parser.error("incorrect number of arguments")
        #if len(self.args) == 0:
        #    parser._add_help_option()
if __name__ == "__main__":
    hotplug_test_help().parser.print_help()


