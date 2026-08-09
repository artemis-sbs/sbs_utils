"""announce() — one call that shows an overlay AND leaves a durable record.

Overlays are an **attention** layer: they draw over the 3D view and the tactical
map, and they are the only cinematic surface — but they auto-dismiss, keep no
history, and a console that connects a second later never sees them. So the house
rule is that an overlay never carries information alone; anything a player might
act on later gets a durable twin (a ``comms_message`` from a character, or an info
panel card with history).

Missions kept hand-rolling that pairing (HTBM's ``here_*`` helpers, LM's
``send_general_message``, ``pr_claim_notify``), each slightly differently. This is
the shared version:

    announce("Raiders inbound", title="TSN Command", level="alert", to=side)
    announce(line, title=admiral.name, face=..., level="hail",
             sender=admiral.id, ship=artemis_id)

``level`` picks BOTH halves — the overlay kind and which record surface is used:

===========  ==============  ===========================================
level        overlay         durable twin
===========  ==============  ===========================================
``chapter``  hero card       info panel card (history)
``hail``     lower third     comms_message from ``sender`` (else a card)
``alert``    top banner      info panel card (history)
``status``   none            ship's log (strip + log tab)
``minor``    none            ship's log (strip + log tab)
===========  ==============  ===========================================

``status`` and ``minor`` used to draw a corner toast and keep NO record -- the one pair
of levels that broke the house rule above, since the toast was carrying the information
alone. They are now log lines: visible immediately in the ambient strip where the toast
appeared, and still there afterwards. The toast is retired (mkdocs build/messages.md).

The overlay gets a **headline** (ASCII, clamped short); the twin gets the full
text. Pass ``record=False`` to suppress the twin (it is already being sent another
way), or ``record=True`` to force a card on a level that has none.
"""
from .gui.overlay import overlay_kind, consoles_of, _KIND_PRIMARY_FIELD
from .comms import comms_info_card, comms_message
from .query import to_id, to_id_list, is_space_object_id

# level -> (overlay kind, twin surface)
#   "card"    -> comms_info_card (info panel, keeps history)
#   "message" -> comms_message from the sender (falls back to a card)
#   "log"     -> a line in the ship's log (ambient strip + log tab)
#   None      -> no twin
#
# A None OVERLAY is legal and means "record only" - status and minor say their piece in
# the log, which is a surface the crew can go back to, rather than on a card that takes
# the message with it when it fades.
LEVELS = {
    "chapter": ("hero",        "card"),
    "hail":    ("lower_third", "message"),
    "alert":   ("banner",      "card"),
    "status":  (None,          "log"),
    "minor":   (None,          "log"),
}
_LEVEL_ALIAS = {"info": "status", "toast": "status", "hero": "chapter",
                "banner": "alert", "lower_third": "hail"}

# How long each level's overlay stays up when the caller doesn't say.
_LEVEL_SECONDS = {"chapter": 5, "hail": 8, "alert": 6, "status": 3, "minor": 3}

HEADLINE_MAX = 60


# --- the traffic clock --------------------------------------------------------
# When did the mission last say something UNPROMPTED to the crew? Every announce
# records here, and so does every urge that speaks (procedural/urge.py), because the
# two are the same thing from the bridge's side: a voice arriving that nobody asked
# for. The urge budget's global floor reads it, so an actor does not pipe up on top of
# mission dispatch - which is the annoyance players actually notice.
#
# Deliberately NOT every comms_message: a player hailing a station is traffic the
# player ASKED for, and counting it would starve autonomous speech exactly when the
# crew is busy - the opposite of what a floor is for.
_LAST_TRAFFIC = [None]


def announce_note_traffic(now=None):
    """Record that something just spoke to the crew unprompted."""
    if now is None:
        from sbs_utils.helpers import FrameContext
        now = FrameContext.sim_seconds
    _LAST_TRAFFIC[0] = now
    return now


def announce_last_traffic():
    """Sim seconds when the crew was last spoken to unprompted, or None."""
    return _LAST_TRAFFIC[0]


def announce_traffic_reset():
    """Drop the traffic clock (called by reset_mission_state)."""
    _LAST_TRAFFIC[0] = None


def announce_headline(text, limit=HEADLINE_MAX):
    """Reduce ``text`` to a single-line ASCII headline for an overlay.

    Engine-rendered text is ASCII-only, and an overlay is a glance, not a
    paragraph — so smart punctuation is folded, newlines collapse, and anything
    past ``limit`` is cut at a word boundary with an ellipsis."""
    if text is None:
        return ""
    s = str(text)
    for bad, good in (("—", "-"), ("–", "-"), ("‘", "'"),
                      ("’", "'"), ("“", '"'), ("”", '"'),
                      ("…", "...")):
        s = s.replace(bad, good)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = " ".join(s.split())
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0]
    return (cut or s[:limit]).rstrip(",.;:-") + "..."


def _twin_audience(to, ship, consoles):
    """Console ids for the info-panel card. Cards land on consoles, same as the
    overlay, so the two halves always reach the same people."""
    return consoles_of(to if to is not None else ship, consoles)


def _ships_of(to, ship):
    """Player ships for a comms_message twin (comms goes to SHIPS, not consoles)."""
    src = ship if ship is not None else to
    return [i for i in to_id_list(src) if is_space_object_id(i)]


def announce(text, title=None, level="status", to=None, ship=None, consoles=None,
             face=None, color=None, sender=None, seconds=None, record=None,
             headline=None, icon=None):
    """Show a level-appropriate overlay and leave the matching durable record.

    Args:
        text (str): the full message — goes to the durable twin, and (shortened)
            to the overlay when no ``headline`` is given.
        title (str, optional): speaker / header line. Used as the hero card's
            title and the lower third's name.
        level (str): ``chapter`` | ``hail`` | ``alert`` | ``status`` | ``minor``
            (see the table in the module docstring). Defaults to ``status``, which
            is a log line and no overlay.
        to: the audience — a console id, a **ship**, a **side**, or a set/role
            query. See ``consoles_of``.
        ship: shorthand for "this ship's crew" — used for ``to`` when ``to`` is
            omitted, and as the comms_message recipient for a ``hail``.
        consoles (str, optional): narrow the overlay/card to console roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
        face (str, optional): face string for the card / hero card.
        color (str, optional): colour for the card and the banner.
        sender: for ``hail``, the agent the comms_message comes FROM. Without one
            the twin falls back to an info card.
        seconds (int, optional): overlay dwell; defaults per level.
        record (bool, optional): force (``True``) or suppress (``False``) the
            durable twin. Defaults to the level's own policy.
        headline (str, optional): explicit overlay text (skips the shortener).
        icon (int, optional): icon index for the card.

    Returns:
        The durable twin's return value (a Promise for a card with a button, else
        None).
    """
    level = _LEVEL_ALIAS.get(str(level or "status").lower(), str(level or "status").lower())
    kind, twin = LEVELS.get(level, LEVELS["status"])
    if record is False:
        twin = None
    elif record is True and twin in (None, "log"):
        # record=True has always meant "give this one a CARD". Kept literal now that the
        # default twin for status/minor is the log, so the escape hatch still escapes to
        # the same place it did before.
        twin = "card"

    audience = to if to is not None else ship
    head = headline if headline is not None else announce_headline(title or text)
    if seconds is None:
        seconds = _LEVEL_SECONDS.get(level)
    announce_note_traffic()     # an actor must not talk over mission dispatch

    # --- the attention half ---------------------------------------------------
    # A hero card and a toast get a HEADLINE - they are a glance, and there is
    # nowhere for a paragraph to go. The banner and the lower third can measure
    # the text and play it in timed parts, so they get it WHOLE: clamping there
    # would throw away the tail for no reason.
    fields = {_KIND_PRIMARY_FIELD.get(kind, "title"): head}
    if kind == "hero":
        fields["subtitle"] = announce_headline(text) if title else None
        fields["face"] = face
    elif kind == "lower_third":
        fields["name"] = announce_headline(title, 40)
        fields["line"] = str(text or "")
    elif kind == "banner":
        fields["text"] = str(text or head)
        if color:
            fields["color"] = color
    if kind is not None:
        overlay_kind(kind, to=audience, consoles=consoles, seconds=seconds, **fields)

    # --- the record half ------------------------------------------------------
    if twin == "message" and sender is not None:
        ships = _ships_of(to, ship)
        if ships:
            comms_message(text, sender, ships, title=title, face=face, color=color)
            return None
        twin = "card"        # nobody to comms — keep the record on the panel
    if twin == "log":
        from .gui.overlay import _log_scopes
        from .gui.log_panel_gui import log_notify_all
        log_notify_all(_log_scopes(audience, consoles), str(text or head), color=color)
        return None
    if twin == "card":
        cids = _twin_audience(to, ship, consoles)
        if cids:
            return comms_info_card(cids, text, title=title, color=color, face=face,
                                   icon_index=icon)
    return None


def announce_clear(slot=None, to=None, consoles=None):
    """Clear an announce overlay early (the durable twin is untouched)."""
    from .gui.overlay import overlay_clear
    overlay_clear(slot, to=to, consoles=consoles)
