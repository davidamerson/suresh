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

def main():
    import frida
    with open("/tmp/sltv_credentials.json") as f:creds=json.load(f)
    assert creds["email"].endswith("@gmail.com"), "Expected authorized test Gmail account"
    _,pkgout,_=shell("adb","shell","pm","list","packages","-3")
    pkgs=re.findall(r"package:([^\s]+)",pkgout)
    print("INSTALLED_THIRD_PARTY",pkgs,flush=True)
    if not pkgs: return
    pkg="com.sltv.app" if "com.sltv.app" in pkgs else pkgs[-1]
    d=frida.get_usb_device(timeout=30)
    pid=d.spawn([pkg])
    sess=d.attach(pid)
    script=sess.create_script(JS)
    script.on("message",on_message)
    script.load()
    d.resume(pid)
    time.sleep(14)
    snap("01_launch")
    tap_node("Get Started")
    time.sleep(6)
    snap("02_signin")
    print("SIGNIN_NODES",json.dumps(visible_nodes()[:40]),flush=True)
    for i in range(4):
        if tap_node("Don't have an account"):
            break
        move_up()
        print("SCROLLED_TO_SIGNUP",i,flush=True)
    else:
        tap_node("Sign Up")
    time.sleep(7)
    snap("03_signup_before_input")
    nodes=private_ui()
    print("SIGNUP_FORM_META",json.dumps(nodes[:50]),flush=True)
    fields=[n for n in nodes if "EditText" in n["class"]]
    print("EDITTEXT_COUNT",len(fields),flush=True)
    if len(fields)<2:
        print("BLOCKER: signup form unavailable",flush=True)
        return
    # Determine field roles using screen hints in accessibility nodes. The typical form:
    # name, email, password, confirm password; only fill requested fields.
    roles=[]
    for i,n in enumerate(fields):
        l=n["text"].lower()
        if "email" in l: roles.append("email")
        elif "confirm" in l: roles.append("confirm")
        elif "password" in l:roles.append("password")
        elif "name" in l:roles.append("name")
        else:roles.append("")
    if not any(roles):
        if len(fields)==2:roles=["email","password"]
        elif len(fields)==3:roles=["name","email","password"]
        elif len(fields)>=4:roles=["name","email","password","confirm"]+[""]*(len(fields)-4)
    print("FIELD_ROLES",roles,flush=True)
    for n,role in zip(fields,roles):
        val={"email":creds["email"],"password":creds["password"],"confirm":creds["password"],"name":"TV Test User"}.get(role)
        if val and press_bounds(n["bounds"]):
            input_text(val)
            shell("adb","shell","input","keyevent","KEYCODE_BACK")
            time.sleep(0.5)
    # Clear plaintext copy from Python memory where possible; Android owns its form state.
    del creds
    n=private_ui()
    print("POST_FILL_UI_META",json.dumps(n[:40]),flush=True)
    for candidate in ["I agree","Accept Terms","Terms and Conditions","Create Account","Sign Up","Register"]:
        if candidate in ("Create Account","Sign Up","Register"):
            if tap_node(candidate):break
        else:
            tap_node(candidate)
    time.sleep(12)
    print("POST_CREATE_UI_META",json.dumps(private_ui()[:50]),flush=True)
    if any("Verify" in n["text"] or "verification" in n["text"].lower() for n in private_ui()):
        print("BLOCKER: email verification required; do not bypass.",flush=True)
    for label in ("Continue","Go to Home","Got it","Skip","Not now","Home","Live TV","Watch"):
        if tap_node(label):
            time.sleep(5)
    print("HOME_UI_META",json.dumps(private_ui()[:60]),flush=True)
    for channel in ["Hiru","Sirasa","Derana","Rupavahini","ITN"]:
        if tap_node(channel):
            time.sleep(10)
            print("CHANNEL_TRIED",channel,flush=True)
            shell("adb","shell","input","keyevent","KEYCODE_BACK")
            time.sleep(2)
    os.makedirs(OUT,exist_ok=True)
    with open(os.path.join(OUT,"network_paths.json"),"w") as f:json.dump(records,f,indent=2)
    with open(os.path.join(OUT,"status.txt"),"w") as f:f.write("Logged redacted hosts/paths only. See public workflow log for nonsecret UI labels.\n")
    print("SUMMARY",json.dumps({"record_count":len(records),"hosts":sorted(set(x["host"] for x in records))}),flush=True)

if __name__=="__main__":
    try:main()
    except Exception:
        import traceback
        print("SAFE_EXCEPTION",traceback.format_exc().replace("ulsampathwasantha","<redacted>"),flush=True)
        sys.exit(1)
