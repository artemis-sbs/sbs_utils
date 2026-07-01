"""Host-side web-page proxy for the REAL Cosmos engine.

Serves MAST //web/<path> pages to browsers without any engine changes, by
combining two things we already have:

  * Gui.web_render_sink (sbs_utils core): lets a web client's send_gui_* output
    be captured in pure Python during present.
  * the dev queue (cosmos_dev.devqueue): runs sbs_utils Python inside the real
    engine (open pages, route browser events, install the sink).

WebRenderSink (render_sink.py) is the in-engine capture shim; it serialises a
web client's GUI into the same wire commands the cosmos_dev.mockgui browser
(client.html) already understands, so the existing renderer is reused as-is.
"""
