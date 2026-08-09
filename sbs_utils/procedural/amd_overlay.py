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
from sbs_utils.procedural.gui.overlay import (
    _show_transient, _KIND_PRIMARY_FIELD, _KIND_DEFAULT_SLOT)

# key -> {"key", "kind", "slot", "fields", "display"}
OVERLAY_AMD = {}

# The per-kind conventions are owned by the overlay module so every front door
# (wrappers, AMD, quest directives) agrees; kept under the old names for callers.
_PRIMARY = _KIND_PRIMARY_FIELD          # body / display -> this field
_DEFAULT_SLOT = _KIND_DEFAULT_SLOT      # slot when a record names no Slot


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


def overlay_amd_clear():
    """Drop the declared overlay records. CONTENT, not vocabulary: these come from a
    mission's .amd, so keeping them means run 2 can resolve a key only the PREVIOUS
    mission declared and fire the wrong card, silently. On the reset ledger, so a
    forgotten clear is reported by name instead of found three runs later."""
    OVERLAY_AMD.clear()


def overlay_amd_count():
    return len(OVERLAY_AMD)


def overlay_amd(key, to=None, fields=None, consoles=None):
    """Fire a declared overlay by key. ``fields`` (a dict) merge over the record's
    fields; a ``seconds`` field auto-dismisses. ``to`` accepts a console, ship, side
    or set (see ``consoles_of``); ``consoles`` narrows by console role. Returns the
    record, or None for an unknown key."""
    rec = OVERLAY_AMD.get(key)
    if rec is None:
        return None
    merged = dict(rec["fields"])
    if fields:
        merged.update(fields)
    seconds = merged.pop("seconds", None)
    _show_transient(rec["slot"], rec["kind"], to, seconds, merged, consoles)
    return rec
