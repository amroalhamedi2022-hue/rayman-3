# Rayman 3 — Big Boss handoff

Snapshot 2026-11-28. Documentation only; README/open PR metadata reviewed, not full code audit or fresh CI/device certification.

## Product and constraints
Android ARM64 GBA Readvanced compatibility port, not official product. Preserve original gameplay, animation timing, collision and levels; HD layer later. GPL-3.0 upstream pinned dd8fb6d9ea34decedc4e57d4c5deebc008b8adbd. NO ROMs/game assets/private archives on GitHub.

## Observed development checkpoint
PR #2 d8b22bbac6d23f50019259cd2536f8b35836f787 actual SoLoud MiniAudio/ABI; #1 3a5c84c6462f82910afc79b25efe6c9e01b0b47f component and engine probe.

## Authoritative plans and evidence
README.md; PR #1/#2; owner-private workspace and reference evidence via private register.

## Execution sequence and acceptance
1. Reconcile native ARM64/managed ABI and platform services; verify compiler, renderer, audio, file access and lifecycle. 2. Run engine with authorized owner input locally; compare timing, animation, collision and levels with reference. 3. Touch/gamepad, performance, save compatibility, pause/resume. 4. Device-proven playable build, then optional HD layer; do not redistribute copyrighted assets.

## Build and test
Use branch-specific build probes and exact upstream pin; no ROM required for compile checks. No playable APK claimed from PR metadata.

## Resume procedure
Read AGENTS.md if present, original plans, current default branch, open PR heads/base/ancestry, exact SHA Actions and artifacts; compare against this snapshot. Choose newest compatible cumulative implementation, never overwrite newer changes. Record completed / remaining / blocked with exact commit and test evidence. Work in substantial nonduplicate batches; build at meaningful milestones, not each change. Before publishing, check package/version/signing continuity, licenses, offline/privacy policy and real-device acceptance where applicable. Do not infer completion from PR title or CI alone.

## Private handoff boundary
Owner-only material (keys, passwords, private data, ROMs, personal documents, original restricted assets) stays outside GitHub in access-restricted owner storage. Consult the private Big Boss Drive register. No secret values or private links are included here. If missing, record blocker; do not generate replacement keys for installed apps.

## Cross-project law
A lot of work to reach our goal as perfect as possible and as masterpiece as possible at best time. Master functionality in a masterpiece app. Evidence over claims; optimize time/cost; no duplicated work.
