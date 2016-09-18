#!/bin/python

import time
import serial
import sys
import signal
import datetime
import logger

class quarch_controller(object):

    def __init__(self,logger):
        self.logger = logger

    #serial communicate function
    def serial_read_until(self,Port,Char,Timeout):
        exit_Str=b""
        Start=datetime.datetime.now()
        done=False

        #loop until done
        while (done == False):
            while (Port.inWaiting() > 0):
                #Read 1 char
                newChar = Port.read(1)
                #if this is the exit char
                if newChar == Char:
                    return exit_Str
                #else append to the current string
                else:
                    exit_Str += newChar

                    #reset start time for latest char
                    Start = datetime.datetime.now()

            now_time = datetime.datetime.now()
            if ( now_time - Start ).seconds > Timeout:
                self.logger.m_logger.info( "timeout,exit")
                return exit_Str
        return exit_Str

    def init_quarch(self):

        self.logger.m_logger.info("connect /dev/ttyUSB0")

        #connect serial port
        global ser
        ser = serial.Serial( port='/dev/ttyUSB0',
                            baudrate=19200,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            bytesize=serial.EIGHTBITS)
        global r
        r = ser.flushInput()

        self.logger.m_logger.info("ready!")
        self.logger.m_logger.info("")

    #define hello?
    def run_hello(self):
        global ser
        global r
        self.logger.m_logger.info(">hello?")
        ser.write(b"hello?\r\n")
        r = self.serial_read_until(ser,b"\n",3) #discards the echoed char
        r = self.serial_read_until(ser,b">",3)  #get the response from the module command
        self.logger.m_logger.info( r)

    def enter_console(self):
        global ser
        global r
        self.logger.m_logger.info("input command ")
        try:
            str_cmd=raw_input(">")
            while ( str(str_cmd) != 'q' ):
                ser.write(b"%s\r\n" % str(str_cmd).strip() )
                r = self.serial_read_until(ser, b"\n",3)
                r = self.serial_read_until(ser, b">",3)
                self.logger.m_logger.info( r)
                str_cmd=raw_input(">")
        except Exception as e:
            self.logger.m_logger.info(e)
        
            sys.exit(1)
        self.logger.m_logger.info("exit console")
        sys.exit(0)

    #plug in device
    def pull_up(self):
        global ser
        global r
        ser.write(b"run:power down\r\n")
        r=self.serial_read_until(ser,b"\n",3)
        r=self.serial_read_until(ser,b">",3)
        self.logger.m_logger.info(">run:power down")
        self.logger.m_logger.info("pull up disk----%s" % r)

    #pull up device
    def plug_in(self):
        global ser
        global r
        ser.write(b"run:power up\r\n")
        r=self.serial_read_until(ser,b"\n",3)
        r=self.serial_read_until(ser,b">",3)
        self.logger.m_logger.info(">run:power up")
        self.logger.m_logger.info("plug in disk----%s" % r)

    #set the module to default
    def set_default(self):
        global ser
        global r
        ser.write(b"conf:def state\r\n")
        r=self.serial_read_until(ser,b"\n",3)
        r=self.serial_read_until(ser,b">",3)
        self.logger.m_logger.info(">conf:def state")
        self.logger.m_logger.info("set default state----%s" % r)

    #param  p_cmd----quarch command
    def exec_quarch_cmd(self,p_cmd):
        global ser
        global r
        command_str = b"%s" % p_cmd + "\r\n"
        ser.write(command_str)
        r=self.serial_read_until(ser,b"\n",3)
        r=self.serial_read_until(ser,b">",3)
        self.logger.m_logger.info(">" + str(command_str))
        self.logger.m_logger.info(">----%s" % r)

    #fast hotplug
    #@p_delay_time delay time (x) ms
    def delay_plug_time(self,p_delay_time):
        global ser
        global r
        command_str = b"source:1:delay "+str(p_delay_time)+"\r\n"
        ser.write(command_str)
        r=self.serial_read_until(ser,b"\n",3)
        r=self.serial_read_until(ser,b">",3)
        self.logger.m_logger.info(">" + str(command_str))
        self.logger.m_logger.info("set hotplug speed----%s" % r)

    #close quarch serial port
    def close_quarch(self):
        global ser
        global r
        ser.close()

#main function
if __name__ == '__main__':


    #debug mode & not in daemon
    opts = {'debug':True,'nofork':True}
    log = logger.logger(opts, 'quarch_console.log')
    log.loginit()

    quarch_obj= quarch_controller(log)

    quarch_obj.init_quarch()
    quarch_obj.run_hello()
    quarch_obj.enter_console()
    #time.sleep(5)
    quarch_obj.close_quarch()

