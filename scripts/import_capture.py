#!/usr/bin/env python3
"""Import research observations from the redacted SLTV Android test artifact.
No credentials, cookies, or DRM material are used or saved.
"""
from pathlib import Path
import json,re,sys
src=Path(sys.argv[1] if len(sys.argv)>1 else "/tmp/sltv_artifact/cached_channel_paths_redacted.json")
rows=json.loads(src.read_text(encoding="utf8"))
dest=[]
for i,item in enumerate(rows):
    name=re.sub(r"[\u200b-\u200f\ufeff]","",str(item.get("name",""))).strip()
    if not name:continue
    stream=item.get("streamUrl") or {}
    host=stream.get("host","")
    path=stream.get("path","")
    scheme=stream.get("scheme","https")
    url=""
    if not host or not path or "<id>" in path:
        access="unresolved"
    else:
        url=f"{scheme}://{host}{':1936' if host=='tv.hiruhost.com' else ''}{path}"
        if host.endswith(".workers.dev"):
            access="sltv_backend"
        elif host.endswith(".peotv.lk"):
            access="provider_restricted"
        elif re.search(r"HBO|Nat Geo|Cartoon Network|Animal Planet|Sony|Zee|Star Sports|Discovery|Colors HD|ESPN|beIN",name,re.I):
            access="provider_restricted"
        else:
            access="public_candidate"
    dest.append({"id":f"ch{i+1:03d}","name":name,
        "category":item.get("category","Other"),"url":url,"access":access})
payload={"schemaVersion":1,"observedFrom":"SLTV V1.4.8 Android cache capture 2026-11-09",
    "caution":"Stream entries are observation only, not proof of redistributable access, compatible DRM, or uninterrupted playback. No third-party authentication is copied.",
    "channels":dest}
for fname in ("catalog/channels.json","common/src/main/assets/channels.json"):
    target=Path(fname)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
modes={m:sum(c["access"]==m for c in dest) for m in set(c["access"] for c in dest)}
print("Imported",len(dest),"channel names,",len(set(c["category"] for c in dest)),"categories; access:",modes)
if len(dest)<170:raise RuntimeError("Expected the complete 174-record researched catalogue.")
