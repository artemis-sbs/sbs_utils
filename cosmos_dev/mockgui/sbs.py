"""
cosmos_dev/mockgui/sbs.py — GUI-capable drop-in replacement for the engine sbs module.

Inherits all simulation state (space objects, navpoints, sides, etc.) from
cosmos_dev.mock.sbs, then overrides the send_gui_* functions with real
WebSocket-based implementations that stream widget commands to a browser client.

Usage:
    import cosmos_dev.mockgui.sbs as sbs
    sbs.start_server()
    sbs.create_new_sim()
    # all simulation + GUI functions now available as 'sbs.*'

For unit tests that don't need live GUI, use the base mock directly:
    from cosmos_dev.mock import sbs
"""

import sys
import multiprocessing
from typing import Any

# Pull in all simulation state — space objects, navpoints, sides, diplomacy, etc.
import cosmos_dev.mock.sbs as _base_mock
from cosmos_dev.mock.sbs import *   # noqa: F401,F403

# Re-register this module as 'sbs' so engine scripts that do `import sbs` get
# the GUI-capable version instead of the base no-op mock.
sys.modules["sbs"] = sys.modules[__name__]


def create_new_sim():
    """Creates a new simulation and syncs the local sim reference."""
    global sim
    result = _base_mock.create_new_sim()
    sim = _base_mock.sim
    return result


# ---------------------------------------------------------------------------
# Shared queues  (initialised by start_server)
# ---------------------------------------------------------------------------
# Outbound GUI commands — script engine writes, server reads.
gui_queue: multiprocessing.Queue = None          # type: ignore[assignment]


# Inbound connection lifecycle events from the server.
# {"event": "connect"|"disconnect", "clientID": int}
client_event_queue: multiprocessing.Queue = None  # type: ignore[assignment]

# Inbound widget events from the browser.
# {"type": "click"|"change"|..., "tag": str, "clientID": int, ...}
gui_event_queue: multiprocessing.Queue = None    # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Server launcher
# ---------------------------------------------------------------------------
def start_server(
    host: str = "0.0.0.0",
    port: int = 8765,
    cosmos_dir: "str | None" = None,
) -> multiprocessing.Process:
    """Start the WebSocket bridge server in a child process.

    Creates multiprocessing.Queue instances for all three queues, assigns them
    to this module so send_gui_* calls work immediately, then spawns the server
    process and waits until it is ready to accept connections.  Returns the
    Process object.

    cosmos_dir: Cosmos install root (e.g. /path/to/Cosmos-1-3-0). Images are
    served from <cosmos_dir>/data/graphics/. Defaults to sbs_utils.fs.exe_dir.

    Requires only Python stdlib — no pip packages needed.
    """
    global gui_queue, client_event_queue, gui_event_queue

    if cosmos_dir is None:
        try:
            from sbs_utils import fs as _fs
            cosmos_dir = _fs.exe_dir
        except Exception:
            pass

    gui_queue          = multiprocessing.Queue()
    client_event_queue = multiprocessing.Queue()
    gui_event_queue    = multiprocessing.Queue()
    ready              = multiprocessing.Event()

    from cosmos_dev.mockgui import server as server_mod

    p = multiprocessing.Process(
        target=server_mod.run_server,
        args=(gui_queue, client_event_queue, gui_event_queue, ready, host, port, cosmos_dir),
        daemon=True,
        name="sbs-server",
    )
    p.start()

    if not ready.wait(timeout=10):
        p.terminate()
        raise RuntimeError(f"sbs server did not start within 10 s on {host}:{port}")
    return p


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------
def _send(clientID: int, cmd: str, **kwargs: Any) -> None:
    """Serialise a command and enqueue it."""
    payload = {"clientID": clientID, "cmd": cmd, **kwargs}
    gui_queue.put(payload)


# ---------------------------------------------------------------------------
# Buffer control  (override base no-ops)
# ---------------------------------------------------------------------------
def send_gui_clear(clientID: int, tag: str) -> None:
    """Clears all GUI elements from screen on the targeted client."""
    _send(clientID, "clear", tag=tag)


def send_gui_complete(clientID: int, tag: str) -> None:
    """Flips the double-buffered display list on the targeted client."""
    _send(clientID, "complete", tag=tag)


# ---------------------------------------------------------------------------
# Widget helpers  (override base no-ops)
# ---------------------------------------------------------------------------
def _widget(cmd: str, clientID: int, parent: str, tag: str,
            style: str, left: float, top: float,
            right: float, bottom: float) -> None:
    _send(clientID, cmd,
          parent=parent, tag=tag, style=style,
          left=left, top=top, right=right, bottom=bottom)


def send_gui_button(clientID, parent, tag, style, left, top, right, bottom):
    _widget("button", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_checkbox(clientID, parent, tag, style, left, top, right, bottom):
    _widget("checkbox", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_clickregion(clientID, parent, tag, style, left, top, right, bottom):
    _widget("clickregion", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_colorbutton(clientID, parent, tag, style, left, top, right, bottom):
    _widget("colorbutton", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_colorcheckbox(clientID, parent, tag, style, left, top, right, bottom):
    _widget("colorcheckbox", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_dropdown(clientID, parent, tag, style, left, top, right, bottom):
    _widget("dropdown", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_icon(clientID, parent, tag, style, left, top, right, bottom):
    _widget("icon", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_iconbutton(clientID, parent, tag, style, left, top, right, bottom):
    _widget("iconbutton", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_iconcheckbox(clientID, parent, tag, style, left, top, right, bottom):
    _widget("iconcheckbox", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_image(clientID, parent, tag, style, left, top, right, bottom):
    _widget("image", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_rawiconbutton(clientID, parent, tag, style, left, top, right, bottom):
    _widget("rawiconbutton", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_sub_region(clientID, parent, tag, style, left, top, right, bottom):
    _widget("sub_region", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_text(clientID, parent, tag, style, left, top, right, bottom):
    _widget("text", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_typein(clientID, parent, tag, style, left, top, right, bottom):
    _widget("typein", clientID, parent, tag, style, left, top, right, bottom)


# ---------------------------------------------------------------------------
# Widgets with extra parameters  (override base no-ops)
# ---------------------------------------------------------------------------
def send_gui_face(clientID: int, parent: str, tag: str, face_string: str,
                  left: float, top: float, right: float, bottom: float) -> None:
    _send(clientID, "face",
          parent=parent, tag=tag, face_string=face_string,
          left=left, top=top, right=right, bottom=bottom)

def send_gui_slider(clientID: int, parent: str, tag: str, current: float,
                    style: str, left: float, top: float,
                    right: float, bottom: float) -> None:
    _send(clientID, "slider",
          parent=parent, tag=tag, current=current, style=style,
          left=left, top=top, right=right, bottom=bottom)

def send_gui_hotkey(clientID: int, category: str, tag: str,
                    keyType: str, description: str) -> None:
    _send(clientID, "hotkey",
          category=category, tag=tag,
          keyType=keyType, description=description)


def send_gui_3dship(clientID: int, parent: str, tag: str, style: str,
                    left: float, top: float, right: float, bottom: float) -> None:
    # Extract hull_tag from the style string so Python can do the shipData lookup.
    hull_tag = ""
    for pair in style.split(";"):
        k, _, v = pair.partition(":")
        if k.strip() == "hull_tag":
            hull_tag = v.strip()
            break

    try:
        from sbs_utils.procedural.ship_data import get_ship_data_for
        ship_info = get_ship_data_for(hull_tag) or {}
    except Exception:
        ship_info = {}

    artfileroot = ship_info.get("artfileroot", hull_tag)
    meshscale   = float(ship_info.get("meshscale", 1.0))

    _send(clientID, "3dship",
          parent=parent, tag=tag, style=style,
          left=left, top=top, right=right, bottom=bottom,
          artfileroot=artfileroot, meshscale=meshscale)
