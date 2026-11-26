"""Global input: mouse buttons (low-level hook) + keyboard shortcuts (RegisterHotKey).

Design (Windows):
* One dedicated native thread owns a WH_MOUSE_LL hook and the registered hotkeys and pumps their
  messages. The Qt GUI thread can be busy (dialogs, painting) without delaying the mouse.
* The hook callback is tiny: mouse moves only increment a counter (used by the watchdog) and are
  passed on at once, so the system cursor never lags and Windows has no reason to drop the hook.
* Keyboard shortcuts use RegisterHotKey: no keyboard hook at all, nothing typed is ever seen,
  virtual-key codes work with any keyboard layout and the shortcuts also work over elevated apps.
* A swallowed button-down always swallows its matching button-up (and vice versa), so other
  programs never see a "stuck" half click.
"""

import ctypes
import os
import threading
import time

from PySide6.QtCore import QObject, Signal

from misbaha import hotkeys, winapi
from misbaha.i18n import tr
from misbaha.paths import log

IS_WIN = winapi.IS_WIN
WM_APP_REHOOK = winapi.WM_APP + 1
WM_APP_HOTKEYS = winapi.WM_APP + 2

DEBOUNCE = 0.06          # s, double reports from worn switches
TILT_REPEAT = 0.30       # s, wheel tilt auto-repeats while held


class InputHook(QObject):
    action = Signal(str)
    button_seen = Signal(str)               # any side/middle/tilt press while `listening` (button test)

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.events = 0                     # incremented for every mouse event the hook sees
        self.error = None                   # mouse hook error (str)
        self.hotkey_errors = []             # [str]
        self._bindings = {}                 # "x1" / "x2" / "middle" / "tilt_left" / "tilt_right" -> action
        self._suppress = True
        self._hk_spec = {}                  # id -> (mods, vk, action)
        self._hk_ids = []
        self._pre_errors = []
        self._swallowed = set()
        self._last_fire = {}
        self._thread = None
        self._tid = 0
        self._hook = None
        self._proc = None
        self._ready = threading.Event()
        self._hk_done = threading.Event()
        self.started_at = 0.0
        self.listening = False
        self.refresh_config()

    # ------------------------------------------------------------------ configuration (GUI thread)
    def refresh_config(self):
        s = self.state.settings
        self._bindings = {"x1": s["x1_action"], "x2": s["x2_action"], "middle": s["mid_action"],
                          "tilt_left": s["tilt_left_action"], "tilt_right": s["tilt_right_action"]}
        self._suppress = bool(s["suppress_side"])

    def _hotkey_table(self):
        s = self.state.settings
        table, errors = {}, []
        if not s.get("hotkeys_enabled"):
            return table, errors
        used = set()
        for key, act in (("hotkey_inc", "inc"), ("hotkey_next", "next"), ("hotkey_undo", "dec")):
            spec = s.get(key) or ""
            if not spec:
                continue
            try:
                mods, vk, _name = hotkeys.parse(spec)
            except ValueError:
                errors.append(tr("تعذّر تسجيل الاختصار %s: %s") % (spec, tr("اختصار غير صالح")))
                continue
            if (mods, vk) in used:
                continue
            used.add((mods, vk))
            table[len(table) + 1] = (mods, vk, act, spec)
        return table, errors

    # ------------------------------------------------------------------ public API (GUI thread)
    def start(self):
        """(Re)start everything. Returns True when mouse capture and all shortcuts are active."""
        self.refresh_config()
        if not IS_WIN or os.environ.get("MISBAHA_NO_INPUT"):      # MISBAHA_NO_INPUT: automated tests
            self.error = tr("غير متاح على هذا النظام")
            self.hotkey_errors = []
            return False
        if self.alive():
            self.reinstall()
            return self.apply_hotkeys()
        self.stop()
        self.error = None
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, name="misbaha-input", daemon=True)
        self._thread.start()
        if not self._ready.wait(3.0):
            self.error = tr("تعذّر تشغيل التقاط أزرار الفأرة: %s") % "timeout"
            log(self.error)
            return False
        ok_hk = self.apply_hotkeys()
        return self.error is None and ok_hk

    def apply_hotkeys(self):
        """Re-register shortcuts from settings (on the input thread). Returns True if all succeeded."""
        table, errors = self._hotkey_table()
        self._hk_spec = table
        self._pre_errors = errors
        if not self.alive():
            self.hotkey_errors = errors
            return not errors
        self._hk_done.clear()
        if self._post(WM_APP_HOTKEYS):
            self._hk_done.wait(2.0)
        return not self.hotkey_errors

    def reinstall(self):
        """Re-install the mouse hook (after sleep, or when Windows silently dropped it)."""
        if self.alive():
            self._post(WM_APP_REHOOK)

    def alive(self):
        t = self._thread
        return t is not None and t.is_alive() and bool(self._tid)

    def stop(self):
        t = self._thread
        if t is not None and t.is_alive() and self._tid:
            self._post(winapi.WM_QUIT)
            t.join(2.0)
        self._thread = None
        self._tid = 0

    def _post(self, msg):
        try:
            return bool(winapi.PostThreadMessageW(self._tid, msg, 0, 0))
        except Exception as e:
            log("PostThreadMessage failed: %s" % e)
            return False

    # ------------------------------------------------------------------ input thread
    def _run(self):
        w = winapi
        msg = w.wintypes.MSG()
        try:
            self._tid = w.GetCurrentThreadId()
            w.PeekMessageW(ctypes.byref(msg), None, 0, 0, w.PM_NOREMOVE)   # create the message queue
            w.SetThreadPriority(w.GetCurrentThread(), w.THREAD_PRIORITY_HIGHEST)
            self._proc = w.HOOKPROC(self._callback)                       # keep a reference!
            self._install()
        except Exception as e:
            self.error = tr("تعذّر تشغيل التقاط أزرار الفأرة: %s") % e
            log(self.error)
        finally:
            self._ready.set()
        try:
            while True:
                r = w.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if r == 0 or r == -1:
                    break
                m = msg.message
                if m == w.WM_HOTKEY:
                    spec = self._hk_spec.get(int(msg.wParam))
                    if spec:
                        self._fire(spec[2], "hk%d" % msg.wParam)
                elif m == WM_APP_REHOOK:
                    self._uninstall()
                    self._install()
                elif m == WM_APP_HOTKEYS:
                    self._register_hotkeys()
                else:
                    w.TranslateMessage(ctypes.byref(msg))
                    w.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            log("input thread error: %s" % e)
        finally:
            self._unregister_hotkeys()
            self._uninstall()
            self._tid = 0

    def _install(self):
        w = winapi
        self._swallowed.clear()
        h = w.SetWindowsHookExW(w.WH_MOUSE_LL, self._proc, w.GetModuleHandleW(None), 0)
        if not h:
            self.error = tr("تعذّر تشغيل التقاط أزرار الفأرة: %s") % ("error %d" % ctypes.get_last_error())
            log(self.error)
            self._hook = None
            return False
        self._hook = h
        self.error = None
        self.started_at = time.monotonic()
        return True

    def _uninstall(self):
        if self._hook:
            try:
                winapi.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
            self._hook = None

    def _register_hotkeys(self):
        self._unregister_hotkeys()
        errors = list(self._pre_errors)
        for hid, (mods, vk, _act, spec) in self._hk_spec.items():
            if winapi.RegisterHotKey(None, hid, mods | hotkeys.MOD_NOREPEAT, vk):
                self._hk_ids.append(hid)
            else:
                errors.append(tr("تعذّر تسجيل الاختصار %s: %s") % (hotkeys.pretty(spec),
                                                                  tr("الاختصار مستخدم من برنامج آخر")))
        self.hotkey_errors = errors
        for e in errors:
            log(e)
        self._hk_done.set()

    def _unregister_hotkeys(self):
        for hid in self._hk_ids:
            try:
                winapi.UnregisterHotKey(None, hid)
            except Exception:
                pass
        self._hk_ids = []

    # The hook callback runs for EVERY mouse event in the session: keep it minimal.
    def _callback(self, n_code, w_param, l_param):
        if n_code == winapi.HC_ACTION:
            self.events += 1
            if w_param != winapi.WM_MOUSEMOVE:
                try:
                    if self._handle(w_param, l_param):
                        return 1                     # swallowed: other programs never see it
                except Exception as e:               # never let an exception escape into Windows
                    log("hook callback error: %s" % e)
        return winapi.CallNextHookEx(None, n_code, w_param, l_param)

    def _handle(self, msg, l_param):
        w = winapi
        if msg in (w.WM_XBUTTONDOWN, w.WM_XBUTTONUP):
            data = w.MSLLHOOKSTRUCT.from_address(l_param)
            xb = (data.mouseData >> 16) & 0xFFFF
            btn = "x1" if xb == 1 else "x2" if xb == 2 else None
            if btn is None:
                return False
            return self._button(btn, msg == w.WM_XBUTTONDOWN)
        if msg in (w.WM_MBUTTONDOWN, w.WM_MBUTTONUP):
            return self._button("middle", msg == w.WM_MBUTTONDOWN)
        if msg == w.WM_MOUSEHWHEEL:
            data = w.MSLLHOOKSTRUCT.from_address(l_param)
            delta = ctypes.c_short((data.mouseData >> 16) & 0xFFFF).value
            if delta == 0:
                return False
            btn = "tilt_right" if delta > 0 else "tilt_left"
            if self.listening:
                self.button_seen.emit(btn)
            act = self._action_for(btn)
            if not act:
                return False
            self._fire(act, btn, TILT_REPEAT)
            return self._suppress
        return False

    def _action_for(self, btn):
        if self.state.paused:                # paused = every button keeps its normal function
            return None
        act = self._bindings.get(btn, "none")
        return None if act == "none" else act

    def _button(self, btn, down):
        if down and self.listening:
            self.button_seen.emit(btn)
        if down:
            act = self._action_for(btn)
            if not act:
                return False
            self._fire(act, btn)
            if self._suppress:
                self._swallowed.add(btn)
                return True
            return False
        # button up: swallow it exactly when its button-down was swallowed
        if btn in self._swallowed:
            self._swallowed.discard(btn)
            return True
        return False

    def _fire(self, act, source, gap=DEBOUNCE):
        now = time.monotonic()
        if now - self._last_fire.get(source, 0.0) < gap:
            return
        self._last_fire[source] = now
        self.action.emit(act)                # queued to the GUI thread automatically

