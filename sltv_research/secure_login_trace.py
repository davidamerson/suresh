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
        path = re.sub(r"/[A-Za-z0-9_-]{20,}(?=/|$)", "/<id>", p.path)
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
    with open(os.path.join(OUT,label+".png"),"wb") as f:
        p=subprocess.run(["adb","exec-out","screencap","-p"], stdout=f,stderr=subprocess.PIPE,timeout=30)
    print("SCREENSHOT",label, flush=True)

def visible_nodes():
    shell("adb","shell","uiautomator","dump","/sdcard/window.xml",timeout=30)
    c,out,err=shell("adb","shell","cat","/sdcard/window.xml",timeout=20)
    if not out: return []
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
    print("UI_LABELS",json.dumps([{"text":"<redacted>" if "@" in n["text"] else n["text"][:70],"bounds":n["bounds"]} for n in nodes[:50]],ensure_ascii=False),flush=True)
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

def move_up():
    shell("adb","shell","input","swipe","530","1490","530","500","380")
    time.sleep(1.5)

def input_text(value):
    # Do not print the credential or persist ADB command traces.
    code,out,err=shell("adb","shell","input","text",value,timeout=15)
    return code == 0

def private_ui():
    # Do NOT log plaintext UI contents once personal data entered.
    shell("adb","shell","uiautomator","dump","/sdcard/window.xml",timeout=20)
    c,out,err=shell("adb","shell","cat","/sdcard/window.xml",timeout=15)
    try:root=ET.fromstring(out.strip())
    except: return []
    nodes=[]
    for n in root.iter("node"):
        kind=n.attrib.get("class","")
        txt=n.attrib.get("text","")+" "+n.attrib.get("content-desc","")
        if re.search(r"@|[A-Za-z0-9_]{16,}",txt):txt="<redacted>"
        b=n.attrib.get("bounds","")
        if txt.strip() or "EditText" in kind or "CheckBox" in kind:
            nodes.append({"text":txt.strip()[:100],"bounds":b,"class":kind})
    return nodes

def press_bounds(b):
    m=re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
    if not m:return False
    x=(int(m.group(1))+int(m.group(3)))//2
    y=(int(m.group(2))+int(m.group(4)))//2
    if x<=0 or y<=0:return False
    shell("adb","shell","input","tap",str(x),str(y))
    time.sleep(1)
    return True

def tap_button(label):
    for i in range(5):
        nodes=private_ui()
        match=next((n for n in nodes if n["class"].endswith("Button") and label.lower() in n["text"].lower() and n["bounds"]!="[0,0][0,0]"),None)
        if match and press_bounds(match["bounds"]):
            print("BUTTON_PRESSED",label,flush=True)
            return True
        move_up()
    print("BUTTON_NOT_FOUND",label,flush=True)
    return False

def safe_view():
    n=private_ui()
    for x in n:
        v=x.get("text","")
        if "@" in v or len(v)>100: x["text"]="<redacted>"
    print("APP_VIEW",json.dumps(n[:55],ensure_ascii=False),flush=True)
    return n

def tap_exact(label):
    n=private_ui()
    for x in n:
        if x.get("text","").lower().strip()==label.lower() and x.get("bounds") not in ("[0,0][0,0]",""):
            if press_bounds(x["bounds"]):
                print("TAP_EXACT",label,flush=True)
                return True
    return False

def safe_scroll():
    shell("adb","shell","input","swipe","510","1470","510","550","400")
    time.sleep(1)

def choose_label(candidates, scrolls=1):
    for attempt in range(scrolls+1):
        for x in candidates:
            if tap_exact(x): return x
        if attempt<scrolls:safe_scroll()
    return None

def save_records(stage):
    with open(os.path.join(OUT,"network_paths.json"),"w") as f:
        json.dump(records,f,ensure_ascii=False,indent=2)
    print("CAPTURE_SUMMARY",stage,json.dumps({
        "count":len(records),
        "hosts":sorted(set(x["host"] for x in records)),
        "manifest_path_count":sum(1 for x in records if ".m3u8" in x["path"].lower() or ".mpd" in x["path"].lower())
    }),flush=True)

def main():
    import frida
    with open("/tmp/sltv_credentials.json","r",encoding="utf-8") as f: creds=json.load(f)
    assert creds["email"].endswith("@gmail.com")
    package="com.sltv.app"
    device=frida.get_usb_device(timeout=30)
    pid=device.spawn([package])
    session=device.attach(pid)
    script=session.create_script(JS)
    script.on("message",on_message)
    script.load()
    device.resume(pid)
    time.sleep(13)
    snap("01_welcome_no_credentials")
    assert tap_node("Get Started"),"Get Started button unavailable"
    time.sleep(5)
    n=safe_view()
    fields=[x for x in n if "EditText" in x["class"]]
    if len(fields)<2:
        print("BLOCKER_LOGIN_INPUTS_NOT_FOUND",flush=True)
        save_records("failed_to_find_login")
        return
    for i,kind in enumerate(["email","password"]):
        if not press_bounds(fields[i]["bounds"]):
            print("LOGIN_FIELD_TAP_FAILED",kind,flush=True)
            save_records("failed_to_fill_login")
            return
        ok=input_text(creds[kind])
        shell("adb","shell","input","keyevent","KEYCODE_BACK")
        print("LOGIN_FIELD_FILLED",kind,ok,flush=True)
        time.sleep(0.6)
    # Secret values never printed, captured in artifacts, or sent in trace.
    del creds
    assert choose_label(["Sign In"],scrolls=1)=="Sign In", "Sign-in submit not found"
    print("LOGIN_SUBMITTED",flush=True)
    time.sleep(16)
    # Verified account opens a first-run tutorial; dismiss it using its visible Skip control.
    # This is ordinary UI navigation, not an authentication or DRM bypass.
    tap_node("English")
    time.sleep(2)
    if not (tap_exact("Skip") or tap_exact("මඟහරින්න") or tap_node("මඟහරින්න")):
        for _ in range(5):
            if tap_exact("Next") or tap_exact("ඊළඟට →"):
                time.sleep(1.5)
            else:break
        tap_exact("Get Started")
        tap_exact("Finish")
    time.sleep(8)
    snap("02_after_tutorial")
    print("AFTER_TUTORIAL",flush=True)
    safe_view()
    n=safe_view()
    if any("verify" in x.get("text","").lower() or "resend email" in x.get("text","").lower() for x in n):
        print("BLOCKER: email verification still requested",flush=True)
        save_records("email_verification")
        return
    if any("wrong password" in x.get("text","").lower() or "invalid credentials" in x.get("text","").lower() for x in n):
        print("BLOCKER: invalid sign-in credentials",flush=True)
        save_records("invalid_credentials")
        return
    # Free/guest access only; never approve a paid plan.
    for stage in range(3):
        n=safe_view()
        labels=[x["text"].strip().lower() for x in n]
        has_local=any(t in ("hiru tv","sirasa tv","rupavahini","tv derana","itn") for t in labels)
        if has_local:break
        selected=choose_label(["Free Plan","Free","Continue for free","Use Free Plan",
                               "Continue","Skip","Not Now","Live TV","Channels"], scrolls=0)
        if selected:
            print("NAVIGATION_CLICK",selected,flush=True)
            time.sleep(6)
        else:
            safe_scroll()
    print("PRE_CHANNELS_STATE",flush=True)
    snap("03_channels_or_plan")
    n=safe_view()
    # Search list, try entering Live TV, then tapping individual channels.
    labels_to_test=["Hiru TV","Sirasa TV","TV Derana","Rupavahini","ITN"]
    played=[]
    for idx,channel in enumerate(labels_to_test):
        hit=choose_label([channel],scrolls=2)
        if not hit:
            if idx==0:
                choose_label(["Live TV","Live Channels","Channels","Local"],scrolls=1)
                time.sleep(5)
                hit=choose_label([channel],scrolls=2)
        if not hit:
            print("CHANNEL_NOT_PRESENT",channel,flush=True)
            continue
        print("CHANNEL_OPENED",channel,flush=True)
        time.sleep(4)
        snap("playing_"+channel.replace(" ","_").lower()+"_t4")
        time.sleep(10)
        snap("playing_"+channel.replace(" ","_").lower()+"_t14")
        save_records("after_"+channel.replace(" ","_").lower())
        result=safe_view()
        played.append(channel)
        shell("adb","shell","input","keyevent","KEYCODE_BACK")
        time.sleep(2)
        if idx==0:print("FIRST_CHANNEL_ATTEMPT_COMPLETE",flush=True)
    print("CHANNEL_ATTEMPTS",json.dumps(played),flush=True)
    print("FINAL_STATE",flush=True)
    safe_view()
    code, lg, e=shell("adb","logcat","-d","-t","400",timeout=25)
    filtered=[x[:300] for x in lg.splitlines() if any(t in x for t in ["ExoPlayer","MediaCodec","flutter","Media3","PlayerError"])]
    with open(os.path.join(OUT,"media_log_excerpt.txt"),"w") as dest: dest.write("\n".join(filtered[-100:]))
    save_records("complete")
if __name__=="__main__":
    try:main()
    except Exception:
        import traceback
        err=traceback.format_exc()
        print("SAFE_EXCEPTION",err.replace("ulsampathwasantha","<redacted>"),flush=True)
        save_records("exception")
        sys.exit(1)
