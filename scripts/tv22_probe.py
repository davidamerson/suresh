#!/usr/bin/env python3
"""Public endpoint and five-frame decode audit for 22-channel TV app.
Do not reuse provider license URLs or access tokens. Do not bypass DRM.
"""
import json,urllib.request,urllib.error,concurrent.futures,subprocess,time,re,os
from pathlib import Path
items=json.loads(Path("tv22/channel_sources.json").read_text())
out=Path("tv22_audit")
out.mkdir(exist_ok=True)

def probe(row):
    now=time.time()
    record={"number":row["number"],"channel":row["label"],"type":row["source_type"],
            "status":"unknown","decoded_video_frames":0}
    url=row["url"]
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (SLTV 22 channel compatibility audit)","Accept":"application/json,application/vnd.apple.mpegurl,application/dash+xml,*/*","Range":"bytes=0-2047"})
        with urllib.request.urlopen(req,timeout=11) as resp:
            content=resp.read(4096)
            typ=(resp.headers.get("Content-Type") or "").lower()
            record["http_code"]=resp.status
            record["content_type"]=typ
        if "json" in typ:
            data=json.loads(content)
            info=data.get("data",{}) if isinstance(data,dict) else {}
            drm=info.get("drm") or {}
            record["drm_flags"]={k:bool(drm.get(k)) for k in ("widevine","verimatrix","fairplay")}
            record["metadata_status"]=data.get("status")
            record["status"]="drm_authorization_required" if any(record["drm_flags"].values()) else "provider_json_not_media"
        elif content.lstrip().startswith(b"#EXTM3U") or ".m3u8" in url:
            record["status"]="hls_manifest_candidate"
        elif b"<MPD" in content:
            record["status"]="dash_manifest_candidate"
        elif "html" in typ:
            record["status"]="html_not_playlist"
        else:
            record["status"]="other_response"
    except urllib.error.HTTPError as e:
        record["http_code"]=e.code
        record["status"]="http_error"
    except Exception as e:
        record["status"]="probe_error_"+type(e).__name__
    # Only direct publicly accessible channels are tested for actual video frames.
    if record["type"]=="direct" and record["status"] in ("hls_manifest_candidate","dash_manifest_candidate"):
        try:
            result=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-rw_timeout","9000000",
                "-i",url,"-map","0:v:0","-frames:v","5","-an","-sn","-dn",
                "-progress","pipe:1","-f","null","-"],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=26)
            frame_counts=[int(x) for x in re.findall(r'(?m)^frame=(\d+)',result.stdout)]
            record["decoded_video_frames"]=max(frame_counts,default=0)
            record["ffmpeg_exit"]=result.returncode
            record["status"]="verified_5_frames" if result.returncode==0 and record["decoded_video_frames"]>=5 else "decode_failed"
            record["decode_error_excerpt"]=result.stderr.strip()[-240:]
        except subprocess.TimeoutExpired:
            record["status"]="decode_timeout"
        except Exception as e:
            record["status"]="decode_error_"+type(e).__name__
    record["probe_seconds"]=round(time.time()-now,1)
    return record

with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
    reports=list(pool.map(probe,items))
reports.sort(key=lambda x:x["number"])
(out/"results.json").write_text(json.dumps(reports,ensure_ascii=False,indent=2))
for r in reports:print("CHANNEL_TEST",json.dumps(r,ensure_ascii=False),flush=True)
counts={}
for r in reports:counts[r["status"]]=counts.get(r["status"],0)+1
print("TEST_SUMMARY",json.dumps({"total":len(reports),"statuses":counts},ensure_ascii=False),flush=True)
assert len(reports)==22
