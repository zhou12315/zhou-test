__author__ = 'yazhou.zhao'
# *************
# hotplug autotest
# create: 2016-05-10
# *************

#!/bin/python
#coding='utf-8'

import sys
import os
import time
import re
import hotplug_test
import hotplug_help

from autotest.server.tests.PblazeTestFramework.linux import pblazeTestBase

class hotplugTest_3DWPD(pblazeTestBase.pblazeTestBase):
    version=1

    #init system env ,make case manager member
    def initialize(self, host,rebuild_env=False ):
        super(hotplugTest_3DWPD, self).initialize(host,rebuild_env=rebuild_env)

    def warmup(self,host,replace_flag=1):
        print "prepare test"
        test_path=host.run("ls /root/hotplugTest_3DWPD",timeout=40,ignore_status=True)
        if test_path.exit_status !=0:
            print "send hotplug test script to test machine"
            script_path=os.path.split(os.path.abspath(__file__))[0]
            host.send_file(script_path,"/root/")
            print "ok"
        else:
            print "test script is already exist"
            if replace_flag == 1:
                print "default delete and replace old script"
                script_path=os.path.split(os.path.abspath(__file__))[0]
                host.send_file(script_path,"/root/")
                print "ok"


        print "prepare OK"

    """*here is run function
       *get case ,run case ,check result of test case
    """
    def run_once(self, host):
        print "step 3: run  test case start"
        try:
            host.run("nohup /root/hotplugTest_3DWPD/hotplug_test.py -f case_list.data >/root/hotplugTest_3DWPD/nohup.log 2>&1 &",ignore_status=True)

            lastFileSize=1
            while True:
                curFileSize = host.run("cat /root/hotplugTest_3DWPD/nohup.log | wc -l").stdout.strip()
                if (int(curFileSize) - int(lastFileSize)) >0:
                    print host.run("sed -n '%s,%sp' /root/hotplugTest_3DWPD/nohup.log" % (lastFileSize + 1, int(curFileSize)) ).stdout.strip()
                lastFileSize = int(curFileSize)

                test_result_obj = host.run("cat /root/hotplugTest_3DWPD/nohup.log | tail -n 10 | grep 'test finish'",ignore_status=True)
                if test_result_obj.exit_status ==0:
                    print "test finish !! "
                    break
                else:
                    process_obj = host.run("ps aux |grep -v grep | grep hotplug_test.py >/dev/null",ignore_status=True)
                    if process_obj.exit_status != 0:
                        print "Error: test process exit"
                        sys.exit(0)
                    else:
                        pass
                time.sleep(5)

        except Exception as e:
            print "run  test case failed"
            print e
            sys.exit(0)

        host.run("echo 'test finish!!' | tr -d '\015' | mailx -s  'hotplug test'  yazhou.zhao@memblaze.com ")

