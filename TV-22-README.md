# TV — 22-channel Xiaomi TV Box S (3rd Gen) build

Source branch: `tv-minimal-22-20261110` · Android application ID: `com.suresh.tv` · Launcher name: **TV**.

## Controls

The app opens a large-icon grid of 22 user-selected TV channels in the supplied order. Press **OK** or mouse-click to open a channel. The player is immersive full-screen with no persistent visual controls. Press remote **Up** for the preceding numbered channel, **Down** for the next, **Back** for channel home. The selection wraps around at the beginning/end. OK toggles pause/play only when a video is available.

## Channel list

1. Rupawahini
2. ITN
3. Sirasa TV
4. Derana
5. Hiru
6. Swarnavahini
7. Siyatha TV
8. Shakthi
9. 10 Cricket
10. Papare SD
11. Papare HD
12. Sony1
13. Sony Sport (mapped to SLTV's "Sony Sports 2" entry)
14. Star Sport 1
15. Star Sport 2 HD (SLTV's "Star Sports 2" URL; HD resolution is not guaranteed)
16. Star Sport 3
17. Mr Bean (public live-action FAST feed)
18. Baby Shark
19. Lego Channel
20. BBC Earth (public FAST feed)
21. &flix
22. Warner TV

All 22 channels are visible. Their source addresses are in `SriLankaTV/app/src/main/assets/verified_channels.m3u`, and the full origin mapping is in `tv22/channel_sources.json`.

## Actual playback evidence and limits

GitHub Actions `tv22-stream-audit.yml` tests all public URLs, and uses FFmpeg to require 5 decoded video frames for any tested direct stream. The Nov 10, 2026 runner results confirmed **Hiru, Siyatha TV, Mr Bean, Baby Shark, Lego Channel, BBC Earth** decode five video frames.

**Rupawahini, ITN, Sirasa, Derana, Swarnavahini and Shakthi** returned HTTP 403 from the GitHub runner. This is compatible with geographic/provider restrictions: users in Sri Lanka have directly reported working playback for some of these in our older app, so do not claim the URLs are universally broken.

The ten SLTV worker routes for **10 Cricket, Papare SD/HD, Sony1, Sony Sport, Star Sport 1/2/3, &flix and Warner TV** return JSON advertising Widevine DRM. They are not playable public HLS URLs. This app **does not bypass DRM, copy licence credentials or import the original SLTV authentication**, and cannot guarantee video for these routes. The player explains why protected channels cannot play; it retains the user's requested channel list/order.

## Offline icons

The build script generates exactly 22 images into APK assets, using a verified channel-logo URL when available, and clearly labelled branded-text fallback artwork otherwise. The app icon is a custom teal/white **TV** vector, and the TV launcher banner is also custom.

## Prime Video remote shortcut — Xiaomi TV Box S 3rd Gen

Tested model-specific community documentation identifies **Prime Video: BUTTON_7, scan code 207**, on Xiaomi Bluetooth RC `Vendor_2717_Product_32b9`. The **TV Prime button shortcut** AccessibilityService is optional, disabled by default, and catches only this key to open TV. It does not see or store other on-screen content. Firmware may intercept the button first: **no guarantee without a physical device test**.

On the TV, open the new **TV** app and select the small gear to open the Prime shortcut setup screen. Choose **OPEN ACCESSIBILITY SETTINGS** and explicitly enable **TV Prime button shortcut**. Some Google TV sideload configurations restrict accessibility services. A third-party key mapper or a firmware-specific solution may be needed if Xiaomi intercepts the shortcut.

The stock Prime Video package is often `com.amazon.amazonvideo.livingroom`. Users can **disable** it in Settings > Apps, or use developer/ADB commands after verifying the package name:

```sh
adb shell pm list packages | grep amazon
adb shell pm uninstall --user 0 com.amazon.amazonvideo.livingroom
# Restore the factory system package for this Android user:
adb shell cmd package install-existing --user 0 com.amazon.amazonvideo.livingroom
```

On Windows use `findstr amazon` instead of `grep amazon`. `pm uninstall --user 0` **removes the app for user 0 only**, not its read-only firmware APK. Physical permanent deletion would require privileged firmware/root modification and is discouraged. Disabling/removing Prime does not itself guarantee remapping its dedicated key. **Do not uninstall the Google TV launcher, system UI, remote service or setup wizard** to achieve a Prime shortcut; it can affect remote controls, Wi-Fi, home screen and updates.

## Build and verification

GitHub Actions `.github/workflows/build-tv22.yml` generates icons, compiles the single APK, validates package/manifest and 22 embedded icons, then installs in Android emulator. Emulator ADB tests focus/OK, full-screen player, Up/Down order, Back, pointer tap, and presence of opt-in AccessibilityService. A successful emulator test is not equivalent to 100% verification on the owner's physical Xiaomi box or successful playback of DRM-protected channels.
