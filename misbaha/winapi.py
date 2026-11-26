"""Thin ctypes wrappers around the Win32 functions Misbaha needs.

Every function is safe to call on other platforms (it does nothing / returns a neutral value),
and never raises: failures are logged once and ignored, so a Windows quirk can't crash the app.
"""

import ctypes
import os
import sys

from misbaha.paths import log

IS_WIN = sys.platform == "win32"

if IS_WIN:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

    LRESULT = ctypes.c_ssize_t
    ULONG_PTR = ctypes.c_size_t
    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    class MSLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [("pt", wintypes.POINT), ("mouseData", wintypes.DWORD), ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    def _sig(fn, res, *args):
        fn.restype = res
        fn.argtypes = list(args)
        return fn

    SetWindowsHookExW = _sig(user32.SetWindowsHookExW, wintypes.HHOOK, ctypes.c_int, HOOKPROC,
                             wintypes.HINSTANCE, wintypes.DWORD)
    UnhookWindowsHookEx = _sig(user32.UnhookWindowsHookEx, wintypes.BOOL, wintypes.HHOOK)
    CallNextHookEx = _sig(user32.CallNextHookEx, LRESULT, wintypes.HHOOK, ctypes.c_int,
                          wintypes.WPARAM, wintypes.LPARAM)
    GetMessageW = _sig(user32.GetMessageW, wintypes.BOOL, ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                       wintypes.UINT, wintypes.UINT)
    PeekMessageW = _sig(user32.PeekMessageW, wintypes.BOOL, ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                        wintypes.UINT, wintypes.UINT, wintypes.UINT)
    TranslateMessage = _sig(user32.TranslateMessage, wintypes.BOOL, ctypes.POINTER(wintypes.MSG))
    DispatchMessageW = _sig(user32.DispatchMessageW, LRESULT, ctypes.POINTER(wintypes.MSG))
    PostThreadMessageW = _sig(user32.PostThreadMessageW, wintypes.BOOL, wintypes.DWORD, wintypes.UINT,
                              wintypes.WPARAM, wintypes.LPARAM)
    RegisterHotKey = _sig(user32.RegisterHotKey, wintypes.BOOL, wintypes.HWND, ctypes.c_int,
                          wintypes.UINT, wintypes.UINT)
    UnregisterHotKey = _sig(user32.UnregisterHotKey, wintypes.BOOL, wintypes.HWND, ctypes.c_int)
    GetModuleHandleW = _sig(kernel32.GetModuleHandleW, wintypes.HMODULE, wintypes.LPCWSTR)
    GetCurrentThreadId = _sig(kernel32.GetCurrentThreadId, wintypes.DWORD)
    GetCurrentThread = _sig(kernel32.GetCurrentThread, wintypes.HANDLE)
    SetThreadPriority = _sig(kernel32.SetThreadPriority, wintypes.BOOL, wintypes.HANDLE, ctypes.c_int)
    GetTickCount = _sig(kernel32.GetTickCount, wintypes.DWORD)
    OpenProcess = _sig(kernel32.OpenProcess, wintypes.HANDLE, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    CloseHandle = _sig(kernel32.CloseHandle, wintypes.BOOL, wintypes.HANDLE)
    OpenProcessToken = _sig(advapi32.OpenProcessToken, wintypes.BOOL, wintypes.HANDLE, wintypes.DWORD,
                            ctypes.POINTER(wintypes.HANDLE))
    GetTokenInformation = _sig(advapi32.GetTokenInformation, wintypes.BOOL, wintypes.HANDLE, ctypes.c_int,
                               ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
    SetWindowPos = _sig(user32.SetWindowPos, wintypes.BOOL, wintypes.HWND, wintypes.HWND, ctypes.c_int,
                        ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT)
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        GetWindowLongPtrW = _sig(user32.GetWindowLongPtrW, ctypes.c_ssize_t, wintypes.HWND, ctypes.c_int)
        SetWindowLongPtrW = _sig(user32.SetWindowLongPtrW, ctypes.c_ssize_t, wintypes.HWND, ctypes.c_int,
                                 ctypes.c_ssize_t)
    else:
        GetWindowLongPtrW = _sig(user32.GetWindowLongW, ctypes.c_long, wintypes.HWND, ctypes.c_int)
        SetWindowLongPtrW = _sig(user32.SetWindowLongW, ctypes.c_long, wintypes.HWND, ctypes.c_int,
                                 ctypes.c_long)
    GetForegroundWindow = _sig(user32.GetForegroundWindow, wintypes.HWND)
    GetWindowThreadProcessId = _sig(user32.GetWindowThreadProcessId, wintypes.DWORD, wintypes.HWND,
                                    ctypes.POINTER(wintypes.DWORD))
    GetWindowRect = _sig(user32.GetWindowRect, wintypes.BOOL, wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    MonitorFromWindow = _sig(user32.MonitorFromWindow, wintypes.HMONITOR, wintypes.HWND, wintypes.DWORD)
    GetMonitorInfoW = _sig(user32.GetMonitorInfoW, wintypes.BOOL, wintypes.HMONITOR,
                           ctypes.POINTER(MONITORINFO))
    GetClassNameW = _sig(user32.GetClassNameW, ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    IsZoomed = _sig(user32.IsZoomed, wintypes.BOOL, wintypes.HWND)
    IsWindowVisible = _sig(user32.IsWindowVisible, wintypes.BOOL, wintypes.HWND)
    GetAsyncKeyState = _sig(user32.GetAsyncKeyState, ctypes.c_short, ctypes.c_int)
    GetLastInputInfo = _sig(user32.GetLastInputInfo, wintypes.BOOL, ctypes.POINTER(LASTINPUTINFO))
    ShellExecuteW = _sig(shell32.ShellExecuteW, wintypes.HINSTANCE, wintypes.HWND, wintypes.LPCWSTR,
                         wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int)

# --- constants ---
WH_MOUSE_LL = 14
HC_ACTION = 0
WM_QUIT = 0x0012
WM_HOTKEY = 0x0312
WM_APP = 0x8000
WM_MOUSEMOVE = 0x0200
WM_MBUTTONDOWN, WM_MBUTTONUP = 0x0207, 0x0208
WM_XBUTTONDOWN, WM_XBUTTONUP = 0x020B, 0x020C
WM_MOUSEHWHEEL = 0x020E
PM_NOREMOVE = 0
THREAD_PRIORITY_HIGHEST = 2
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE, SWP_FRAMECHANGED, SWP_NOOWNERZORDER = \
    0x0001, 0x0002, 0x0004, 0x0010, 0x0020, 0x0200
MONITOR_DEFAULTTONEAREST = 2
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TOKEN_QUERY = 0x0008
TokenElevation = 20
VK_CONTROL = 0x11
SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Windows.UI.Core.CoreWindow",
                 "MultitaskingViewFrame", "XamlExplorerHostIslandWindow", "ForegroundStaging",
                 "TaskListThumbnailWnd", "LockScreenBackstopFrame"}

_logged = set()


def _fail(where, e):
    if where not in _logged:            # log each kind of failure once, never spam
        _logged.add(where)
        log("%s failed: %s" % (where, e))


# --- windows -----------------------------------------------------------------------------
def set_topmost(hwnd):
    """Re-assert HWND_TOPMOST without activating or moving the window."""
    if not IS_WIN or not hwnd:
        return
    try:
        SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                     SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_NOOWNERZORDER)
    except Exception as e:
        _fail("SetWindowPos", e)


def is_topmost(hwnd):
    if not IS_WIN or not hwnd:
        return True
    try:
        return bool(GetWindowLongPtrW(hwnd, GWL_EXSTYLE) & WS_EX_TOPMOST)
    except Exception:
        return True


def set_overlay_style(hwnd, click_through):
    """Make the widget a non-activating tool window; toggle mouse transparency natively.

    Doing it with SetWindowLongPtr avoids Qt re-creating the native window (flicker, lost top-most).
    Returns True when the style was changed.
    """
    if not IS_WIN or not hwnd:
        return False
    try:
        ex = GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        new = ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_LAYERED
        new = (new | WS_EX_TRANSPARENT) if click_through else (new & ~WS_EX_TRANSPARENT)
        if new != ex:
            SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new)
            SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE
                         | SWP_FRAMECHANGED | SWP_NOOWNERZORDER)
            return True
    except Exception as e:
        _fail("SetWindowLongPtr", e)
    return False


def ctrl_down():
    if not IS_WIN:
        return False
    try:
        return bool(GetAsyncKeyState(VK_CONTROL) & 0x8000)
    except Exception:
        return False


def user_idle_seconds():
    """Seconds since the last keyboard/mouse input anywhere in the session."""
    if not IS_WIN:
        return 0.0
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if GetLastInputInfo(ctypes.byref(lii)):
            return ((GetTickCount() - lii.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception as e:
        _fail("GetLastInputInfo", e)
    return 0.0


def _window_pid(hwnd):
    pid = wintypes.DWORD(0)
    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def foreground_window():
    if not IS_WIN:
        return 0
    try:
        return GetForegroundWindow() or 0
    except Exception:
        return 0


def foreground_is_fullscreen(own_pid=None):
    """True when the foreground window is a real full-screen app (video, slideshow, game).

    Maximized windows (e.g. Revit with an auto-hide taskbar) are NOT treated as full-screen.
    """
    if not IS_WIN:
        return False
    try:
        hwnd = GetForegroundWindow()
        if not hwnd or not IsWindowVisible(hwnd) or IsZoomed(hwnd):
            return False
        if own_pid and _window_pid(hwnd) == own_pid:
            return False
        buf = ctypes.create_unicode_buffer(128)
        GetClassNameW(hwnd, buf, 128)
        if buf.value in SHELL_CLASSES:
            return False
        r = wintypes.RECT()
        if not GetWindowRect(hwnd, ctypes.byref(r)):
            return False
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if not GetMonitorInfoW(MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST), ctypes.byref(mi)):
            return False
        m = mi.rcMonitor
        return r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom
    except Exception as e:
        _fail("fullscreen check", e)
        return False


def _process_elevated(pid):
    """True / False, or None when it can't be determined (protected or higher-integrity process)."""
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        tok = wintypes.HANDLE()
        if not OpenProcessToken(h, TOKEN_QUERY, ctypes.byref(tok)):
            return None                  # access denied: almost always an elevated process
        try:
            val = wintypes.DWORD(0)
            size = wintypes.DWORD(0)
            if not GetTokenInformation(tok, TokenElevation, ctypes.byref(val), ctypes.sizeof(val),
                                       ctypes.byref(size)):
                return None
            return bool(val.value)
        finally:
            CloseHandle(tok)
    finally:
        CloseHandle(h)


_SELF_ELEVATED = None


def self_elevated():
    """Is Misbaha itself running as administrator? (cached: it can't change while running)"""
    global _SELF_ELEVATED
    if _SELF_ELEVATED is None:
        _SELF_ELEVATED = False
        if IS_WIN:
            try:
                _SELF_ELEVATED = bool(_process_elevated(os.getpid()))
            except Exception as e:
                _fail("self elevation", e)
    return _SELF_ELEVATED


def foreground_blocked_by_uipi():
    """True when the foreground app runs at a higher privilege than us: Windows then hides
    its mouse input from our hook (keyboard shortcuts still work)."""
    if not IS_WIN or self_elevated():
        return False
    try:
        hwnd = GetForegroundWindow()
        if not hwnd:
            return False
        pid = _window_pid(hwnd)
        if not pid or pid == os.getpid():
            return False
        el = _process_elevated(pid)
        return el is None or el
    except Exception as e:
        _fail("foreground elevation", e)
        return False


def run_as_admin(exe, params):
    """Start a program elevated (UAC prompt). Returns True when it was launched."""
    if not IS_WIN:
        return False
    try:
        return int(ShellExecuteW(None, "runas", exe, params, None, 1) or 0) > 32
    except Exception as e:
        _fail("ShellExecuteW", e)
        return False


def set_app_user_model_id(app_id):
    if not IS_WIN:
        return
    try:
        shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(app_id))
    except Exception:
        pass
