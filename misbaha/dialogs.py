# -*- coding: utf-8 -*-
"""Library / wird, settings, statistics, help and about dialogs."""

import datetime
import html
import os
import sys
import uuid

from PySide6.QtCore import QTime, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDialog, QFormLayout,
                               QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QScrollArea, QSlider, QSpinBox, QTableWidget, QTableWidgetItem,
                               QTabWidget, QTimeEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from misbaha import __version__, hotkeys, winapi
from misbaha.data import ACTIONS, CATEGORIES, CLICK_ACTIONS, MOUSE_BINDINGS, PRESETS, THEMES
from misbaha.i18n import (ABOUT_AR, APP_TITLE, HELP_AR, HINT_AR, LANGS, STATS_HEAD_AR, WELCOME_CARD_AR, ar, fmt,
                          tr, ui_dir)
from misbaha.update import update_repo
from misbaha.paths import DATA_DIR, LOG_FILE, STATE_FILE
from misbaha.state import to_int, today_str
from misbaha.ui import accent_css, arabic_font_list, button_css, get_theme, luminance, make_icon, ui_font

DIALOG_FLAGS = Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint


class NoWheelSpinBox(QSpinBox):
    """Spin box that ignores the wheel unless focused (scrolling a list never changes goals by accident)."""

    def __init__(self, *a):
        super().__init__(*a)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class NoWheelSlider(QSlider):
    def __init__(self, *a):
        super().__init__(*a)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class NoWheelCombo(QComboBox):
    def __init__(self, *a):
        super().__init__(*a)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class HotkeyEdit(QLineEdit):
    """Click, then press the shortcut. Stores the canonical "<ctrl>+<alt>+<page_up>" text."""

    QT_KEYS = {Qt.Key_Space: "space", Qt.Key_PageUp: "page_up", Qt.Key_PageDown: "page_down",
               Qt.Key_Home: "home", Qt.Key_End: "end", Qt.Key_Insert: "insert", Qt.Key_Delete: "delete",
               Qt.Key_Up: "up", Qt.Key_Down: "down", Qt.Key_Left: "left", Qt.Key_Right: "right",
               Qt.Key_Pause: "pause", Qt.Key_ScrollLock: "scroll_lock", Qt.Key_Tab: "tab",
               Qt.Key_Return: "enter", Qt.Key_Enter: "enter", Qt.Key_Backspace: "backspace",
               Qt.Key_Escape: "esc", Qt.Key_Print: "print_screen"}

    def __init__(self, spec):
        super().__init__()
        self.setReadOnly(True)
        self.setLayoutDirection(Qt.LeftToRight)
        self.setPlaceholderText(tr("انقر ثم اضغط الاختصار…"))
        self.setToolTip(tr("اضغط الاختصار الآن (Backspace للمسح)"))
        self.set_spec(spec)

    def set_spec(self, spec):
        self.spec = spec or ""
        self.setText(hotkeys.pretty(self.spec))

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.setPlaceholderText(tr("اضغط الاختصار الآن (Backspace للمسح)"))

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.setPlaceholderText(tr("انقر ثم اضغط الاختصار…"))

    def _key_name(self, e):
        if sys.platform == "win32" and e.nativeVirtualKey():
            name = hotkeys.VK_TO_NAME.get(e.nativeVirtualKey())     # layout independent
            if name:
                return name
        k = e.key()
        if k in self.QT_KEYS:
            return self.QT_KEYS[k]
        if Qt.Key_F1 <= k <= Qt.Key_F24:
            return "f%d" % (k - Qt.Key_F1 + 1)
        if Qt.Key_A <= k <= Qt.Key_Z:
            return chr(ord("a") + k - Qt.Key_A)
        if Qt.Key_0 <= k <= Qt.Key_9:
            d = chr(ord("0") + k - Qt.Key_0)
            return ("num" + d) if e.modifiers() & Qt.KeypadModifier else d
        return None

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta, Qt.Key_AltGr):
            return
        mods = e.modifiers()
        if k in (Qt.Key_Backspace, Qt.Key_Delete) and not (mods & (Qt.ControlModifier | Qt.AltModifier)):
            self.set_spec("")
            return
        if k == Qt.Key_Tab and not mods:
            super().keyPressEvent(e)
            return
        name = self._key_name(e)
        if not name:
            return
        m = 0
        if mods & Qt.ControlModifier:
            m |= hotkeys.MOD_CONTROL
        if mods & Qt.AltModifier:
            m |= hotkeys.MOD_ALT
        if mods & Qt.ShiftModifier:
            m |= hotkeys.MOD_SHIFT
        if mods & Qt.MetaModifier:
            m |= hotkeys.MOD_WIN
        spec = hotkeys.build(m, name)
        if hotkeys.is_valid(spec):
            self.set_spec(spec)
        else:
            self.setText(hotkeys.pretty(spec) + "  ✗")


def _scroll(widget):
    sa = QScrollArea()
    sa.setWidget(widget)
    sa.setWidgetResizable(True)
    sa.setFrameShape(QFrame.NoFrame)
    return sa


def _hint(text):
    lb = QLabel(text)
    lb.setWordWrap(True)
    lb.setStyleSheet("color:#6B6B6B")        # 5.3:1 on white (WCAG AA)
    lb.setTextFormat(Qt.RichText)
    return lb


# ----------------------------------------------------------------------------------
# Library / wird
# ----------------------------------------------------------------------------------
class LibraryDialog(QDialog):
    def __init__(self, app):
        super().__init__(None, DIALOG_FLAGS | Qt.WindowMaximizeButtonHint)
        self.app = app
        self.state = app.state
        th = get_theme(self.state.settings)
        self.setWindowTitle(tr("مكتبة الأذكار — اختر وردك"))
        self.setWindowIcon(make_icon(th))
        self.setLayoutDirection(ui_dir())
        self.resize(1000, 640)
        self.fam = self.state.settings.get("font_family", "Amiri")

        lay = QHBoxLayout(self)
        lg = QGroupBox(tr("المكتبة  (انقر مرتين للإضافة)"))
        ll = QVBoxLayout(lg)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("الذكر"), tr("العدد")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setStretchLastSection(False)
        self.tree.setFont(QFont(self.fam, 14))
        self.tree.itemDoubleClicked.connect(lambda *a: self.add_selected())
        self.tree.currentItemChanged.connect(self.show_fadl)
        ll.addWidget(self.tree)
        self.fadl = QLabel(tr("اختر ذكرًا لعرض فضله ومصدره"))
        self.fadl.setWordWrap(True)
        self.fadl.setTextFormat(Qt.PlainText)          # custom adhkar are user text: never rich text
        self.fadl.setMinimumHeight(64)
        self.fadl.setStyleSheet(accent_css(th) + "padding:8px;border-radius:8px;")
        self.fadl.setFont(ui_font(11))
        self.fadl.setLayoutDirection(Qt.RightToLeft)       # virtues are Arabic text
        self.fadl.setAlignment(Qt.AlignRight | Qt.AlignAbsolute | Qt.AlignVCenter)
        ll.addWidget(self.fadl)

        cg = QGroupBox(tr("إضافة ذكر خاص"))
        cf = QHBoxLayout(cg)
        self.c_text = QLineEdit()
        self.c_text.setPlaceholderText(tr("اكتب الذكر هنا…"))
        self.c_text.setMaxLength(400)
        self.c_text.returnPressed.connect(self.add_custom)
        self.c_text.setLayoutDirection(Qt.RightToLeft)
        self.c_goal = NoWheelSpinBox()
        self.c_goal.setRange(1, 100000)
        self.c_goal.setValue(100)
        b_c = QPushButton(tr("إضافة للمكتبة"))
        b_c.clicked.connect(self.add_custom)
        self.b_add_custom = b_c
        b_e = QPushButton(tr("تعديل الخاص المحدد"))
        b_e.clicked.connect(self.edit_custom)
        b_d = QPushButton(tr("حذف الخاص المحدد"))
        b_d.clicked.connect(self.del_custom)
        cf.addWidget(self.c_text, 3)
        cf.addWidget(self.c_goal)
        cf.addWidget(b_c)
        cf.addWidget(b_e)
        cf.addWidget(b_d)
        self._editing = None            # id of the custom dhikr being edited
        ll.addWidget(cg)
        lay.addWidget(lg, 3)

        mid = QVBoxLayout()
        mid.addStretch()
        b_add = QPushButton(tr("⟵ إضافة"))
        b_add.clicked.connect(self.add_selected)
        mid.addWidget(b_add)
        mid.addStretch()
        lay.addLayout(mid)

        wg = QGroupBox(tr("وِردي وأهدافي"))
        wl = QVBoxLayout(wg)
        self.wlist = QTableWidget(0, 3)
        self.wlist.setHorizontalHeaderLabels([tr("الذكر"), tr("الهدف"), tr("اليوم")])
        self.wlist.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.wlist.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.wlist.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.wlist.verticalHeader().setVisible(False)
        self.wlist.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.wlist.setSelectionMode(QAbstractItemView.SingleSelection)
        self.wlist.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.wlist.setWordWrap(True)
        wl.addWidget(self.wlist)
        row = QHBoxLayout()
        for txt, fn in ((tr("▲ أعلى"), lambda: self.move_row(-1)), (tr("▼ أسفل"), lambda: self.move_row(1)),
                        (tr("✕ حذف"), self.remove_row), (tr("مسح الكل"), self.clear_rows)):
            b = QPushButton(txt)
            b.clicked.connect(fn)
            row.addWidget(b)
        wl.addLayout(row)
        presets = QHBoxLayout()
        presets.addWidget(QLabel(tr("قوالب جاهزة:")))
        for txt, items in PRESETS:
            b = QPushButton(tr(txt))
            b.clicked.connect(lambda _c=False, its=items: self.set_rows(its))
            presets.addWidget(b)
        wl.addLayout(presets)
        bottom = QHBoxLayout()
        b_ok = QPushButton(tr("حفظ وبدء الورد"))
        b_ok.setStyleSheet(button_css(th))
        b_ok.clicked.connect(self.save)
        b_cancel = QPushButton(tr("إلغاء"))
        b_cancel.clicked.connect(self.reject)
        bottom.addStretch()
        bottom.addWidget(b_cancel)
        bottom.addWidget(b_ok)
        wl.addLayout(bottom)
        lay.addWidget(wg, 2)

        self.fill_tree()
        self.set_rows([(w["id"], w["goal"]) for w in self.state.wird])

    def fill_tree(self):
        self.tree.clear()
        for cid, cname in CATEGORIES:
            items = [i for i in self.state.all_items() if i.get("cat") == cid]
            if not items:
                continue
            top = QTreeWidgetItem([tr(cname), ""])
            top.setFont(0, ui_font(12, True))
            top.setFlags(Qt.ItemIsEnabled)
            self.tree.addTopLevelItem(top)
            for it in items:
                ch = QTreeWidgetItem([it["text"], fmt(it.get("goal", 100))])
                ch.setData(0, Qt.UserRole, it["id"])
                ch.setToolTip(0, "<p dir='rtl'>%s<br><br>%s</p>" % (html.escape(it["text"]),
                                                                    html.escape(it.get("fadl", ""))))
                top.addChild(ch)
            top.setExpanded(True)

    def show_fadl(self, cur, _prev=None):
        did = cur.data(0, Qt.UserRole) if cur else None
        it = self.state.item(did) if did else None
        if it:
            t = it.get("fadl") or ""
            if it.get("src"):
                t += "  — " + it["src"]
            self.fadl.setText(t or tr("ذكر خاص"))

    def _row_of(self, did):
        for r in range(self.wlist.rowCount()):
            if self.wlist.item(r, 0).data(Qt.UserRole) == did:
                return r
        return -1

    def append_row(self, did, goal):
        it = self.state.item(did)
        if not it:
            return
        existing = self._row_of(did)
        if existing >= 0:                        # no duplicates: they would share one counter
            self.wlist.selectRow(existing)
            return
        r = self.wlist.rowCount()
        self.wlist.insertRow(r)
        cell = QTableWidgetItem(it["text"])
        cell.setData(Qt.UserRole, did)
        cell.setToolTip("<p dir='rtl'>%s</p>" % html.escape(it["text"]))
        cell.setFont(QFont(self.fam, 13))
        self.wlist.setItem(r, 0, cell)
        sp = NoWheelSpinBox()
        sp.setRange(1, 100000)
        sp.setValue(to_int(goal, 100, 1, 100000))
        self.wlist.setCellWidget(r, 1, sp)
        cnt = QTableWidgetItem(fmt(self.state.counts.get(did, 0)))
        cnt.setTextAlignment(Qt.AlignCenter)
        self.wlist.setItem(r, 2, cnt)
        self.wlist.resizeRowToContents(r)

    def rows(self):
        return [(self.wlist.item(r, 0).data(Qt.UserRole), self.wlist.cellWidget(r, 1).value())
                for r in range(self.wlist.rowCount())]

    def set_rows(self, rows, select=None):
        self.wlist.setRowCount(0)
        for did, g in rows:
            self.append_row(did, g)
        if select is not None and 0 <= select < self.wlist.rowCount():
            self.wlist.selectRow(select)

    def add_selected(self):
        cur = self.tree.currentItem()
        did = cur.data(0, Qt.UserRole) if cur else None
        if did:
            self.append_row(did, self.state.item(did).get("goal", 100))

    def move_row(self, d):
        r = self.wlist.currentRow()
        rows = self.rows()
        if r < 0 or not (0 <= r + d < len(rows)):
            return
        rows[r], rows[r + d] = rows[r + d], rows[r]
        self.set_rows(rows, r + d)

    def remove_row(self):
        r = self.wlist.currentRow()
        if r >= 0:
            self.wlist.removeRow(r)

    def clear_rows(self):
        self.wlist.setRowCount(0)

    def _selected_custom(self):
        cur = self.tree.currentItem()
        did = cur.data(0, Qt.UserRole) if cur else None
        if not did or not str(did).startswith("c_"):
            QMessageBox.information(self, tr(APP_TITLE), tr("اختر ذكرًا من «أذكاري الخاصة» لحذفه."))
            return None
        return did

    def edit_custom(self):
        did = self._selected_custom()
        it = self.state.item(did) if did else None
        if not it:
            return
        self._editing = did
        self.c_text.setText(it["text"])
        self.c_goal.setValue(to_int(it.get("goal"), 100, 1, 100000))
        self.b_add_custom.setText(tr("حفظ التعديل"))
        self.c_text.setFocus()

    def add_custom(self):
        t = " ".join(self.c_text.text().split())
        if not t:
            return
        if self._editing:                         # same id: history and wird stay attached
            it = self.state.item(self._editing)
            if it and not any(i["text"] == t and i["id"] != it["id"] for i in self.state.all_items()):
                it["text"], it["goal"] = t, self.c_goal.value()
                self.state.save()
                rows = self.rows()
                self.fill_tree()
                self.set_rows(rows)
                self.app.refresh()
            self._editing = None
            self.b_add_custom.setText(tr("إضافة للمكتبة"))
            self.c_text.clear()
            return
        if any(i["text"] == t for i in self.state.all_items()):
            QMessageBox.information(self, tr(APP_TITLE), tr("هذا الذكر موجود بالفعل في المكتبة."))
            return
        it = dict(id="c_" + uuid.uuid4().hex[:8], cat="custom", text=t, goal=self.c_goal.value(), fadl="", src="")
        self.state.custom.append(it)
        self.state.clean_wird()
        self.state.save()
        self.c_text.clear()
        self.fill_tree()
        self.append_row(it["id"], it["goal"])

    def del_custom(self):
        cur = self.tree.currentItem()
        did = cur.data(0, Qt.UserRole) if cur else None
        if not did or not str(did).startswith("c_"):
            QMessageBox.information(self, tr(APP_TITLE), tr("اختر ذكرًا من «أذكاري الخاصة» لحذفه."))
            return
        self.state.custom = [c for c in self.state.custom if c["id"] != did]
        self.set_rows([r for r in self.rows() if r[0] != did])
        self.fill_tree()
        self.state.clean_wird()        # it may be in the active wird
        self.state.save()
        self.app.refresh()

    def save(self):
        rows = self.rows()
        if not rows:
            QMessageBox.warning(self, tr(APP_TITLE), tr("أضف ذكرًا واحدًا على الأقل إلى وردك."))
            return
        self.state.wird = [dict(id=d, goal=g) for d, g in rows]
        # start at the first dhikr that is not finished yet today
        self.state.index = next((i for i, (d, g) in enumerate(rows) if self.state.counts.get(d, 0) < g), 0)
        self.state.clean_wird()
        self.app.refresh()
        self.accept()


# ----------------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, app):
        super().__init__(None, DIALOG_FLAGS)
        self.app = app
        self.s = dict(app.state.settings)
        th = get_theme(self.s)
        self.setWindowTitle(tr("الإعدادات"))
        self.setWindowIcon(make_icon(th))
        self.setLayoutDirection(ui_dir())
        self.resize(600, 680)
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        lay.addWidget(tabs)

        # --- controls ---
        t1 = QWidget()
        f1 = QFormLayout(t1)
        self.bind = {}
        for key, label in MOUSE_BINDINGS:
            self.bind[key] = self._action_combo(self.s[key])
            f1.addRow(tr(label), self.bind[key])
        self.suppress = QCheckBox(tr("منع الأزرار المربوطة من الوصول للبرامج الأخرى (مثل «رجوع» في المتصفح)"))
        self.suppress.setChecked(self.s["suppress_side"])
        f1.addRow(self.suppress)
        self.hk_en = QCheckBox(tr("تفعيل اختصارات لوحة المفاتيح العامة"))
        self.hk_en.setChecked(self.s["hotkeys_enabled"])
        f1.addRow(self.hk_en)
        self.hk = {}
        for key, label in (("hotkey_inc", "اختصار الزيادة:"), ("hotkey_next", "اختصار الذكر التالي:"),
                           ("hotkey_undo", "اختصار الإنقاص −١:")):
            ed = HotkeyEdit(self.s[key])
            clr = QPushButton(tr("مسح"))
            clr.clicked.connect(lambda _c=False, e=ed: e.set_spec(""))
            row = QHBoxLayout()
            row.addWidget(ed, 1)
            row.addWidget(clr)
            self.hk[key] = ed
            f1.addRow(tr(label), row)
        f1.addRow(_hint(tr("الاختصارات تُسجَّل لدى Windows مباشرة وتعمل حتى في البرامج التي تعمل كمسؤول. "
                           "يُفضَّل استخدام Ctrl + Alt مع مفتاح خاص (PgUp، PgDn، Space، F9…).")))
        f1.addRow(_hint(tr(HINT_AR)))
        tabs.addTab(_scroll(t1), tr("التحكم"))

        # --- counting ---
        tc = QWidget()
        fc = QFormLayout(tc)
        self.wheel = QCheckBox(tr("العدّ بعجلة الفأرة عند الوقوف على الودجت (الإيقاف أكثر أمانًا)"))
        self.wheel.setChecked(self.s["wheel_count"])
        fc.addRow(self.wheel)
        self.click_action = NoWheelCombo()
        for kk, name in CLICK_ACTIONS:
            self.click_action.addItem(tr(name), kk)
        self.click_action.setCurrentIndex(max(0, self.click_action.findData(self.s["click_action"])))
        fc.addRow(tr("النقر على الودجت:"), self.click_action)
        self.auto_adv = QCheckBox(tr("الانتقال تلقائيًا للذكر التالي عند بلوغ الهدف"))
        self.auto_adv.setChecked(self.s["auto_advance"])
        fc.addRow(self.auto_adv)
        self.loop = QCheckBox(tr("إعادة الورد من البداية بعد إتمامه"))
        self.loop.setChecked(self.s["loop_wird"])
        fc.addRow(self.loop)
        self.daily = QCheckBox(tr("تصفير العداد مع بداية كل يوم"))
        self.daily.setChecked(self.s["daily_reset"])
        fc.addRow(self.daily)
        tabs.addTab(_scroll(tc), tr("العدّ"))

        # --- appearance ---
        t2 = QWidget()
        f2 = QFormLayout(t2)
        self.lang = NoWheelCombo()
        for code, name in LANGS:
            self.lang.addItem(name, code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(self.s.get("ui_lang", "en"))))
        f2.addRow(tr("اللغة / Language:"), self.lang)
        self.theme = NoWheelCombo()
        for key, t in THEMES.items():
            self.theme.addItem(tr(t[0]), key)
            if t[1]:
                sw = QPixmap(28, 16)
                sw.fill(QColor(t[1]))
                pp = QPainter(sw)
                pp.fillRect(16, 0, 12, 16, QColor(t[3]))
                pp.end()
                self.theme.setItemIcon(self.theme.count() - 1, QIcon(sw))
        self.theme.setCurrentIndex(max(0, self.theme.findData(self.s["theme"])))
        f2.addRow(tr("لون الواجهة:"), self.theme)
        crow = QHBoxLayout()
        self.b_bg = QPushButton(tr("لون الخلفية"))
        self.b_acc = QPushButton(tr("لون التمييز"))
        self.b_bg.clicked.connect(lambda: self.pick_color("custom_bg"))
        self.b_acc.clicked.connect(lambda: self.pick_color("custom_accent"))
        crow.addWidget(self.b_bg)
        crow.addWidget(self.b_acc)
        f2.addRow(tr("ألوان مخصصة:"), crow)
        self.font = NoWheelCombo()
        for fam in arabic_font_list():
            self.font.addItem(fam)
        self.font.setCurrentIndex(max(0, self.font.findText(self.s["font_family"])))
        f2.addRow(tr("خط الذكر:"), self.font)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(110)
        f2.addRow(self.preview)
        self.digits = QCheckBox(tr("استخدام الأرقام العربية (١٢٣)"))
        self.digits.setChecked(self.s["arabic_digits"])
        self.digits.toggled.connect(self.update_preview)
        f2.addRow(self.digits)
        tabs.addTab(_scroll(t2), tr("المظهر"))

        # --- widget / overlay ---
        tw = QWidget()
        fw = QFormLayout(tw)
        self.mini = QCheckBox(tr("الوضع المصغّر (الرقم فقط)"))
        self.mini.setChecked(self.s["mini"])
        fw.addRow(self.mini)
        self.click_through = QCheckBox(tr("تمرير النقرات عبر الودجت (لا يعترض الفأرة — اضغط Ctrl فوقه لاستخدامه)"))
        self.click_through.setChecked(self.s["click_through"])
        fw.addRow(self.click_through)
        self.hide_fs = QCheckBox(tr("إخفاء الودجت فوق البرامج بملء الشاشة (فيديو، عروض تقديمية)"))
        self.hide_fs.setChecked(self.s["hide_fullscreen"])
        self.hide_fs.setEnabled(winapi.IS_WIN)
        fw.addRow(self.hide_fs)
        self.opacity, op_row = self._slider(20, 100, self.s["opacity"], "%")
        self.opacity.valueChanged.connect(self._opacity_changed)
        fw.addRow(tr("الشفافية:"), op_row)
        self.dim = QCheckBox(tr("تعتيم الودجت تلقائيًا عند عدم الاستخدام"))
        self.dim.setChecked(self.s["dim_idle"])
        fw.addRow(self.dim)
        self.idle_op, idle_row = self._slider(50, 100, self.s["idle_opacity"], "%")
        fw.addRow(tr("الشفافية عند الخمول:"), idle_row)
        self.idle_sec = NoWheelSpinBox()
        self.idle_sec.setRange(2, 3600)
        self.idle_sec.setSuffix(tr(" ثانية"))
        self.idle_sec.setValue(self.s["idle_seconds"])
        fw.addRow(tr("التعتيم بعد:"), self.idle_sec)
        self.dim.toggled.connect(lambda on: (self.idle_op.setEnabled(on), self.idle_sec.setEnabled(on)))
        self.idle_op.setEnabled(self.s["dim_idle"])
        self.idle_sec.setEnabled(self.s["dim_idle"])
        fw.addRow(_hint(tr("تلميح: Ctrl + عجلة الفأرة على الودجت لتغيير الشفافية بسرعة.")))
        self.scale, sc_row = self._slider(60, 200, self.s["scale"], "%")
        fw.addRow(tr("الحجم:"), sc_row)
        tabs.addTab(_scroll(tw), tr("الودجت"))
        self.theme.currentIndexChanged.connect(self.update_preview)
        self.font.currentTextChanged.connect(self.update_preview)

        # --- reminders ---
        t3 = QWidget()
        f3 = QFormLayout(t3)
        self.rem = QCheckBox(tr("تذكيري بذكر الله"))
        self.rem.setChecked(self.s["remind_enabled"])
        f3.addRow(self.rem)
        self.rem_min = NoWheelSpinBox()
        self.rem_min.setRange(1, 600)
        self.rem_min.setSuffix(tr(" دقيقة"))
        self.rem_min.setValue(self.s["remind_minutes"])
        f3.addRow(tr("ذكّرني إذا لم أذكر منذ:"), self.rem_min)
        self.quiet = QCheckBox(tr("أوقات الهدوء (بدون تذكير)"))
        self.quiet.setChecked(self.s["quiet_enabled"])
        f3.addRow(self.quiet)
        self.q_from = QTimeEdit(QTime.fromString(self.s["quiet_from"], "HH:mm"))
        self.q_to = QTimeEdit(QTime.fromString(self.s["quiet_to"], "HH:mm"))
        for q in (self.q_from, self.q_to):
            q.setDisplayFormat("HH:mm")
            q.setLayoutDirection(Qt.LeftToRight)
        f3.addRow(tr("من:"), self.q_from)
        f3.addRow(tr("إلى:"), self.q_to)
        self.notify_goal = QCheckBox(tr("إشعار عند بلوغ الهدف"))
        self.notify_goal.setChecked(self.s["notify_goal"])
        f3.addRow(self.notify_goal)
        f3.addRow(_hint(tr("لا تذكير أثناء غيابك عن الجهاز أو أثناء البرامج بملء الشاشة.")))
        b_test = QPushButton(tr("تجربة إشعار الآن"))
        b_test.clicked.connect(lambda: self.app.remind(force=True))
        f3.addRow(b_test)
        tabs.addTab(_scroll(t3), tr("التذكير"))

        # --- system ---
        t4 = QWidget()
        f4 = QFormLayout(t4)
        self.startup = QCheckBox(tr("التشغيل مع بدء Windows"))
        self.startup.setChecked(self.s["start_with_windows"])
        self.startup.setEnabled(winapi.IS_WIN)
        f4.addRow(self.startup)
        f4.addRow(QLabel("<b>%s</b>" % tr("حالة الالتقاط")))
        self.status = QLabel(self.app.status_text())
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f4.addRow(self.status)
        info = QLabel(tr("ملف البيانات:\n%s\n\nسجل الأخطاء:\n%s\n\nالإصدار %s") % (STATE_FILE, LOG_FILE, __version__))
        info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info.setWordWrap(True)
        f4.addRow(info)
        b_open = QPushButton(tr("فتح مجلد البيانات"))
        b_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(DATA_DIR)))
        f4.addRow(b_open)
        self.upd = QCheckBox(tr("التحقق من وجود إصدار جديد على GitHub مرة يوميًا"))
        self.upd.setChecked(self.s["update_check"])
        b_upd = QPushButton(tr("تحقق الآن"))
        b_upd.clicked.connect(self._check_now)
        urow = QHBoxLayout()
        urow.addWidget(self.upd, 1)
        urow.addWidget(b_upd)
        f4.addRow(urow)
        self.upd_status = QLabel(tr("يفتح صفحة الإصدار فقط — لا يُنزَّل أو يُثبَّت شيء تلقائيًا، ولا تُرسل أي بيانات شخصية."))
        self.upd_status.setWordWrap(True)
        self.upd_status.setTextFormat(Qt.PlainText)
        self.upd_status.setStyleSheet("color:#6B6B6B")
        f4.addRow(self.upd_status)
        if not update_repo():
            self.upd.setEnabled(False)
            b_upd.setEnabled(False)
            self.upd_status.setText(tr("التحقق من التحديثات متاح في الإصدارات الرسمية فقط."))
        tabs.addTab(_scroll(t4), tr("النظام"))

        row = QHBoxLayout()
        row.addStretch()
        bc = QPushButton(tr("إلغاء"))
        bc.clicked.connect(self.reject)
        self.bo = QPushButton(tr("حفظ"))
        self.bo.setDefault(True)
        self.bo.clicked.connect(self.save)
        row.addWidget(bc)
        row.addWidget(self.bo)
        lay.addLayout(row)
        self.update_preview()

    def _check_now(self):
        self.upd_status.setText(tr("جارٍ التحقق…"))
        self.app.check_updates(manual=True, status_label=self.upd_status)

    def _slider(self, lo, hi, val, suffix):
        sl = NoWheelSlider(Qt.Horizontal)
        sl.setRange(lo, hi)
        sl.setValue(val)
        lb = QLabel(fmt(val) + suffix)
        lb.setMinimumWidth(44)
        sl.valueChanged.connect(lambda v: lb.setText(fmt(v) + suffix))
        row = QHBoxLayout()
        row.addWidget(sl, 1)
        row.addWidget(lb)
        return sl, row

    def _opacity_changed(self, v):
        self.app.widget.preview_opacity(v)          # live preview on the real widget

    def done(self, r):
        self.app.widget.end_preview()
        super().done(r)

    def _action_combo(self, val):
        c = NoWheelCombo()
        for k, name in ACTIONS:
            c.addItem(tr(name), k)
        c.setCurrentIndex(max(0, c.findData(val)))
        return c

    def pick_color(self, key):
        c = QColorDialog.getColor(QColor(self.s.get(key)), self, tr("اختر اللون"))
        if c.isValid():
            self.s[key] = c.name()
            self.theme.setCurrentIndex(self.theme.findData("custom"))
            self.update_preview()

    def update_preview(self, *a):
        if not hasattr(self, "bo"):
            return
        self.s["theme"] = self.theme.currentData()
        th = get_theme(self.s)
        self.preview.setFont(QFont(self.font.currentText(), 22))
        digits = self.digits.isChecked()
        n33, n100 = (ar(33), ar(100)) if digits else ("33", "100")
        self.preview.setText("سُبْحَانَ اللهِ وَبِحَمْدِهِ\n\u202a%s / %s\u202c" % (n33, n100) if not digits
                             else "سُبْحَانَ اللهِ وَبِحَمْدِهِ\n%s / %s" % (n33, n100))
        self.preview.setStyleSheet(
            "QLabel{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 %s,stop:1 %s);color:%s;"
            "border:2px solid %s;border-radius:14px;padding:6px;}"
            % (th["bg1"].name(), th["bg2"].name(), th["text"].name(), th["acc"].name()))
        custom = self.s["theme"] == "custom"
        self.b_bg.setStyleSheet("background:%s;color:%s;" % (
            self.s["custom_bg"], "#fff" if luminance(QColor(self.s["custom_bg"])) < .6 else "#000") if custom else "")
        self.b_acc.setStyleSheet("background:%s;color:#000;" % self.s["custom_accent"] if custom else "")
        self.bo.setStyleSheet(button_css(th))

    def save(self):
        s = self.app.state.settings
        s.update({k: c.currentData() for k, c in self.bind.items()})
        s.update({k: e.spec for k, e in self.hk.items()})
        s.update(
            suppress_side=self.suppress.isChecked(), hotkeys_enabled=self.hk_en.isChecked(),
            wheel_count=self.wheel.isChecked(), click_action=self.click_action.currentData(),
            auto_advance=self.auto_adv.isChecked(), loop_wird=self.loop.isChecked(),
            daily_reset=self.daily.isChecked(), font_family=self.font.currentText(),
            theme=self.theme.currentData(), custom_bg=self.s["custom_bg"], custom_accent=self.s["custom_accent"],
            arabic_digits=self.digits.isChecked(), mini=self.mini.isChecked(),
            click_through=self.click_through.isChecked(), hide_fullscreen=self.hide_fs.isChecked(),
            opacity=self.opacity.value(), dim_idle=self.dim.isChecked(), idle_opacity=self.idle_op.value(),
            idle_seconds=self.idle_sec.value(), scale=self.scale.value(),
            remind_enabled=self.rem.isChecked(), remind_minutes=self.rem_min.value(),
            quiet_enabled=self.quiet.isChecked(), quiet_from=self.q_from.time().toString("HH:mm"),
            quiet_to=self.q_to.time().toString("HH:mm"), notify_goal=self.notify_goal.isChecked(),
            start_with_windows=self.startup.isChecked(), ui_lang=self.lang.currentData(),
            update_check=self.upd.isChecked(),
        )
        self.app.state._sanitize_settings()
        self.app.settings_changed()
        self.accept()


# ----------------------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------------------
class StatsDialog(QDialog):
    def __init__(self, app):
        super().__init__(None, DIALOG_FLAGS)
        st = app.state
        th = get_theme(st.settings)
        self.setWindowTitle(tr("إحصائياتي"))
        self.setWindowIcon(make_icon(th))
        self.setLayoutDirection(ui_dir())
        self.resize(580, 560)
        lay = QVBoxLayout(self)
        head = QLabel(tr(STATS_HEAD_AR) % (fmt(st.today_total()), fmt(st.streak()), fmt(st.all_time_total())))
        head.setStyleSheet(accent_css(th) + "font-size:16px;padding:10px;border-radius:8px;")
        lay.addWidget(head)

        lay.addWidget(QLabel(tr("أذكار اليوم:")))
        today = {k: v for k, v in st.history.get(today_str(), {}).items() if v > 0}
        t = QTableWidget(len(today), 2)
        t.setHorizontalHeaderLabels([tr("الذكر"), tr("العدد")])
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for r, (did, n) in enumerate(sorted(today.items(), key=lambda x: -x[1])):
            it = st.item(did)
            t.setItem(r, 0, QTableWidgetItem(it["text"] if it else tr("(ذكر محذوف)")))
            t.setItem(r, 1, QTableWidgetItem(fmt(n)))
        lay.addWidget(t)

        lay.addWidget(QLabel(tr("آخر ٧ أيام:")))
        t2 = QTableWidget(7, 2)
        t2.setHorizontalHeaderLabels([tr("التاريخ"), tr("المجموع")])
        t2.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        t2.verticalHeader().setVisible(False)
        t2.setEditTriggers(QAbstractItemView.NoEditTriggers)
        days = [tr("الاثنين"), tr("الثلاثاء"), tr("الأربعاء"), tr("الخميس"), tr("الجمعة"), tr("السبت"), tr("الأحد")]
        for r in range(7):
            d = datetime.date.today() - datetime.timedelta(days=r)
            t2.setItem(r, 0, QTableWidgetItem("%s  %s" % (days[d.weekday()], fmt(d.strftime("%d/%m")))))
            t2.setItem(r, 1, QTableWidgetItem(fmt(st.day_total(d.isoformat()))))
        lay.addWidget(t2)
        b = QPushButton(tr("إغلاق"))
        b.clicked.connect(self.accept)
        lay.addWidget(b)


# ----------------------------------------------------------------------------------
# Help & About
# ----------------------------------------------------------------------------------
class WelcomeDialog(QDialog):
    """First run (and menu → Test mouse buttons): live check that the side buttons reach Misbaha."""

    BUTTONS = [("x2", "x2_action", "الزر الجانبي الأمامي (X2)"), ("x1", "x1_action", "الزر الجانبي الخلفي (X1)")]

    def __init__(self, app):
        super().__init__(None, DIALOG_FLAGS)
        self.app = app
        th = get_theme(app.state.settings)
        self.setWindowTitle(tr("مرحبًا بك في المِسبحة"))
        self.setWindowIcon(make_icon(th))
        self.setLayoutDirection(ui_dir())
        self.resize(540, 340)
        lay = QVBoxLayout(self)
        head = QLabel(tr(WELCOME_CARD_AR))
        head.setWordWrap(True)
        head.setTextFormat(Qt.RichText)
        head.setStyleSheet(accent_css(th) + "padding:12px;border-radius:10px;font-size:14px;")
        lay.addWidget(head)
        self.rows = {}
        actions = dict(ACTIONS)
        for btn, key, label in self.BUTTONS:
            lb = QLabel()
            lb.setTextFormat(Qt.PlainText)
            lb.setFont(ui_font(12))
            self.rows[btn] = (lb, tr(label), tr(actions.get(app.state.settings[key], "لا شيء")))
            lay.addWidget(lb)
        s = app.state.settings
        if s.get("hotkeys_enabled"):
            keys = QLabel(tr("لوحة المفاتيح: %s = زيادة +١ ، %s = الذكر التالي") % (
                hotkeys.pretty(s.get("hotkey_inc")) or "—", hotkeys.pretty(s.get("hotkey_next")) or "—"))
            keys.setTextFormat(Qt.PlainText)
            keys.setStyleSheet("color:#6B6B6B")
            lay.addWidget(keys)
        self.hint = QLabel(tr("لم يُكتشف أي زر؟ قد يكون برنامج الفأرة (Logitech، Razer…) يلتقطه. "
                              "افتح «مساعدة ونصائح»، أو استخدم اختصارات لوحة المفاتيح."))
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color:#8A4B00")
        self.hint.hide()
        lay.addWidget(self.hint)
        lay.addStretch()
        row = QHBoxLayout()
        for txt, fn in ((tr("اختيار وردي…"), app.open_library), (tr("مساعدة ونصائح"), app.open_help)):
            b = QPushButton(txt.replace("&", "&&"))
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        ok = QPushButton(tr("ابدأ"))
        ok.setStyleSheet(button_css(th))
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        row.addWidget(ok)
        lay.addLayout(row)
        self.seen = set()
        self._refresh()
        app.hook.listening = True
        app.hook.button_seen.connect(self._seen)
        QTimer.singleShot(10000, self._maybe_hint)

    def _refresh(self):
        for btn, (lb, label, act) in self.rows.items():
            mark = "✔" if btn in self.seen else "○"
            lb.setText("%s  %s  →  %s" % (mark, label, act))
            lb.setStyleSheet("color:#1E7B34;font-weight:bold;" if btn in self.seen else "")

    def _seen(self, btn):
        if btn in self.rows:
            self.seen.add(btn)
            self.hint.hide()
            self._refresh()

    def _maybe_hint(self):
        if not self.seen and self.isVisible():
            self.hint.show()

    def done(self, r):
        self.app.hook.listening = False
        try:
            self.app.hook.button_seen.disconnect(self._seen)
        except (RuntimeError, TypeError):
            pass
        self.app.state.settings["welcome_done"] = True
        self.app.state.save()
        super().done(r)


class HelpDialog(QDialog):
    def __init__(self, app):
        super().__init__(None, DIALOG_FLAGS)
        s = app.state.settings
        th = get_theme(s)
        self.setWindowTitle(tr("مساعدة ونصائح"))
        self.setWindowIcon(make_icon(th))
        self.setLayoutDirection(ui_dir())
        self.resize(620, 600)
        lay = QVBoxLayout(self)
        inc = s.get("hotkey_inc") or "<ctrl>+<alt>+<page_up>"
        nxt = s.get("hotkey_next") or "<ctrl>+<alt>+<page_down>"
        body = QLabel(tr(HELP_AR) % (hotkeys.pretty(inc), hotkeys.pretty(nxt), hotkeys.pretty(inc),
                                     hotkeys.pretty(nxt), hotkeys.ahk(inc), hotkeys.ahk(nxt)))
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setAlignment(Qt.AlignTop)
        inner = QWidget()
        il = QVBoxLayout(inner)
        il.addWidget(body)
        lay.addWidget(_scroll(inner))
        b = QPushButton(tr("إغلاق"))
        b.clicked.connect(self.accept)
        lay.addWidget(b)


class AboutDialog(QDialog):
    def __init__(self, app):
        super().__init__(None, DIALOG_FLAGS)
        th = get_theme(app.state.settings)
        self.setWindowTitle(tr("عن المِسبحة"))
        self.setWindowIcon(make_icon(th))
        self.setLayoutDirection(ui_dir())
        self.resize(520, 420)
        lay = QVBoxLayout(self)
        icon = QLabel()
        icon.setPixmap(make_icon(th, 96).pixmap(96, 96))
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)
        title = QLabel("مِسبحة<br><span style='font-size:13pt'>Misbaha %s</span>" % __version__)
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont(app.state.settings.get("font_family", "Amiri"), 22))
        title.setStyleSheet(accent_css(th) + "padding:12px;border-radius:10px;")
        lay.addWidget(title)
        body = QLabel(tr(ABOUT_AR) % os.path.dirname(STATE_FILE))
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        body.setOpenExternalLinks(True)
        lay.addWidget(body)
        lay.addStretch()
        b = QPushButton(tr("إغلاق"))
        b.clicked.connect(self.accept)
        lay.addWidget(b)
