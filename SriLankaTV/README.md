# Sri Lanka TV (Android TV) · v0.1 test build

This project is a new, independently written Android TV/Google TV player targeting Xiaomi TV Box S (3rd Gen) and other Android TV devices. It does not copy CyberTV's binary, backend credentials, encryption routines, proprietary DRM keys, or paid stream access.

## Status

- **APK compile:** passed on GitHub Actions run [42414274822](https://github.com/davidamerson/suresh/actions/runs/42414274822).
- **Built-in feeds with confirmed video-frame decoding:** Hiru TV, Rupavahini, Siyatha TV, Shakthi TV.
- **Unverified or missing:** Sirasa TV, TV Derana, Swarnavahini, ITN, TV1, Nethra TV, Vasantham TV, Supreme TV, Ada Derana 24.
- **Real Xiaomi TV Box test:** not yet completed.
- **Signing:** GitHub's debug signing. Future install updates may need an uninstall until a permanent production key is configured.

## TV controls

- D-pad: navigate the channel grid
- OK: open and play highlighted channel
- In player, Up/Down: change channel
- In player, OK: pause or resume
- Back: return to channel grid

## M3U import

From the home page, enter any publicly accessible HTTP(S) M3U playlist URL and choose *Load M3U URL*. The app stores the text locally on the TV and parses up to 1,000 entries, with a 1MB size limit. *Restore starter list* brings back the built-in streams. Do not paste DRM license keys, signed subscriber URLs or account tokens.

## Technical setup

- `namespace` and `applicationId`: `com.suresh.srilankatv`
- Android 6.0+ (`minSdk 23`), Java, Gradle, Android Gradle Plugin
- AndroidX Media3 ExoPlayer + HLS + DASH
- `LEANBACK_LAUNCHER` and no touch requirement
- TV-remote-compatible programmatic UI and full-screen player
- Source under `SriLankaTV/app/`
- One-off APK build workflow: `.github/workflows/build-sri-lanka-tv.yml`

## CyberTV research

A separate line of research confirmed CyberTV 3.1 parses encrypted/obfuscated hexadecimal `link` fields using `SplashScreen.nativeDecryptName`, implemented in native `librtx_rebrand.so`. Playback has separate media authorization and PRO/geo-gating logic. Our project does not depend on that binary or bypass any technical restrictions.

No daily monitoring or scheduled checks are part of this Android TV branch.
