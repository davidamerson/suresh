#!/usr/bin/env bash
set -euo pipefail
mkdir -p tvtest
adb install -r tvtest/independent/build/outputs/apk/debug/independent-debug.apk
adb install -r tvtest/companion/build/outputs/apk/debug/companion-debug.apk
adb shell am start -n lk.openstream.tv.independent/.MainActivity
sleep 10
adb shell uiautomator dump /sdcard/window.xml
adb shell cat /sdcard/window.xml > tvtest/independent_ui.xml
adb exec-out screencap -p > tvtest/independent_home.png
python3 - <<'PY'
from pathlib import Path
s=Path('tvtest/independent_ui.xml').read_text()
assert 'OPENSTREAM' in s, 'Independent app did not launch'
assert '174 channels' in s, '174-channel catalogue not visible'
assert 'All channels' in s
print('PASS independent app: displayed 174-channel catalogue')
PY
# Exercise channel search. The emulator is in landscape (1794x1080).
adb shell input tap 820 300
adb shell input text Hiru
adb shell input keyevent 4
sleep 2
adb shell uiautomator dump /sdcard/window.xml
adb shell cat /sdcard/window.xml > tvtest/independent_search_ui.xml
adb exec-out screencap -p > tvtest/independent_search.png
python3 - <<'PY'
from pathlib import Path
s=Path('tvtest/independent_search_ui.xml').read_text()
assert 'Hiru' in s, 'Channel search did not show Hiru'
print('PASS independent search: Hiru visible')
PY
# Click the specific public Hiru tile (not the separate Hiru HD server entry).
python3 - <<'PY'
from pathlib import Path
import re, xml.etree.ElementTree as ET
root=ET.fromstring(Path("tvtest/independent_search_ui.xml").read_text())
for n in root.iter("node"):
    if n.attrib.get("text","").strip()=="Hiru":
        b=n.attrib.get("bounds","")
        m=re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",b)
        if m:
            x=(int(m.group(1))+int(m.group(3)))//2
            y=(int(m.group(2))+int(m.group(4)))//2
            Path("/tmp/hiru_position").write_text(f"{x} {y}")
            print("HIRU_TILE",x,y)
            break
else:
    raise RuntimeError("Hiru item not visible")
PY
read CX CY < /tmp/hiru_position
adb shell input tap "$CX" "$CY"
sleep 14
adb shell uiautomator dump /sdcard/window.xml
adb shell cat /sdcard/window.xml > tvtest/independent_hiru_player_ui.xml
adb exec-out screencap -p > tvtest/independent_hiru_player.png
python3 - <<'PY'
from pathlib import Path
s=Path("tvtest/independent_hiru_player_ui.xml").read_text()
player=any(x in s for x in ("Buffering", "Playing", "Unable to play", "Connecting", "Error code"))
print("INDEPENDENT_PLAYER_OPENED",player)
if not player:
    print("PLAYER_UI_EXCERPT",s[:1200])
assert player,"Selecting Hiru did not open our Media3 player"
PY
adb shell am force-stop lk.openstream.tv.independent
adb shell am start -n lk.openstream.tv.companion/.MainActivity
sleep 9
adb shell uiautomator dump /sdcard/window.xml
adb shell cat /sdcard/window.xml > tvtest/companion_ui.xml
adb exec-out screencap -p > tvtest/companion_home.png
python3 - <<'PY'
from pathlib import Path
s=Path('tvtest/companion_ui.xml').read_text()
assert 'SLTV COMPANION' in s, 'Companion app did not launch'
assert '174 channels' in s, '174-channel companion catalogue missing'
print('PASS companion app: displayed 174-channel catalogue')
PY
# Click the companion channel tile. Without original SLTV installed it must explain dependency.
adb shell input tap 688 440
sleep 2
adb shell uiautomator dump /sdcard/window.xml
adb shell cat /sdcard/window.xml > tvtest/companion_missing_sltv_ui.xml
adb exec-out screencap -p > tvtest/companion_missing_sltv.png
python3 - <<'PY'
from pathlib import Path
s=Path("tvtest/companion_missing_sltv_ui.xml").read_text()
ok="Original SLTV app is required" in s or "Install SLTV V1.4.8" in s
print("COMPANION_ORIGINAL_APP_DEPENDENCY_DIALOG",ok)
assert ok,"Companion tile did not open expected original-app requirement dialog"
PY
adb shell dumpsys package lk.openstream.tv.companion | grep "NavigationService" > tvtest/accessibility_service_status.txt || true
echo 'SMOKE TEST COMPLETE'
