#!/usr/bin/env bash
set -euo pipefail
mkdir -p smoke-results

adb install -r output_apks/SLTV_Independent_TV_Remote_Mouse.apk
adb install -r output_apks/SLTV_Channel_Bridge_TV_Remote_Mouse.apk
adb install -r output_apks/Sri_Lanka_TV_Android_Phone.apk

for flavor in standalone bridge phone; do
  case "$flavor" in
    standalone) pkg=com.suresh.sltv.standalone ;;
    bridge) pkg=com.suresh.sltv.bridge ;;
    phone) pkg=com.suresh.sltv.phone ;;
  esac
  echo "TEST_APP $flavor $pkg"
  if [ "$flavor" = phone ]; then
    adb shell settings put system accelerometer_rotation 0 || true
    adb shell settings put system user_rotation 0 || true
  fi
  adb shell am force-stop "$pkg" || true
  adb shell am start -n "$pkg/com.suresh.srilankatv.MainActivity"
  sleep 7
  adb exec-out screencap -p > "smoke-results/${flavor}_home.png"
  adb shell uiautomator dump /sdcard/tvtest.xml >/dev/null
  adb shell cat /sdcard/tvtest.xml > "smoke-results/${flavor}_home.xml"
  if [ "$flavor" = "bridge" ]; then
    grep -q '138 channels' "smoke-results/${flavor}_home.xml"
    echo "BRIDGE_NORMAL_AND_HD_CHANNELS_PRESENT"
  fi
  if [ "$flavor" = "standalone" ]; then
    grep -q '138 channels' "smoke-results/${flavor}_home.xml"
  fi

  if [ "$flavor" != phone ]; then
    adb shell input keyevent 23
    sleep 3
    adb shell dumpsys activity activities | grep -q 'PlayerActivity'
    echo "REMOTE_OK_OPENED_PLAYER $flavor"
    adb exec-out screencap -p > "smoke-results/${flavor}_remote_player.png"
    adb shell input keyevent 4
    sleep 3
  fi

  # ADB tap follows Android's pointer click path used by touch and a mouse.
  python3 - "$flavor" <<'PY'
import sys,re,subprocess,xml.etree.ElementTree as ET
flavor=sys.argv[1]
subprocess.run(["adb","shell","uiautomator","dump","/sdcard/tvtest.xml"],
               stdout=subprocess.DEVNULL,check=True)
xml=subprocess.check_output(["adb","shell","cat","/sdcard/tvtest.xml"],text=True)
root=ET.fromstring(xml)
candidates=[]
for node in root.iter("node"):
    title=node.attrib.get("text","")
    bounds=node.attrib.get("bounds","")
    if re.match(r"^(?:▣\s*)?\d+\s+",title):
        m=re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",bounds)
        if m:
            x=(int(m[1])+int(m[3]))//2
            y=(int(m[2])+int(m[4]))//2
            candidates.append((x,y,title))
assert candidates, f"No visible channel buttons for {flavor}"
x,y,title=candidates[0]
print("POINTER_TAP",flavor,title,x,y,flush=True)
subprocess.run(["adb","shell","input","tap",str(x),str(y)],check=True)
PY

  sleep 3
  adb exec-out screencap -p > "smoke-results/${flavor}_pointer_player.png"
  adb shell dumpsys activity activities > "smoke-results/${flavor}_after_tap_activity.txt"
  if ! grep -q 'PlayerActivity' "smoke-results/${flavor}_after_tap_activity.txt"; then
    adb logcat -d -t 500 > "smoke-results/${flavor}_tap_logcat.txt" || true
    echo "POINTER_PLAYER_NOT_VISIBLE $flavor"
    exit 1
  fi
  echo "POINTER_TAP_OPENED_PLAYER $flavor"
  adb shell input keyevent 4
  sleep 2
  adb shell am force-stop "$pkg"
done

echo "ALL_THREE_APPS_SELECTION_SMOKE_PASSED"
