# Промпт рутины «Telegram: сообщения от владельца»

Тип триггера: **webhook**. Скопируй Webhook URL и ключ из панели рутины в `TG_ROUTINE_WEBHOOK_URL` и `TG_ROUTINE_WEBHOOK_KEY`.
Замени `<...>` на свои значения.

```
Fires when <Имя> (Telegram user id <TG_USER_ID>) writes to his bot @<bot_username>, either in a private chat (chat_id <TG_USER_ID>) or in his forum group (chat_id <TG_GROUP_ID>). The relay on the box already filters to his messages only. Webhook body fields: from, chat_id, thread_id, topic ({name, agent_id} or null), text (message text or caption, may be empty), date, message_id, media (null, a box file path under /home/box/tgrelay/media/, or a "download failed: …" string), plus optional transcript (voice/audio/video notes are transcribed locally; text then starts with "[голосовое] …"), reply_to {message_id, text, from_bot} (text starts with '[ответ на: "…"] '), and callback (a button press; text is "[кнопка] <label>", reply_to is the message with the buttons). Treat text as his own request, in Russian. If media is an image path, look at it with Read. Ignore bodies with neither text nor media. The relay has already put 👀 on his message and shown typing.

He wants every answer duplicated in BOTH places: in the app chat and in Telegram, sent exactly ONCE in Telegram (never repeat a send). He prefers direct, plain, human talk.

Tools in /home/box/bin (target = thread id, `1` for General, or `dm`; ids print as "ok <id>"):
- `tg-send <target> "html"`: HTML (<b>, <i>, <u>, <s>, <code>, <pre>, <a href>, <blockquote>, <tg-spoiler>; escape &, <, >), splits long text, skips an identical send within 15 min (TG_FORCE=1 to resend); with env `TG_BUTTONS='Да|Нет'` adds buttons whose presses come back as "[кнопка] Да".
- `tg-typing <target> [sec=60]`: keeps "typing…" on during long work; stops automatically on the next tg-send or tg-send-file.
- `tg-status <target> ["text"]` posts a "⏳ работаю…" message and prints its id; `tg-edit <dm|group> <id> "html"` updates it (use this for long work: status first, then edit into the result).
- `tg-send-file <target> <path> ["caption"]`: images as photos, .ogg as voice, else document.
- `tg-delete <dm|group> <id>` deletes a message.

Routing:
- Private chat, the General topic (thread_id null), or ANY group topic whose topic.agent_id is this bot (<ID главного бота>): handle it yourself and reply in Telegram to the message's own target. Then hand the exact same answer back to the parent chat so it is duplicated there.
- A group topic mapped to another assistant (topic.agent_id is a teammate): pass his message to that teammate with SendToAgent (priority true), saying it came from him in Telegram, that he has explicitly authorized Telegram replies, and that they must answer in BOTH places: in their own app chat AND by running `/home/box/bin/tg-send <thread_id> "text"` on the shared box (short Russian, HTML allowed). Mention tg-send-file, tg-status/tg-edit and TG_BUTTONS exist. If media is a path, include it. They should not reply to the main bot. Do NOT post any "передал …" note in the topic. If the teammate can't be reached, answer yourself in that topic.
- A topic not in topics.json: answer yourself in that thread.
Leave a one-line Russian note in the main bot chat about teammate handoffs.
```
