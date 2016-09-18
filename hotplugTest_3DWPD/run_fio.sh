#!/bin/bash
#function random()
#{
#        min=$1
#        max=$2
#        num=$RANDOM
#        echo $(( retnum = num % max + min ))
#
#}

command -v screen >/dev/null 2>&1 || { echo >2& "need install screen"; yum install -y screen; }
trap '{
echo "
fio  quit!!" > temp_test.log ;
kill -9 `pidof fio` >/dev/null 2>&1;
kill -9 `pidof SCREEN` >/dev/null 2>&1;
screen -wipe >/dev/null 2>&1;
echo "ok,exit";
exit 1;
}' INT


nvme_ls_count=0


while true
do
    c=0

    command=`ls /dev/nvme*n1`
    if [ -z "$command" ]; then
            echo "no file,retry  "
            sleep 10
            nvme_ls_count=$(( $nvme_ls_count + 1 ))
            if [ $nvme_ls_count -lt 200  ];then
              continue
            else
              echo "no file ,exit"
              exit 1
            fi
    else
            nvme_ls_count=0
    fi

    for filename in $command
    do
      filelist[$c]="$filename"
      c=$(( $c + 1 ))
    done

    for (( i=0; i < $c; i++ ))
    do
      ps -ef |grep -v grep | grep "filename=${filelist[$i]}" >/dev/null 2>&1
      if [ $? -ne 0 ]; then
            nohup fio --ioengine=libaio --randrepeat=0 --norandommap --filename=${filelist[$i]} --runtime=9999999 --time_based --allow_file_create=0 --name=rand_rw --rw=randrw --rwmixwrite=90 --bsrange=1k-64k --blocksize_unaligned  --iodepth=64 --size=10M --numjobs=6 --name=rw_global --rw=randrw --rwmixwrite=70 --direct=1 --bs=64k --iodepth=64 --numjobs=3 >/dev/null 2>&1 &
            #screen -S "fio_$i" -p 0 -X stuff "wait;exit"$(echo -ne '\015')
      fi
      sleep 1
    done
    sleep 5
done

