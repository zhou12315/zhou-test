#!/usr/bin/python
#!coding=utf-8

#need run_fio.sh

import sys
import os
import time
import fcntl
import subprocess
import quarch_controller
import signal
import hotplug_help
import random
import logger
import errno
import socket
from functools import wraps
from multiprocessing import Process, Queue

global g_delay_time,g_loop_count
g_delay_time=0
g_loop_count=0

class TimeoutError(Exception):
    pass

"""
  " descorator function for 120s timeout exit
"""
def timeout(seconds=120,msg="", error_msg = os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            testIp=""
            try:
                csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                csock.connect(('8.8.8.8',80))
                (testIp,port)=csock.getsockname()
                csock.close()
            except socket.error:
                raise Exception("error socket")
            error_log = run_command_with_result("nvmemgr pcie-dump-msglog | grep Err")
            str_msg= "Error: " + msg + ", errno: " +error_msg + error_log
            base_path=os.path.split(os.path.abspath(__file__))[0]
            test_log = os.path.join(base_path,"dump_msg_*.log")
            run_command("nvmemgr pcie-dump-msglog > %s " % test_log)

            run_command("echo 'test fail ! %s ip:%s' | tr -d '\015' | mailx -s 'hotplug test' -a %s yazhou.zhao@memblaze.com" % (str_msg,testIp,test_log))
            raise TimeoutError(str_msg)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)

            return result
        return wraps(func)(wrapper)

    return decorator

"""
  "run system shell command
"""
def run_command(cmd,*args):
    std_out = ""
    if not cmd:
        return -1
    if args:
        cmd=''.join((cmd,) + args)
    p = subprocess.Popen(cmd,shell=True,\
         stdout=open('/dev/null','rw'),stderr=subprocess.STDOUT,close_fds=True)
    #make stdin and stdout non-blocking
    #fcntl.fcntl(p.stdin, fcntl.F_SETFL, os.O_NONBLOCK)
    #fcntl.fcntl(p.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
    #std_out,std_err = p.communicate()
    #while p.poll() ==None:
    #    std_out += p.stdout.readline()
    p.wait()
    return p.returncode

def run_command_with_result(cmd,*args):
    result_str=""
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    p.wait()
    for line in p.stdout:
        result_str += line.strip()
    return result_str


class hotplug_test(object):

    def __init__(self):
        self.base_path=os.path.split(os.path.abspath(__file__))[0]
        fw_version_name = ""
        cmd_str="nvmemgr fw-describe |grep 'vendor specific' | awk -F : '{print $6}' | sed -n 's/..$//;p' | head -n 1"
        p = subprocess.Popen(cmd_str,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
        for line in p.stdout:
            fw_version_name += line.strip()
        log_file_name= "hotplug_%s.log" % fw_version_name
        opts= { 'debug':True,'nofork':True}

        self.logger = logger.logger(opts,log_file_name)
        self.logger.loginit()
        self.logger.m_logger.info("fw version:%s" % fw_version_name)
        self.quarch_controller=quarch_controller.quarch_controller(self.logger)


    """
      "test prepare ,test env initialize,init quarch device
    """
    def test_init(self):
        self.logger.m_logger.info("hotplug test init...")
        self.quarch_controller.init_quarch()
        self.quarch_controller.run_hello()
        #self.quarch_controller.exec_quarch_cmd("*RST")

        self.logger.m_logger.info("init ok")

    """
      "test exec main process.
      "    1. run fio in background
      "    2. start device monitor,  if timeout 120s , device insmod fail,and report test fail by e-mail
      "    3. wait for fio 10s "    3. pull up disk, wait <off_time>s, plug in
      disk,wait for fio <on_time>s "    4. loops step (3) " "param: <run_count>
      , times of exec loop "       <on_time>   , after plug in disk, wait
      time,then pull up disk "       <off_time>  , after pull up disk, wait
      time, then plug in disk
      "       <io_type>   , whether is with IO (0 or 1)
      "
      "Note:  please note run_count, progress will do three hotplug with
      "       (normal speed, quick speed,slow speed) per run_count/3 times
      "
    """
    def test_start(self,run_count, on_time, off_time, io_type):

        #prepare run fio and monitor by condition
        self.prepare_test(io_type)

        i=0
        #loops begin
        while i < run_count:
            #check progress whether is ready
            self.check_process(io_type)

            #print case
            self.print_case_describe(i,run_count,io_type)

            #pull up disk
            self.exec_pull_up_disk(off_time)

            #plug in disk
            self.exec_plug_in_disk(on_time)

            i = i + 1

        self.logger.m_logger.info("**************test finish!!!****************")
        #reset quarch hotplug speed to default value
        #self.quarch_controller.delay_plug_time(25)




    """
      "test exec from file data (here is input test case data file)
      "file path must be same with hotplug_test.py
    """
    def test_start_from_file(self,case_file_name):


        case_file_path = os.path.join(self.base_path,case_file_name)

        if os.path.exists(case_file_path):
            pass
        else:
            self.logger.m_logger.info("not find '%s' at path:%s" % (case_file_name,self.base_path))
            self.test_exit()

        self.logger.m_logger.info("will read test case from %s" % case_file_path)

        with open(case_file_path) as case_fd:
            case_number=0
            for case_line in case_fd.readlines():
                #clean up before test
                cleanup()
                #parse arg from case line
                (return_code, run_count, on_time, off_time, io_type) = self.parse_case_line(case_line)
                if return_code !=0:
                    continue

                case_number = case_number + 1

                #prepare run fio and monitor by condition
                self.prepare_test(io_type)

                i=0
                #loops begin
                while i < run_count:
                    #check progress whether is ready
                    self.check_process(io_type)
                    #set source 4 delay 25ms
                    #self.quarch_controller.exec_quarch_cmd("source:4:delay 40")
                    #self.quarch_controller.exec_quarch_cmd("signal:12V_POWER:source 4")

                    #set 12V_CHARGE to delay 10ms
                    #self.quarch_controller.exec_quarch_cmd("source:2:delay 25")
                    #time.sleep(1)

                    #print case
                    self.print_case_describe(i,run_count,io_type,case_number)
                    #pull up disk
                    self.exec_pull_up_disk(off_time)

                    #reset to default status
                    #self.quarch_controller.exec_quarch_cmd("signal:12V_POWER:source 3")
                    #self.quarch_controller.exec_quarch_cmd("source:2:delay 25")
                    #time.sleep(1)
                    #plug in disk
                    self.exec_plug_in_disk(on_time)

                    i = i + 1

        self.logger.m_logger.info("**************test finish!!!****************")
        #reset quarch hotplug speed to default value
        #self.quarch_controller.delay_plug_time(25)

    #parse case line
    def parse_case_line(self,case):
        test_number = ""
        on_time = ""
        off_time = ""
        io_type = ""

        #check whether is test case by order format
        return_code = 1 if case.find('#') != -1  else 0
        #check  -n arg ,if no arg or error arg, set default value
        if case.find('-n') != -1:
            if len(case.split('-n')[1].split()) > 0:
                test_number = case.split('-n')[1].split()[0].strip()
                test_number = test_number if test_number.isdigit() else "1000"
            else:
                self.logger.m_logger.info("Error: test case '-n' arg has no value, need value")
                self.test_exit()
        else:
            test_number = "1000"


        #check  -o arg ,if no arg or error arg, set default value

        if case.find('-o') != -1:

            if len(case.split('-o')[1].split()) > 0:
                on_time = case.split('-o')[1].split()[0].strip()
                on_time = on_time if on_time.isdigit() else "0"
            else:
                self.logger.m_logger.info("Error: test case '-o' arg has no value, need value")
                self.test_exit()
        else:
            on_time = "0"

        #check  -u arg ,if no arg or error arg, set default value
        if case.find('-u') != -1:
            if len(case.split('-u')[1].split()) > 0:
                off_time = case.split('-u')[1].split()[0].strip()
                off_time = off_time if off_time.isdigit() else "0"
            else:
                self.logger.m_logger.info("Error: test case '-u' arg has no value, need value")
                self.test_exit()
        else:
            off_time = "0"

        #check  -i arg ,if no arg or error arg, set default value
        if case.find('-i') != -1:
            if len(case.split('-i')[1].split()) > 0:
                io_type = case.split('-i')[1].split()[0].strip()
                io_type = io_type if io_type.isdigit() else "0"
            else:
                self.logger.m_logger.info("Error: test case '-i' arg has no value, need value")
                self.test_exit()
        else:
            io_type="0"
            return_code=1
        #print return_code, test_number,on_time,off_time,io_type
        return (return_code, int(test_number) , int(on_time), int(off_time), int(io_type) )

    #pull up disk ,then wait time
    def exec_pull_up_disk(self,off_time):
        real_off_time = off_time if off_time != 0 else random.randint(5,15)

        #note: before pull up disk , send signal 12 to monitor for reset count_register
        #run_command("ps aux | grep -v grep | grep check_device.sh | awk '{print $2}' | xargs kill -SIGUSR2")

        self.quarch_controller.pull_up()
        #clean up dmesg messages
        run_command("dmesg -c >/dev/null ")
        self.logger.m_logger.info("sleep offtime: %ss" % real_off_time)
        time.sleep(real_off_time)


    #plug in disk, then wait time
    def exec_plug_in_disk(self,on_time):
        real_on_time = on_time if on_time != 0 else random.randint(20,600)

        self.quarch_controller.plug_in()
        self.logger.m_logger.info("sleep on_time: %ss" % real_on_time)
        self.wait_on_time(real_on_time)


    #test case describe message
    def print_case_describe(self,cur_count,total_count,io_type,case_number=1):

        loop_count=0
        io_str= "带I/O" if io_type else "不带I/O"


        self.logger.m_logger.info("********case %s *******(%s/%s)***********" % (case_number,cur_count + 1, total_count))
        #if cur_count > (2 * (total_count / 3)):
        #    loop_count = self.change_hotplug_speed(100)
        #    self.logger.m_logger.info("test case: %s 慢速插拔盘" % io_str)
        #elif cur_count > (total_count / 3):
        #    loop_count = self.change_hotplug_speed(10)
        #    self.logger.m_logger.info("test case: %s 快速插拔盘" % io_str)
        #else:
        #    loop_count = self.change_hotplug_speed(25)
        #    self.logger.m_logger.info("test case: %s 正常插拔盘" % io_str)
        self.logger.m_logger.info("test case: %s 插拔盘" % io_str)

        self.logger.m_logger.info("***case loop: %s " % loop_count)


    """
      "switch hotplug speed:
      "             10 ms ---quick speed hotplug
      "             25 ms ---normal speed hotplug
      "             100ms ---slow speed hotplug
    """
    global g_delay_time,g_loop_count
    g_delay_time=0
    g_loop_count=0
    def change_hotplug_speed(self,delay_time):
        global g_delay_time
        global g_loop_count
        global step_time

        if g_delay_time == delay_time:
            g_loop_count=g_loop_count + 1
            return g_loop_count
        else:
            g_delay_time=delay_time
            self.logger.m_logger.info("调整test case（25ms正常拔，10ms快拔，100ms慢拔）")
            self.quarch_controller.delay_plug_time(delay_time)
            g_loop_count = 1
            step_time=20
            return g_loop_count


    """prepare environment,if need io, run fio,run monitor progress.
      "param:  <io_type>=0, no I/O;
      "        <io_type>=1, with I/O;
    """
    def prepare_test(self,io_type):

        #get abspath of test script dic

        #run fio
        if io_type == 1:
            #find fio script file
            fio_path=os.path.join(self.base_path,"run_fio.sh")
            if os.path.exists(fio_path):
                self.logger.m_logger.info("[YES] run fio start...")
                run_command("%s &" % fio_path)
                time.sleep(5)
            else:
                self.logger.m_logger.info("not find 'run_fio.sh' at path:%s" % self.base_path)
                self.logger.m_logger.info("prepare fio fail,test exit")
                self.test_exit()

        elif io_type == 0:
            self.logger.m_logger.info("[No ] run fio in background")
        else:
            self.logger.m_logger.info("unknow io type value(%s),should be 0 or 1" % io_type)
            self.test_exit()


        ##find monitor script file
        #monitor_script_path=os.path.join(self.base_path,"check_device.sh")
        #if os.path.exists(monitor_script_path):
        #    self.logger.m_logger.info("[YES] run monitor progress ...")
        #    run_command("%s &" % monitor_script_path)
        #    time.sleep(6)
        #else:
        #    self.logger.m_logger.info("not find 'check_device.sh' at path:%s" % self.base_path)
        #    self.logger.m_logger.info("run monitor fail,test exit")
        #    self.test_exit()

    """
      "check device whether is ready ,put insmod time to msg queue
    """
    @timeout(120,"insmod nvme timeout")
    def check_device(self,msg_queue):
        try:
            time.sleep(2)
            device_init_count=run_command_with_result("lspci |grep Non |wc -l")
            dev_count = int(device_init_count) * 2
            t_start = time.time()
            dev_count_cur = run_command_with_result("ls /dev/nvme{?,?n?} 2>/dev/null |wc -l ")
            while int(dev_count_cur) != dev_count:
                time.sleep(1)
                dev_count_cur = run_command_with_result("ls /dev/nvme{?,?n?} 2>/dev/null |wc -l ")

            insmod_ok_time= time.time() - t_start
            msg_queue.put("%.6fs" % insmod_ok_time,block=False )
        except TimeoutError as e:
            self.logger.m_logger.info("ERROR: %s" % e)
    """
      "wait for on_time
    """
    def wait_on_time(self,on_time):
        try:
            msg_queue=Queue()
            #create process for check device
            p = Process(target=self.check_device, args=(msg_queue,))
            p.start()
            #get current time
            t_start=time.time()

            p.join(on_time)

            if p.is_alive():
                p.terminate()
                p.join()
            else:
                self.logger.m_logger.info("insmod device time: %s" % msg_queue.get(block=False))

            while(time.time() - t_start) < on_time:
                #self.logger.m_logger.info("wait ")
                time.sleep(1)

        except Exception as e:
            self.logger.m_logger.info("ERROR:%s" % e)
            self.test_exit()
    #check fio and monitor progress whether is running
    #check whether have error messages in dmesg
    def check_process(self,io_type):
        #check fio and monitor process
        fio_return_code=0
        if io_type == 0:
            fio_return_code = 0
        else:
            fio_return_code = run_command("ps -ef |grep -v grep | grep fio >/dev/null 2>&1")

        if fio_return_code != 0:
            self.logger.m_logger.info("fio error !!!,exit")
            self.test_exit()

        Cancelling_IO_code = run_command("dmesg |grep nvme |grep -A 1 'unknown partition' |tail -n 1 | grep 'Cancelling I/O'")
        Abort_IO_code = run_command("dmesg |grep nvme |grep -A 1 'unknown partition' |tail -n 1 | grep 'Aborting I/O'")
        Buffer_IOError_code = run_command("dmesg |grep nvme |grep -A 1 'unknown partition' |tail -n 1 | grep  'Buffer I/O error'")
        if Cancelling_IO_code == 0:
            self.logger.m_logger.info("Error:  Cancelling I/O")
            self.test_exit()
        if Abort_IO_code == 0:
            self.logger.m_logger.info("Error:  Abort IO error")
            self.test_exit()
        if Buffer_IOError_code == 0:
            self.logger.m_logger.info("Error:  buffer io error")
            self.test_exit()
        power_log = run_command_with_result("nvmemgr pcie-dump-msglog | grep 'last powerloss timing'")
        self.logger.m_logger.info("oob-info:%s" % power_log)
        err_log = run_command_with_result("nvmemgr pcie-dump-msglog | grep Err")
        if "Err" in err_log:
            self.logger.m_logger.info("Error:%s" % err_log)
            self.test_exit()


    """
      "test finish,clean test env,reset device to default state
    """
    def test_exit(self):
        #reset quarch hotplug speed to default value
        #self.quarch_controller.delay_plug_time(25)
        #clean up environment
        cleanup()
        base_path=os.path.split(os.path.abspath(__file__))[0]
        test_dir = "test_" + time.strftime("%m_%d_%H_%M_%S",time.localtime(time.time()))
        test_dir = os.path.join(base_path,test_dir)
        test_log = os.path.join(base_path,"hotplug_*.log")
        run_command("mkdir %s" % test_dir)
        run_command("mv -f %s %s" % (test_log,test_dir))
        sys.exit(0)

global step_time
step_time=20
def random_time():
    #first case: time add by *2
    #second case: random 30s to 360s
    global g_loop_count
    global step_time
    if g_loop_count > 8:
        step_time=random.randint(20,360)
    else:
        step_time=step_time *2
    return step_time

def cleanup():
    run_command("ps aux |grep -v grep | grep fio | awk '{print $2}' | xargs kill -9 >/dev/null 2>&1")
    time.sleep(1)

def handler(signum, frame):
    global is_exit
    is_exit = True
    print "receive signal %d, is_exit = %d" % ( signum, is_exit)
    cleanup()
    base_path=os.path.split(os.path.abspath(__file__))[0]
    test_dir = "test_" + time.strftime("%m_%d_%H_%M_%S",time.localtime(time.time()))
    test_dir = os.path.join(base_path,test_dir)
    test_log = os.path.join(base_path,"hotplug_*.log")
    run_command("mkdir %s" % test_dir)
    run_command("mv -f %s %s" % (test_log,test_dir))
    sys.exit(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT,handler)

    help_obj=hotplug_help.hotplug_test_help()
    if help_obj.options.file_name ==None:
        if help_obj.options.on_time ==None or \
            help_obj.options.off_time ==None or \
            help_obj.options.test_number == None or \
            help_obj.options.io_type ==None:
            help_obj.parser.print_help()
            sys.exit(1)

        hotplug_obj= hotplug_test()

        hotplug_obj.test_init()
        hotplug_obj.test_start(help_obj.options.test_number,help_obj.options.on_time,help_obj.options.off_time,help_obj.options.io_type)
        hotplug_obj.test_exit()
    else:
        hotplug_obj= hotplug_test()

        hotplug_obj.test_init()
        hotplug_obj.test_start_from_file(help_obj.options.file_name)
        hotplug_obj.test_exit()

