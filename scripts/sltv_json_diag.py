#!/usr/bin/env python3
import urllib.request,urllib.error,json,re
samples=[
    ("Hiru HD","https://sltv-app.thundercat.workers.dev/hirutv"),
    ("Derana HD","https://sltv-app.thundercat.workers.dev/tvderana"),
    ("Sirasa HD","https://sltv-app.thundercat.workers.dev/sirasatv"),
    ("Rupavahini HD","https://sltv-app.thundercat.workers.dev/rupavahini")]
def describe(x):
    if isinstance(x,dict):return {"type":"object","keys":list(x)[:30],"fields":{k:describe(v) for k,v in list(x.items())[:20]}}
    if isinstance(x,list):return {"type":"array","count":len(x),"first":describe(x[0]) if x else None}
    if isinstance(x,str):
        if x.startswith(("http://","https://")):
            return {"type":"url","extension":("m3u8" if ".m3u8" in x else ("mpd" if ".mpd" in x else "other"))}
        return {"type":"string","len":len(x),"status_hint":bool(re.search(r"unauthor|forbidden|subscription|paid|blocked|login|token|expired|error|denied",x,re.I))}
    return {"type":type(x).__name__}
for name,url in samples:
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"SLTV-Compatibility-Reader/1.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=15) as r:
            payload=r.read(20000)
            print("CHANNEL",name,"STATUS",r.status,"TYPE",r.headers.get("content-type"),"BODY_BYTES",len(payload))
        try:
            parsed=json.loads(payload)
            print("JSON_SCHEMA",name,json.dumps(describe(parsed),ensure_ascii=False))
        except Exception as e:
            print("NOT_JSON",name,type(e).__name__)
    except urllib.error.HTTPError as e:
        print("HTTP_ERROR",name,e.code)
    except Exception as e:
        print("ERROR",name,type(e).__name__)
