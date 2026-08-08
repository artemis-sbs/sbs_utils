"""Ship's log store and renderer - the data half of the Log Panel (LOG_PANEL_PLAN.md).

The text waterfall became a dumping ground: everything wrote to one undifferentiated
stream that nothing owned. This is its replacement's data layer - an append-only tagged
store plus a PURE render function, deliberately separated from any GUI so the part that
decides what a player reads can be tested without a console, an engine, or a browser.

Two axes, kept apart on purpose (see the plan):

* ``category`` is what an entry is ABOUT, and picks the TAB it appears in. The default,
  ``"log"``, is why migration is lossless: an untagged message shows in the Log tab -
  which shows everything - and in no subset tab. Nothing can go missing by being
  mis-tagged.
* ``severity`` is how URGENT it is, and picks the CALLOUT. It is not derived from the
  category: a ship entry may be routine ("docked at DS 1") or critical ("hull breach").

A callout costs two rows plus a background box, so it is reserved for severity; a
category is carried by COLOR, which costs one style string. One box per line would
roughly halve how many entries fit and turn the log into a wall of panels.
"""
from sbs_utils.procedural.amd_callout import amd_callout_render


# Entries are strings, so memory is not what bounds this: ~300 bytes an entry means 500
# is ~150 KB. The real cost is WRAP - the text area lays out every line on recalc, and
# this surface updates whenever content arrives. 500 lines is far more scrollback than
# anyone reads. If it ever hitches, the fix is to split the store from a smaller render
# window and add paging - measured wrap cost, not a memory number, is what should move it.
LOG_CAP = 500

TAB_LOG = "log"
TAB_SHIP = "ship"
TAB_MISSION = "mission"

# Category -> line color. `log` is deliberately uncolored: an untagged entry must look
# exactly like a waterfall line does today, so day-one parity costs nothing.
CATEGORY_COLOR = {
    TAB_LOG: None,
    TAB_SHIP: "#9cf",
    TAB_MISSION: "#cf9",
}

# Severity -> callout kind (amd_callout._CALLOUT_KINDS). "" means a plain line, which is
# most of them.
SEVERITY_CALLOUT = {
    "tip": "TIP",
    "warning": "WARNING",
    "danger": "DANGER",
}

# scope id -> list[entry]. Registered with the reset ledger below: a module-level
# per-mission container that nothing clears is a "works on run 1, broken on run 2" bug by
# construction.
_LOG = {}
_SEQ = [0]


def log_clear():
    """Drop every scope's log (fresh mission / in-process recompile)."""
    _LOG.clear()
    _SEQ[0] = 0


def log_size():
    """Total entries held across all scopes - the reset-ledger probe."""
    return sum(len(v) for v in _LOG.values())


def log_add(scope, text, color=None, category=TAB_LOG, severity=""):
    """Append one entry to a scope's log and return it.

    ``scope`` is normally a player-ship id: every console on that ship shares one log,
    which is what makes it the SHIP's log rather than five diverging ones. A client id
    may be used for a console-specific notice.

    The ``seq`` is monotonic across the whole mission, NOT an index into the list. That
    is what lets a reader who has scrolled back keep a stable "N new below" count while
    the ring drops entries off the top underneath them.
    """
    _SEQ[0] += 1
    entry = {
        "seq": _SEQ[0],
        "text": "" if text is None else str(text),
        "color": color,
        "category": category or TAB_LOG,
        "severity": severity or "",
    }
    entries = _LOG.setdefault(scope, [])
    entries.append(entry)
    if len(entries) > LOG_CAP:
        del entries[:len(entries) - LOG_CAP]
    return entry


def log_entries(scope, tab=TAB_LOG):
    """Entries for a scope, filtered to a tab, oldest first.

    The Log tab is not a category - it is EVERYTHING. Subset tabs match their category,
    so an entry nobody tagged appears in Log and nowhere else.
    """
    entries = _LOG.get(scope) or []
    if tab == TAB_LOG:
        return list(entries)
    return [e for e in entries if e.get("category") == tab]


def log_render(entries):
    """``entries`` -> ``(text, line_styles)`` for ``gui_text_area``.

    PURE: no GUI, no engine, no globals. This is the whole point of the split - what a
    player ends up reading can be asserted in a unit test.

    One entry is one line, so a style slot maps to an entry by index. An entry's own text
    is flattened for that reason: a log line that silently became three would break the
    mapping and the "N new" count with it.
    """
    lines = []
    plain_styles = []
    for e in entries:
        text = (e.get("text") or "").replace("\n", " ").replace("^", " ").strip()
        kind = SEVERITY_CALLOUT.get(e.get("severity") or "")
        if kind:
            # A one-line callout: amd_callout_render turns the opening line into the
            # styled title, so a log entry needs no body.
            lines.append(f"> [!{kind}] {text}")
            plain_styles.append(None)      # the callout supplies its own style
        else:
            lines.append(text)
            # An explicit color on the call wins over the category's - a caller that
            # asked for a color meant it.
            color = e.get("color") or CATEGORY_COLOR.get(e.get("category"))
            plain_styles.append({"style": f"color:{color};"} if color else None)

    text, styles = amd_callout_render("\n".join(lines))
    if styles is None:
        styles = [None] * len(lines)
    # Fill the slots the callout pass left alone with the category/color styling.
    for i, own in enumerate(plain_styles):
        if own is not None and i < len(styles) and styles[i] is None:
            styles[i] = own
    return text, styles
