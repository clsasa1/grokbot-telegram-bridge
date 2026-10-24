#!/bin/bash
[ -f /home/box/tgrelay/config.env ] && set -a && . /home/box/tgrelay/config.env && set +a
# Restart relay if not running or heartbeat stale (>120s). Single instance via flock.
D=/home/box/tgrelay
exec 9>$D/watchdog.lock; flock -n 9 || exit 0
pids=$(pgrep -f "python3 $D/relay.py|python3 relay.py")
hb=$(cat $D/heartbeat 2>/dev/null || echo 0); age=$(( $(date +%s) - hb ))
if [ -z "$pids" ] || [ $age -gt 120 ]; then
  echo "$(date '+%F %T') watchdog: restart (pids='$pids' hb_age=${age}s)" >> $D/relay.out
  [ -n "$pids" ] && kill $pids && sleep 2 && kill -9 $pids 2>/dev/null
  date +%s > $D/heartbeat
  cd $D && setsid nohup python3 $D/relay.py >> $D/relay.out 2>&1 < /dev/null &
fi
