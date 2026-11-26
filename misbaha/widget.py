# -*- coding: utf-8 -*-
"""The floating always-on-top counter."""

import time

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget

from misbaha import winapi
from misbaha.data import CAT_NAME
from misbaha.i18n import APP_TITLE, fmt, is_rtl, num_dir, tr, ui_dir
from misbaha.ui import get_theme, ui_font

FRAME_MS = 33            # animation frame (~30 fps) - only runs while something is changing


class CounterWidget(QWidget):
    def __init__(self, app):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint)
        self.app = app
        self.state = app.state
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)
        self.setWindowTitle(tr(APP_TITLE))
        self.setAccessibleName("Misbaha")
        self.setLayoutDirection(ui_dir())
        self._drag = None
        self._moved = False
        self._wheel = 0
        self._op_wheel = 0
        self._fit_cache = {}
        self.pulse = 0.0          # 0..1 glow after each count
        self.flash = 0.0          # 0..1 accent flash on goal
        self.remind_glow = 0.0
        self._op = None           # current painted opacity 0..1
        self._preview = None      # opacity preview from the settings dialog
        self.last_active = time.monotonic()
        self.osd = ""
        self._ct_state = None     # native click-through state currently applied
        self._last_raise = 0.0
        self.th = get_theme(self.state.settings)

        self.anim = QTimer(self)
        self.anim.setTimerType(Qt.CoarseTimer)
        self.anim.timeout.connect(self._tick)
        self.idle_timer = QTimer(self)
        self.idle_timer.setTimerType(Qt.VeryCoarseTimer)
        self.idle_timer.timeout.connect(self._idle_check)
        self.osd_timer = QTimer(self)
        self.osd_timer.setSingleShot(True)
        self.osd_timer.timeout.connect(self._clear_osd)
        self.ct_timer = QTimer(self)           # "hold Ctrl over the widget" in click-through mode
        self.ct_timer.timeout.connect(self._ctrl_poll)
        self.apply_settings()

    # ------------------------------------------------------------------ geometry / settings
    def k(self):
        return self.state.settings.get("scale", 100) / 100.0

    def base_size(self):
        k = self.k()
        if self.state.settings.get("mini"):
            return QSize(int(150 * k), int(78 * k))
        return QSize(int(330 * k), int(190 * k))

    def apply_settings(self):
        s = self.state.settings
        self.th = get_theme(s)
        self._fit_cache.clear()
        self.setFixedSize(self.base_size())
        self.setLayoutDirection(ui_dir())
        self.setWindowTitle(tr(APP_TITLE))
        if s.get("dim_idle"):
            if not self.idle_timer.isActive():
                self.idle_timer.start(1000)
        else:
            self.idle_timer.stop()
        self._apply_click_through(bool(s.get("click_through")))
        if s.get("click_through") and winapi.IS_WIN:
            self.ct_timer.start(120)
        else:
            self.ct_timer.stop()
        self.move(self._valid_pos(self.state.pos))
        self.refresh_opacity(instant=True)
        self.update()

    def _default_pos(self):
        scr = QApplication.primaryScreen().availableGeometry()
        return QPoint(scr.right() - self.width() - 24, scr.bottom() - self.height() - 24)

    def _on_screen(self, p):
        centre = p + QPoint(self.width() // 2, self.height() // 2)
        return any(sc.availableGeometry().contains(centre) for sc in QApplication.screens())

    def _valid_pos(self, pos):
        if pos:
            p = QPoint(int(pos[0]), int(pos[1]))
            if self._on_screen(p):
                return p
        return self._default_pos()

    def reposition(self):
        """Called when monitors change: bring the widget back if it ended up off-screen."""
        if not self._on_screen(self.pos()):
            self.move(self._valid_pos(self.state.pos))

    # ------------------------------------------------------------------ overlay / click-through
    def _apply_click_through(self, enabled):
        if winapi.IS_WIN:
            winapi.set_overlay_style(int(self.winId()), enabled)
        elif bool(self.windowFlags() & Qt.WindowTransparentForInput) != enabled:
            vis = self.isVisible()
            self.setWindowFlag(Qt.WindowTransparentForInput, enabled)
            if vis:
                self.show()
        self._ct_state = enabled

    def ensure_overlay(self, raise_now=False):
        """Re-assert the overlay window styles, and top-most only when it was lost (or raise_now).

        Not raising blindly every few seconds keeps the widget from covering other apps' menus."""
        if not self.isVisible() or not winapi.IS_WIN:
            return
        hwnd = int(self.winId())
        winapi.set_overlay_style(hwnd, bool(self._ct_state))
        now = time.monotonic()
        if raise_now:
            if now - self._last_raise < 3:
                return
        elif winapi.is_topmost(hwnd):
            return
        self._last_raise = now
        winapi.set_topmost(hwnd)

    def _ctrl_poll(self):
        if not self.isVisible() or not self.state.settings.get("click_through"):
            return
        interactive = winapi.ctrl_down() and self.frameGeometry().contains(QCursor.pos())
        want = not interactive
        if want != self._ct_state:
            self._apply_click_through(want)
            if interactive:
                self.wake()

    def showEvent(self, e):
        super().showEvent(e)
        self._apply_click_through(bool(self.state.settings.get("click_through")))
        self.ensure_overlay(raise_now=True)

    # ------------------------------------------------------------------ opacity (painted, no layered-window tricks)
    def target_opacity(self):
        if self._preview is not None:
            return self._preview
        s = self.state.settings
        op = s.get("opacity", 92) / 100.0
        if s.get("dim_idle") and not self.underMouse() and self.flash <= 0 and self.remind_glow <= 0 \
                and self._drag is None and time.monotonic() - self.last_active > s.get("idle_seconds", 10):
            op = min(op, s.get("idle_opacity", 40) / 100.0)
        return op

    def refresh_opacity(self, instant=False):
        t = self.target_opacity()
        if instant or self._op is None:
            self._op = t
            self.update()
        elif abs(t - self._op) > 0.005:
            self._animate()

    def preview_opacity(self, value):
        self._preview = value / 100.0
        self.refresh_opacity(instant=True)

    def end_preview(self):
        self._preview = None
        self.refresh_opacity(instant=True)

    def wake(self):
        self.last_active = time.monotonic()
        self.refresh_opacity()

    def _idle_check(self):
        self.refresh_opacity()

    def change_opacity(self, delta):
        s = self.state.settings
        s["opacity"] = max(20, min(100, int(s.get("opacity", 92)) + delta))
        self.last_active = time.monotonic()
        self.refresh_opacity(instant=True)
        self.show_osd(tr("الشفافية: %s%%") % fmt(s["opacity"]))
        self.app.schedule_save()

    def show_osd(self, text):
        self.osd = text
        self.update()
        self.osd_timer.start(1200)

    def _clear_osd(self):
        self.osd = ""
        self.update()

    def enterEvent(self, e):
        self.wake()

    def leaveEvent(self, e):
        self.last_active = time.monotonic()

    # ------------------------------------------------------------------ animation
    def _tick(self):
        active = False
        for attr, step in (("pulse", 0.08), ("flash", 0.03), ("remind_glow", 0.008)):
            v = getattr(self, attr)
            if v > 0:
                setattr(self, attr, max(0.0, v - step))
                active = True
        t = self.target_opacity()
        if self._op is not None and abs(t - self._op) > 0.005:
            step = 0.06 if t > self._op else 0.02          # wake fast, dim gently
            self._op = t if abs(t - self._op) <= step else self._op + (step if t > self._op else -step)
            active = True
        self.update()
        if not active:
            self.anim.stop()
        else:
            slow_only = self.pulse <= 0 and self.flash <= 0 and abs(t - (self._op or t)) <= 0.005
            want = FRAME_MS * 2 if slow_only else FRAME_MS
            if self.anim.interval() != want:
                self.anim.setInterval(want)

    def _animate(self):
        if not self.anim.isActive():
            self.anim.start(FRAME_MS)

    def bump(self):
        self.pulse = 1.0
        self.last_active = time.monotonic()
        self._animate()

    def celebrate(self):
        self.flash = 1.0
        self.last_active = time.monotonic()
        self._animate()

    def glow(self):
        self.remind_glow = 1.0
        self._animate()

    # ------------------------------------------------------------------ painting
    def _fit_size(self, text, fam, rect, start):
        key = (text, fam, int(rect.width()), int(rect.height()), int(start))
        size = self._fit_cache.get(key)
        if size is not None:
            return size
        size = int(start)
        flags = int(Qt.AlignCenter | Qt.TextWordWrap)
        while size > 7:
            br = QFontMetrics(QFont(fam, size)).boundingRect(rect.toRect(), flags, text)
            if br.height() <= rect.height() and br.width() <= rect.width():
                break
            size -= 1
        if len(self._fit_cache) > 64:
            self._fit_cache.clear()
        self._fit_cache[key] = size
        return size

    def paintEvent(self, ev):
        s = self.state
        th = self.th
        w, it = s.current()
        goal = max(1, int(w["goal"]))
        cnt = s.counts.get(w["id"], 0)
        W, H = self.width(), self.height()
        k = self.k()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setOpacity(self._op if self._op is not None else 1.0)

        rect = QRectF(3, 3, W - 6, H - 6)
        radius = 18 * k
        g = QLinearGradient(0, 0, 0, H)
        g.setColorAt(0, th["bg1"])
        g.setColorAt(1, th["bg2"])
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        p.fillPath(path, g)

        if self.flash > 0:
            c = QColor(th["acc"])
            c.setAlphaF(0.45 * self.flash)
            p.fillPath(path, c)
        glow = max(self.pulse * 0.9, self.remind_glow)
        pen_c = QColor(th["acc"])
        pen_c.setAlphaF(min(1.0, 0.55 + 0.45 * glow))
        p.setPen(QPen(pen_c, (1.4 + 2.2 * glow) * k))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        inner = QPainterPath()
        inner.addRoundedRect(rect.adjusted(6 * k, 6 * k, -6 * k, -6 * k), radius * .7, radius * .7)
        c2 = QColor(th["acc"])
        c2.setAlphaF(0.25)
        p.setPen(QPen(c2, 0.8))
        p.drawPath(inner)

        fam = s.settings.get("font_family", "Aref Ruqaa")
        prog = min(1.0, cnt / goal)
        done = cnt >= goal

        if s.settings.get("mini"):
            p.setFont(QFont(fam, max(8, int(26 * k)), QFont.Bold))
            p.setPen(th["acc_l"] if done else th["text"])
            p.setLayoutDirection(num_dir())
            p.drawText(QRectF(0, 4 * k, W, H - 22 * k), Qt.AlignCenter, ("⏸ " if s.paused else "") + fmt(cnt))
            self._bar(p, QRectF(16 * k, H - 18 * k, W - 32 * k, 5 * k), prog)
        else:
            p.setFont(ui_font(max(7, int(8.5 * k))))
            hc = QColor(th["acc_l"])
            hc.setAlphaF(0.85)
            p.setPen(hc)
            top = QRectF(16 * k, 10 * k, W - 32 * k, 18 * k)
            rtl = is_rtl()
            cat_al = (Qt.AlignRight if rtl else Qt.AlignLeft) | Qt.AlignAbsolute | Qt.AlignVCenter
            pos_al = (Qt.AlignLeft if rtl else Qt.AlignRight) | Qt.AlignAbsolute | Qt.AlignVCenter
            p.setLayoutDirection(ui_dir())
            p.drawText(top, cat_al, tr(CAT_NAME.get(it.get("cat"), "")))
            p.setLayoutDirection(num_dir() if not s.paused else ui_dir())
            p.drawText(top, pos_al, (tr("⏸ موقوف   ") if s.paused else "")
                       + "%s / %s" % (fmt(s.index + 1), fmt(len(s.wird))))

            text_rect = QRectF(16 * k, 28 * k, W - 32 * k, H * 0.46)
            size = self._fit_size(it["text"], fam, text_rect, 30 * k)
            p.setFont(QFont(fam, size))
            p.setPen(th["text"])
            p.setLayoutDirection(Qt.RightToLeft)            # adhkar are always Arabic
            p.drawText(text_rect, Qt.AlignCenter | Qt.TextWordWrap, it["text"])

            cy = text_rect.bottom() + 2 * k
            p.setFont(QFont(fam, max(8, int(24 * k)), QFont.Bold))
            p.setPen(th["acc_l"] if done else th["acc"])
            p.setLayoutDirection(num_dir())                 # 5 / 100  or  ٥ / ١٠٠
            ctext = fmt(cnt) + "  /  " + fmt(goal)
            if done:
                ctext = ctext + "  ✓" if not s.settings.get("arabic_digits") else "✓  " + ctext
            p.drawText(QRectF(0, cy, W, 40 * k), Qt.AlignCenter, ctext)
            self._bar(p, QRectF(22 * k, H - 20 * k, W - 44 * k, 6 * k), prog)

        if self.osd:
            p.setOpacity(1.0)
            p.setFont(ui_font(max(7, int(9 * k)), True))
            fm = p.fontMetrics()
            tw = min(W - 8, fm.horizontalAdvance(self.osd) + 18 * k)
            if s.settings.get("mini"):
                box = QRectF((W - tw) / 2, 4, tw, 20 * k)
            else:
                box = QRectF((W - tw) / 2, H / 2 - 13 * k, tw, 26 * k)
            bg = QColor(th["bg2"])
            bg.setAlphaF(0.92)
            p.setPen(QPen(th["acc"], 1))
            p.setBrush(bg)
            p.drawRoundedRect(box, 8 * k, 8 * k)
            p.setPen(th["acc_l"])
            p.setLayoutDirection(ui_dir())
            p.drawText(box, Qt.AlignCenter, self.osd)
        p.end()

    def _bar(self, p, r, prog):
        th = self.th
        p.setPen(Qt.NoPen)
        p.setBrush(th["track"])
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        if prog > 0:
            fr = QRectF(r)
            fr.setWidth(max(r.height(), r.width() * prog))
            if is_rtl():
                fr.moveRight(r.right())                   # RTL fills from the right, LTR from the left
            g = QLinearGradient(fr.topLeft(), fr.topRight())
            g.setColorAt(0, th["acc_l"])
            g.setColorAt(1, th["acc"])
            p.setBrush(g)
            p.drawRoundedRect(fr, r.height() / 2, r.height() / 2)

    # ------------------------------------------------------------------ mouse on the widget itself
    def mousePressEvent(self, e):
        self.wake()
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._moved = False
        elif e.button() == Qt.RightButton:
            self.app.show_menu(e.globalPosition().toPoint())
        e.accept()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            np_ = e.globalPosition().toPoint() - self._drag
            if not self._moved and (np_ - self.pos()).manhattanLength() > 4:
                self._moved = True
            if self._moved:
                self.move(np_)
        e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._drag is not None:
            if self._moved:
                if not self._on_screen(self.pos()):
                    self.move(self._valid_pos(None))
                self.state.pos = [self.x(), self.y()]
                self.app.schedule_save()
            elif self.state.settings.get("click_action") == "single":
                self.app.do_action("inc")
            self._drag = None
            self.last_active = time.monotonic()
        e.accept()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            mode = self.state.settings.get("click_action")
            if mode == "double":
                self.app.do_action("inc")
            elif mode == "single":
                self.mousePressEvent(e)      # second click of a fast pair still counts
        e.accept()

    def wheelEvent(self, e):
        e.accept()
        dy = e.angleDelta().y()
        if e.modifiers() & Qt.ControlModifier:
            self._op_wheel += dy
            while abs(self._op_wheel) >= 120:
                self.change_opacity(5 if self._op_wheel > 0 else -5)
                self._op_wheel -= 120 if self._op_wheel > 0 else -120
            return
        if not self.state.settings.get("wheel_count", False):
            return
        # accumulate so high-resolution touchpads don't add dozens per swipe
        self._wheel += dy
        while abs(self._wheel) >= 120:
            self.app.do_action("inc" if self._wheel > 0 else "dec")
            self._wheel -= 120 if self._wheel > 0 else -120
