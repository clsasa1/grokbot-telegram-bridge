#!/bin/bash
# Ставит мост Telegram <-> Grok Bot на бокс: /home/box/tgrelay (relay) и /home/box/bin (tg-* команды).
# Перед запуском заполни /home/box/tgrelay/config.env (см. config.env.example) или задай эти переменные окружения:
# TELEGRAM_BOT_TOKEN, TG_ROUTINE_WEBHOOK_KEY, TG_ROUTINE_WEBHOOK_URL, TG_USER_ID, TG_GROUP_ID.
set -e
cd "$(dirname "$0")"
[ -f /home/box/tgrelay/config.env ] && set -a && . /home/box/tgrelay/config.env && set +a
for v in TELEGRAM_BOT_TOKEN TG_ROUTINE_WEBHOOK_KEY TG_ROUTINE_WEBHOOK_URL TG_USER_ID TG_GROUP_ID; do
  [ -n "${!v}" ] || { echo "Нет переменной $v"; exit 1; }
done
mkdir -p /home/box/tgrelay/media /home/box/tgrelay/typing /home/box/bin
cp relay/relay.py relay/transcribe.py relay/watchdog.sh relay/watchdog-loop.sh /home/box/tgrelay/
[ -f /home/box/tgrelay/topics.json ] || echo '{}' > /home/box/tgrelay/topics.json
cp bin/* /home/box/bin/; chmod +x /home/box/bin/tg-* /home/box/tgrelay/*.sh
# Расшифровка голосовых (по желанию, ~500 МБ): faster-whisper в venv
if [ "${SKIP_WHISPER:-0}" != 1 ]; then
  command -v ffmpeg >/dev/null || sudo apt-get install -y ffmpeg || true
  python3 -m venv /home/box/tgrelay/venv && /home/box/tgrelay/venv/bin/pip install -q faster-whisper numpy || echo "whisper не встал, голосовые будут без расшифровки"
fi
pgrep -f watchdog-loop.sh >/dev/null || (cd /home/box/tgrelay && setsid nohup ./watchdog-loop.sh >/dev/null 2>&1 < /dev/null &)
echo "Готово. Проверка: pgrep -af relay.py; cat /home/box/tgrelay/relay.out"
