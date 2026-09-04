"""Win32 window handling for the harness: find, measure, title, place.

The measuring half exists because the resolution the reel is shot at is the engine
WINDOW's client area - not any setting. `main-buff-*` in preferences.json is the
engine's internal image buffer and does not tell you what a capture will contain.
The only honest answer comes from the live window, so nothing here guesses.

The find-by-pid approach is lifted from sbs_cli/src/run_cmd.py: matching on the
process rather than on a title is what makes it deterministic when several engine
windows exist and none of them are titled yet.
"""
import ctypes
import time


try:
    _user32 = ctypes.windll.user32
    IS_WINDOWS = True
except AttributeError:                      # not Windows; every call becomes a no-op
    _user32 = None
    IS_WINDOWS = False


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def set_dpi_aware():
    """Per-monitor DPI v2, BEFORE any measuring.

    Without it a scaled display reports window rects in virtual pixels while the
    capture holds real ones, so every measurement is quietly wrong by the scale
    factor - and it looks like a correct number, which is the dangerous part.
    """
    if not IS_WINDOWS:
        return False
    try:
        # -4 = DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        return bool(_user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))
    except Exception:
        try:
            return bool(ctypes.windll.shcore.SetProcessDpiAwareness(2))
        except Exception:
            return False


def windows_of_pid(pid):
    """Every visible top-level window belonging to a process."""
    if not IS_WINDOWS:
        return []
    found = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def cb(hwnd, _lparam):
        owner = ctypes.c_ulong()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and _user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    _user32.EnumWindows(WNDENUMPROC(cb), None)
    return found


def window_of_pid(pid, timeout=15.0, poll=0.25):
    """Wait for a process to show a window, and return its hwnd (or None)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        got = windows_of_pid(pid)
        if got:
            return got[0]
        time.sleep(poll)
    return None


def client_size(hwnd):
    """The window's CLIENT area in pixels - what a capture of it actually contains.

    Client, not window: GetWindowRect includes the title bar and borders, which are
    not in the frame, so using it would overstate the height by ~30px and make an
    aspect check disagree with reality for no reason.
    """
    if not IS_WINDOWS or not hwnd:
        return None
    r = RECT()
    if not _user32.GetClientRect(hwnd, ctypes.byref(r)):
        return None
    return (r.right - r.left, r.bottom - r.top)


def set_title(hwnd, title):
    """Rename a window so OBS can capture it by title."""
    if IS_WINDOWS and hwnd:
        _user32.SetWindowTextW(hwnd, title)


def move(hwnd, x, y, w, h):
    """Place and SIZE a window. Never minimize one that is being captured:
    game_capture hooks the swap chain, and a minimized window stops presenting."""
    if IS_WINDOWS and hwnd:
        _user32.MoveWindow(hwnd, int(x), int(y), int(w), int(h), True)


SW_MAXIMIZE = 3
SW_RESTORE = 9


def screen_size():
    """The primary monitor, in real pixels (call set_dpi_aware first)."""
    if not IS_WINDOWS:
        return None
    return (_user32.GetSystemMetrics(0), _user32.GetSystemMetrics(1))


def maximize(hwnd):
    """Fill the monitor - unless the window is ALREADY filling it.

    A window left at its opening size shoots at that size, so the reel would be cut
    from whatever the engine happened to open at. Maximizing makes the capture the
    monitor's native resolution, which is the largest honest source available.

    But maximizing is NOT as good as the engine's own fullscreen mode: a maximized
    window keeps its title bar, so its CLIENT area is the monitor height minus the
    chrome - 2560x1351 on a 2560x1440 screen, which is 1.895:1, not 16:9. The engine's
    fullscreen gives a true 2560x1440. Fullscreen is set by hand (it is not scriptable),
    so when a window already covers the screen this leaves it alone rather than
    dragging it back out of fullscreen.

    Returns the resulting client size, so the caller records what it actually got.
    """
    if not IS_WINDOWS or not hwnd:
        return None
    size = client_size(hwnd)
    screen = screen_size()
    if size and screen and size[0] >= screen[0] and size[1] >= screen[1]:
        return size                          # already fullscreen - do not touch it
    _user32.ShowWindow(hwnd, SW_MAXIMIZE)
    _user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)                          # let the swap chain resize before measuring
    return client_size(hwnd)
