#!/bin/bash
#this file is created by yazhou.zhao
# this file is monitor process,if device insmod is gather than times 120s ,monitor is exit
# and send mail to QA

command -v sendmail >/dev/null 2>&1 || { echo >2& "need install sendmail"; yum install -y sendmail; }
command -v uuencode > /dev/null 2>&1 || { echo >2& "need install sharutils"; yum install -y sharutils; }

trap "{
rm -rf temp*;
echo 'ok,exit';
exit 1;
}" INT

trap "{
echo 'hotplug test finish !!';
kill -9 `pidof SCREEN` >/dev/null 2>&1;
screen -wipe >/dev/null 2>&1;
kill -9 `pidof fio` >/dev/nulli 2>&1;
tr -d '\015' < 'test finish!' | mailx -s  'hotplug test' yazhou.zhao@memblaze.com

exit 1;
}" QUIT


trap '{
count=0;
flag=0;

}' SIGUSR2


device=`lspci | grep Non | wc -l`
device=$(( $device * 2 ))

count=0
flag=0
while true
do
  #check device whether is exisdmesg |grep nvme | grep -i "Cancelling I/O"
  device_count=`ls /dev/{nvme?,nvme?n?} 2>/dev/null | wc -l`
  if [ $device_count -eq $device ]; then
        count=0
        flag=0
  else
        count=$(( $count + 1 ))
  fi

  #stop check progress, collect dump message
  if [ $count -gt 65 ]; then
    nvmemgr pcie-dump-msglog > temp_workaround_before.txt
    if [ $flag -lt 1 ];then
        flag=$(( $flag + 1 ))
        echo "workaround "
        echo "$flag :workaround issue,rmmod nvme ,modprobe nvme" >>temp_test.txt
        rmmod nvme >/dev/null 2>&1
        modprobe nvme >/dev/null 2>&1
        count=0
    else
        nvmemgr pcie-dump-msglog > temp_dumpmsg.txt
        echo '
        hotplug test failed !!
        please ssh  192.168.28.125  check device status.
        root abc123
        ' >> temp_test.txt
        echo "">/var/spool/mail/root
        tr -d '\015' < temp_test.txt | mailx -s  'hotplug test' -a temp_workaround_before.txt -a temp_dumpmsg.txt yazhou.zhao@memblaze.com
        #tr -d '\015' < temp_test.txt | mailx -s  'hotplug test' -a temp_workaround_before.txt -a temp_dumpmsg.txt ming.jiang@memblaze.com
        #tr -d '\015' < temp_test.txt | mailx -s  'hotplug test' -a temp_workaround_before.txt -a temp_dumpmsg.txt yufeng.ren@memblaze.com
        #tr -d '\015' < temp_test.txt | mailx -s  'hotplug test' -a temp_workaround_before.txt -a temp_dumpmsg.txt yang.yuan@memblaze.com
        rm -rf temp*
        exit 1
    fi
  fi
  echo $count
  sleep 2

done
