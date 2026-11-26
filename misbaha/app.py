# -*- coding: utf-8 -*-
"""Application controller: tray icon, menu, counting logic, watchdogs, reminders, start-up."""

import datetime
import os
import random
import sys
import threading
import time

from PySide6.QtCore import QLockFile, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QCursor, QDesktopServices
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from misbaha import APP_ID, APP_NAME, __version__, winapi
from misbaha.data import OPACITY_STEPS, REMINDERS, THEMES
from misbaha.dialogs import AboutDialog, HelpDialog, LibraryDialog, SettingsDialog, StatsDialog, WelcomeDialog
from misbaha.i18n import ADMIN_HINT_AR, APP_TITLE, ELEVATE_AR, fmt, tr, ui_dir
from misbaha.input_hook import InputHook
from misbaha.paths import DATA_DIR, app_dir, dump_all_threads, install_error_handlers, log
from misbaha.state import State
from misbaha.ui import get_theme, load_fonts, make_icon, ui_font
from misbaha.update import UpdateChecker
from misbaha.widget import CounterWidget

WATCH_MS = 2000            # hook health / overlay check interval
AWAY_SECONDS = 300         # no reminders when the user has been away this long
UNDO_SECONDS = 30          # "Undo reset" stays in the menu this long
FREEZE_SECONDS = 20        # GUI thread unresponsive this long -> stack dump in crash.log


class FreezeDetector:
    """Background thread: if the GUI thread stops ticking, dump every thread's stack to crash.log."""

    def __init__(self):
        self.beat = time.monotonic()
        self._stop = threading.Event()
        self._dumped = False
        threading.Thread(target=self._run, name="misbaha-freeze", daemon=True).start()

    def tick(self):
        self.beat = time.monotonic()
        self._dumped = False

    def stop(self):
        self._stop.set()

    def _run(self):
        last = time.monotonic()
        while not self._stop.wait(5):
            now = time.monotonic()
            if now - last > 15:                 # we were asleep (PC suspended): not a freeze
                self.beat = now
            last = now
            if not self._dumped and now - self.beat > FREEZE_SECONDS:
                self._dumped = True
                log("GUI thread unresponsive for %ds - stacks written to crash.log" % int(now - self.beat))
                dump_all_threads("GUI thread unresponsive")


class MisbahaApp(QObject):
    def __init__(self, qapp):
        super().__init__()
        self.qapp = qapp
        self.state = State()
        self.last_count_time = time.time()
        self.last_remind_time = time.time()
        self._dialogs = {}
        self._last_cursor = QCursor.pos()
        self._last_events = 0
        self._suspect = 0
        self._last_watch = time.monotonic()
        self._last_rehook_log = 0.0
        self._uipi_seconds = 0
        self._admin_hint_shown = False
        self._fs_hidden = False
        self._fs_count = 0
        self._fs_override = False      # user explicitly showed the widget over a full-screen app
        self._user_hidden = False
        self._save_err_shown = False
        self._undo_reset = None         # (dhikr id, previous count, time) for "Undo reset"
        self._update = None              # (version, release page) when a newer release exists
        self._update_label = None
        self.updater = UpdateChecker()
        self.updater.found.connect(self._update_found)
        self.updater.done.connect(self._update_done)
        self.freeze = FreezeDetector()

        self.widget = CounterWidget(self)
        self.widget.show()

        self.tray = QSystemTrayIcon(make_icon(self.widget.th), self)
        self._menu = self._build_menu()
        self.tray.setContextMenu(self._menu)
        self.tray.activated.connect(self._tray_click)
        self.tray.show()
        self._update_tooltip()

        self.hook = InputHook(self.state)
        self.hook.action.connect(self.do_action)

        self.save_timer = QTimer(self)          # batch disk writes while counting fast
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_now)

        self.minute = QTimer(self)
        self.minute.setTimerType(Qt.VeryCoarseTimer)
        self.minute.timeout.connect(self._every_minute)
        self.minute.start(60 * 1000)

        self.watch = QTimer(self)
        self.watch.timeout.connect(self._watchdog)
        self.watch.start(WATCH_MS)

        for sc in qapp.screens():
            sc.availableGeometryChanged.connect(self._screens_changed)
        qapp.screenAdded.connect(self._screen_added)
        qapp.screenRemoved.connect(self._screens_changed)
        qapp.aboutToQuit.connect(self._on_quit)
        qapp.commitDataRequest.connect(lambda *a: self.state.save())

        self.restart_hook(notify_ok=False)
        if self.state.settings.get("start_with_windows"):
            set_startup(True)                    # keep the registry path right if the program moved
        if not self.state.settings.get("welcome_done"):
            if self.state.first_run:
                self.state.save()
            QTimer.singleShot(1200, self.open_welcome)
        QTimer.singleShot(90 * 1000, self._maybe_check_update)

    # ------------------------------------------------------------------ input hook
    def restart_hook(self, notify_ok=True):
        ok = self.hook.start()
        errors = ([self.hook.error] if self.hook.error and winapi.IS_WIN else []) + self.hook.hotkey_errors
        if errors:
            self.notify(tr("تنبيه"), "\n".join(errors))
        elif notify_ok and ok:
            self.notify(tr(APP_TITLE), tr("تمت إعادة تشغيل التقاط أزرار الفأرة."))
        self._last_events = self.hook.events
        self._suspect = 0

    def status_text(self):
        if not winapi.IS_WIN:
            mouse = tr("غير متاح على هذا النظام")
        else:
            mouse = tr("يعمل") if self.hook.alive() and not self.hook.error else (self.hook.error or tr("متوقف"))
        if not winapi.IS_WIN:
            keys = tr("غير متاح على هذا النظام")
        elif not self.state.settings.get("hotkeys_enabled"):
            keys = tr("معطّلة")
        else:
            keys = "\n".join(self.hook.hotkey_errors) or tr("مسجّلة")
        return "\n".join([tr("التقاط أزرار الفأرة: %s") % mouse, tr("الاختصارات: %s") % keys,
                          tr("يعمل كمسؤول: %s") % (tr("نعم") if winapi.self_elevated() else tr("لا"))])

    def _watchdog(self):
        now = time.monotonic()
        gap = now - self._last_watch
        self._last_watch = now
        self.freeze.tick()

        if gap > 15:
            # the PC was asleep / the session was locked: Windows may have dropped the hook
            log("resumed after %ds - reinstalling input capture" % int(gap))
            if self.state.check_new_day():
                self.refresh()
            self.hook.start()
            self._last_events = self.hook.events
            self._last_cursor = QCursor.pos()
            return

        dialogs_open = any(d.isVisible() for d in self._dialogs.values())
        if not dialogs_open and not QApplication.activePopupWidget():
            self.widget.ensure_overlay()
        self._fullscreen_check()

        if not winapi.IS_WIN:
            return
        if not self.hook.alive():
            log("input thread not running - restarting")
            self.hook.start()
            self._last_events = self.hook.events
            return

        # Hook health: the cursor moved but the hook saw no event at all since the last check
        # -> Windows silently removed it (sleep, lock, heavy load) -> reinstall (instant, no gap).
        cur = QCursor.pos()
        moved = cur != self._last_cursor
        self._last_cursor = cur
        events = self.hook.events
        silent = moved and events == self._last_events
        self._last_events = events
        if not silent:
            self._suspect = 0
            return
        if winapi.foreground_blocked_by_uipi():
            # an elevated app is in front: Windows hides its mouse input from us. Not a dead hook.
            self._uipi_seconds += WATCH_MS // 1000
            if self._uipi_seconds >= 10 and not self._admin_hint_shown:
                self._admin_hint_shown = True
                self.notify(tr(APP_TITLE), tr(ADMIN_HINT_AR))
            return
        self._suspect += 1
        if self._suspect >= 2:                       # two checks in a row: really silent
            self._suspect = 0
            if time.time() - self._last_rehook_log > 600:
                self._last_rehook_log = time.time()
                log("mouse hook was silent while the cursor moved - reinstalled")
            self.hook.reinstall()

    def _fullscreen_check(self):
        want_hidden = bool(self.state.settings.get("hide_fullscreen")) and \
            winapi.foreground_is_fullscreen(os.getpid())
        self._fs_count = self._fs_count + 1 if want_hidden else 0
        if not want_hidden:
            self._fs_override = False
        if self._fs_count >= 2 and not self._fs_hidden and not self._fs_override and self.widget.isVisible():
            self._fs_hidden = True
            self.widget.hide()
        elif not want_hidden and self._fs_hidden:
            self._fs_hidden = False
            if not self._user_hidden:
                self.widget.show()

    # ------------------------------------------------------------------ screens
    def _screen_added(self, sc):
        sc.availableGeometryChanged.connect(self._screens_changed)
        self._screens_changed()

    def _screens_changed(self, *a):
        QTimer.singleShot(800, self.widget.reposition)

    # ------------------------------------------------------------------ menu (one persistent menu: tray + widget)
    def _build_menu(self):
        m = QMenu()
        m.setLayoutDirection(ui_dir())
        m.setFont(ui_font(11))

        def add(text, fn, checkable=False, menu=m):
            a = QAction(text.replace("&", "&&"), menu)      # "&" would become a shortcut underline
            a.setCheckable(checkable)
            a.triggered.connect(fn)
            menu.addAction(a)
            return a

        add(tr("الذكر التالي  ⟵"), lambda: self.do_action("next"))
        add(tr("الذكر السابق  ⟶"), lambda: self.do_action("prev"))
        add(tr("إنقاص واحد  −١"), lambda: self.do_action("dec"))
        add(tr("تصفير الذكر الحالي"), self.reset_current)
        self.a_undo_reset = add(tr("تراجع عن التصفير"), self.undo_reset)
        add(tr("تصفير الورد كله…"), self.reset_all)
        m.addSeparator()
        add(tr("📿  مكتبة الأذكار / وردي…"), self.open_library)
        add(tr("📊  إحصائياتي…"), self.open_stats)
        add(tr("⚙  الإعدادات…"), self.open_settings)
        add(tr("❓  مساعدة ونصائح…"), self.open_help)
        add(tr("🖱  اختبار أزرار الفأرة…"), self.open_welcome)
        add(tr("ℹ  عن المِسبحة…"), self.open_about)
        self.theme_menu = m.addMenu(tr("🎨  لون الواجهة"))
        self.theme_menu.setLayoutDirection(ui_dir())
        tg = QActionGroup(self.theme_menu)
        for key, t in THEMES.items():
            if key == "custom":
                continue
            a = add(tr(t[0]), lambda _c=False, k=key: self.set_theme(k), True, self.theme_menu)
            a.setData(key)
            tg.addAction(a)
        self.opacity_menu = m.addMenu(tr("🔅  الشفافية"))
        self.opacity_menu.setLayoutDirection(ui_dir())
        og = QActionGroup(self.opacity_menu)
        for v in OPACITY_STEPS:
            a = add(fmt(v) + "%", lambda _c=False, val=v: self.set_opacity(val), True, self.opacity_menu)
            a.setData(v)
            og.addAction(a)
        m.addSeparator()
        self.a_pause = add(tr("إيقاف العدّ مؤقتًا"), self.toggle_pause, True)
        self.a_mini = add(tr("الوضع المصغّر"), self.toggle_mini, True)
        self.a_click = add(tr("تمرير النقرات عبر الودجت"), self.toggle_click_through, True)
        self.a_show = add(tr("إخفاء الودجت"), self.toggle_visible)
        add(tr("إعادة تشغيل التقاط أزرار الفأرة"), lambda: self.restart_hook(True))
        self.a_admin = add(tr("إعادة التشغيل كمسؤول"), self.restart_as_admin)
        m.addSeparator()
        self.a_update = add("", self.open_update_page)
        self.a_update.setVisible(False)
        add(tr("خروج"), self.quit)
        m.aboutToShow.connect(self._sync_menu)
        return m

    def _sync_menu(self):
        s = self.state.settings
        self.a_pause.setChecked(self.state.paused)
        self.a_update.setVisible(bool(self._update))
        if self._update:
            self.a_update.setText((tr("⬆  إصدار جديد متاح: %s — فتح صفحة التنزيل") % self._update[0]).replace("&", "&&"))
        u = self._undo_reset
        self.a_undo_reset.setVisible(bool(u) and time.monotonic() - u[2] <= UNDO_SECONDS)
        self.a_mini.setChecked(bool(s.get("mini")))
        self.a_click.setChecked(bool(s.get("click_through")))
        self.a_show.setText(tr("إخفاء الودجت") if self.widget.isVisible() else tr("إظهار الودجت"))
        self.a_admin.setVisible(winapi.IS_WIN and not winapi.self_elevated())
        for a in self.theme_menu.actions():
            a.setChecked(a.data() == s.get("theme"))
        for a in self.opacity_menu.actions():
            a.setChecked(a.data() == s.get("opacity"))

    def show_menu(self, pos):
        self._menu.popup(pos)

    def _tray_click(self, reason):
        # a click on the tray icon always brings the widget back; hiding is a menu choice
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.widget.isVisible():
                self.widget.ensure_overlay(raise_now=True)
                self.widget.wake()
            else:
                self.toggle_visible()

    # ------------------------------------------------------------------ core counting
    def do_action(self, act):
        st = self.state
        if st.check_new_day():
            self.refresh()
        if st.paused and act in ("inc", "dec"):
            return
        w, it = st.current()
        did = w["id"]
        goal = int(w["goal"])
        if act == "inc":
            n = st.counts.get(did, 0) + 1
            st.counts[did] = n
            st.add_history(did, 1)
            self.last_count_time = time.time()
            self.widget.bump()
            self.widget.ensure_overlay(raise_now=True)     # counting = you want to see it
            if n == goal:
                self.goal_reached(w, it)
        elif act == "dec":
            if st.counts.get(did, 0) > 0:
                st.counts[did] -= 1
                st.add_history(did, -1)
            self.widget.wake()
        elif act == "next":
            st.index = (st.index + 1) % len(st.wird)
            self.widget.wake()
        elif act == "prev":
            st.index = (st.index - 1) % len(st.wird)
            self.widget.wake()
        self.widget.update()
        self.schedule_save()

    def schedule_save(self):
        if not self.save_timer.isActive():
            self.save_timer.start(3000)

    def _save_now(self):
        self.state.save()
        self._update_tooltip()

    def _update_tooltip(self):
        try:
            w, it = self.state.current()
            cnt = self.state.counts.get(w["id"], 0)
            self.tray.setToolTip("%s — %s / %s" % (tr(APP_TITLE), fmt(cnt), fmt(w["goal"])))
            self.widget.setAccessibleDescription("%s — %s / %s" % (it["text"], cnt, w["goal"]))
        except Exception:
            self.tray.setToolTip(tr(APP_TITLE))

    def goal_reached(self, w, it):
        st = self.state
        self.widget.celebrate()
        if all(st.counts.get(x["id"], 0) >= int(x["goal"]) for x in st.wird):
            self.notify(tr("ما شاء الله تبارك الله 🌿"), tr("أتممتَ وردك كاملًا، تقبّل الله منك."))
            if st.settings.get("loop_wird"):
                self._restart_wird()          # immediately, so the next press isn't lost
            return
        if st.settings.get("notify_goal"):
            self.notify(tr("تقبّل الله"), tr("أتممت «%s» %s مرة") % (self._short(it["text"]), fmt(w["goal"])))
        if st.settings.get("auto_advance"):
            self._advance_to_unfinished()     # presses right after the goal go to the next dhikr

    def _advance_to_unfinished(self):
        st = self.state
        n = len(st.wird)
        for k in range(1, n + 1):
            i = (st.index + k) % n
            x = st.wird[i]
            if st.counts.get(x["id"], 0) < int(x["goal"]):
                st.index = i
                break
        self.widget.update()

    def _restart_wird(self):
        st = self.state
        for x in st.wird:
            st.counts[x["id"]] = 0
        st.index = 0
        self.refresh()

    @staticmethod
    def _short(t, n=40):
        return t if len(t) <= n else t[:n] + "…"

    def reset_current(self):
        w, _it = self.state.current()
        prev = self.state.counts.get(w["id"], 0)
        if prev:
            self._undo_reset = (w["id"], prev, time.monotonic())
        self.state.counts[w["id"]] = 0
        self.refresh()

    def undo_reset(self):
        u = self._undo_reset
        self._undo_reset = None
        if u and time.monotonic() - u[2] <= UNDO_SECONDS:
            self.state.counts[u[0]] = u[1]
            self.refresh()

    def reset_all(self):
        box = QMessageBox(QMessageBox.Question, tr(APP_TITLE), tr("تصفير عدّادات الورد كله؟\n(الإحصائيات لا تُحذف)"),
                          QMessageBox.Yes | QMessageBox.No)
        box.setWindowFlag(Qt.WindowStaysOnTopHint)
        box.setLayoutDirection(ui_dir())
        if box.exec() == QMessageBox.Yes:
            self._restart_wird()

    # ------------------------------------------------------------------ toggles
    def toggle_pause(self):
        self.state.paused = not self.state.paused
        self.refresh()

    def toggle_mini(self):
        self.state.settings["mini"] = not self.state.settings.get("mini")
        self.widget.apply_settings()
        self.state.save()

    def toggle_click_through(self):
        self.state.settings["click_through"] = not self.state.settings.get("click_through")
        self.widget.apply_settings()
        self.state.save()
        if self.state.settings["click_through"]:
            self.notify(tr(APP_TITLE), tr("الودجت الآن لا يعترض الفأرة. اضغط Ctrl فوقه لاستخدامه، أو استخدم أيقونة شريط المهام."))

    def set_opacity(self, value):
        self.state.settings["opacity"] = int(value)
        self.widget.last_active = time.monotonic()
        self.widget.refresh_opacity(instant=True)
        self.widget.show_osd(tr("الشفافية: %s%%") % fmt(value))
        self.state.save()

    def set_theme(self, key):
        self.state.settings["theme"] = key
        self.state.save()
        self.apply_theme()

    def apply_theme(self):
        self.widget.apply_settings()
        icon = make_icon(self.widget.th)
        self.tray.setIcon(icon)
        self.qapp.setWindowIcon(icon)

    def apply_language(self):
        self.qapp.setLayoutDirection(ui_dir())
        old = self._menu
        self._menu = self._build_menu()
        self.tray.setContextMenu(self._menu)
        old.deleteLater()
        self._update_tooltip()
        self.widget.apply_settings()

    def settings_changed(self):
        """Called by the settings dialog after it wrote new values."""
        s = self.state.settings
        set_startup(s["start_with_windows"])
        self.state.save()
        self.restart_hook(notify_ok=False)
        self.apply_theme()
        self.apply_language()
        if not s.get("hide_fullscreen") and self._fs_hidden:
            self._fs_hidden = False
            if not self._user_hidden:
                self.widget.show()

    def toggle_visible(self):
        if self.widget.isVisible():
            self._user_hidden = True
            self.widget.hide()
            self.notify(tr(APP_TITLE), tr("المِسبحة ما زالت تعمل — انقر أيقونة شريط المهام لإظهارها."))
        else:
            self._user_hidden = False
            if self._fs_hidden or self._fs_count:
                self._fs_override = True
            self._fs_hidden = False
            self.widget.show()
            self.widget.wake()

    def show_from_second_launch(self):
        self._user_hidden = False
        self._fs_hidden = False
        self.widget.show()
        self.widget.ensure_overlay(raise_now=True)
        self.widget.wake()
        self.notify(tr(APP_TITLE), tr("المِسبحة تعمل بالفعل — تم إظهار الودجت."))

    def restart_as_admin(self):
        box = QMessageBox(QMessageBox.Question, tr(APP_TITLE), tr(ELEVATE_AR), QMessageBox.Yes | QMessageBox.No)
        box.setWindowFlag(Qt.WindowStaysOnTopHint)
        box.setLayoutDirection(ui_dir())
        if box.exec() != QMessageBox.Yes:
            return
        # same data folder even if the administrator is a different Windows account
        extra = '--wait-for-lock "--data-dir=%s"' % DATA_DIR
        if getattr(sys, "frozen", False):
            exe, params = sys.executable, extra
        else:
            exe = sys.executable
            pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
            exe = pyw if os.path.exists(pyw) else exe
            params = '"%s" %s' % (launcher_script(), extra)
        if winapi.run_as_admin(exe, params):
            self.quit()

    def refresh(self):
        self.widget.update()
        self.state.save()
        self._update_tooltip()

    # ------------------------------------------------------------------ dialogs
    def _open(self, key, cls):
        dlg = self._dialogs.get(key)
        if dlg is not None and dlg.isVisible():
            dlg.raise_()
            dlg.activateWindow()
            return
        try:
            dlg = cls(self)
        except Exception as e:
            log("could not open %s: %s" % (cls.__name__, e))
            raise
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.destroyed.connect(lambda *a, k=key: self._dialogs.pop(k, None))
        self._dialogs[key] = dlg
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def open_library(self):
        self._open("lib", LibraryDialog)

    def open_settings(self):
        self._open("set", SettingsDialog)

    def open_stats(self):
        self._open("stats", StatsDialog)

    def open_help(self):
        self._open("help", HelpDialog)

    def open_about(self):
        self._open("about", AboutDialog)

    def open_welcome(self):
        self._open("welcome", WelcomeDialog)

    # ------------------------------------------------------------------ updates (notify only)
    def _maybe_check_update(self):
        s = self.state.settings
        if s.get("update_check") and time.time() - s.get("update_last_check", 0) >= 24 * 3600:
            self.check_updates()

    def check_updates(self, manual=False, status_label=None):
        self._update_label = status_label if manual else None
        self.state.settings["update_last_check"] = int(time.time())
        self.state.save()
        self.updater.check()

    def _update_found(self, version, url):
        self._update = (version, url)
        s = self.state.settings
        if s.get("update_seen") != version or self._update_label is not None:
            s["update_seen"] = version
            self.state.save()
            self.notify(tr(APP_TITLE), tr("إصدار جديد متاح: %s — من القائمة اختر «فتح صفحة التنزيل».") % version)

    def _update_done(self, ok, err):
        lb = self._update_label
        self._update_label = None
        if lb is None:
            return
        try:
            if not ok:
                lb.setText(tr("تعذّر التحقق (لا يوجد اتصال أو لم تُنشر إصدارات بعد)."))
            elif self._update:
                lb.setText(tr("إصدار جديد متاح: %s — من القائمة اختر «فتح صفحة التنزيل».") % self._update[0])
            else:
                lb.setText(tr("لديك أحدث إصدار (%s).") % __version__)
        except RuntimeError:            # the settings dialog was closed meanwhile
            pass

    def open_update_page(self):
        if self._update:
            QDesktopServices.openUrl(QUrl(self._update[1]))

    # ------------------------------------------------------------------ reminders
    def _in_quiet(self):
        s = self.state.settings
        if not s.get("quiet_enabled"):
            return False
        now = datetime.datetime.now().strftime("%H:%M")
        a, b = s.get("quiet_from", "23:00"), s.get("quiet_to", "06:00")
        if a == b:
            return False
        return (a <= now < b) if a < b else (now >= a or now < b)

    def _every_minute(self):
        if self.state.check_new_day():
            self.refresh()
        err = self.state.save_error
        if err and not self._save_err_shown:
            self._save_err_shown = True
            self.notify(tr("تنبيه"), tr("تعذّر حفظ البيانات: %s") % err)
        s = self.state.settings
        self._maybe_check_update()
        if not s.get("remind_enabled") or self.state.paused or self._in_quiet():
            return
        if winapi.user_idle_seconds() > AWAY_SECONDS or winapi.foreground_is_fullscreen(os.getpid()):
            return
        gap = s.get("remind_minutes", 30) * 60
        now = time.time()
        if now - self.last_count_time >= gap and now - self.last_remind_time >= gap:
            self.remind()

    def remind(self, force=False):
        self.last_remind_time = time.time()
        w, it = self.state.current()
        left = max(0, int(w["goal"]) - self.state.counts.get(w["id"], 0))
        body = random.choice(REMINDERS) + "\n" + self._short(it["text"], 60)
        if left:
            body += tr("  (باقٍ %s)") % fmt(left)
        self.notify(tr("اذكر الله 🤍"), body)
        self.widget.glow()

    def notify(self, title, body):
        try:
            if QSystemTrayIcon.isSystemTrayAvailable() and QSystemTrayIcon.supportsMessages():
                self.tray.showMessage(title, body, make_icon(self.widget.th), 6000)
        except Exception as e:
            log("notify failed: %s" % e)

    # ------------------------------------------------------------------ exit
    def _on_quit(self):
        self.watch.stop()
        self.freeze.stop()
        if self.widget.isVisible():
            self.state.pos = [self.widget.x(), self.widget.y()]
        self.hook.stop()
        self.state.close()

    def quit(self):
        self.tray.hide()
        self.qapp.quit()


# ----------------------------------------------------------------------------------
# Start with Windows
# ----------------------------------------------------------------------------------
def launcher_script():
    """Script used to start Misbaha from source (Misbaha.pyw at the repository root)."""
    p = os.path.join(app_dir(), "Misbaha.pyw")
    return p if os.path.exists(p) else os.path.abspath(sys.argv[0])


def startup_command():
    if getattr(sys, "frozen", False):
        return '"%s"' % sys.executable
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return '"%s" "%s"' % (pyw if os.path.exists(pyw) else exe, launcher_script())


def set_startup(enable):
    if not winapi.IS_WIN:
        return
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as key:
            if enable:
                cmd = startup_command()
                try:
                    if winreg.QueryValueEx(key, APP_NAME)[0] == cmd:
                        return
                except FileNotFoundError:
                    pass
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
    except Exception as e:
        log("startup registry failed: %s" % e)


# ----------------------------------------------------------------------------------
def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    install_error_handlers()
    winapi.set_app_user_model_id(APP_ID)
    sys.setswitchinterval(0.002)          # the mouse-hook thread never waits long for the GIL

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    qapp = QApplication(argv)
    qapp.setApplicationName(APP_NAME)
    qapp.setApplicationVersion(__version__)
    qapp.setQuitOnLastWindowClosed(False)

    # single instance: a second launch just shows the running widget
    user = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    server_name = "Misbaha-%s" % "".join(ch for ch in user if ch.isalnum())
    lock = QLockFile(os.path.join(DATA_DIR, "misbaha.lock"))
    lock.setStaleLockTime(0)
    wait_ms = 15000 if "--wait-for-lock" in argv else 100
    if not lock.tryLock(wait_ms):
        sock = QLocalSocket()
        sock.connectToServer(server_name)
        if sock.waitForConnected(800):
            sock.write(b"show")
            sock.waitForBytesWritten(800)
            sock.disconnectFromServer()
            return 0
        if not lock.removeStaleLockFile() or not lock.tryLock(100):
            QMessageBox.information(None, "Misbaha", tr("المِسبحة تعمل بالفعل (انظر أيقونة شريط المهام)."))
            return 0

    load_fonts()
    qapp.setFont(ui_font(11))
    if not QSystemTrayIcon.isSystemTrayAvailable():
        log("system tray not available")
    app = MisbahaApp(qapp)
    qapp.setLayoutDirection(ui_dir())
    qapp.setWindowIcon(make_icon(get_theme(app.state.settings)))

    server = QLocalServer()
    server.setSocketOptions(QLocalServer.UserAccessOption)     # other Windows users can't connect
    QLocalServer.removeServer(server_name)
    if server.listen(server_name):
        def on_conn():
            c = server.nextPendingConnection()
            if c:
                c.readyRead.connect(lambda: (c.readAll(), app.show_from_second_launch()))
                c.disconnected.connect(c.deleteLater)
        server.newConnection.connect(on_conn)
    else:
        log("single-instance server failed: %s" % server.errorString())

    log("started Misbaha %s (%s, Python %s, admin=%s)" % (__version__, sys.platform, sys.version.split()[0],
                                                       winapi.self_elevated()))
    rc = qapp.exec()
    server.close()
    lock.unlock()
    return rc
