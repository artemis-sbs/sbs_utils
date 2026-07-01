"""In-engine API for the web-page proxy, driven over the dev queue.

The host proxy (proxy.py) issues dev-queue commands that call these functions
inside the real engine:

    web_open(cid, path, query)   - open a //web/<path> session for a browser
    web_event(cid, event)        - deliver a browser widget event
    web_close(cid)               - browser disconnected
    web_drain()                  - return + clear the wire commands rendered for
                                   web clients since the last call (the engine's
                                   own tick drives Gui.present, which renders web
                                   clients through the installed WebRenderSink)

This module holds no engine specifics, so it runs identically under the mock
and is unit-testable. Only proxy.py (WS server + dev-queue file polling) needs
a live engine.
"""
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, FakeEvent
from .render_sink import make_sink_factory

# Wire commands rendered for all web clients, awaiting a drain by the host.
_frames = []
_installed = False


def _out(wire):
    _frames.append(wire)


def install():
    """Route web clients' render through the capture sink. Idempotent."""
    global _installed
    if not _installed:
        Gui.web_render_sink = make_sink_factory(out=_out)
        _installed = True


def uninstall():
    global _installed
    Gui.web_render_sink = None
    _installed = False
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
