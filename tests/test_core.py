# -*- coding: utf-8 -*-
"""Headless tests. Run:  python -m unittest discover -s tests -v
(Qt runs with the 'offscreen' platform; the Windows mouse hook is not exercised here.)"""

import json
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_TMP = tempfile.mkdtemp(prefix="misbaha-test-")
os.environ["MISBAHA_DATA_DIR"] = _TMP
os.environ["MISBAHA_NO_INPUT"] = "1"         # never install a real global mouse hook in tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402

from misbaha import hotkeys  # noqa: E402
from misbaha.state import DEFAULT_SETTINGS, State  # noqa: E402

QAPP = QApplication.instance() or QApplication([])
QAPP.setQuitOnLastWindowClosed(False)


def state_at(path, content=None):
    if content is not None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content if isinstance(content, str) else json.dumps(content))
    return State(path, background_save=False)


class HotkeyTests(unittest.TestCase):
    def test_parse_and_normalize(self):
        self.assertEqual(hotkeys.normalize("<ctrl>+<alt>+<page_up>"), "<ctrl>+<alt>+<page_up>")
        self.assertEqual(hotkeys.normalize("Alt+Ctrl+PgDn"), "<ctrl>+<alt>+<page_down>")
        self.assertEqual(hotkeys.normalize("<ctrl>+<shift>+k"), "<ctrl>+<shift>+k")
        self.assertEqual(hotkeys.normalize("f9"), "<f9>")
        self.assertEqual(hotkeys.normalize(""), "")
        mods, vk, _ = hotkeys.parse("<ctrl>+<alt>+<space>")
        self.assertEqual((mods, vk), (hotkeys.MOD_CONTROL | hotkeys.MOD_ALT, 0x20))

    def test_invalid(self):
        for bad in ("<ctrl>+<alt>", "k", "<ctrl>+foo", "<ctrl>+a+b"):
            self.assertFalse(hotkeys.is_valid(bad), bad)

    def test_pretty_and_ahk(self):
        self.assertEqual(hotkeys.pretty("<ctrl>+<alt>+<page_up>"), "Ctrl+Alt+PgUp")
        self.assertEqual(hotkeys.ahk("<ctrl>+<alt>+<page_up>"), "^!{PgUp}")
        self.assertEqual(hotkeys.ahk("<ctrl>+<shift>+<f9>"), "^+{F9}")


class StateTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(dir=_TMP)
        self.path = os.path.join(self.dir, "state.json")

    def test_defaults(self):
        st = state_at(self.path)
        self.assertTrue(st.first_run)
        self.assertEqual(len(st.wird), 4)
        self.assertEqual(st.settings, DEFAULT_SETTINGS)

    def test_corrupt_file_is_quarantined(self):
        st = state_at(self.path, "{not json")
        self.assertEqual(len(st.wird), 4)
        self.assertTrue(any(f.startswith("state.json.broken") for f in os.listdir(self.dir)))

    def test_backup_used_when_main_is_corrupt(self):
        with open(self.path + ".bak", "w", encoding="utf-8") as f:
            json.dump({"wird": [{"id": "tas1", "goal": 33}], "counts": {"tas1": 5}, "day": "2099-01-01"}, f)
        st = state_at(self.path, "garbage")
        self.assertEqual(st.wird, [{"id": "tas1", "goal": 33}])

    def test_bad_values_are_sanitized(self):
        st = state_at(self.path, {
            "settings": {"opacity": "abc", "scale": 9999, "x1_action": "explode", "theme": "nope",
                         "quiet_from": "25:99", "hotkey_inc": "<ctrl>+zzz", "mini": "yes", "custom_bg": "red",
                         "unknown_key": 1},
            "wird": [{"id": "sal1", "goal": -5}, {"id": "sal1", "goal": 10}, {"id": "missing"}, "junk"],
            "counts": {"sal1": "7", "x": -3}, "history": {"bad-date": {"a": 1}, "2026-01-01": {"sal1": 3}},
            "pos": ["a", 2], "index": 99,
        })
        s = st.settings
        self.assertEqual(s["opacity"], DEFAULT_SETTINGS["opacity"])
        self.assertEqual(s["scale"], 200)
        self.assertEqual(s["x1_action"], DEFAULT_SETTINGS["x1_action"])
        self.assertEqual(s["theme"], "emerald")
        self.assertEqual(s["quiet_from"], "23:00")
        self.assertEqual(s["hotkey_inc"], DEFAULT_SETTINGS["hotkey_inc"])
        self.assertEqual(s["mini"], DEFAULT_SETTINGS["mini"])
        self.assertEqual(s["custom_bg"], DEFAULT_SETTINGS["custom_bg"])
        self.assertNotIn("unknown_key", s)
        self.assertEqual(st.wird, [{"id": "sal1", "goal": 1}])
        self.assertEqual(st.index, 0)
        self.assertEqual(list(st.history), ["2026-01-01"])
        self.assertIsNone(st.pos)

    def test_v16_file_migrates(self):
        st = state_at(self.path, {"version": "1.6", "settings": {"x1_action": "next", "x2_action": "inc",
                                                                 "hotkey_inc": "<ctrl>+<alt>+<space>",
                                                                 "click_action": "none", "dim_idle": True},
                                  "wird": [{"id": "sal1", "goal": 500}], "index": 0,
                                  "counts": {"sal1": 20}, "day": "2026-11-26"})
        self.assertEqual(st.settings["hotkey_inc"], "<ctrl>+<alt>+<space>")
        self.assertTrue(st.settings["dim_idle"])
        st.save()
        with open(self.path, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d["schema"], 2)
        self.assertEqual(d["wird"], [{"id": "sal1", "goal": 500}])

    def test_oversized_file_is_refused(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write('{"wird": [{"id": "tas1", "goal": 3}], "pad": "')
            f.write("x" * (21 * 1024 * 1024))
            f.write('"}')
        st = state_at(self.path)
        self.assertEqual(len(st.wird), 4)                 # defaults, not the huge file

    def test_stale_temp_files_are_cleaned(self):
        tmp = self.path + ".1234.tmp"
        with open(tmp, "w") as f:
            f.write("{}")
        old = os.path.getmtime(tmp) - 3600
        os.utime(tmp, (old, old))
        state_at(self.path)
        self.assertFalse(os.path.exists(tmp))

    def test_saved_file_is_compact(self):
        st = state_at(self.path)
        st.save()
        with open(self.path, encoding="utf-8") as f:
            self.assertNotIn("\n", f.read())

    def test_day_rollover(self):
        st = state_at(self.path, {"counts": {"sal1": 9}, "day": "2000-01-01", "index": 2})
        self.assertEqual(st.counts, {})
        self.assertEqual(st.index, 0)

    def test_threaded_saver_writes_latest(self):
        st = State(self.path, background_save=True)
        for i in range(50):
            st.counts["sal1"] = i
            st.save()
        st.close()
        with open(self.path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["counts"]["sal1"], 49)


class UpdateTests(unittest.TestCase):
    REPO = "someone/Misbaha"

    def rel(self, **kw):
        d = {"tag_name": "v1.1.0", "draft": False, "prerelease": False,
             "html_url": "https://github.com/someone/Misbaha/releases/tag/v1.1.0"}
        d.update(kw)
        return d

    def test_versions(self):
        from misbaha.update import parse_version
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version("1.2"), (1, 2, 0))
        for bad in ("", "latest", "v1", "1.2.3-beta", "v1.2.3.4", None):
            self.assertIsNone(parse_version(bad), bad)

    def test_only_valid_newer_releases(self):
        from misbaha.update import evaluate_release as ev
        self.assertEqual(ev(self.rel(), self.REPO, "1.0.0"),
                         ("1.1.0", "https://github.com/someone/Misbaha/releases/tag/v1.1.0"))
        self.assertIsNone(ev(self.rel(), self.REPO, "1.1.0"))                    # same
        self.assertIsNone(ev(self.rel(tag_name="v0.9.0"), self.REPO, "1.0.0"))    # downgrade
        self.assertIsNone(ev(self.rel(draft=True), self.REPO, "1.0.0"))
        self.assertIsNone(ev(self.rel(prerelease=True), self.REPO, "1.0.0"))
        self.assertIsNone(ev(self.rel(tag_name="v2-evil"), self.REPO, "1.0.0"))
        for url in ("https://evil.example/releases/x", "http://github.com/someone/Misbaha/releases/x",
                    "https://github.com/other/Misbaha/releases/x",
                    "https://github.com/someone/Misbaha/releases/x\"><script>"):
            self.assertIsNone(ev(self.rel(html_url=url), self.REPO, "1.0.0"), url)
        self.assertIsNone(ev(["not", "a", "dict"], self.REPO, "1.0.0"))

    def test_repo_validation(self):
        from misbaha import update
        os.environ["MISBAHA_UPDATE_REPO"] = "good-owner/Misbaha"
        self.assertEqual(update.update_repo(), "good-owner/Misbaha")
        os.environ["MISBAHA_UPDATE_REPO"] = "../../evil"
        self.assertIsNone(update.update_repo())
        del os.environ["MISBAHA_UPDATE_REPO"]

    def test_checker_with_fake_server(self):
        import io
        import urllib.request
        from misbaha import update

        class Resp(io.BytesIO):
            status = 200

            def geturl(self):
                return "https://api.github.com/repos/someone/Misbaha/releases/latest"

        class Opener:
            def __init__(self, body):
                self.body = body

            def open(self, req, timeout):
                assert req.full_url == "https://api.github.com/repos/someone/Misbaha/releases/latest"
                return Resp(self.body)

        orig = urllib.request.build_opener
        found, done = [], []
        c = update.UpdateChecker()
        c.found.connect(lambda v, u: found.append(v))
        c.done.connect(lambda ok, e: done.append(ok))
        try:
            urllib.request.build_opener = lambda *a: Opener(json.dumps(self.rel(tag_name="v9.0.0")).encode())
            c._run("someone/Misbaha")
            urllib.request.build_opener = lambda *a: Opener(b"x" * (update.MAX_BYTES + 10))
            c._run("someone/Misbaha")
        finally:
            urllib.request.build_opener = orig
        QAPP.processEvents()
        self.assertEqual(found, ["9.0.0"])
        self.assertEqual(done, [True, False])           # oversized answer rejected


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from misbaha.app import MisbahaApp
        cls.app = MisbahaApp(QAPP)

    @classmethod
    def tearDownClass(cls):
        cls.app._on_quit()

    def setUp(self):
        st = self.app.state
        st.paused = False
        st.wird = [{"id": "tas1", "goal": 3}, {"id": "tas2", "goal": 2}]
        st.counts = {}
        st.index = 0
        st.settings.update(auto_advance=True, loop_wird=True)

    def test_count_goal_advance_loop(self):
        a, st = self.app, self.app.state
        for _ in range(3):
            a.do_action("inc")
        self.assertEqual(st.counts["tas1"], 3)
        self.assertEqual(st.index, 1)              # auto-advance
        a.do_action("inc")
        a.do_action("inc")                         # whole wird done -> loop restarts
        self.assertEqual(st.index, 0)
        self.assertEqual(st.counts, {"tas1": 0, "tas2": 0})

    def test_pause_and_undo(self):
        a, st = self.app, self.app.state
        a.do_action("inc")
        a.do_action("dec")
        a.do_action("dec")
        self.assertEqual(st.counts["tas1"], 0)
        st.paused = True
        a.do_action("inc")
        self.assertEqual(st.counts["tas1"], 0)

    def test_reset_and_undo(self):
        a, st = self.app, self.app.state
        a.do_action("inc")
        a.do_action("inc")
        a.reset_current()
        self.assertEqual(st.counts["tas1"], 0)
        a._menu.aboutToShow.emit()
        self.assertTrue(a.a_undo_reset.isVisible())
        a.undo_reset()
        self.assertEqual(st.counts["tas1"], 2)

    def test_tray_click_shows_never_hides(self):
        from PySide6.QtWidgets import QSystemTrayIcon
        a = self.app
        a._tray_click(QSystemTrayIcon.Trigger)
        self.assertTrue(a.widget.isVisible())
        a.toggle_visible()                               # hide from the menu
        self.assertFalse(a.widget.isVisible())
        a._tray_click(QSystemTrayIcon.Trigger)          # tray click brings it back
        self.assertTrue(a.widget.isVisible())

    def test_custom_text_is_escaped_in_tooltips(self):
        a, st = self.app, self.app.state
        st.custom.append(dict(id="c_html", cat="custom", text="<img src='x'>test", goal=5, fadl="", src=""))
        st.clean_wird()
        a.open_library()
        QAPP.processEvents()
        dlg = a._dialogs["lib"]
        tips = []
        for i in range(dlg.tree.topLevelItemCount()):
            top = dlg.tree.topLevelItem(i)
            tips += [top.child(j).toolTip(0) for j in range(top.childCount())]
        self.assertTrue(any("&lt;img" in t for t in tips))
        self.assertFalse(any("<img" in t for t in tips))
        dlg.close()
        st.custom = [c for c in st.custom if c["id"] != "c_html"]
        st.clean_wird()

    def test_welcome_button_test(self):
        a = self.app
        a.open_welcome()
        QAPP.processEvents()
        dlg = a._dialogs["welcome"]
        self.assertTrue(a.hook.listening)
        a.hook.button_seen.emit("x2")
        QAPP.processEvents()
        self.assertIn("✔", dlg.rows["x2"][0].text())
        self.assertNotIn("✔", dlg.rows["x1"][0].text())
        dlg.accept()
        QAPP.processEvents()
        self.assertFalse(a.hook.listening)
        self.assertTrue(a.state.settings["welcome_done"])

    def test_edit_custom_keeps_id(self):
        a, st = self.app, self.app.state
        st.custom.append(dict(id="c_edit", cat="custom", text="سبحان", goal=5, fadl="", src=""))
        st.clean_wird()
        st.add_history("c_edit", 3)
        a.open_library()
        QAPP.processEvents()
        dlg = a._dialogs["lib"]
        for i in range(dlg.tree.topLevelItemCount()):
            top = dlg.tree.topLevelItem(i)
            for j in range(top.childCount()):
                if top.child(j).data(0, 256) == "c_edit":
                    dlg.tree.setCurrentItem(top.child(j))
        dlg.edit_custom()
        dlg.c_text.setText("سبحان الله")
        dlg.c_goal.setValue(7)
        dlg.add_custom()
        it = st.item("c_edit")
        self.assertEqual((it["text"], it["goal"]), ("سبحان الله", 7))
        self.assertEqual(st.today_total() >= 3, True)
        self.assertEqual(sum(1 for c in st.custom if c["id"] == "c_edit"), 1)
        dlg.close()
        st.custom = [c for c in st.custom if c["id"] != "c_edit"]
        st.clean_wird()

    def test_update_menu_item(self):
        a = self.app
        a._update_found("9.9.9", "https://github.com/x/Misbaha/releases/tag/v9.9.9")
        a._menu.aboutToShow.emit()
        self.assertTrue(a.a_update.isVisible())
        self.assertIn("9.9.9", a.a_update.text())
        a._update = None

    def test_next_prev_wrap(self):
        a, st = self.app, self.app.state
        a.do_action("prev")
        self.assertEqual(st.index, 1)
        a.do_action("next")
        self.assertEqual(st.index, 0)

    def test_dialogs_open_and_settings_save(self):
        a = self.app
        for f in (a.open_library, a.open_settings, a.open_stats, a.open_help, a.open_about):
            f()
            QAPP.processEvents()
        dlg = a._dialogs["set"]
        dlg.opacity.setValue(55)
        self.assertAlmostEqual(a.widget._op, 0.55)
        dlg.save()
        QAPP.processEvents()
        self.assertEqual(a.state.settings["opacity"], 55)
        for d in list(a._dialogs.values()):
            d.close()
        QAPP.processEvents()

    def test_widget_paints_all_themes_and_modes(self):
        from misbaha.data import THEMES
        a = self.app
        for key in THEMES:
            for mini in (False, True):
                a.state.settings.update(theme=key, mini=mini)
                a.widget.apply_settings()
                self.assertFalse(a.widget.grab().isNull())
        a.state.settings.update(theme="emerald", mini=False)
        a.widget.apply_settings()


if __name__ == "__main__":
    unittest.main()
