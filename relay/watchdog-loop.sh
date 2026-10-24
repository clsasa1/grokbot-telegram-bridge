#!/bin/bash
exec 8>/home/box/tgrelay/watchdog-loop.lock; flock -n 8 || exit 0
while true; do /home/box/tgrelay/watchdog.sh; sleep 60; done
