#!/bin/sh

ACQ="main_ro"

while true; do
    if pgrep -x "$ACQ" >/dev/null
    then
        :
    else
        sudo /home/pi-unh-hdmi/ULF/main_ro &
    fi
    sleep 60
done
