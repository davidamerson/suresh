# CyberTV v3.1 APK streaming research: verified result

**Research date:** 8 November 2026 (Sri Lanka time)

## Source and reproducibility

- Original publicly downloadable APK: `Cyber Tv V3_1.apk`
- Package: `com.cy.cybertv`; version: `3.1`.
- APK SHA-256: `8f779d144ec1dfe1c5e6c2c22df1cc99a9de82ce1c26fc3b1dd2e1fc95799f50`.
- Application installed and launched in an isolated GitHub Actions Android emulator.
- Channel database: `channelss.db`, table `tvlist`. The 13 main local-channel entries use `type=DDDD`.
- Decompilation revealed `SplashScreen.nativeDecryptName(String)` called by the player; implemented in `librtx_rebrand.so`. This is a JNI native decoder, not a simple hex-to-ASCII conversion.

## What actual native execution proved

The native function was invoked on all 13 local-channel encrypted records using a Frida Java hook **within a temporary Android emulator**. No DRM keys, subscription credentials, protected license responses or user account tokens were extracted or published.

All 13 input values were **192 hex characters long**, and all resolved to **HTTPS MPEG-DASH `.mpd`-like addresses** under `tv1.floodsupport.site`. The following channels were observed: Rupavahini, Nethra TV, ITN, Vasantham TV, TV Derana, Swarnavahini, Sirasa TV, Shakthi TV, TV1, Hiru TV, Supreme TV, Ada Derana 24 and Siyatha TV.

An additional Hiru TV entry of type `OOOO` was 32 hex characters and decoded to the literal text `PRO`, not a media address.

Native decoder evidence: [GitHub Actions run 42415260942](https://github.com/davidamerson/suresh/actions/runs/42415260942).

## Independent stream test

A separate run privately passed all 13 decoded addresses to a normal HTTPS client to request the advertised MPD, without DRM licenses, signatures or custom privileged headers.

**Every address returned HTTP 200 with `Content-Type: text/html; charset=UTF-8` and a body of 0 bytes.** None returned a valid XML MPEG-DASH manifest. None produced independently decoded video frames. HTTP 200 alone is **not** proof that a media stream works.

This means the URL paths contain the letters `drm`, but the test did **not** obtain an actual MPD that could be inspected for `ContentProtection`, PSSH or encryption. It would be incorrect to infer either encrypted or unencrypted playable video solely from those URL strings.

Independent media test evidence: [GitHub Actions run 42415974546](https://github.com/davidamerson/suresh/actions/runs/42415974546).

## Technical implication

The observed data flow is:

`channelss.db encrypted hex` -> `nativeDecryptName()` -> `MPEG-DASH-looking URL` -> `StreamUrlParser / Media3 ExoPlayer` -> **additional upstream access conditions may apply**.

CyberTV also contains separate code for signed streaming requests, DRM, geo-gating and PRO features; the exact cause of the empty HTTP response was **not** isolated. An extracted URL is therefore **not** a verified free M3U entry, and the native decoder alone does not create valid independent playback access.

## Independent Android TV app

The separately authored Android TV app is in [SriLankaTV](../SriLankaTV/).

- [Successful APK build and downloadable test artifact](https://github.com/davidamerson/suresh/actions/runs/42414274822)
- [Successful install and TV remote selection emulator smoke test](https://github.com/davidamerson/suresh/actions/runs/42414613267)
- Four public streams with previously confirmed five decoded video frames: Hiru TV, Rupavahini, Siyatha TV and Shakthi TV.
- The app supports TV remote D-pad navigation, full-screen HLS/DASH playback and user-imported M3U playlists.
- **The nine other local channels are not claimed to play.** CyberTV's encrypted links have **not** been copied into the app.
- No scheduled or daily TV verification was created in this project.

This report preserves the results to avoid repeating broken-link tests or claiming that encoded addresses automatically provide free TV.
