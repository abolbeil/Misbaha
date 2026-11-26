"""Keyboard shortcut strings  <->  Windows RegisterHotKey (modifiers, virtual-key).

Format stored in settings:  "<ctrl>+<alt>+<page_up>"   (lower case, one key, any modifiers).
Virtual-key codes are layout independent, so shortcuts keep working with the Arabic layout.
"""

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000

MODIFIERS = {
    "ctrl": MOD_CONTROL, "control": MOD_CONTROL, "ctrl_l": MOD_CONTROL, "ctrl_r": MOD_CONTROL,
    "alt": MOD_ALT, "alt_l": MOD_ALT, "alt_r": MOD_ALT, "alt_gr": MOD_ALT | MOD_CONTROL,
    "shift": MOD_SHIFT, "shift_l": MOD_SHIFT, "shift_r": MOD_SHIFT,
    "win": MOD_WIN, "cmd": MOD_WIN, "super": MOD_WIN, "windows": MOD_WIN,
}
MOD_ORDER = [(MOD_CONTROL, "ctrl"), (MOD_ALT, "alt"), (MOD_SHIFT, "shift"), (MOD_WIN, "win")]
MOD_PRETTY = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"}

KEYS = {
    "space": 0x20, "page_up": 0x21, "page_down": 0x22, "end": 0x23, "home": 0x24,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "insert": 0x2D, "delete": 0x2E,
    "pause": 0x13, "scroll_lock": 0x91, "tab": 0x09, "enter": 0x0D, "backspace": 0x08,
    "esc": 0x1B, "print_screen": 0x2C,
    "num_multiply": 0x6A, "num_add": 0x6B, "num_subtract": 0x6D, "num_decimal": 0x6E, "num_divide": 0x6F,
    "media_next": 0xB0, "media_prev": 0xB1, "media_play_pause": 0xB3,
    "comma": 0xBC, "period": 0xBE, "minus": 0xBD, "equal": 0xBB,
}
for _i in range(10):
    KEYS[str(_i)] = 0x30 + _i
    KEYS["num%d" % _i] = 0x60 + _i
for _i in range(26):
    KEYS[chr(ord("a") + _i)] = 0x41 + _i
for _i in range(1, 25):
    KEYS["f%d" % _i] = 0x6F + _i

ALIASES = {
    "pgup": "page_up", "prior": "page_up", "pageup": "page_up",
    "pgdn": "page_down", "pagedown": "page_down", "next": "page_down",
    "del": "delete", "ins": "insert", "return": "enter", "escape": "esc",
    "scrolllock": "scroll_lock", "spacebar": "space",
}
VK_TO_NAME = {}
for _n, _v in KEYS.items():
    VK_TO_NAME.setdefault(_v, _n)

PRETTY_KEYS = {"page_up": "PgUp", "page_down": "PgDn", "space": "Space", "delete": "Del",
               "insert": "Ins", "scroll_lock": "ScrollLock", "print_screen": "PrtSc", "esc": "Esc",
               "backspace": "Backspace", "enter": "Enter", "tab": "Tab", "pause": "Pause",
               "home": "Home", "end": "End", "up": "Up", "down": "Down", "left": "Left", "right": "Right"}
AHK_KEYS = {"page_up": "{PgUp}", "page_down": "{PgDn}", "space": "{Space}", "delete": "{Del}",
            "insert": "{Ins}", "home": "{Home}", "end": "{End}", "up": "{Up}", "down": "{Down}",
            "left": "{Left}", "right": "{Right}", "pause": "{Pause}", "tab": "{Tab}", "enter": "{Enter}",
            "esc": "{Esc}", "backspace": "{BS}", "scroll_lock": "{ScrollLock}"}


def _tokens(spec):
    for raw in str(spec or "").lower().replace(" ", "").split("+"):
        tok = raw.strip().strip("<>")
        if tok:
            yield ALIASES.get(tok, tok)


def parse(spec):
    """Return (modifiers, vk, canonical_key_name). Raises ValueError for invalid shortcuts."""
    mods, key = 0, None
    for tok in _tokens(spec):
        if tok in MODIFIERS:
            mods |= MODIFIERS[tok]
        elif tok in KEYS:
            if key is not None:
                raise ValueError("only one non-modifier key is allowed: %s" % spec)
            key = tok
        else:
            raise ValueError("unknown key '%s'" % tok)
    if key is None:
        raise ValueError("no key in shortcut: %s" % spec)
    if not mods and not key.startswith("f") and not key.startswith("media_") and key not in ("pause", "scroll_lock"):
        raise ValueError("add Ctrl, Alt, Shift or Win to '%s'" % spec)
    return mods, KEYS[key], key


def build(mods, key):
    parts = ["<%s>" % name for bit, name in MOD_ORDER if mods & bit]
    parts.append(key if len(key) == 1 else "<%s>" % key)
    return "+".join(parts)


def normalize(spec):
    """Canonical text for a shortcut, '' for empty. Raises ValueError for invalid."""
    if not str(spec or "").strip():
        return ""
    mods, _vk, key = parse(spec)
    return build(mods, key)


def is_valid(spec):
    try:
        normalize(spec)
        return True
    except ValueError:
        return False


def pretty(spec):
    """Human readable: 'Ctrl+Alt+PgUp'. Returns the raw text if invalid, '' if empty."""
    if not str(spec or "").strip():
        return ""
    try:
        mods, _vk, key = parse(spec)
    except ValueError:
        return str(spec)
    parts = [MOD_PRETTY[name] for bit, name in MOD_ORDER if mods & bit]
    parts.append(PRETTY_KEYS.get(key, key.upper() if len(key) <= 3 else key.replace("_", " ").title()))
    return "+".join(parts)


def ahk(spec):
    """AutoHotkey 'Send' syntax for the shortcut, e.g. '^!{PgUp}'."""
    try:
        mods, _vk, key = parse(spec)
    except ValueError:
        return ""
    pre = ("^" if mods & MOD_CONTROL else "") + ("!" if mods & MOD_ALT else "") + \
          ("+" if mods & MOD_SHIFT else "") + ("#" if mods & MOD_WIN else "")
    if key in AHK_KEYS:
        k = AHK_KEYS[key]
    elif key.startswith("f") and key[1:].isdigit():
        k = "{%s}" % key.upper()
    elif len(key) == 1:
        k = key
    else:
        k = "{%s}" % key
    return pre + k
