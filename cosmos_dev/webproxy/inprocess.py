"""In-process web-page serving for NON-engine MAST hosts.

The dev-queue proxy (proxy.py) exists only because the real Cosmos engine can't
host an HTTP server (no threads/asyncio inside its embedded Python). A non-engine
MAST host - the mock runner, a PyMAST tool, or any plain-Python sbs_utils app -
runs the mockgui server IN-PROCESS and has no such limit: it dispatches browser
web events straight to Gui. No dev queue, no render sink - rendering flows through
the live sbs to the browser exactly like any other GUI client.

Minimal host loop (the host already runs the mockgui server and ticks
Gui.present each frame):

    import cosmos_dev.mockgui.sbs as sbs      # starts the in-process WS/HTTP server
    from cosmos_dev.webproxy import inprocess

    while running:
        while not sbs.client_event_queue.empty():
            cev = sbs.client_event_queue.get_nowait()
            if not inprocess.handle_web_client_event(cev):
                ...                            # a normal console connect/disconnect
        # gui_message events (incl. web clients) flow through Gui.on_message as usual
        Gui.present(event)                     # renders open web pages to their browsers

`mission_runner` already does the equivalent inline (with connect deferral until
server init); this module is the small, reusable form for other hosts.
"""
from sbs_utils.gui import Gui


def handle_web_client_event(cev):
    """Dispatch a mockgui client-event to Gui when it is a web-page event.

    Returns True if handled (``web_connect`` opens the //web/<path> session,
    ``web_disconnect`` closes it), False otherwise so the caller can handle a
    normal console connect/disconnect.
    """
    ev = cev.get("event")
    cid = cev.get("clientID")
    if ev == "web_connect":
        Gui.web_page_open(cid, cev.get("path", ""), data=cev.get("query") or None)
        return True
    if ev == "web_disconnect":
        Gui.web_page_close(cid)
        return True
    return False
