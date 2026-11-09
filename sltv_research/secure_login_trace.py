#!/usr/bin/env python3
"""SLTV V1.4.8 authenticated Android video playback observation; no DRM bypass."""
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


def inspect_local_cache():
    # Only examine the current app's channel cache, not account/token/preferences.
    import xml.etree.ElementTree as ET
    result=[]
    rc, listing, _ = shell("adb","shell","ls","-1","/data/user/0/com.sltv.app/shared_prefs",timeout=15)
    names=[x.strip() for x in listing.splitlines() if x.strip().endswith(".xml")]
    print("PREF_FILE_COUNT",len(names),flush=True)
    for fname in names[:35]:
        rc, raw, _=shell("adb","shell","cat","/data/user/0/com.sltv.app/shared_prefs/"+fname,timeout=20)
        if rc!=0 or not raw:continue
        try:root=ET.fromstring(raw)
        except Exception:continue
        for node in root:
            key=node.attrib.get("name","")
            if not ("sltv_cached_channels" in key or "sltv_cached_categories" in key):continue
            value=node.text or ""
            print("CACHE_KEY_FOUND",key,"chars",len(value),flush=True)
            if value.startswith("json."):value=value[5:]
            try:obj=json.loads(value)
            except Exception:
                print("CACHE_NOT_JSON",flush=True)
                continue
            print("CACHE_CONTAINER",type(obj).__name__,len(obj) if hasattr(obj,"__len__") else -1,flush=True)
            def walk(v,group="",depth=0):
                if depth>8:return
                if isinstance(v,list):
                    for sub in v:walk(sub,group,depth+1)
                elif isinstance(v,dict):
                    nm=next((v[k] for k in ("name","channelName","title","channel_name","label") if isinstance(v.get(k),str)),None)
                    grp=next((v[k] for k in ("category","categoryName","group","groupTitle") if isinstance(v.get(k),str)),group)
                    streams={k:clean_url(v[k]) for k in ("streamUrl","streamUrlMp4","stream_url","url","stream","link","hlsUrl","dashUrl") if isinstance(v.get(k),str) and v[k].startswith(("http://","https://"))}
                    if nm and streams:
                        result.append({"name":nm[:100],"category":grp[:100] if isinstance(grp,str) else "",**streams})
                    for sub in v.values():
                        if isinstance(sub,(dict,list)):walk(sub,grp,depth+1)
            walk(obj)
    unique={q["name"]:q for q in result}
    print("CACHE_CHANNEL_COUNT",len(unique),flush=True)
    with open(os.path.join(OUT,"cached_channel_paths_redacted.json"),"w") as out:
        json.dump(list(unique.values()),out,ensure_ascii=False,indent=2)
    for item in list(unique.values())[:100]:
        print("CACHE_CHANNEL",json.dumps(item,ensure_ascii=False),flush=True)

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
    # SLTV onboarding overlays sometimes remain visible after a "Skip" click.
    # Verify dismissal by observing the channel cards; use only visible close/back UI.
    for attempt in range(7):
        nodes=private_ui()
        labels=[z["text"] for z in nodes]
        if any("1. SL Channels" in v or "Derana SD" in v or "Charana TV" in v for v in labels):
            print("ONBOARDING_DISMISSED",attempt,flush=True)
            break
        print("ONBOARDING_CHECK",attempt,json.dumps(labels[:9],ensure_ascii=False),flush=True)
        if any("මඟහරින්න" in v for v in labels):
            if not tap_node("මඟහරින්න"):
                shell("adb","shell","input","tap","933","245")
        elif any("Skip" in v for v in labels):
            if not tap_exact("Skip"):shell("adb","shell","input","tap","933","245")
        else:
            shell("adb","shell","input","keyevent","KEYCODE_BACK")
        time.sleep(3.5)
        if attempt==2:
            snap("02_tutorial_after_three_close_attempts")
    time.sleep(3)
    print("AFTER_TUTORIAL",flush=True)
    snap("02_after_tutorial")
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
    print("VERIFIED_LOGIN_HOME_SCREEN",flush=True)
    inspect_local_cache()
    snap("02_home_after_tutorial")
    safe_view()
    # Normal free UI navigation. Never select paid subscription offers.
    def normalize(t):
        return "".join(ch for ch in t.casefold() if ch.isalnum() or ch.isspace()).strip()
    def select_channel(names, tries=4):
        for i in range(tries):
            nodes=private_ui()
            for n in nodes:
                txt=normalize(n.get("text",""))
                if any(normalize(name) == txt or (len(normalize(name))>=5 and normalize(name) in txt) for name in names):
                    if press_bounds(n.get("bounds","")):
                        print("CHANNEL_TAPPED",names[0],flush=True)
                        return True
            if i<tries-1:
                safe_scroll()
                time.sleep(1.4)
        return False
    def reset_to_top():
        for _ in range(5):
            shell("adb","shell","input","swipe","500","680","500","1520","340")
            time.sleep(.4)
    def after_player(label):
        safe_view()
        stage=label.lower().replace(" ","_")
        time.sleep(4)
        snap("player_"+stage+"_t4")
        time.sleep(10)
        snap("player_"+stage+"_t14")
        print("PLAYER_FINAL_UI",label,flush=True)
        safe_view()
        save_records("player_"+stage)
        # Save app-level playback metrics and errors without copying potentially secret URL query strings.
        code,stat,err=shell("adb","shell","dumpsys","media.metrics",timeout=15)
        with open(os.path.join(OUT,"metrics_"+stage+".txt"),"w") as dest:
            dest.write("\n".join([line[:200] for line in stat.splitlines() if any(w in line.lower() for w in ["playback","video","audio","error","underrun","codec"])][:80]))
        # Player is embedded in the SLTV home grid: Back exits the app.
        # Keep the main page open and tap the next channel card instead.
        print("PLAYER_RETURN_TO_GRID",label,flush=True)
    targets=[
        ("Charana TV",["Charana TV"]),
        ("Derana SD",["Derana SD"]),
        ("Event TV",["Event TV"]),
        ("Haritha",["Haritha"]),
        ("Hiru",["Hiru"]),
        ("ITN",["ITN"]),
        ("Rupawahini",["Rupawahini","Rupavahini"]),
        ("Shakthi",["Shakthi"]),
        ("Sirasa TV",["Sirasa TV"]),
        ("Supreme TV",["Supreme TV"]),
        ("Swarnavahini",["Swarnavahini"]),
        ("Vasantham",["Vasantham"]),
        ("Siyatha TV",["Siyatha TV"]),
        ("TV1",["TV1","TV 1"]),
        ("Nethra",["Nethra"]),
        ("Rangiri",["Rangiri"]),
        ("Ridee",["Ridee"]),
        ("Jaya TV",["Jaya TV"]),
        ("TV Didula",["TV Didula"]),
        ("ART Television",["ART Television"]),
        ("Channel One",["Channel One"]),
    ]
    test_results=[]
    for label, variants in targets:
        reset_to_top()
        print("TESTING_CHANNEL",label,flush=True)
        selected=select_channel(variants,tries=4)
        if selected:
            test_results.append({"channel":label,"clicked":True})
            after_player(label)
        else:
            test_results.append({"channel":label,"clicked":False})
            print("NOT_FOUND",label,flush=True)
    print("TEST_RESULTS",json.dumps(test_results),flush=True)
    with open(os.path.join(OUT,"channels_tested.json"),"w") as dest:
        json.dump(test_results,dest,indent=2)
    save_records("all_channels_tested")
    print("FINAL_APP_SCREEN",flush=True)
    safe_view()
    code,lg,e=shell("adb","logcat","-d","-t","1500",timeout=25)
    filtered=[]
    for line in lg.splitlines():
        if any(t in line for t in ("ExoPlayerImpl","MediaCodec","Media3","PlayerError","PlaybackException")):
            # Remove full HTTP(S) URLs and possible access tokens from logs.
            filtered.append(re.sub(r"https?://\S+","<URL_REDACTED>",line[:280]))
    with open(os.path.join(OUT,"media_errors_redacted.txt"),"w") as dest:
        dest.write("\n".join(filtered[-200:]))
if __name__=="__main__":
    try:main()
    except Exception:
        import traceback
        err=traceback.format_exc()
        print("SAFE_EXCEPTION",err.replace("ulsampathwasantha","<redacted>"),flush=True)
        save_records("exception")
        sys.exit(1)
