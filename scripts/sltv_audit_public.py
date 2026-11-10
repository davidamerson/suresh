#!/usr/bin/env python3
"""Public-only SLTV endpoint diagnostics and public channel logo matching.
No login credentials, DRM keys, cookies, signed tokens, or authentication bypass.
"""
import json, os, re, sys, zipfile, urllib.request, urllib.error, urllib.parse, hashlib
from pathlib import Path

out = Path("sltv_audit")
out.mkdir(exist_ok=True)
BASE = Path("SriLankaTV/app/src/main/assets/verified_channels.m3u")

def parse_m3u(data):
    pairs=[]
    title=""
    group=""
    for line in data.splitlines():
        s=line.strip()
        if s.startswith("#EXTINF:"):
            title=s.rsplit(",",1)[-1].strip()
            group=re.search(r'group-title="([^"]*)"',s)
            group=group.group(1) if group else ""
        elif s.startswith(("http://","https://")):
            pairs.append({"name":title,"category":group,"url":s})
    return pairs

channels=parse_m3u(BASE.read_text(encoding="utf8"))
print("SOURCE_CHANNELS",len(channels),flush=True)

def safe_url(url):
    p=urllib.parse.urlsplit(url)
    return p.scheme+"://"+p.netloc+p.path

def sniff(content):
    s=content.lstrip()
    if s.startswith(b"#EXTM3U"):return "hls_manifest"
    if s.startswith(b"<?xml") and b"<MPD" in s:return "dash_manifest"
    if s.startswith(b"<MPD"):return "dash_manifest"
    if s.startswith((b"<!DOCTYPE html",b"<html",b"<HTML")):return "html_error_or_player"
    if s.startswith((b"{",b"[")):return "json_response"
    if not s:return "empty_body"
    return "other"

probes=[]
wanted=[("normal","Hiru"),("normal","Siyatha TV"),("normal","Rupavahini"),
        ("hd","Hiru HD"),("hd","Dearana HD"),("hd","Sirasa HD"),
        ("hd","ITN HD"),("hd","Rupawahini HD"),("hd","Siyatha HD"),
        ("hd","Swarnawahini HD"),("hd","Sirasa TV²"),("hd","Rupavahini²")]
for kind,name in wanted:
    matched=next((c for c in channels if c["name"].lower()==name.lower()),None)
    if not matched:
        print("SKIP_NAME_NOT_FOUND",name,flush=True)
        continue
    url=matched["url"]
    req=urllib.request.Request(url,headers={
        "User-Agent":"SLTV-Open-Compatibility-Diagnostic/1.0",
        "Range":"bytes=0-2047","Accept":"application/vnd.apple.mpegurl,application/dash+xml,*/*"
    })
    record={"type":kind,"channel":matched["name"],"url":safe_url(url)}
    try:
        with urllib.request.urlopen(req,timeout=12) as res:
            content=res.read(1024)
            record.update({"status":res.status,"content_type":res.headers.get("Content-Type",""),
             "body_kind":sniff(content),"final_url":safe_url(res.url),
             "redirected":safe_url(res.url)!=safe_url(url)})
    except urllib.error.HTTPError as e:
        record.update({"status":e.code,"content_type":e.headers.get("Content-Type",""),
            "body_kind":"http_error"})
    except Exception as e:
        record.update({"status":None,"error":type(e).__name__})
    probes.append(record)
    print("STREAM_PROBE",json.dumps(record,ensure_ascii=False),flush=True)
(out/"endpoint_report.json").write_text(json.dumps(probes,indent=2,ensure_ascii=False))

# Retrieve public metadata from iptv-org. Require exact normalized name; ambiguous names excluded.
def norm(s):
    s=s.casefold().replace("\u200e","").replace("\u200f","")
    s=re.sub(r"[\u00b2\u00b3]","",s)
    s=re.sub(r"\b(hd|sd|ultra|fullhd|fhd|4k|live)\b"," ",s)
    s=re.sub(r"[^a-z0-9]+","",s)
    return s
aliases={
  "hiru":"Hiru TV","dearana":"TV Derana","derana":"TV Derana",
  "rupawahini":"Rupavahini","itn":"ITN","shakthi":"Shakthi TV",
  "siyatha":"Siyatha TV","sirasa":"Sirasa TV",
  "supreem":"Supreme TV","swarnawahini":"Swarnavahini",
  "vasanthem":"Vasantham TV","vasantham":"Vasantham TV",
  "nethra":"Nethra TV",
}
def canonical(s):
    n=norm(s)
    if n in aliases:return norm(aliases[n])
    return n

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"SLTV-Public-Logo-Matcher/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r:
        content=r.read(18_000_000)
    return json.loads(content)

try:
    meta=get_json("https://iptv-org.github.io/api/channels.json")
    logos=get_json("https://iptv-org.github.io/api/logos.json")
    ids={}
    for c in meta:
        for name in [c.get("name","")]+c.get("alt_names",[]):
            key=norm(name)
            if key:ids.setdefault(key,set()).add(c["id"])
    good={}
    for i in logos:
        if i.get("in_use") is not True or i.get("feed") is not None:
            continue
        if (i.get("format") or "").upper() not in {"PNG","JPEG","WEBP"}:continue
        link=i.get("url") or ""
        if not link.startswith("https://"):continue
        good.setdefault(i.get("channel"),[]).append(i)
    results=[]
    for c in channels:
        n=canonical(c["name"])
        matches=ids.get(n,set())
        matched_logos=[]
        if len(matches)==1:
            channel_id=next(iter(matches))
            matched_logos=good.get(channel_id,[])
        # Names such as "ITN" and "TV1" can be globally ambiguous;
        # only choose a unique name / channel id, never guessed fuzzy matches.
        chosen=None
        if matched_logos:
            chosen=sorted(matched_logos,key=lambda z:(
                'horizontal' not in (z.get('tags') or []),
                -min(z.get("width",0),1000)))[0]
        results.append({"name":c["name"],"category":c["category"],"channel_id":next(iter(matches)) if len(matches)==1 else None,
         "logo":chosen.get("url") if chosen else None,
         "match_status":"unique_exact" if chosen else ("ambiguous" if len(matches)>1 else "no_logo")})
    (out/"logo_candidates.json").write_text(json.dumps(results,indent=2,ensure_ascii=False))
    print("LOGO_MATCH_SUMMARY",json.dumps({
     "total":len(results),"matched":sum(bool(x["logo"]) for x in results),
     "ambiguous":sum(x["match_status"]=="ambiguous" for x in results)},ensure_ascii=False),flush=True)
    for x in results:
        if x["category"].startswith(("SL Channels","🇱🇰")) or x["name"] in ("Hiru","Siyatha TV"):
            print("LOGO_LOCAL",x["name"],x["match_status"],x["channel_id"] or "",flush=True)
except Exception as e:
    print("LOGO_DATA_ERROR",type(e).__name__,str(e)[:200],flush=True)

# Check resources packaged inside publicly distributed original APK. Do NOT
# access its private Firebase database, cookies, logins, or cached credentials.
apk_url="https://github.com/nxt-owner/SLTV-APP/releases/download/V1.4.8/V1.4.8.apk"
try:
    req=urllib.request.Request(apk_url,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=100) as r,open(out/"sltv_original.apk","wb") as w:
        while True:
            b=r.read(1<<20)
            if not b:break
            w.write(b)
    with zipfile.ZipFile(out/"sltv_original.apk") as z:
        names=z.namelist()
        imgs=[x for x in names if x.lower().endswith((".png",".jpg",".jpeg",".webp"))]
        related=[x for x in imgs if "channel" in x.lower() or "logo" in x.lower() or "icon" in x.lower()]
        with (out/"apk_image_inventory.txt").open("w") as f:
            f.write("Total image assets: %d\nLikely channel/logo assets: %d\n"%(len(imgs),len(related)))
            f.write("\n".join(related[:400]))
        print("ORIGINAL_APK_ASSETS",json.dumps({"all_images":len(imgs),"channel_logo_candidates":len(related),"sample":related[:25]}),flush=True)
    (out/"sltv_original.apk").unlink()
except Exception as e:
    print("ORIGINAL_APK_ERROR",type(e).__name__,str(e)[:180],flush=True)
