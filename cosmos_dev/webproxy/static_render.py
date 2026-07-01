"""Turn a one-shot web-page snapshot into a standalone HTML document.

A static page reuses the exact mockgui renderer (client.html): we embed the
captured wire commands as ``window.__STATIC_FRAMES__`` so client.html renders
them once and skips the WebSocket. No live session, no per-tick work - the
result is a self-contained .html you can open directly or serve to many viewers.
"""
import json


def _load_client_html():
    """Read client.html from the cosmos_dev.mockgui package."""
    try:
        from importlib import resources
        return (resources.files("cosmos_dev.mockgui")
                .joinpath("client.html").read_text(encoding="utf-8"))
    except Exception:
        import os
        here = os.path.dirname(os.path.dirname(__file__))
        with open(os.path.join(here, "mockgui", "client.html"), encoding="utf-8") as f:
            return f.read()


def frames_to_html(frames, template=None):
    """Embed `frames` (a list of wire-command dicts) into the client.html
    renderer as window.__STATIC_FRAMES__, producing a complete HTML document.

    The inject goes right after <body> so it runs before client.html's main
    script (which reads the global on load).
    """
    if template is None:
        template = _load_client_html()
    inject = ("<script>window.__STATIC_FRAMES__ = "
              + json.dumps(frames or [])
              + ";</script>\n")
    lower = template.lower()
    i = lower.find("<body")
    if i != -1:
        i = template.find(">", i)
        if i != -1:
            return template[:i + 1] + "\n" + inject + template[i + 1:]
    # Fallback: prepend (still defines the global before any script runs)
    return inject + template
