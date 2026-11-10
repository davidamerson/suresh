#!/usr/bin/env python3
"""Bundle a channel-specific icon for every packaged TV channel.
Strict logo associations come from tvg-logo metadata already reviewed.
If a URL fails, generate a clearly generic labelled placeholder, not a false logo.
No stream URL is altered and no proprietary SLTV resources are accessed.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
import hashlib, json, re, urllib.request, urllib.error

SOURCE=Path("SriLankaTV/app/src/main/assets/verified_channels.m3u")
ASSETS=Path("SriLankaTV/app/src/main/assets/logos")
ASSETS.mkdir(parents=True,exist_ok=True)
SIZE=(192,108)
FONT_PATH="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def font(size):
    try:return ImageFont.truetype(FONT_PATH,size=size)
    except OSError:return ImageFont.load_default()

def parse():
    records=[]
    name=logo=group=""
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if line.startswith("#EXTINF:"):
            name=line.rsplit(",",1)[-1].strip()
            m=re.search(r'tvg-logo="([^"]+)"',line)
            logo=m.group(1) if m else ""
            m=re.search(r'group-title="([^"]+)"',line)
            group=m.group(1) if m else ""
        elif line.startswith(("https://","http://")):
            records.append({"name":name,"url":line,"logo":logo,"group":group})
    return records

def asset_name(c):
    return hashlib.sha256((c["name"]+"\0"+c["url"]).encode("utf-8")).hexdigest()[:24]+".png"

def placeholder(c):
    # A channel-specific typographic tile, never a falsely attributed logo.
    accent={"Local":(18,199,180),"Sports":(58,164,241),
            "Kids":(231,179,79),"Movies":(176,128,229),
            "Entertainment":(244,150,111),"Nature":(89,191,134)}
    color=accent.get(c.get("group"),(65,183,214))
    out=Image.new("RGBA",SIZE,(19,35,52,255))
    d=ImageDraw.Draw(out)
    d.rounded_rectangle((5,5,187,103),radius=15,outline=color+(255,),width=3)
    d.rounded_rectangle((9,9,183,16),radius=3,fill=color+(255,))
    name=c["name"]
    size=23 if len(name)<11 else (18 if len(name)<16 else 15)
    words=name.split()
    if len(words)>1 and len(name)>15:
        midpoint=(len(words)+1)//2
        wrapped=[" ".join(words[:midpoint])," ".join(words[midpoint:])]
    else: wrapped=[name]
    y=57 if len(wrapped)==1 else 43
    for line in wrapped:
        d.text((96,y),line,font=font(size),anchor="mm",fill=(242,248,255,255))
        y+=25
    return out

def get_logo(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (SLTV channel-icon bundle; public image)","Accept":"image/png,image/jpeg,image/webp,image/*"})
    with urllib.request.urlopen(req,timeout=12) as r:
        if r.status!=200:raise ValueError("HTTP "+str(r.status))
        ct=(r.headers.get("Content-Type") or "").lower()
        if "image/" not in ct and not any(k in url.lower() for k in (".png",".jpg",".jpeg",".webp")):
            raise ValueError("not_image")
        raw=r.read(1_200_001)
        if len(raw)>1_200_000:raise ValueError("image_too_large")
    img=Image.open(BytesIO(raw))
    img.load()
    if img.width>6000 or img.height>6000:raise ValueError("image_dimensions")
    return img.convert("RGBA")

def make_icon(c):
    out=placeholder(c)
    status="placeholder"
    # The source logo for Sirasa TV in the reference database currently
    # returns an HTTP error. Wikimedia Commons hosts the identical
    # Sri Lankan broadcaster logo; do not substitute a foreign Sirasa.
    alternatives=[]
    if c["logo"]:
        alternatives.append(c["logo"])
    if c["name"] in ("Sirasa TV","Sirasa HD","Sirasa TV²"):
        alternatives.append("https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Sirasa_TV_Logo.png/500px-Sirasa_TV_Logo.png")
    for candidate in alternatives:
        try:
            original=get_logo(candidate)
            # Logos are shown on a light, deliberately neutral mat so both
            # black and white broadcaster marks can remain legible.
            out=Image.new("RGBA",SIZE,(237,241,249,255))
            d=ImageDraw.Draw(out)
            d.rounded_rectangle((2,2,190,106),radius=17,outline=(173,183,203,255),width=2)
            fitted=ImageOps.contain(original,(174,92),method=Image.Resampling.LANCZOS)
            x=(SIZE[0]-fitted.width)//2
            y=(SIZE[1]-fitted.height)//2
            out.alpha_composite(fitted,(x,y))
            status="logo"
            break
        except Exception as exc:
            status="logo_download_failed_"+type(exc).__name__
    return (c, out.convert("RGB"),status)

def main():
    channels=parse()
    assert len(channels)==22, "Expected exactly the 22 chosen channels"
    result=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures=[pool.submit(make_icon,c) for c in channels]
        for future in as_completed(futures):
            channel,im,status=future.result()
            filename=asset_name(channel)
            im.save(ASSETS/filename,format="PNG",optimize=True)
            result.append({"name":channel["name"],"key":filename,"status":status,"matched_public_url":bool(channel["logo"])})
    result.sort(key=lambda x:x["name"].casefold())
    Path("logo_bundle_report.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf8")
    counts={}
    for x in result:counts[x["status"]]=counts.get(x["status"],0)+1
    print("PACKAGED_LOGO_ICONS",len(result),"STATUS",json.dumps(counts,sort_keys=True),flush=True)
    for name in ("Rupawahini","ITN","Sirasa TV","Derana","Hiru","Shakthi","10 Cricket","Papare SD","Sony1","BBC Earth","Mr Bean"):
        match=next((z for z in result if z["name"]==name),None)
        if match:print("KEY_CHANNEL_ICON",name,match["status"],flush=True)
    assert len(list(ASSETS.glob("*.png")))>=len(result)
    assert counts.get("logo",0)>=10, "Too few real source logos; investigate before release"

if __name__=="__main__":main()
