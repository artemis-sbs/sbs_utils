"""What the viewscreen's data column says about the thing on screen.

Every page is a PURE function of ``(subject_id, ship_id)`` returning markdown, or
``None`` when it has nothing to say. That is the whole contract, and it is deliberately
the same one for the built-ins and for a mission's own pages - there is one code path,
and the built-ins are simply the first entries in the registry.

Pure because it makes the part that decides what a crew READS testable without a
console, an engine or a browser - the same split ``log_render`` uses.

A page returning ``None`` is skipped rather than shown blank, so the slideshow never
pages onto an empty screen. That is what makes "one page per science tab" work: an
object with two tabs of scan data gets two pages, not five.
"""
import math

from ..query import to_id, to_object


# name -> (order, fn). Lower order shows first; ties fall back to insertion.
_PAGES = {}


def viewscreen_page_register(name, fn, order=50):
    """Register a data page.

    Args:
        name (str): identifies the page (``"vitals"``, ``"cargo"``, ...). Re-registering
            a name REPLACES it, which is how a mission overrides a built-in.
        fn (callable): ``fn(subject_id, ship_id)`` -> markdown, or None for "nothing to
            say about this subject".
        order (int): sort key. The built-ins leave gaps so a mission can slot between.
    """
    _PAGES[name] = (order, fn)
    return fn


def viewscreen_page_remove(name):
    """Drop a page (including a built-in a mission does not want)."""
    return _PAGES.pop(name, None) is not None


def viewscreen_page_names():
    """Every registered page name, in display order."""
    return [n for n, _ in sorted(_PAGES.items(), key=lambda kv: (kv[1][0], kv[0]))]


def viewscreen_pages(subject, ship):
    """``[(name, markdown), ...]`` for this subject - empty pages dropped.

    A page that raises is skipped rather than taking the column down with it: one
    mission page with a bad key must not blank the whole viewer.
    """
    subject_id = to_id(subject)
    ship_id = to_id(ship)
    out = []
    for name in viewscreen_page_names():
        _order, fn = _PAGES[name]
        try:
            text = fn(subject_id, ship_id)
        except Exception as e:
            from ...mast.mast import DEBUG
            DEBUG(f"[viewscreen] page {name!r} raised: {e}")
            continue
        if text and str(text).strip():
            out.append((name, str(text)))
    return out


# --- helpers -----------------------------------------------------------------
def _pct(cur, mx):
    if not mx:
        return None
    return max(0, min(100, int(round(100.0 * float(cur) / float(mx)))))


def viewscreen_hull_percent(subject):
    """Remaining hull as 0-100, summed over the four ship systems.

    NOTE: LM's ``results_helpers.py`` carries the same formula for the end-game screen.
    Two copies of "what does damaged mean" is one too many - when phase 5 touches LM,
    promote one of them and delete the other.
    """
    so = to_object(subject)
    eo = so.space_object() if so is not None else None
    blob = getattr(eo, "data_set", None) if eo is not None else None
    if blob is None:
        return None
    cur = 0
    mx = 0
    for i in range(4):
        mx += blob.get("system_max_damage", i) or 0
        cur += blob.get("system_damage", i) or 0
    if mx <= 0:
        return None
    return _pct(mx - cur, mx)


def viewscreen_relative_bearing(subject, ship):
    """Bearing of ``subject`` from ``ship``: 0 is dead ahead, degrees clockwise.

    The convention is the engine's own, taken from the forward/right vectors rather
    than assumed from an axis - the same maths the damage-facing code uses. Returns
    None when either object (or its heading) is unavailable, because a bearing that is
    quietly 90 degrees out is worse than no bearing.
    """
    a = to_object(ship)
    b = to_object(subject)
    if a is None or b is None:
        return None
    ao = a.space_object()
    if ao is None:
        return None
    try:
        fwd = ao.forward_vector()
        right = ao.right_vector()
    except Exception:
        return None
    dx = b.pos.x - a.pos.x
    dz = b.pos.z - a.pos.z
    if dx == 0.0 and dz == 0.0:
        return None
    f = fwd.x * dx + fwd.z * dz
    r = right.x * dx + right.z * dz
    return int(round(math.degrees(math.atan2(r, f)))) % 360


def _range_to(subject, ship):
    from ...helpers import FrameContext
    try:
        return FrameContext.context.sbs.distance_id(to_id(ship), to_id(subject))
    except Exception:
        return None


def _row(label, value):
    return f"| {label} | {value} |"


# --- built-in pages ----------------------------------------------------------
def page_vitals(subject_id, ship_id):
    """Who and what it is, and where it is relative to us."""
    so = to_object(subject_id)
    if so is None:
        return None
    lines = [f"# {so.name}", ""]
    rows = ["| | |", "|---|---|"]
    side = getattr(so, "side", None)
    race = getattr(so, "race", None)
    if side:
        rows.append(_row("Side", side))
    if race and race != side:
        rows.append(_row("Origin", race))

    dist = _range_to(subject_id, ship_id)
    if dist:
        rows.append(_row("Range", f"{int(dist)}"))
    bearing = viewscreen_relative_bearing(subject_id, ship_id)
    if bearing is not None:
        rows.append(_row("Bearing", f"{bearing:03d}"))

    eo = so.space_object()
    blob = getattr(eo, "data_set", None) if eo is not None else None
    if blob is not None:
        front = _pct(blob.get("shield_val", 0) or 0, blob.get("shield_max_val", 0) or 0)
        rear = _pct(blob.get("shield_val", 1) or 0, blob.get("shield_max_val", 1) or 0)
        if front is not None or rear is not None:
            rows.append(_row("Shields", f"{front if front is not None else '-'}% / "
                                        f"{rear if rear is not None else '-'}%"))
    hull = viewscreen_hull_percent(subject_id)
    if hull is not None:
        rows.append(_row("Hull", f"{hull}%"))

    # Two rows is a header and nothing else - not worth a page of its own.
    if len(rows) <= 2:
        return None
    lines.extend(rows)
    return "\n".join(lines)


# The engine's tab keys are terse; these are what a viewscreen should call them.
SCAN_TAB_TITLES = {
    "scan": "Scan",
    "status": "Status",
    "intel": "Intel",
    "mat": "Materials",
    "bio": "Bio",
}


def page_science(subject_id, ship_id):
    """EVERY science tab that has been scanned, on ONE page.

    One page per tab was the first cut and it was wrong: the slideshow then shows a
    single tab at a time, so a contact scanned on three tabs reads as a contact scanned
    on one - you see Scan and nothing else unless you happen to look again at the right
    moment. The tabs are facets of one readout, not separate topics, and what science
    has learned belongs together.

    Only tabs with data appear, so the page grows as the crew scans. Reads what the
    SIDE knows (``science_get_scan_data``), not what is true.
    """
    from ..science import science_get_scan_data, SCIENCE_SCAN_TABS
    parts = []
    for tab in SCIENCE_SCAN_TABS:
        text = science_get_scan_data(ship_id, subject_id, tab)
        if not text:
            continue
        parts.append(f"## {SCAN_TAB_TITLES.get(tab, tab.capitalize())}\n\n{text}")
    if not parts:
        return None
    return "# Science\n\n" + "\n\n".join(parts)


def page_comms(subject_id, ship_id):
    """The last few exchanges with this contact."""
    from ..comms import comms_history_for
    entries = comms_history_for(ship_id, subject_id, limit=6)
    if not entries:
        return None
    lines = ["# Comms", ""]
    for e in entries:
        who = e.get("from_name") or ("Them" if e.get("receive") else "Us")
        lines.append(f"**{who}**: {e.get('message', '')}")
        lines.append("")
    return "\n".join(lines).strip()


def page_quest(subject_id, ship_id):
    """Anything the crew has been told about this contact - quests bound to the OBJECT.

    Rows come from ``quest_log_build_items``, the same builder both quest logs use, so
    a quest reads the same here as it does in the log. Only the presentation differs:
    this is a text area, not a list box, so the row TEMPLATE cannot be shared too.
    """
    from ..quest import quest_log_build_items
    from .listbox import gui_list_box_is_header
    try:
        items = quest_log_build_items([("Quests", subject_id)])
    except Exception:
        return None
    lines = []
    for item in items:
        if gui_list_box_is_header(item):
            continue
        title = item.get("title") if hasattr(item, "get") else None
        if not title:
            continue
        state = item.get("state_label") or ""
        progress = item.get("progress") or ""
        tail = " - ".join([t for t in (state, progress) if t])
        lines.append(f"- {title}" + (f"  *{tail}*" if tail else ""))
    if not lines:
        return None
    return "# Orders\n\n" + "\n".join(lines)


viewscreen_page_register("vitals", page_vitals, order=10)
viewscreen_page_register("science", page_science, order=20)
viewscreen_page_register("comms", page_comms, order=40)
viewscreen_page_register("quest", page_quest, order=45)
