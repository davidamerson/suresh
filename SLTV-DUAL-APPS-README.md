# SLTV Android TV Research Builds (2026-11-09)

Two separately installable Android TV packages built from the same Java/Media3 codebase.

## 1. Independent Android TV app
- Package: `com.suresh.sltv.standalone`
- Displays the 138 complete stream addresses recovered from 174 entries in the SLTV V1.4.8 cache.
- Uses AndroidX Media3/ExoPlayer with HLS/DASH handling and TV remote navigation.
- Search box, channel list, D-pad channel changes.
- Attempts refresh of the channel catalogue from the M3U in **this GitHub branch** at startup; saves a local fallback.
- Not all captured sources are verified, free, redistributable, or accessible outside the original SLTV app.

## 2. SLTV Channel Bridge (experimental)
- Package: `com.suresh.sltv.bridge`
- Shows the entries pointing to the SLTV-hosted `thundercat.workers.dev` service routes from that catalogue.
- Attempts HLS then DASH playback of each route using Android Media3; **does not inherit the original SLTV app's authorization or DRM licences**.
- Includes an Open Original SLTV button that launches `com.sltv.app` if installed.
- **Cannot switch directly to a particular channel inside SLTV**, because no documented deep-link/API for per-channel launching has been verified.
- Stream endpoints may return HTTP 403 and may not work in the bridge; this is not a subscription/DRM bypass.

## What automatic updates actually mean
- The app fetches this branch's `verified_channels.m3u` catalogue and caches it for subsequent launches. Updating **our** catalogue automatically updates the apps.
- For SLTV-hosted URLs, updates made **behind the same stable route** might be reflected automatically if the server permits playback.
- Changes to the original SLTV app's private database are NOT automatically synchronized. No private SLTV authentication, licences, secrets or bundled SLTV player code are included.

## Build
GitHub workflow: `.github/workflows/build-sltv-dual.yml` builds
`assembleStandaloneDebug` and `assembleSltvbridgeDebug`.

These are debug-signed test builds, not Play Store releases. Built successfully in GitHub Actions; no completed end-to-end playback test of these new APKs on a physical TV device has been performed.

Only use sources for which you have permission to access and redistribute.
