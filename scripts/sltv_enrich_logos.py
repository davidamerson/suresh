#!/usr/bin/env python3
"""Annotate the 138 channel entries with exact, public, currently-in-use logos.
No fuzzy matches, and local Sri Lankan entries MUST use a Sri Lankan logo.
Third-party trademark logos identify channels; no stream access is changed.
"""
from pathlib import Path
from collections import defaultdict
import urllib.request, json, re

m3u=Path("SriLankaTV/app/src/main/assets/verified_channels.m3u")
content=m3u.read_text(encoding="utf-8")
def norm(s):
    s=s.casefold().replace("\u200e","").replace("\u200f","")
    s=re.sub(r"[\u00b2\u00b3]","",s)
    s=re.sub(r"\b(hd|sd|ultra|fullhd|fhd|4k|live)\b"," ",s)
    return re.sub("[^a-z0-9]+","",s)
aliases={
 "hiru": "HiruTV.lk",
 "dearana": "TVDerana.lk",
 "derana": "TVDerana.lk",
 "rupawahini": "Rupavahini.lk",
 "itn": "ITN.lk",
 "shakthi": "ShakthiTV.lk",
 "siyatha": "SiyathaTV.lk",
 "sirasa": "SirasaTV.lk",
 "swarnawahini": "Swarnavahini.lk",
 "vasanthem": "VasanthamTV.lk",
 "vasantham": "VasanthamTV.lk",
 "nethra": "NethraTV.lk",
}
def api(url):
    req=urllib.request.Request(url,headers={"User-Agent":"SLTV-Logo-Editor/1.0"})
    with urllib.request.urlopen(req,timeout=95) as response:
        return json.loads(response.read(18_000_000))
channels=api("https://iptv-org.github.io/api/channels.json")
logos=api("https://iptv-org.github.io/api/logos.json")
meta={x["id"]:x for x in channels}
byname=defaultdict(set)
for x in channels:
    for n in [x.get("name","")]+x.get("alt_names",[]):
        if norm(n):byname[norm(n)].add(x["id"])
byid=defaultdict(list)
for x in logos:
    if x.get("in_use") is True and x.get("feed") is None and str(x.get("format","")).upper() in ("PNG","JPEG","WEBP") and str(x.get("url","")).startswith("https://"):
        byid[x["channel"]].append(x)

lines=content.splitlines()
matches=[]
match_count=0
for i,line in enumerate(lines):
    if not line.startswith("#EXTINF:"):continue
    name=line.rsplit(",",1)[-1].strip()
    n=norm(name)
    category=re.search(r'group-title="([^"]*)"',line)
    category=category.group(1) if category else ""
    local=category.startswith("SL Channels") or category.startswith("🇱🇰")
    match=set()
    if n in aliases and aliases[n] in meta:
        match={aliases[n]}
    else:
        match=byname.get(n,set()).copy()
        if local:match={c for c in match if meta[c].get("country")=="LK"}
    logo=""
    matched_id=None
    if len(match)==1:
        matched_id=next(iter(match))
        eligible=byid.get(matched_id,[])
        if local and meta[matched_id].get("country")!="LK":eligible=[]
        if eligible:
            best=sorted(eligible,key=lambda z:("horizontal" not in (z.get("tags") or []),-min(z.get("width",0) or 0,1000)))[0]
            logo=best["url"].replace('"',"%22")
    if logo:
        match_count+=1
        line=re.sub(r'\s+tvg-logo="[^"]*"',"",line)
        lines[i]=line.replace("#EXTINF:","#EXTINF:-1 tvg-logo=\""+logo+"\" ",1) if not line.startswith("#EXTINF:-1") else line.replace("#EXTINF:-1","#EXTINF:-1 tvg-logo=\""+logo+"\"",1)
        # Retain rest of existing metadata. Never change stream address.
    matches.append({"name":name,"channel_id":matched_id,"logo":logo,"match_status":"matched" if logo else "unmatched"})
m3u.write_text("\n".join(lines)+"\n",encoding="utf8")
Path("sltv_logo_report.json").write_text(json.dumps(matches,indent=2,ensure_ascii=False))
print("LOGO_ENRICHED",match_count,"TOTAL",len(matches),flush=True)
assert len(matches)>=130
assert match_count>=65, "Unexpectedly low logo match count"
