# Sri Lanka TV: TV remote, mouse and Android phone builds

This branch adds **three APKs** from the same Java / AndroidX Media3 codebase:

1. **SLTV Independent TV** — `com.suresh.sltv.standalone`, landscape TV grid with D-pad/OK remote selection and mouse clicks.
2. **SLTV Channel Bridge TV** — `com.suresh.sltv.bridge`, TV grid, same remote/mouse controls, SLTV-hosted worker routes, and a button to open the original SLTV application if available.
3. **Sri Lanka TV Phone** — `com.suresh.sltv.phone`, portrait-friendly grid with touch/mouse, screen-width responsive channel buttons, fullscreen player controls.

All variants show bottom-of-player buttons for **Previous**, **Play/Pause**, **Next**, **Back**, usable by mouse or touch. The TV versions also support **remote D-pad Up/Down** for channel switching, **OK** to pause/resume, and **Back** to return to the grid.

## Builds and tests

Workflow: `.github/workflows/build-sltv-tv-mouse-phone.yml`

Runs Java 17, Gradle 8.10.2 and Android SDK 35 to compile all three debug APKs. It also installs them in an Android API 30 emulator and tests launching each, a remote OK selection, and a pointer/touch channel-button tap, with Android activity checks and screenshots. The phone app runs portrait; TV apps run landscape.

The 138 observed complete source URLs from SLTV v1.4.8 are bundled with independent TV and phone; the bridge displays 65 SLTV-controlled worker routes. Some URLs may be unavailable, restricted, changed, or not licensed for use outside SLTV, and a successful app launch does not mean every channel produces video. The bridge is not the original SLTV player, does not inherit its login, and cannot switch channels inside SLTV.

Install via Android's standard APK package installer, allowing installation from the chosen file manager if prompted. These are development builds, not Play Store apps. The phone variant is a separate package and can coexist with both TV variants.
