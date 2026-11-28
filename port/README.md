# Android-first Readvanced integration

Pinned public upstream: dd8fb6d9ea34decedc4e57d4c5deebc008b8adbd.
Only the port code and synthetic tests are tracked here. Never add original ROMs, private artwork, extracted game resources, saves, credentials or archives.
The code is intended to be integrated in compliance with upstream GPL-3.0; see upstream license before distributing a combined build.

- Stage 02: existing touch input bridge, normalized layout, SHA-256 guarded private import; hook retains original input conflict resolution and replay pipeline.
- Stage 03: Android compile probe of six existing engine/game projects, not a rewritten game; removes desktop entry point and content build only for diagnosis. It may expose unresolved platform-specific calls, native libraries or framework dependencies.
- CI runs component checks and compile diagnostic once per meaningful port change, not for documentation edits. No APK release is built.
- Next acceptance gate: resolve compile errors, Android host/lifecycle and storage, native audio and content pipeline; verify on Android with user-supplied ROM locally. Compare core simulation against original GBA runtime before enabling HD. Do not alter approved art or game logic for convenience.

Run locally with Python 3 and .NET 10 Android SDK, or open the Actions tab.
