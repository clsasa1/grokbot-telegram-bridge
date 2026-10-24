# Telegram relay for your bot: long-polls getUpdates, forwards the owner's messages (DM TG_USER_ID / group TG_GROUP_ID)
# to the routine webhook as JSON {from, chat_id, thread_id, topic, text, date, message_id, media, transcript?, reply_to?, callback?}.
# On receipt: sets 👀 reaction + typing. Voice/audio/video_note -> local faster-whisper transcript (timeout, in background thread),
# text prefixed '[голосовое] '. Replies -> reply_to {message_id,text<=500,from_bot}, text prefixed '[ответ на: "..."] '.
# Inline-button presses (callback_query) -> answered, keyboard removed, forwarded as text '[кнопка] <label>'.
# Kept alive by watchdog.sh (heartbeat file). Never logs the token.
import os, json, time, traceback, urllib.request, urllib.parse, subprocess, threading
# Optional: values from /home/box/tgrelay/config.env (KEY=VALUE lines) if not already in the environment
try:
    for _l in open("/home/box/tgrelay/config.env"):
        if "=" in _l and not _l.lstrip().startswith("#"):
            _k,_v=_l.strip().split("=",1); os.environ.setdefault(_k,_v.strip().strip('"'))
except FileNotFoundError: pass
TOK=os.environ["TELEGRAM_BOT_TOKEN"]; KEY=os.environ["TG_ROUTINE_WEBHOOK_KEY"]
HOOK=os.environ["TG_ROUTINE_WEBHOOK_URL"]  # Webhook URL из панели рутины
D="/home/box/tgrelay"; OFF=D+"/offset"; FAIL=D+"/failed.jsonl"; HB=D+"/heartbeat"; OUT=D+"/relay.out"
MEDIA="/home/box/tgrelay/media"; os.makedirs(MEDIA,exist_ok=True)
API="https://api.telegram.org/bot"+TOK; USER=int(os.environ["TG_USER_ID"]); CHATS=(USER,int(os.environ["TG_GROUP_ID"]))
TRANSCRIBE_TIMEOUT=180
def log(msg):
    msg=str(msg).replace(TOK,"<TOKEN>")
    with open(OUT,"a") as f: f.write(time.strftime("%Y-%m-%d %H:%M:%S ")+msg+"\n")
def tgget(path,timeout):
    with urllib.request.urlopen(API+path,timeout=timeout) as r: return json.load(r)
def tgpost(method,params,timeout=10):
    try:
        data=json.dumps(params).encode()
        r=urllib.request.Request(API+"/"+method,data=data,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(r,timeout=timeout) as resp: return json.load(resp)
    except Exception as e: log(f"{method} error: {e!r}"); return None
def media_of(m):
    fid=None; ext="bin"
    if m.get("photo"): fid=m["photo"][-1]["file_id"]; ext="jpg"
    elif m.get("document"): fid=m["document"]["file_id"]; ext=(m["document"].get("file_name") or "f.bin").rsplit(".",1)[-1]
    elif m.get("voice"): fid=m["voice"]["file_id"]; ext="ogg"
    elif m.get("audio"): fid=m["audio"]["file_id"]; ext=(m["audio"].get("file_name") or "a.mp3").rsplit(".",1)[-1]
    elif m.get("video_note"): fid=m["video_note"]["file_id"]; ext="mp4"
    elif m.get("video"): fid=m["video"]["file_id"]; ext="mp4"
    elif m.get("sticker"): fid=m["sticker"]["file_id"]; ext="webp"
    if not fid: return None
    try:
        fp=tgget("/getFile?file_id="+fid,30)["result"]["file_path"]
        dst=f"{MEDIA}/{m['message_id']}.{ext}"
        with urllib.request.urlopen(f"https://api.telegram.org/file/bot{TOK}/{fp}",timeout=60) as r: data=r.read()
        open(dst,"wb").write(data); return dst
    except Exception as e:
        log("media error: "+repr(e)); return ("download failed: "+str(e)[:200]).replace(TOK,"<TOKEN>")
def transcribe(path):
    try:
        p=subprocess.run([D+"/venv/bin/python",D+"/transcribe.py",path],capture_output=True,text=True,timeout=TRANSCRIBE_TIMEOUT)
        if p.returncode==0 and p.stdout.strip(): return p.stdout.strip()
        log("transcribe failed rc=%s %s"%(p.returncode,p.stderr[-300:]))
    except Exception as e: log("transcribe error: "+repr(e))
    return None
def post_hook(b,uid):
    body=json.dumps(b,ensure_ascii=False).encode()
    for i in range(3):
        try:
            r=urllib.request.Request(HOOK,data=body,method="POST",headers={"Content-Type":"application/json","Authorization":"Bearer "+KEY,"X-Automation-Key":KEY})
            with urllib.request.urlopen(r,timeout=20) as resp: log(f"forwarded update {uid} -> {resp.status}")
            return
        except Exception as e:
            log(f"webhook error (try {i+1}): {e!r}"); time.sleep(2*(i+1))
    open(FAIL,"a").write(body.decode()+"\n")
def topic_of(th):
    try: return json.load(open(D+"/topics.json")).get(str(th)) if th else None
    except Exception: return None
def ack(cid,th,mid):
    tgpost("setMessageReaction",{"chat_id":cid,"message_id":mid,"reaction":[{"type":"emoji","emoji":"👀"}]})
    p={"chat_id":cid,"action":"typing"}
    if th: p["message_thread_id"]=th
    tgpost("sendChatAction",p)
def reply_info(m):
    r=m.get("reply_to_message")
    if not r: return None
    # in forum topics every message "replies" to the topic-creation service message; ignore that
    if r.get("forum_topic_created") or (m.get("is_topic_message") and r.get("message_id")==m.get("message_thread_id")): return None
    t=(r.get("text") or r.get("caption") or "")[:500]
    return {"message_id":r.get("message_id"),"text":t,"from_bot":bool((r.get("from") or {}).get("is_bot"))}
def handle_message(m,uid):
    cid=m["chat"]["id"]
    th=m.get("message_thread_id") if m.get("is_topic_message") else None
    media=media_of(m)
    text=m.get("text") or m.get("caption") or ""
    if not text and not media: return
    b={"from":"telegram","chat_id":cid,"thread_id":th,"topic":topic_of(th),"text":text,"media":media,"message_id":m.get("message_id"),"date":m.get("date")}
    ri=reply_info(m)
    if ri:
        b["reply_to"]=ri; short=ri["text"][:100].replace("\n"," ")
        b["text"]=f'[ответ на: "{short}"] '+b["text"]
    isvoice=any(m.get(k) for k in ("voice","audio","video_note"))
    def finish():
        if isvoice and media and not str(media).startswith("download failed"):
            t=transcribe(media)
            if t: b["transcript"]=t; b["text"]=("[голосовое] "+t+("\n"+b["text"] if b["text"] else "")).strip()
        post_hook(b,uid)
    if isvoice: threading.Thread(target=finish,daemon=True).start()
    else: finish()
def handle_callback(q,uid):
    if (q.get("from") or {}).get("id")!=USER: return
    tgpost("answerCallbackQuery",{"callback_query_id":q["id"]})
    m=q.get("message") or {}; cid=(m.get("chat") or {}).get("id")
    if cid not in CHATS: return
    label=q.get("data") or ""
    tgpost("editMessageReplyMarkup",{"chat_id":cid,"message_id":m.get("message_id"),"reply_markup":{"inline_keyboard":[]}})
    th=m.get("message_thread_id") if m.get("is_topic_message") else None
    p={"chat_id":cid,"action":"typing"}
    if th: p["message_thread_id"]=th
    tgpost("sendChatAction",p)
    b={"from":"telegram","chat_id":cid,"thread_id":th,"topic":topic_of(th),"text":"[кнопка] "+label,"media":None,
       "message_id":m.get("message_id"),"date":int(time.time()),"callback":label,
       "reply_to":{"message_id":m.get("message_id"),"text":(m.get("text") or m.get("caption") or "")[:500],"from_bot":True}}
    post_hook(b,uid)
off=int(open(OFF).read()) if os.path.exists(OFF) else 0
log("relay start, offset=%d"%off); backoff=1
AU=urllib.parse.quote(json.dumps(["message","callback_query","my_chat_member"]))
while True:
    open(HB,"w").write(str(int(time.time())))
    try:
        ups=tgget(f"/getUpdates?timeout=30&offset={off}&allowed_updates={AU}",40).get("result",[])
        backoff=1
        for u in ups:
            off=u["update_id"]+1; open(OFF,"w").write(str(off))
            try:
                if u.get("callback_query"): handle_callback(u["callback_query"],u["update_id"]); continue
                m=u.get("message") or {}
                c=(m.get("chat") or (u.get("my_chat_member") or {}).get("chat") or {})
                if c and c.get("id")!=USER: open(D+"/chats.jsonl","a").write(json.dumps({"chat":c,"thread":m.get("message_thread_id"),"text":m.get("text") or m.get("caption")},ensure_ascii=False)+"\n")
                cid=m.get("chat",{}).get("id")
                if (m.get("from") or {}).get("id")!=USER or cid not in CHATS: continue
                ack(cid,m.get("message_thread_id") if m.get("is_topic_message") else None,m["message_id"])
                handle_message(m,u["update_id"])
            except Exception:
                log("update error: "+traceback.format_exc())
    except Exception as e:
        log(f"poll error: {e!r}; retry in {backoff}s"); time.sleep(backoff); backoff=min(backoff*2,60)
