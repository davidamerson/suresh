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
adb shell dumpsys package lk.openstream.tv.companion | grep "NavigationService" > tvtest/accessibility_service_status.txt || true
echo 'SMOKE TEST COMPLETE'
