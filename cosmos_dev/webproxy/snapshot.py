"""Render a MAST //web/<path> to a standalone static HTML file.

One-shot: connects to a running engine's dev queue, renders the page once
(no live session), and writes a self-contained .html (embeds the frames into
the mockgui renderer). Great for read-only dashboards/reports - open the file
directly or serve it from any web server; it scales to any number of viewers
with zero engine load after generation.

    python -m cosmos_dev.webproxy.snapshot <mission_dir> <path> [-o out.html]
                                            [--query k=v ...] [--ticks N]

Prereqs: the engine is running the mission with cosmos_devqueue enabled
(dev_queue.enable marker or COSMOS_DEV_QUEUE) - same as the live proxy.
"""
import argparse
import sys

from .proxy import _QueueClient, _call
from .static_render import frames_to_html


def snapshot_html(queue_dir, path, query=None, ticks=6, timeout=15.0):
    """Fetch a one-shot render of //web/<path> from the running engine and
    return a standalone HTML document (or None if the route is missing)."""
    client = _QueueClient(queue_dir)
    frames = client.eval(_call("web_snapshot", path, query or {}, ticks),
                         timeout=timeout)
    if frames is None:
        return None
    return frames_to_html(frames)


def main():
    ap = argparse.ArgumentParser(
        description="Render a MAST //web/<path> to standalone static HTML.")
    ap.add_argument("mission_dir", help="Mission dir holding the dev_queue files")
    ap.add_argument("path", help="Web path, e.g. scores (or web/scores)")
    ap.add_argument("-o", "--out", default=None,
                    help="Output .html file (default: stdout)")
    ap.add_argument("--query", action="append", default=[], metavar="K=V",
                    help="Seed a page variable (repeatable)")
    ap.add_argument("--ticks", type=int, default=6,
                    help="Render ticks to let the layout build (default 6)")
    a = ap.parse_args()

    query = {}
    for kv in a.query:
        k, _, v = kv.partition("=")
        query[k] = v

    import os
    html = snapshot_html(os.path.abspath(a.mission_dir), a.path, query, a.ticks)
    if html is None:
        sys.exit(f"no //web/{a.path.lstrip('/')} route in the running mission")

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"wrote {a.out} ({len(html)} bytes)")
    else:
        sys.stdout.write(html)


if __name__ == "__main__":
    main()
