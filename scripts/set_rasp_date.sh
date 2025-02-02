#!/bin/bash

IP_ADDR=$1
if [[ $# -eq 0 ]]; then
    echo "No ip supplied"
else
    # Set date on remote machine
    sshpass -p 'raspberry' ssh pi@$IP_ADDR "sudo date -s '$(date --iso-8601=seconds)'"

    # Set rtc time
    sshpass -p 'raspberry' ssh pi@$IP_ADDR 'PYTHONPATH=~/Inhalator ~/Inhalator/.inhalator_env/bin/python ~/Inhalator/scripts/set_rtc_time.py'
fi
