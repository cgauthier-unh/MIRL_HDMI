#!/bin/bash

RTD="python"

# In order for the display to pop up on boot we have to retart
# the python command by opening a terminal on boot (done using /etc/xdg/autostart/open_termianl.desktop)
# stop_check.sh will kill the "check" programs, which will restart once the terminal opens

# This kills the python command when the terminal is opened
pkill -x "$RTD"
sleep 200

while true; do
    if pgrep -x "$RTD" >/dev/null
    then
        :
    else
        python /home/pi-unh-hdmi/ULF/make_spec_and_time_xy.py rtd 180 &
    fi
    sleep 60
done
