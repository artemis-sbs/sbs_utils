"""Launch the engine and bind each client window to the client_id the engine gave it.

The binding is the whole problem. OBS captures a WINDOW (by title), the harness drives
a CONSOLE (by client_id), and nothing in either world knows about the other. The join
is the process id:

    Popen -> pid -> hwnd (EnumWindows, matched on pid) -> retitle
    engine -> Gui.clients keys -> the NEW key is this pid's client_id

Clients are launched SERIALLY for exactly that reason: with two in flight, two new keys
appear and neither can be attributed. One at a time makes it deterministic.
"""
import os
import time
import subprocess

from . import windows


class Client:
    """One engine client: its process, its window, and its engine-side identity."""

    def __init__(self, role, proc, hwnd, client_id, title):
        self.role = role
        self.proc = proc
        self.hwnd = hwnd
        self.client_id = client_id
        self.title = title
        self.size = None

    def __repr__(self):
        return "<Client %s pid=%s hwnd=%s cid=%s %r>" % (
            self.role, self.proc.pid if self.proc else None,
            self.hwnd, self.client_id, self.title)


# The engine reports client ids as very large ints; ask for them as strings so the
# round trip through JSON cannot lose precision.
_CLIENT_KEYS = (
    "[str(k) for k in sorted(__import__('sbs_utils.gui', fromlist=['Gui']).Gui.clients.keys())]"
)


def client_ids(drv, timeout=10.0):
    """The engine's current client ids, server (0) included."""
    got = drv.eval(_CLIENT_KEYS, timeout=timeout)
    return [int(x) for x in (got or [])]


def wait_for_new_client(drv, before, timeout=60.0, poll=0.5):
    """Wait until exactly one new client id appears, and return it.

    Returns None on timeout. More than one new id means something else connected
    concurrently - the caller should treat that as a failed binding rather than
    guess which is which.
    """
    deadline = time.time() + timeout
    before = set(before)
    while time.time() < deadline:
        try:
            now = set(client_ids(drv, timeout=5.0))
        except Exception:
            time.sleep(poll)
            continue
        new = now - before
        if len(new) == 1:
            return new.pop()
        if len(new) > 1:
            return None
        time.sleep(poll)
    return None


def launch_client(drv, role, title, ip="127.0.0.1", timeout=60.0, maximize=True):
    """Start one client, bind it, title it, and measure it.

    Order matters: the window is found by PID before the title is set, because at
    launch the engine's window has no distinguishing title to find it by.
    """
    before = client_ids(drv)
    proc = subprocess.Popen(
        [drv.exe, "autostartclient", "clientautoconnectip=%s" % ip],
        cwd=drv.cosmos_dir, env=dict(os.environ))

    hwnd = windows.window_of_pid(proc.pid, timeout=30.0)
    cid = wait_for_new_client(drv, before, timeout=timeout)

    client = Client(role, proc, hwnd, cid, title)
    if hwnd:
        windows.set_title(hwnd, title)
        client.size = windows.maximize(hwnd) if maximize else windows.client_size(hwnd)
    return client


def stop(clients):
    for c in clients or []:
        try:
            if c.proc and c.proc.poll() is None:
                c.proc.terminate()
        except Exception:
            pass


def table(clients):
    """A printable pid -> hwnd -> client_id table. The M2 deliverable."""
    lines = ["  %-8s %-8s %-10s %-22s %s"
             % ("role", "pid", "hwnd", "client_id", "window size")]
    for c in clients:
        lines.append("  %-8s %-8s %-10s %-22s %s" % (
            c.role,
            c.proc.pid if c.proc else "-",
            c.hwnd if c.hwnd else "-",
            c.client_id if c.client_id is not None else "UNBOUND",
            ("%dx%d" % c.size) if c.size else "-"))
    return "\n".join(lines)
