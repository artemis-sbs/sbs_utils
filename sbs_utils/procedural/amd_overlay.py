"""Declarative overlays from AMD - author cinematic / notification overlays as data
(one ``# [Display](key)`` per overlay) and fire them by key with ``overlay_amd(key)``.

A section authors one heading per overlay (fields between ``---`` fences, then body):

    ## [Chapter Two](ch2)
    ---
    Kind: hero
    Subtitle: The Long Dark
    Seconds: 4
    ---
    CHAPTER TWO

The ``---`` fence fields become the builder's content; the body is the kind's PRIMARY
text (``title`` for hero/credits/choice, ``text`` for toast/banner, ``line`` for
lower_third), and the ``[Display]`` is the fallback primary when there's no body.
``Kind`` picks the builder (default ``hero``); ``Slot`` is optional (a per-kind default
is used). A projection of ``amd_records`` - overlays live in the same ``.amd`` as
quests / scans / landmarks. ``overlay_amd("ch2", to=role("mainscreen"))`` fires it;
a ``Seconds`` field auto-dismisses.
"""
from sbs_utils.procedural.amd_doc import amd_records
from sbs_utils.procedural.gui.overlay import _show_transient

# key -> {"key", "kind", "slot", "fields", "display"}
OVERLAY_AMD = {}

# the body / display maps to this field for each kind
_PRIMARY = {
    "hero": "title", "credits": "title", "choice": "title",
    "toast": "text", "banner": "text", "lower_third": "line",
}
# slot to use when a record names no Slot
_DEFAULT_SLOT = {
    "hero": "center_hero", "credits": "fullscreen", "choice": "center_hero",
    "toast": "corner_toast", "banner": "top_banner", "lower_third": "lower_third",
    "hud": "hud",
}


def _num(v):
    """Coerce a fence string to int/float where possible (Seconds: 4 -> 4)."""
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return v


def amd_overlays(section):
    """Load + register the overlay records in ``section``; returns the ``{key: record}``
    map (also merged into the module registry for ``overlay_amd``). Empty when None."""
    for rec in amd_records(section):
        key = rec.get("key")
        if not key:
            continue
        data = rec.get("data") or {}
        kind = str(data.get("kind") or "hero").strip().lower()
        slot = data.get("slot") or _DEFAULT_SLOT.get(kind, "center_hero")
        fields = {k: v for k, v in data.items() if k not in ("kind", "slot")}
        if "seconds" in fields:
            fields["seconds"] = _num(fields["seconds"])
        prim = _PRIMARY.get(kind, "title")
        body = (rec.get("body") or "").strip()
        if prim not in fields:
            if body:
                fields[prim] = body
            elif rec.get("display"):
                fields[prim] = rec.get("display")
        OVERLAY_AMD[key] = {"key": key, "kind": kind, "slot": slot,
                            "fields": fields, "display": rec.get("display")}
    return dict(OVERLAY_AMD)


def overlay_amd(key, to=None, **overrides):
    """Fire a declared overlay by key. ``overrides`` merge over the record's fields;
    a ``seconds`` field auto-dismisses. Returns the record, or None for an unknown key."""
    rec = OVERLAY_AMD.get(key)
    if rec is None:
        return None
    fields = dict(rec["fields"])
    fields.update(overrides)
    seconds = fields.pop("seconds", None)
    _show_transient(rec["slot"], rec["kind"], to, seconds, fields)
    return rec
