#!/bin/bash

while read line
do
	let data_addr=$line
	echo "obase=2;$data_addr" |bc >> $2
done < $1
