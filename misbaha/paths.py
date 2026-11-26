"""File locations, logging and crash diagnostics."""

import datetime
import faulthandler
import os
import sys
import threading
import traceback

from misbaha import APP_NAME

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_MAX_BYTES = 512 * 1024


def resource_dir():
    """Folder holding bundled resources (fonts). Works for PyInstaller builds too."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "misbaha")
    return PACKAGE_DIR


def app_dir():
    """Folder of the running program (exe folder when frozen, repository root otherwise)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(PACKAGE_DIR)


def _pick_data_dir():
    # 0) --data-dir=<folder> (used when restarting as administrator, which may be another account)
    for arg in sys.argv[1:]:
        if arg.startswith("--data-dir="):
            return arg.split("=", 1)[1]
    # 1) explicit override (tests, power users)
    env = os.environ.get("MISBAHA_DATA_DIR")
    if env:
        return env
    # 2) portable mode: a "misbaha-data" folder next to the program
    portable = os.path.join(app_dir(), "misbaha-data")
    if os.path.isdir(portable):
        return portable
    # 3) per-user application data
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, APP_NAME)


DATA_DIR = _pick_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, "state.json")
LOG_FILE = os.path.join(DATA_DIR, "error.log")
CRASH_FILE = os.path.join(DATA_DIR, "crash.log")

_log_lock = threading.Lock()


def _rotate(path):
    try:
        if os.path.getsize(path) > LOG_MAX_BYTES:
            os.replace(path, path + ".1")
    except OSError:
        pass


def log(msg):
    """Append one line to error.log. Never raises."""
    try:
        with _log_lock:
            _rotate(LOG_FILE)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write("[%s] %s\n" % (datetime.datetime.now().isoformat(timespec="seconds"), msg))
    except Exception:
        pass


class _LogStream:
    """Replacement for stdout/stderr when there is no console (pythonw / --noconsole exe)."""

    def write(self, text):
        if text and text.strip():
            log(text.rstrip())
        return len(text or "")

    def flush(self):
        pass

    def isatty(self):
        return False


_crash_fh = None


def install_error_handlers():
    global _crash_fh
    if sys.stdout is None:
        sys.stdout = _LogStream()
    if sys.stderr is None:
        sys.stderr = _LogStream()

    def hook(etype, value, tb):
        log("".join(traceback.format_exception(etype, value, tb)).rstrip())
        try:
            sys.__excepthook__(etype, value, tb)
        except Exception:
            pass

    sys.excepthook = hook

    def thread_hook(args):
        log("thread %s: %s" % (getattr(args.thread, "name", "?"),
                               "".join(traceback.format_exception(args.exc_type, args.exc_value,
                                                                  args.exc_traceback)).rstrip()))

    threading.excepthook = thread_hook
    # native crashes (access violations inside Qt/ctypes) are written here instead of vanishing
    try:
        _rotate(CRASH_FILE)
        _crash_fh = open(CRASH_FILE, "a", encoding="utf-8")
        faulthandler.enable(file=_crash_fh, all_threads=True)
    except Exception:
        _crash_fh = None


def dump_all_threads(reason):
    """Write the stack of every thread to crash.log (used by the freeze detector)."""
    if _crash_fh is None:
        return
    try:
        _crash_fh.write("\n[%s] %s\n" % (datetime.datetime.now().isoformat(timespec="seconds"), reason))
        _crash_fh.flush()
        faulthandler.dump_traceback(file=_crash_fh, all_threads=True)
        _crash_fh.flush()
    except Exception:
        pass
