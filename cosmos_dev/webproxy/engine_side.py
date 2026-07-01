"""In-engine API for the web-page proxy, driven over the dev queue.

The host proxy (proxy.py) issues dev-queue commands that call these functions
inside the real engine:

    web_open(cid, path, query)   - open a //web/<path> session for a browser
    web_event(cid, event)        - deliver a browser widget event
    web_close(cid)               - browser disconnected

Rendered wire commands reach the host two ways:
  * PUSH (default when set_frames_file is called): each command is appended as an
    NDJSON line to a file the proxy tails - no per-frame dev-queue round-trip, so
    the browser updates as soon as the engine renders (no polling stalls).
  * PULL (web_drain): return + clear buffered commands on request (used by tests
    and as a fallback). The engine's own tick drives Gui.present, which renders
    web clients through the installed WebRenderSink.

This module holds no engine specifics, so it runs identically under the mock
and is unit-testable. Only proxy.py (WS server + dev-queue bridge) needs a live
engine.
"""
import json
import os

from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, FakeEvent
from .render_sink import make_sink_factory

# PULL buffer: wire commands awaiting a web_drain() (when no frames file is set).
_frames = []
# PUSH target: absolute path of the NDJSON frames file, or None for pull mode.
_frames_path = None
_installed = False


def _out(wire):
    if _frames_path is not None:
        # Append one JSON line. Open/append/close per line keeps it robust to a
        # concurrent tailing reader on Windows (no long-lived shared handle);
        # web GUIs are low volume so the cost is negligible.
        try:
            with open(_frames_path, "a") as f:
                f.write(json.dumps(wire) + "\n")
        except OSError:
            pass
    else:
        _frames.append(wire)


def set_frames_file(path):
    """Enable PUSH mode: stream rendered frames as NDJSON to `path`. Truncates
    the file so the proxy starts from a clean stream. Returns the path."""
    global _frames_path
    _frames_path = path
    try:
        open(path, "w").close()   # truncate / create
    except OSError:
        pass
    install()
    return path


def clear_frames_file():
    """Back to PULL mode (web_drain)."""
    global _frames_path
    _frames_path = None


def install():
    """Route web clients' render through the capture sink. Idempotent."""
    global _installed
    if not _installed:
        Gui.web_render_sink = make_sink_factory(out=_out)
        _installed = True


def uninstall():
    global _installed, _frames_path
    Gui.web_render_sink = None
    _installed = False
    _frames_path = None
    _frames.clear()


def web_open(client_id, path, query=None):
    """Open a //web/<path> session for a browser client id. Returns True if the
    route exists. Frames from the initial present are captured immediately."""
    install()
    return Gui.web_page_open(client_id, path, data=query or None)


def web_event(client_id, event):
    """Deliver a browser widget event (dict) to the web client's page.

    `event` mirrors the mockgui browser payload: tag (default "gui_message"),
    sub_tag (widget tag), and optional value_tag / sub_float / extra_tag.
    """
    ev = FakeEvent(client_id=client_id, tag=event.get("tag", "gui_message"))
    for k in ("sub_tag", "value_tag", "sub_float", "extra_tag"):
        if k in event and event[k] is not None:
            setattr(ev, k, event[k])
    Gui.on_message(ev)


def web_close(client_id):
    """Tear down a web session (browser disconnected)."""
    Gui.web_page_close(client_id)


def web_drain():
    """Return and clear the wire commands rendered for web clients so far."""
    f = _frames[:]
    _frames.clear()
    return f
