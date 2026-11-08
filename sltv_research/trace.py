#!/usr/bin/env python3
"""SLTV V1.4.8 Android emulator observation. No DRM, TLS or auth bypass."""
import os, re, sys, json, time, subprocess, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone

OUT = "sltv_trace_results"
os.makedirs(OUT, exist_ok=True)
records = []
seen = set()
def shell(*args, timeout=20):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr
def clean_url(raw):
    raw = str(raw).strip()
    if len(raw) > 4096: raw = raw[:4096]
    try:
        p = urllib.parse.urlsplit(raw)
        if p.scheme not in ("http", "https"): return None
        # Do NOT save authentication data / signed URL query values in public artifacts.
        qs = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
        keys = sorted(set(k for k,v in qs))
        path = re.sub(r"/[0-9a-fA-F]{48,}(?=/|$)", "/<long-token>", p.path)
        return {"scheme": p.scheme, "host": p.hostname, "path": path,
                "query_parameter_names":keys, "has_query":bool(qs)}
    except Exception:
        return None
def on_message(message, data):
    if message.get("type") == "send":
        payload = message.get("payload", {})
        url = clean_url(payload.get("url", ""))
        if not url: return
        source = str(payload.get("source", "unspecified"))
        key = (url["host"],url["path"],",".join(url["query_parameter_names"]),source)
        if key in seen: return
        seen.add(key)
        obj = {"timestamp":datetime.now(timezone.utc).isoformat(), "source":source,**url}
        records.append(obj)
        print("CAPTURED", json.dumps(obj,ensure_ascii=False), flush=True)
    elif message.get("type") == "error":
        print("FRIDA ERROR",str(message.get("stack",""))[:1200],flush=True)

JS = r"""
'use strict';
function emit(source, value) {
  try {
    const s = String(value);
    if (s.startsWith('http://') || s.startsWith('https://')) {
      send({source:source, url:s});
    }
  } catch(e){}
}
function hookFactory(cname, method, signatures, argIndex) {
  try {
    let cls=Java.use(cname);
    for (const signature of signatures) {
      try {
        const m=cls[method].overload.apply(cls[method], signature);
        m.implementation=function() {
          try { emit(cname+'.'+method, arguments[argIndex].toString()); } catch(e) {}
          return m.apply(this,arguments);
        };
        send({source:'hook',url:'note://'+cname+'.'+method});
      } catch(e) {}
    }
  } catch(e) {}
}
Java.perform(function(){
  hookFactory('android.net.Uri', 'parse', [['java.lang.String']],0);
  hookFactory('android.webkit.WebView','loadUrl',[['java.lang.String']],0);
  hookFactory('okhttp3.Request$Builder','url',[['java.lang.String'],['okhttp3.HttpUrl']],0);
  hookFactory('androidx.media3.common.MediaItem$Builder','setUri',[['java.lang.String'],['android.net.Uri']],0);
  hookFactory('com.google.android.exoplayer2.MediaItem$Builder','setUri',[['java.lang.String'],['android.net.Uri']],0);
  const pfx=['androidx.media3.datasource','com.google.android.exoplayer2.upstream'];
  pfx.forEach(function(pkg) {
    try {
      const DataSpec=Java.use(pkg+'.DataSpec');
      const Source=Java.use(pkg+'.DefaultHttpDataSource');
      const open=Source.open.overload(pkg+'.DataSpec');
      open.implementation=function(spec) {
        try{emit(pkg+'.DefaultHttpDataSource.open',spec.uri.toString());}catch(e){}
        return open.call(this,spec);
      };
    }catch(e){}
  });
});
"""

def snap(label):
    shell("adb","exec-out","screencap","-p",timeout=25) # avoid dumping screenshot bytes in process output?
    with open(os.path.join(OUT,label+".png"),"wb") as f:
        p=subprocess.run(["adb","exec-out","screencap","-p"], stdout=f,stderr=subprocess.PIPE,timeout=30)
    print("SCREENSHOT",label, flush=True)

def visible_nodes():
    shell("adb","shell","uiautomator","dump","/sdcard/window.xml",timeout=30)
    c,out,err=shell("adb","shell","cat","/sdcard/window.xml",timeout=20)
    if not out: return []
    with open(os.path.join(OUT,"ui.xml"),"w") as f:f.write(out)
    try:
        root=ET.fromstring(out.strip())
    except Exception:
        return []
    nodes=[]
    for n in root.iter("node"):
        txt=n.attrib.get("text","")+" "+n.attrib.get("content-desc","")
        bounds=n.attrib.get("bounds","")
        if txt.strip():nodes.append({"text":txt.strip()[:120],"bounds":bounds})
    return nodes

def tap_node(keyword):
    nodes=visible_nodes()
    print("UI_NODES",json.dumps(nodes[:50],ensure_ascii=False),flush=True)
    for n in nodes:
        if keyword.lower() in n["text"].lower():
            m=re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",n["bounds"])
            if m:
                x=(int(m.group(1))+int(m.group(3)))//2
                y=(int(m.group(2))+int(m.group(4)))//2
                shell("adb","shell","input","tap",str(x),str(y))
                print("TAPPED",keyword,x,y,flush=True)
                return True
    return False

def main():
    import frida
    _,pkgout,_=shell("adb","shell","pm","list","packages","-3")
    pkgs=re.findall(r"package:([^\s]+)",pkgout)
    print("INSTALLED_THIRD_PARTY",pkgs,flush=True)
    if not pkgs: return
    pkg=pkgs[-1]
    d=frida.get_usb_device(timeout=30)
    pid=d.spawn([pkg])
    sess=d.attach(pid)
    script=sess.create_script(JS)
    script.on("message",on_message)
    script.load()
    d.resume(pid)
    print("APP_STARTED",pkg,pid,flush=True)
    time.sleep(15)
    snap("01_launch")
    tap_node("Live TV")
    time.sleep(12)
    snap("02_after_livetv")
    if not tap_node("Hiru"): 
        if not tap_node("Local"):
            shell("adb","shell","input","keyevent","KEYCODE_DPAD_DOWN")
            shell("adb","shell","input","keyevent","KEYCODE_DPAD_CENTER")
    time.sleep(12)
    snap("03_after_channel")
    for name in ["Sirasa","Derana","Rupavahini","ITN"]:
        shell("adb","shell","input","keyevent","KEYCODE_BACK")
        time.sleep(2)
        if not tap_node(name):
            shell("adb","shell","input","keyevent","KEYCODE_DPAD_RIGHT")
            shell("adb","shell","input","keyevent","KEYCODE_DPAD_CENTER")
        time.sleep(9)
        snap("04_"+name.lower())
    time.sleep(7)
    with open(os.path.join(OUT,"network_paths.json"),"w") as f:json.dump(records,f,indent=2)
    c,log,_=shell("adb","logcat","-d","-t","500",timeout=25)
    # Safety: keep only generic media/network error messages, never full credentials
    lines=[x[:350] for x in log.splitlines() if re.search(r"ExoPlayer|Media3|Flutter|ssl|http|Stream|Firebase",x,re.I)]
    with open(os.path.join(OUT,"app_log_summary.txt"),"w") as f:f.write("\n".join(lines[-150:]))
    print("SUMMARY",json.dumps({"record_count":len(records),"hosts":sorted(set(x["host"] for x in records))}),flush=True)
if __name__=="__main__":
    try:main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        open(os.path.join(OUT,"error.txt"),"w").write(traceback.format_exc())
        sys.exit(1)
