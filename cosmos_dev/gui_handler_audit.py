"""Measure how many GUI handler sites belong to a task that has already ended.

LM issue #707: a widget's handler is owned by the task that BUILT the widget.
If that task ended, the handler is dropped when the widget is clicked. The
corpus question -- "how many of the `on gui_message` / `on_press` sites in a
mission are actually in that state?" -- decides how much waking them up can
disturb.

Sampling happens when the GUI is BUILT, not when it is clicked, so this needs
GUI coverage rather than click coverage: as soon as a page holds the widget,
its site is classified. A site seen alive on one page and dead on another is
reported as dead, because dead is the state that matters.

Dev-only. Never imported by the shipped library.
"""
import json


_sites = {}
_seen = {"calls": 0, "clients": 0, "pages": 0, "entries": 0, "nodes": 0, "unkeyed": 0}


def _site_key(node):
    """(file, line, label) for a handler's registration, or a best-effort id."""
    from sbs_utils.procedural.gui.message import _handler_site
    task = getattr(node, "task", None)
    if task is None:
        return None
    label = getattr(node, "label", None)
    loc = getattr(node, "loc", 0)
    if label is None:
        # MessageHandler (on_press): the handler label is the only source
        # location it carries.
        label = getattr(node, "handler", None)
        loc = 0
    if label is None or callable(label):
        return None                     # python callable: no task, not at risk
    try:
        f, line = _handler_site(task, label, loc)
    except Exception:
        return None
    return (f or "?", line, str(getattr(node, "label", label)))


def _kind(node):
    from sbs_utils.procedural.gui.message import MessageTrigger
    if isinstance(node, MessageTrigger):
        return "gui_message" if node.use_sub_task else "on gui_message"
    return "on_press"


def sample():
    """Classify every handler currently registered on every client's page."""
    from sbs_utils.gui import Gui
    from sbs_utils.procedural.gui.message import MessageTrigger
    from sbs_utils.procedural.gui.button import MessageHandler
    from sbs_utils.message_chain import message_handlers
    _seen["calls"] += 1
    for client in list(getattr(Gui, "clients", {}).values()):
        _seen["clients"] += 1
        pages = list(getattr(client, "page_stack", None) or [])
        page = getattr(client, "page", None)
        if page is not None and page not in pages:
            pages.append(page)
        entries = []
        for pg in pages:
            # BOTH maps: swap_layout moves pending_tag_map -> tag_map on a
            # repaint, so on most ticks a page's handlers are only in the
            # pending one and tag_map is empty.
            for attr in ("tag_map", "pending_tag_map"):
                m = getattr(pg, attr, None)
                if m:
                    entries.extend(m.values())
        if not entries:
            continue
        _seen["pages"] += 1
        for entry in entries:
            _seen["entries"] += 1
            node = entry[1] if isinstance(entry, tuple) and len(entry) > 1 else entry
            # A widget can hold several handlers now (LM #614), and they arrive
            # here wrapped in a MessageChain. Flatten, or every handler past the
            # first is invisible to this audit.
            for node in message_handlers(node):
                if not isinstance(node, (MessageTrigger, MessageHandler)):
                    continue
                _seen["nodes"] += 1
                key = _site_key(node)
                if key is None:
                    _seen["unkeyed"] += 1
                    continue
                rec = _sites.setdefault(key, {"kind": _kind(node), "visible": 0, "dead": 0})
                rec["visible"] += 1
                task = node.task
                try:
                    if task.done() or task.active_ticker.done:
                        rec["dead"] += 1
                except Exception:
                    pass


def report(path=None):
    dead = {k: v for k, v in _sites.items() if v["dead"]}
    print("==== GUI handler audit (LM #707) ====")
    print(f"sites observed: {len(_sites)}   dead-builder: {len(dead)}")
    print(f"sampled: calls={_seen['calls']} clients={_seen['clients']} pages={_seen['pages']} tag-entries={_seen['entries']} "
          f"handler-nodes={_seen['nodes']} unresolvable={_seen['unkeyed']}")
    # Every site, not just the dead ones: runs are unioned by hand across maps
    # and missions, and "which sites did this map even build?" is half of that.
    for (f, line, label), v in sorted(_sites.items(), key=lambda kv: str(kv[0])):
        mark = "DEAD" if v["dead"] else "live"
        print(f"  {mark} {v['kind']:<16} {f}:{line}  label={label} "
              f"({v['dead']}/{v['visible']} ticks dead)")
    if not dead:
        print("  no site was ever visible while its owning task was finished")
    print("=====================================")
    if path:
        out = [{"file": k[0], "line": k[1], "label": k[2], **v}
               for k, v in _sites.items()]
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(out, fp, indent=1)
        print(f"[audit] wrote {path}")


def reset():
    _sites.clear()
