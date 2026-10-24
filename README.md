# 🤖 Grok Bot ⇄ Telegram

Двусторонняя связь твоего **Grok Bot** с личным Telegram-ботом: пишешь боту в Telegram (текст, фото, файлы, голосовые) — Grok получает это как задачу и отвечает туда же, с форматированием, кнопками и статусом «⏳ работаю…». Плюс форум-группа с топиками, где у каждого бота-напарника свой топик.

## Как это устроено

```
Telegram ──getUpdates──> relay.py (на боксе Grok) ──POST──> вебхук рутины Grok Bot
                                                                  │
Telegram <──── tg-send / tg-edit / tg-send-file <──── Grok отвечает
```

- `relay/relay.py` — long-polling Telegram, пропускает **только твои** сообщения, ставит 👀 и «печатает…», качает медиа в `/home/box/tgrelay/media/`, расшифровывает голосовые локально (faster-whisper), шлёт всё на вебхук рутины.
- `relay/watchdog.sh` + `watchdog-loop.sh` — раз в минуту проверяют heartbeat и перезапускают relay, если он упал.
- `bin/tg-*` — команды, которыми Grok отвечает: `tg-send`, `tg-edit`, `tg-status`, `tg-typing`, `tg-send-file`, `tg-delete`, `tg-notify` (в личку). Защита от дублей: одинаковый текст в тот же чат за 15 минут не уходит повторно.
- `relay/topics.json` — какой топик группы к какому боту относится (пример в `topics.example.json`).

## Установка (дай эту ссылку своему Grok Bot и скажи «сделай себе так же»)

1. Создай бота у [@BotFather](https://t.me/BotFather), возьми токен. Свой user id узнай у [@userinfobot](https://t.me/userinfobot).
2. (По желанию) создай группу, включи **Темы**, добавь бота админом с правом управлять темами и удалять сообщения. В BotFather выключи у бота Group Privacy.
3. Попроси Grok создать рутину с **webhook**-триггером, промпт — из [`docs/routine-prompt.md`](docs/routine-prompt.md). Webhook URL и ключ берутся из панели рутины.
4. На боксе:
   ```bash
   git clone https://github.com/clsasa1/grokbot-telegram-bridge && cd grokbot-telegram-bridge
   mkdir -p /home/box/tgrelay && cp config.env.example /home/box/tgrelay/config.env   # заполнить!
   ./install.sh            # SKIP_WHISPER=1 ./install.sh — без расшифровки голосовых
   ```
5. Скопируй `relay/topics.example.json` в `/home/box/tgrelay/topics.json` и пропиши свои топики и id ботов.
6. Добавь правила из [`docs/memory-rules.md`](docs/memory-rules.md) в память бота — главное, чтобы он после рестарта бокса сам поднимал relay.
7. Напиши боту в Telegram «привет» — должен появиться 👀 и прийти ответ.

## Проверка и починка

```bash
pgrep -af "relay.py|watchdog-loop"     # живы?
tail /home/box/tgrelay/relay.out       # лог (токен там замазан)
setsid nohup /home/box/tgrelay/watchdog-loop.sh >/dev/null 2>&1 &   # поднять
```

## Безопасность

Токен бота и ключ вебхука храни только в `config.env` / переменных окружения — в репу их не клади (`.gitignore` уже настроен). Relay игнорирует всех, кроме `TG_USER_ID`.
