from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
def gui_reroute_client (client_id, label, data=None):
    """Jump a specific client's GUI task to a new label immediately.
    
    Finds the client's active page, optionally sets variables from ``data``,
    then jumps the page's GUI task to ``label`` and ticks it in the current
    frame context.
    
    Args:
        client_id (int): The client to reroute.
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on the task before
            jumping. Defaults to None.
    
    Example:
        gui_reroute_client(CLIENT_ID, briefing_screen)"""
def web_living (persist=True, refresh=None):
    """Declare the current web page living/persistent. Call inside the `//web`
    route body; no-op if called outside a web page."""
def web_living_clear ():
    """Drop all living-page registrations (called on mission reset)."""
def web_living_pages ():
    """Return a copy of the living-page registry: {path: {persist, refresh}}."""
def web_norm_path (path):
    """Normalize a web path to the page key used by //web routes: no surrounding
    slashes and no leading ``web/`` (so "scores", "/web/scores" -> "scores")."""
def web_refresh (path):
    """Repaint every live ``//web/<path>`` session (re-runs the route so it
    rebuilds with current data). Returns how many sessions were refreshed."""
