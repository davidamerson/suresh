# OpenStream TV & SLTV Companion TV

Two original Android TV apps based on SLTV V1.4.8 channel-cache observations, not SLTV proprietary source code.

## App A: OpenStream TV (independent)
- A TV-remote friendly grid with search and categories.
- AndroidX Media3 ExoPlayer with HLS/DASH support.
- Attempts public-candidate streams without copying SLTV cookies, tokens, licence requests or special headers.
- Flags other streams as restricted, SLTV backend or unresolved.
- Fetches a remote JSON catalogue from the project's public GitHub branch on app startup, with a bundled offline fallback. Updating JSON does not require APK updates.
- Public-candidate does NOT imply reliable playback or redistribution rights.

## App B: SLTV Companion TV
- An independent TV-remote friendly channel selector.
- Requires the original SLTV package (com.sltv.app) to be installed and signed in.
- Optional Android Accessibility Service, enabled explicitly by the device owner, navigates and clicks channel cards in the original SLTV app, which handles its own source links and player.
- No SLTV login credentials, DRM secrets or private API are copied into our companion.
- The original app registers the sltv:// scheme, but a verified per-channel deep link was NOT found. Android UI navigation is therefore an experimental best-effort approach and may need tuning.

## Catalogue
The channel list is a 174-record catalogue from an authorized Android cache analysis. Source statuses are public_candidate, provider_restricted, sltv_backend and unresolved. Full-looking URLs are not proof of legal or working playback. Some URL path identifiers were redacted in the original research evidence and cannot be reconstructed reliably. Premium or protected content stays restricted.

## Build and install
The GitHub Actions workflow builds two debug APKs with Android SDK 35. It imports the redacted researched metadata from a prior authorized diagnostic artifact and uploads the APKs.

Install OpenStream TV APK for independent public-stream experiments. Install SLTV Companion TV APK separately, and ensure the original SLTV app is installed and signed in. To make the companion try selecting a channel, explicitly enable its accessibility service under Android Settings > Accessibility (exact menu depends on the device).

Neither app guarantees 100% working streams or grants access to third-party protected broadcasts.
