"""Probe whether November 2026 Raw Spread tick archive is available yet.
HEAD / range request only; avoid downloading a potentially huge file.
"""
import requests,json
from datetime import datetime,timezone
base="https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/2026/11/"
urls=[
 base,
 base+"Exness_XAUUSD_Raw_Spread_2026_11.zip",
 "https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/2026/10/Exness_XAUUSD_Raw_Spread_2026_10.zip",
 "https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/2026/",
 base+"05/",
 base+"04/",
 base+"03/",
]
sess=requests.Session()
print("PROBE_UTC_TIME",datetime.now(timezone.utc).isoformat(),flush=True)
for url in urls:
 try:
  r=sess.head(url,timeout=20,allow_redirects=True,headers={"User-Agent":"Mozilla/5.0"})
  result={"url":url,"code":r.status_code,"type":r.headers.get("content-type"),"bytes":r.headers.get("content-length"),"last_modified":r.headers.get("last-modified"),"final_url":r.url}
  print("HEAD_RESULT",json.dumps(result,sort_keys=True),flush=True)
  if "zip" not in url:
   p=sess.get(url,timeout=20,headers={"User-Agent":"Mozilla/5.0"})
   print("LIST_RESULT",json.dumps({"status":p.status_code,"type":p.headers.get("content-type"),"body_first_2400":p.text[:2400]}),flush=True)
 except Exception as e:
  print("PROBE_ERROR",repr(e),url,flush=True)
