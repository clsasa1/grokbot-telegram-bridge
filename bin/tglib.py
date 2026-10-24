# Shared helper for tg-* scripts (Telegram bot your bot). Token from env TELEGRAM_BOT_TOKEN; never printed.
import os, sys, json, signal, urllib.request, urllib.parse, uuid, mimetypes
# Optional: values from /home/box/tgrelay/config.env (KEY=VALUE lines) if not already in the environment
try:
    for _l in open("/home/box/tgrelay/config.env"):
        if "=" in _l and not _l.lstrip().startswith("#"):
            _k,_v=_l.strip().split("=",1); os.environ.setdefault(_k,_v.strip().strip('"'))
except FileNotFoundError: pass
TOK=os.environ["TELEGRAM_BOT_TOKEN"]; API="https://api.telegram.org/bot"+TOK
DM=int(os.environ["TG_USER_ID"]); GROUP=int(os.environ["TG_GROUP_ID"]); PIDDIR="/home/box/tgrelay/typing"
def target(t):
    if t=="dm": return {"chat_id":DM}
    return {"chat_id":GROUP,"message_thread_id":int(t)}
def chat(c): return DM if c=="dm" else GROUP
def call(method,params):
    data=urllib.parse.urlencode({k:(json.dumps(v) if isinstance(v,(dict,list)) else v) for k,v in params.items()}).encode()
    try:
        with urllib.request.urlopen(API+"/"+method,data=data,timeout=30) as r: return json.load(r)
    except urllib.error.HTTPError as e: return json.load(e)
    except Exception as e: return {"ok":False,"description":str(e).replace(TOK,"<TOKEN>")}
def call_html(method,params):
    r=call(method,dict(params,parse_mode="HTML"))
    if not r.get("ok") and "parse entities" in r.get("description",""): r=call(method,params)
    return r
def upload(method,params,field,path):
    b=uuid.uuid4().hex; body=b""
    for k,v in params.items():
        v=json.dumps(v) if isinstance(v,(dict,list)) else str(v)
        body+=f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    ct=mimetypes.guess_type(path)[0] or "application/octet-stream"
    body+=f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{os.path.basename(path)}"\r\nContent-Type: {ct}\r\n\r\n'.encode()+open(path,"rb").read()+f"\r\n--{b}--\r\n".encode()
    req=urllib.request.Request(API+"/"+method,data=body,headers={"Content-Type":"multipart/form-data; boundary="+b})
    try:
        with urllib.request.urlopen(req,timeout=120) as r: return json.load(r)
    except urllib.error.HTTPError as e: return json.load(e)
    except Exception as e: return {"ok":False,"description":str(e).replace(TOK,"<TOKEN>")}
def stop_typing(t):
    pf=f"{PIDDIR}/{t}.pid"
    try: os.kill(int(open(pf).read()),signal.SIGTERM)
    except Exception: pass
    try: os.remove(pf)
    except Exception: pass
def split(text,limit=4000):
    parts=[]
    while len(text)>limit:
        cut=text.rfind("\n\n",0,limit)
        if cut<limit//2: cut=text.rfind("\n",0,limit)
        if cut<limit//2: cut=text.rfind(" ",0,limit)
        if cut<=0: cut=limit
        parts.append(text[:cut].rstrip()); text=text[cut:].lstrip("\n")
    parts.append(text); return [p for p in parts if p.strip()]
def res(r):
    print("ok "+str(r["result"]["message_id"]) if r.get("ok") else "fail "+r.get("description",""))
    sys.exit(0 if r.get("ok") else 1)
