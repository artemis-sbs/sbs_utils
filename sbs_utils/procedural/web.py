"""Procedural helpers for MAST-authored web pages (`//web/<path>`).

- ``web_refresh(path)`` - force the live `//web/<path>` session(s) to re-render.
  Call it after changing the data a page shows (e.g. leaderboard stats) so open
  browsers update. Pure core: a mission can call it with no dev tooling.

- ``web_living(persist=True, refresh=None)`` - call inside a `//web` route body to
  declare the page "living": it should be persisted (a snapshot saved so it's
  still viewable after the game) and, optionally, re-persisted every ``refresh``
  seconds. The host-side web proxy reads this registry to drive persistence and
  to serve the snapshot when the engine is gone.

Both are inert/no-ops when there is no matching web session (safe to call
anywhere).
"""
from ..gui import Gui
from ..helpers import FrameContext
from .gui.navigation import gui_reroute_client


def web_norm_path(path):
    """Normalize a web path to the page key used by //web routes: no surrounding
    slashes and no leading ``web/`` (so "scores", "/web/scores" -> "scores")."""
    p = str(path).strip("/")
    if p.startswith("web/"):
        p = p[len("web/"):]
    return p


# path -> {"persist": bool, "refresh": int|None}
_living_pages = {}


def web_refresh(path):
    """Repaint every live ``//web/<path>`` session (re-runs the route so it
    rebuilds with current data). Returns how many sessions were refreshed."""
    target = web_norm_path(path)
    count = 0
    for client_id in list(Gui.web_client_ids):
        client = Gui.clients.get(client_id)
        if client is None:
            continue
        page = client.page
        if page is None or getattr(page, "web_path", None) != target:
            continue
        gui_reroute_client(client_id, page.start_label,
                           getattr(page, "start_data", None))
        count += 1
    return count


def web_living(persist=True, refresh=None):
    """Declare the current web page living/persistent. Call inside the `//web`
    route body; no-op if called outside a web page."""
    page = FrameContext.page
    path = getattr(page, "web_path", None) if page is not None else None
    if path is None:
        return
    _living_pages[path] = {"persist": bool(persist), "refresh": refresh}


def web_living_pages():
    """Return a copy of the living-page registry: {path: {persist, refresh}}."""
    return dict(_living_pages)


def web_living_clear():
    """Drop all living-page registrations (called on mission reset)."""
    _living_pages.clear()
