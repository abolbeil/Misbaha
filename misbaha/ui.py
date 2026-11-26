"""Theme colours, fonts and the painted app icon."""

import math
import os

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap, QRadialGradient

from misbaha.data import THEMES
from misbaha.paths import log, resource_dir

FALLBACK_FONTS = ["Aref Ruqaa", "Amiri", "Reem Kufi", "Noto Naskh Arabic", "Traditional Arabic",
                  "Sakkal Majalla", "Arabic Typesetting", "Segoe UI"]
_UI_FAMILY = None
_ARABIC_FONTS = None
_ICON_CACHE = {}


def luminance(c):
    return (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255.0


def get_theme(settings):
    key = settings.get("theme", "emerald")
    if key == "custom":
        bg = QColor(settings.get("custom_bg", "#0B3D91"))
        acc = QColor(settings.get("custom_accent", "#FFD166"))
        light_bg = luminance(bg) > 0.6
        th = dict(bg1=bg, bg2=bg.darker(125) if light_bg else bg.darker(230), acc=acc,
                  acc_l=acc.darker(150) if light_bg else acc.lighter(140),
                  text=QColor("#1F2A26") if light_bg else QColor("#F7F7F2"))
    else:
        t = THEMES.get(key, THEMES["emerald"])
        th = dict(bg1=QColor(t[1]), bg2=QColor(t[2]), acc=QColor(t[3]), acc_l=QColor(t[4]), text=QColor(t[5]))
    th["track"] = QColor(th["text"])
    th["track"].setAlpha(35)
    th["key"] = (key, th["bg1"].name(), th["acc"].name())
    return th


def accent_css(th):
    return "background:%s;color:%s;" % (th["bg1"].name(), th["acc_l"].name())


def button_css(th):
    return ("QPushButton{background:%s;color:%s;border:1px solid %s;border-radius:6px;padding:7px 18px;"
            "font-weight:bold;} QPushButton:hover{background:%s;}"
            % (th["bg1"].name(), th["acc_l"].name(), th["acc"].name(), th["bg2"].name()))


def load_fonts():
    fdir = os.path.join(resource_dir(), "fonts")
    if not os.path.isdir(fdir):
        log("fonts folder not found: %s" % fdir)
        return
    for fn in sorted(os.listdir(fdir)):
        if fn.lower().endswith((".ttf", ".otf")):
            if QFontDatabase.addApplicationFont(os.path.join(fdir, fn)) < 0:
                log("font failed to load: %s" % fn)


def arabic_font_list():
    """Fonts able to show Arabic. Cached: enumerating every system font is slow on big font sets."""
    global _ARABIC_FONTS
    if _ARABIC_FONTS is None:
        fams = QFontDatabase.families()
        famset = set(fams)
        out = [f for f in FALLBACK_FONTS if f in famset]
        for f in sorted(fams):
            if f not in out and not f.startswith("@") and \
                    QFontDatabase.WritingSystem.Arabic in QFontDatabase.writingSystems(f):
                out.append(f)
        _ARABIC_FONTS = out or ["Segoe UI"]
    return _ARABIC_FONTS


def ui_family():
    global _UI_FAMILY
    if _UI_FAMILY is None:
        fams = set(QFontDatabase.families())
        _UI_FAMILY = next((f for f in ("Noto Naskh Arabic", "Segoe UI", "Amiri") if f in fams),
                          QFont().family())
    return _UI_FAMILY


def ui_font(size=11, bold=False):
    f = QFont(ui_family(), size)
    f.setBold(bold)
    return f


def make_icon(th, size=64):
    """A misbaha (prayer-beads) icon painted in the theme colours. Cached per theme."""
    key = (th["key"], size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QRadialGradient(size / 2, size / 2, size / 2)
    g.setColorAt(0, th["bg1"].lighter(150))
    g.setColorAt(1, th["bg2"])
    p.setBrush(g)
    p.setPen(QPen(th["acc"], size * 0.05))
    p.drawEllipse(QRectF(size * .04, size * .04, size * .92, size * .92))
    p.setPen(Qt.NoPen)
    p.setBrush(th["acc_l"])
    r = size * 0.30
    for i in range(11):
        a = -math.pi / 2 + (i + 0.5) * 2 * math.pi / 12 + math.pi / 12
        p.drawEllipse(QRectF(size / 2 + r * math.cos(a) - size * .045, size / 2 + r * math.sin(a) - size * .045,
                             size * .09, size * .09))
    p.setBrush(th["acc"])
    p.drawRect(QRectF(size * .47, size * .12, size * .06, size * .16))
    p.end()
    icon = QIcon(pm)
    _ICON_CACHE[key] = icon
    return icon
