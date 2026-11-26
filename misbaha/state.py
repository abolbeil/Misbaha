# -*- coding: utf-8 -*-
"""Persistent state: settings, wird, counters and history (state.json).

* Every value read from disk is validated, so a hand-edited or half-written file can never crash the app.
* Saving is done on a background thread (AppData can live on a slow network share on company PCs),
  written atomically (temp file + replace) and a daily backup state.json.bak is kept.
"""

import datetime
import json
import os
import shutil
import threading
import time

from misbaha import __version__, hotkeys, i18n
from misbaha.data import ACTION_KEYS, CLICK_ACTIONS, DEFAULT_WIRD, LIBRARY, THEMES
from misbaha.paths import STATE_FILE, log

SCHEMA = 2

DEFAULT_SETTINGS = dict(
    # mouse
    x1_action="next",
    x2_action="inc",
    mid_action="none",
    tilt_left_action="none",
    tilt_right_action="none",
    suppress_side=True,              # bound buttons don't reach other apps (no browser "Back")
    # keyboard (RegisterHotKey; virtual keys work with any keyboard layout)
    hotkeys_enabled=True,
    hotkey_inc="<ctrl>+<alt>+<page_up>",
    hotkey_next="<ctrl>+<alt>+<page_down>",
    hotkey_undo="",
    # counting
    wheel_count=False,
    click_action="none",
    daily_reset=True,
    auto_advance=True,
    loop_wird=True,
    # reminders
    remind_enabled=True,
    remind_minutes=30,
    quiet_enabled=False,
    quiet_from="23:00",
    quiet_to="06:00",
    notify_goal=False,               # the widget's gold flash already marks each goal
    # appearance
    font_family="Aref Ruqaa",
    theme="emerald",
    custom_bg="#0B3D91",
    custom_accent="#FFD166",
    arabic_digits=False,
    ui_lang="en",
    opacity=92,
    dim_idle=False,
    idle_opacity=50,
    idle_seconds=10,
    scale=100,
    mini=False,
    click_through=False,
    hide_fullscreen=True,
    # system
    start_with_windows=False,
    update_check=True,               # notify-only GitHub release check, at most once a day
    update_last_check=0,             # epoch seconds
    update_seen="",                  # newest version already announced (announce each version once)
    welcome_done=False,
)

INT_RANGES = dict(opacity=(20, 100), idle_opacity=(50, 100), idle_seconds=(2, 3600), scale=(60, 200),
                  remind_minutes=(1, 600), update_last_check=(0, 2 ** 40))
ACTION_SETTINGS = ("x1_action", "x2_action", "mid_action", "tilt_left_action", "tilt_right_action")
HOTKEY_SETTINGS = ("hotkey_inc", "hotkey_next", "hotkey_undo")
MAX_GOAL = 1000000
MAX_STATE_BYTES = 20 * 1024 * 1024        # a real state file is ~100 KB after years of use


def today_str():
    return datetime.date.today().isoformat()


def valid_hhmm(s, default):
    try:
        return datetime.datetime.strptime(str(s), "%H:%M").strftime("%H:%M")
    except Exception:
        return default


def to_int(v, default, lo=1, hi=MAX_GOAL):
    try:
        if isinstance(v, bool):
            raise TypeError
        return max(lo, min(hi, int(v)))
    except Exception:
        return default


def valid_color(s, default):
    s = str(s or "")
    if len(s) == 7 and s.startswith("#"):
        try:
            int(s[1:], 16)
            return s
        except ValueError:
            pass
    return default


def valid_date(s):
    try:
        datetime.date.fromisoformat(str(s))
        return True
    except Exception:
        return False


# ----------------------------------------------------------------------------------
class Saver:
    """Writes state on a background thread; only the newest snapshot is written."""

    def __init__(self, path, threaded=True):
        self.path = path
        self.threaded = threaded
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._pending = None
        self._stop = False
        self._backup_day = None
        self.last_error = None
        self._thread = None
        if threaded:
            self._thread = threading.Thread(target=self._run, name="misbaha-saver", daemon=True)
            self._thread.start()

    def submit(self, text):
        if not self.threaded:
            self._write(text)
            return
        with self._lock:
            self._pending = text
        self._event.set()

    def close(self, final_text=None, timeout=4.0):
        if not self.threaded:
            if final_text is not None:
                self._write(final_text)
            return
        if final_text is not None:
            with self._lock:
                self._pending = final_text
        self._stop = True
        self._event.set()
        self._thread.join(timeout)

    def _run(self):
        while True:
            self._event.wait()
            self._event.clear()
            with self._lock:
                text, self._pending = self._pending, None
            if text is not None:
                self._write(text)
            if self._stop:
                with self._lock:
                    text, self._pending = self._pending, None
                if text is not None:
                    self._write(text)
                return

    def _backup(self):
        day = today_str()
        if self._backup_day == day:
            return
        self._backup_day = day
        bak = self.path + ".bak"
        try:
            if os.path.exists(self.path) and os.path.getsize(self.path) > 0:
                if not os.path.exists(bak) or \
                        datetime.date.fromtimestamp(os.path.getmtime(bak)).isoformat() != day:
                    shutil.copy2(self.path, bak)
        except Exception as e:
            log("backup failed: %s" % e)

    def _write(self, text):
        self._backup()
        tmp = "%s.%d.tmp" % (self.path, threading.get_ident())
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            for attempt in range(6):          # antivirus / OneDrive can hold the file for a moment
                try:
                    os.replace(tmp, self.path)
                    self.last_error = None
                    return
                except PermissionError:
                    time.sleep(0.15 * (attempt + 1))
            os.replace(tmp, self.path)
            self.last_error = None
        except Exception as e:
            self.last_error = str(e)
            log("save failed: %s" % e)
            try:
                os.remove(tmp)
            except OSError:
                pass


# ----------------------------------------------------------------------------------
class State:
    def __init__(self, path=STATE_FILE, background_save=True):
        self.path = path
        self.settings = dict(DEFAULT_SETTINGS)
        i18n.SETTINGS = self.settings            # tr() / fmt() read the live settings
        self.custom = []                         # user adhkar
        self.wird = [dict(id=i, goal=g) for i, g in DEFAULT_WIRD]
        self.index = 0
        self.counts = {}                         # id -> count for the current day
        self.history = {}                        # "YYYY-MM-DD" -> {id: n}
        self.day = today_str()
        self.pos = None
        self.paused = False
        self.first_run = not os.path.exists(path)
        self._items = {}
        self._saver = Saver(path, threaded=background_save)
        self._clean_temp_files()
        self.load()
        self.check_new_day()

    # --- library helpers ---
    def all_items(self):
        return LIBRARY + self.custom

    def _reindex(self):
        self._items = {it["id"]: it for it in self.all_items()}

    def item(self, did):
        it = self._items.get(did)
        if it is None and did is not None:
            self._reindex()
            it = self._items.get(did)
        return it

    def clean_wird(self):
        self._reindex()
        seen, out = set(), []
        for w in self.wird if isinstance(self.wird, list) else []:
            did = w.get("id") if isinstance(w, dict) else None
            if did in seen or not self.item(did):
                continue
            seen.add(did)
            out.append(dict(id=did, goal=to_int(w.get("goal"), self.item(did).get("goal", 100))))
        self.wird = out or [dict(id=i, goal=g) for i, g in DEFAULT_WIRD]
        self.index = max(0, min(to_int(self.index, 0, 0), len(self.wird) - 1))

    # --- persistence ---
    def _clean_temp_files(self):
        """Remove temp files left behind if the app was killed in the middle of a save."""
        folder, base = os.path.split(self.path)
        try:
            for fn in os.listdir(folder or "."):
                if fn.startswith(base + ".") and fn.endswith(".tmp"):
                    p = os.path.join(folder, fn)
                    if time.time() - os.path.getmtime(p) > 60:
                        os.remove(p)
        except OSError as e:
            log("temp cleanup failed: %s" % e)

    def load(self):
        d = self._read(self.path)
        if d is None and os.path.exists(self.path + ".bak"):
            d = self._read(self.path + ".bak")
            if d is not None:
                log("state restored from backup")
        if d is None:
            self.clean_wird()
            return
        self._apply(d)

    def _read(self, path):
        try:
            if os.path.getsize(path) > MAX_STATE_BYTES:
                raise ValueError("state file is unreasonably large (%d bytes)" % os.path.getsize(path))
            with open(path, "r", encoding="utf-8-sig") as f:
                d = json.load(f)
            if not isinstance(d, dict):
                raise ValueError("state root is not an object")
            return d
        except FileNotFoundError:
            return None
        except Exception as e:
            log("state load failed (%s): %s" % (os.path.basename(path), e))
            if path == self.path:
                try:   # keep the broken file for inspection, start from the backup / defaults
                    os.replace(path, "%s.broken-%s" % (path, time.strftime("%Y%m%d-%H%M%S")))
                except OSError:
                    pass
            return None

    def _apply(self, d):
        s = d.get("settings")
        if isinstance(s, dict):
            for k, v in s.items():
                if k in DEFAULT_SETTINGS:
                    self.settings[k] = v
        self._sanitize_settings()

        custom = []
        for c in d.get("custom", []) if isinstance(d.get("custom"), list) else []:
            if isinstance(c, dict) and isinstance(c.get("id"), str) and isinstance(c.get("text"), str) \
                    and c["text"].strip():
                custom.append(dict(id=c["id"], cat="custom", text=c["text"].strip(),
                                   goal=to_int(c.get("goal"), 100), fadl=str(c.get("fadl") or ""),
                                   src=str(c.get("src") or "")))
        self.custom = custom
        self.wird = d.get("wird") if isinstance(d.get("wird"), list) else self.wird
        self.index = d.get("index", 0)
        counts = d.get("counts")
        self.counts = {str(k): to_int(v, 0, 0) for k, v in counts.items()} if isinstance(counts, dict) else {}
        hist = d.get("history")
        self.history = {}
        if isinstance(hist, dict):
            for day, per in hist.items():
                if valid_date(day) and isinstance(per, dict):
                    clean = {str(k): to_int(v, 0, 0) for k, v in per.items()}
                    if clean:
                        self.history[day] = clean
        self.day = d.get("day") if valid_date(d.get("day")) else today_str()
        pos = d.get("pos")
        if isinstance(pos, list) and len(pos) == 2 and all(isinstance(v, (int, float)) for v in pos):
            self.pos = [int(pos[0]), int(pos[1])]
        self.clean_wird()

    def _sanitize_settings(self):
        s = self.settings
        for k, default in DEFAULT_SETTINGS.items():
            v = s.get(k)
            if isinstance(default, bool):
                s[k] = v if isinstance(v, bool) else bool(v) if isinstance(v, int) else default
            elif isinstance(default, int):
                lo, hi = INT_RANGES.get(k, (0, MAX_GOAL))
                s[k] = to_int(v, default, lo, hi)
            elif isinstance(default, str):
                s[k] = v if isinstance(v, str) else default
        for k in ACTION_SETTINGS:
            if s[k] not in ACTION_KEYS:
                s[k] = DEFAULT_SETTINGS[k]
        if s["click_action"] not in {k for k, _ in CLICK_ACTIONS}:
            s["click_action"] = "none"
        if s["ui_lang"] not in i18n.TABLES:
            s["ui_lang"] = "en"
        if s["theme"] not in THEMES:
            s["theme"] = "emerald"
        s["custom_bg"] = valid_color(s["custom_bg"], DEFAULT_SETTINGS["custom_bg"])
        s["custom_accent"] = valid_color(s["custom_accent"], DEFAULT_SETTINGS["custom_accent"])
        s["quiet_from"] = valid_hhmm(s["quiet_from"], "23:00")
        s["quiet_to"] = valid_hhmm(s["quiet_to"], "06:00")
        if s["hotkey_next"] == "<ctrl>+<alt>+n":         # very old default: failed with the Arabic layout
            s["hotkey_next"] = DEFAULT_SETTINGS["hotkey_next"]
        for k in HOTKEY_SETTINGS:
            try:
                s[k] = hotkeys.normalize(s[k])
            except ValueError:
                s[k] = DEFAULT_SETTINGS[k]

    def snapshot(self):
        return json.dumps(dict(app="Misbaha", version=__version__, schema=SCHEMA, settings=self.settings,
                               custom=self.custom, wird=self.wird, index=self.index, counts=self.counts,
                               history=self.history, day=self.day, pos=self.pos),
                          ensure_ascii=False, separators=(",", ":"))

    def save(self):
        self._saver.submit(self.snapshot())

    def close(self):
        """Final, blocking save (on exit)."""
        self._saver.close(self.snapshot())

    @property
    def save_error(self):
        return self._saver.last_error

    def check_new_day(self):
        t = today_str()
        if t != self.day:
            self.day = t
            if self.settings.get("daily_reset", True):
                self.counts = {}
                self.index = 0
            return True
        return False

    # --- current ---
    def current(self):
        if not self.wird or not (0 <= self.index < len(self.wird)):
            self.clean_wird()
        w = self.wird[self.index]
        it = self.item(w["id"])
        if it is None:                           # custom item deleted meanwhile
            self.clean_wird()
            w = self.wird[self.index]
            it = self.item(w["id"])
        return w, it

    def add_history(self, did, n):
        day = self.history.setdefault(today_str(), {})
        day[did] = max(0, day.get(did, 0) + n)

    def day_total(self, d):
        return sum(self.history.get(d, {}).values())

    def today_total(self):
        return self.day_total(today_str())

    def all_time_total(self):
        return sum(sum(v.values()) for v in self.history.values())

    def streak(self):
        s = 0
        d = datetime.date.today()
        if self.day_total(d.isoformat()) == 0:      # today not started yet: count up to yesterday
            d -= datetime.timedelta(days=1)
        while self.day_total(d.isoformat()) > 0:
            s += 1
            d -= datetime.timedelta(days=1)
        return s

