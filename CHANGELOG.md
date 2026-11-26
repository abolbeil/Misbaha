# Changelog

All notable changes to this project are documented here. Versions follow [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-11-26

First public open-source release. It consolidates the private builds 1.0 – 1.6 into a reviewed, stable codebase.
Existing `%APPDATA%\Misbaha\state.json` files from those builds are loaded automatically (settings, wird, counters and history are kept).

### Input capture — rewritten
- **No more pynput.** The mouse hook is a native `WH_MOUSE_LL` hook on a dedicated high-priority thread with a minimal callback: mouse moves are passed on at once, so the cursor never lags and Windows no longer drops the hook under load.
- **Keyboard shortcuts use `RegisterHotKey`** instead of a global keyboard hook: zero typing overhead, nothing typed is ever seen, layout-independent, and they work over elevated (administrator) apps. Conflicts with other programs are reported by name.
- **No stuck buttons:** a swallowed button-down always swallows its matching button-up (even if you pause in between).
- **New bindable inputs:** middle (wheel) button and wheel tilt left / right (off by default; tilt auto-repeat is throttled).
- **Watchdog fixed:** builds ≤ 1.6 compared a 30 s cursor window with a 25 s event window, so they restarted a healthy hook many times a day (`hook restarted by watchdog (alive=True, stale=True)`). The new check compares the same 2 s window twice in a row, reinstalls instantly without a capture gap, and recognises elevated foreground apps (shows a one-time hint instead of restarting).
- Re-installs capture automatically after sleep / resume.
- *Restart as administrator* menu item.

### Overlay, transparency and click-through
- Click-through is toggled with native window styles — no window re-creation, flicker or lost top-most.
- **Hold Ctrl over the widget** to use it while click-through is on.
- Opacity is painted by the widget instead of layered-window opacity (fixes black/invisible widget glitches after display changes).
- Top-most is only re-asserted when it was actually lost or when you count, so the widget no longer jumps over other apps' menus.
- Optional: hide over full-screen apps (videos, slideshows); maximised windows such as Revit are not affected.
- Widget is brought back on-screen when a monitor is unplugged or resolution changes.

### Performance and stability
- Saving runs on a background thread (company PCs often keep `%APPDATA%` on a network share), atomically, with retries and a daily `state.json.bak`. A corrupt file is quarantined and the backup is used.
- Every setting is type- and range-checked on load.
- Animation timer runs only while something animates; idle-dim check runs only when enabled; font list is cached.
- Freeze detector writes all thread stacks to `crash.log` if the UI thread ever stops responding; native crashes are logged via `faulthandler`; logs rotate at 512 KB.
- Reminders are skipped while you are away from the PC or a full-screen app is in front.
- Spin boxes, sliders and combo boxes in dialogs ignore the mouse wheel unless focused (no accidental goal changes while scrolling).

### Settings
- Shortcut recorder: click the field and press the keys.
- New tabs: *Counting* and *Widget*; *System* shows live capture status and opens the data folder.
- Portable mode: a `misbaha-data` folder next to the exe keeps all data there.

### Pre-release audit fixes
- Single-instance pipe is restricted to the current Windows user.
- Dhikr text is escaped in tooltips; user text is always shown as plain text.
- *Restart as administrator* asks first, explains the safer alternative and keeps the same data folder even under another admin account (`--data-dir`).
- State files over 20 MB are refused (backup used); stale temp files from an interrupted save are cleaned at start-up.
- Clicking the tray icon always shows the widget; hiding is a menu choice and says how to bring it back.
- *Undo reset* in the menu for 30 s after *Reset current dhikr*.
- Accessibility: hint text 5.3:1, Ivory theme accent 5.6:1, idle opacity at least 50%, screen-reader name and description on the widget.
- Per-dhikr goal notification off by default (the widget flash marks each goal).
- Compact state file, saved at most every 3 s while counting; slow animations run at 15 fps.
- Mini mode: the opacity label no longer covers the number.
- Each bundled font now ships with its own OFL copyright notice.
- CI: actions pinned to commit SHAs, least-privilege permissions, hash-locked build dependencies, SHA-256 published with each release, Dependabot; `SECURITY.md` added.

### Completing the audit
- **Update notice (notify-only):** once a day, checks the GitHub releases API of the repository the build came from, validates the answer (no drafts or pre-releases, strictly newer, release page on that repository only, no redirects, size-capped) and offers to open the download page. Never downloads or installs. Toggle and *Check now* in Settings → System.
- **Welcome / button test:** first run (and menu → *Test mouse buttons*) shows live which side buttons reach Misbaha, the keyboard shortcuts, and what to do if nothing is detected.
- **Edit custom adhkar** in the library; the id, history and wird position are kept.
- About box, README and SECURITY.md describe the update check honestly.
- Fixed: "Help & tips" showed as "Help _tips" (Qt read `&` as a shortcut marker).
- Optional code signing in CI (Azure Artifact Signing), dormant until configured — see `docs/SIGNING.md`.
- New screenshots of the current interface.
- Mouse hook stays in Python by decision: measured at 0.18 µs per event, a native DLL would add an untestable, system-wide failure mode for no visible gain.

### Project
- Split into a package (`misbaha/`), headless unit tests, GitHub Actions build, MIT license.

## Private builds (before open-sourcing)

- **1.6** — auto-dim when idle, Ctrl + wheel opacity, opacity menu, left-click action setting, wheel counting off by default, help & about dialogs, second launch shows the running widget, watchdog back-off.
- **1.2** — English interface and Latin digits by default.
- **1.1** — themes and custom colours, click-through, hook watchdog, keep-on-top, immediate auto-advance, layout-independent default shortcut, pause releases the side buttons, state validation, error log, and 21 other fixes.
- **1.0** — first version.
