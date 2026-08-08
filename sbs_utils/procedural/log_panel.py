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

# Log lines run one size DOWN from document text. amd_callout is built for in-fiction
# DOCUMENTS: its body is gui-2 and it bumps a title to gui-3. Every severity log entry is
# a one-line callout, so it was being styled as a title - a size up - when a log line is
# not a heading, it is a line. Set here so both are tunable in one place.
LOG_FONT = "gui-1"          # plain lines
# The compact tail that replaces the engine waterfall in a console's layout. Two lines is
# the useful default: one is a headline, three starts competing with the panel that already
# holds the history.
LOG_TAIL_LINES = 2
# ...and the reason the tail exists at all: the ENGINE waterfall's background cannot be
# controlled from script, and it is too dark. A MAST text area's can.
LOG_TAIL_BACKGROUND = "#1572"
LOG_CALLOUT_FONT = "gui-2"  # severity lines, still a step above plain

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
# client id -> the newest seq that client has been shown. Lets the panel's tick redraw
# only when the log actually grew, instead of re-presenting at 1 Hz forever.
_SEEN = {}


def log_clear():
    """Drop every scope's log (fresh mission / in-process recompile)."""
    _LOG.clear()
    _SEEN.clear()
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
    # Size every line for a LOG rather than a document. amd_callout is built for
    # in-fiction DOCUMENTS - body gui-2, and a title bumped to gui-3 - and every severity
    # entry here is a ONE-LINE callout, so it was being styled as a title, a size up. A
    # log line is not a heading. A style string is last-wins, so appending the font beats
    # whatever the callout pass put there.
    for i in range(len(styles)):
        is_callout = plain_styles[i] is None and styles[i] is not None
        font = LOG_CALLOUT_FONT if is_callout else LOG_FONT
        base = dict(styles[i]) if styles[i] else {}
        base["style"] = (base.get("style") or "") + f"font:{font};"
        styles[i] = base
    return text, styles


def log_entries_union(scopes, tab=TAB_LOG):
    """Entries from several scopes merged into one stream, oldest first.

    A console shows its SHIP's log (the crew's shared record) PLUS anything addressed to
    that console alone - `comms_broadcast` takes either, so both have to arrive somewhere
    visible. Merged by `seq`, which is monotonic across every scope, so a console-only
    note lands in the right place in time rather than clumped at one end.
    """
    out = []
    for scope in scopes:
        if scope is None:
            continue
        out.extend(log_entries(scope, tab))
    out.sort(key=lambda e: e["seq"])
    return out


def log_newest_seq(scope):
    """The newest entry's ``seq`` for a scope, or 0 when it has no log yet.

    Cheap change detection: a panel compares this against what it last drew rather than
    re-rendering on a timer.
    """
    entries = _LOG.get(scope)
    return entries[-1]["seq"] if entries else 0


def log_newest_seq_union(scopes):
    """Newest seq across several scopes - the change check for a merged view."""
    return max([log_newest_seq(s) for s in scopes if s is not None] or [0])


def log_mark_seen(client_id, seq):
    """Record the newest seq a client has been shown. Returns True if it CHANGED."""
    if _SEEN.get(client_id) == seq:
        return False
    _SEEN[client_id] = seq
    return True


def log_unseen(client_id, scope):
    """How many entries have arrived for `scope` since this client last saw it.

    Counts by SEQ, not by index, so it stays right when the ring has dropped entries off
    the top underneath a reader who scrolled back.
    """
    last = _SEEN.get(client_id)
    if last is None:
        return 0
    return sum(1 for e in (_LOG.get(scope) or []) if e["seq"] > last)
