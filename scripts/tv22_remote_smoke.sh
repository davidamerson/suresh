#!/usr/bin/env bash
set -euo pipefail
mkdir -p tv22_smoke
PACKAGE=com.suresh.tv
adb install -r output_apks/TV.apk
adb shell am force-stop "$PACKAGE" || true
adb shell am start -n "$PACKAGE/com.suresh.srilankatv.MainActivity"
sleep 5
adb exec-out screencap -p > tv22_smoke/home.png
adb shell uiautomator dump /sdcard/homex.xml >/dev/null
adb shell cat /sdcard/homex.xml > tv22_smoke/home.xml
python3 - <<'PY'
import xml.etree.ElementTree as E,re
root=E.parse("tv22_smoke/home.xml")
text=" ".join(x.attrib.get("text","") for x in root.iter("node"))
assert "22 CHANNELS" in text, text[:800]
assert "Rupawahini" in text and "Hiru" in text
assert "TV" in text
print("HOME_22_CHANNELS",flush=True)
PY
adb logcat -c || true
adb shell input keyevent 23
sleep 3
adb shell dumpsys activity activities | grep -q 'PlayerActivity'
echo "OK_BUTTON_OPENS_FULLSCREEN_PLAYER"
adb exec-out screencap -p > tv22_smoke/player.png
adb shell input keyevent 20
sleep 1
adb shell input keyevent 20
sleep 1
adb shell input keyevent 19
sleep 1
adb logcat -d -s TV_CHANNEL:I '*:S' > tv22_smoke/channel_log.txt
cat tv22_smoke/channel_log.txt
python3 - <<'PY'
from pathlib import Path
import re
s=Path("tv22_smoke/channel_log.txt").read_text()
events=re.findall(r"SELECT (\d+) (.+)",s)
print("REMOTE_CHANNEL_SEQUENCE",events,flush=True)
assert [int(x[0]) for x in events[-4:]]==[1,2,3,2],events
PY
adb shell input keyevent 4
sleep 2
adb shell dumpsys activity activities | grep -q 'MainActivity'
echo "BACK_RETURNS_CHANNEL_HOME"
# Pointer tap from mouse/touch uses Android's regular click input.
adb shell uiautomator dump /sdcard/pointer.xml >/dev/null
adb shell cat /sdcard/pointer.xml > tv22_smoke/pointer.xml
python3 - <<'PY'
import re,xml.etree.ElementTree as E,subprocess
root=E.parse("tv22_smoke/pointer.xml")
for node in root.iter("node"):
    t=node.attrib.get("text","")
    if re.match(r"^01\s+Rupawahini$",t):
        b=node.attrib.get("bounds","")
        p=re.findall(r"\d+",b)
        if len(p)==4:
            x=(int(p[0])+int(p[2]))//2
            y=(int(p[1])+int(p[3]))//2
            subprocess.run(["adb","shell","input","tap",str(x),str(y)],check=True)
            print("POINTER_CLICKED_CHANNEL",x,y,flush=True)
            break
else:
    raise AssertionError("Rupawahini button missing from home XML")
PY
sleep 3
adb shell dumpsys activity activities | grep -q 'PlayerActivity'
echo "MOUSE_TAP_OPENS_PLAYER"
adb shell input keyevent 4
sleep 1
# Confirm original remote shortcut service exists but user must authorize it.
adb shell dumpsys package "$PACKAGE" > tv22_smoke/package.txt
grep -q "PrimeButtonAccessibilityService" tv22_smoke/package.txt
echo "OPT_IN_PRIME_SHORTCUT_SERVICE_PACKAGED"
echo "TV22_REMOTE_AND_MOUSE_SMOKE_PASSED"
