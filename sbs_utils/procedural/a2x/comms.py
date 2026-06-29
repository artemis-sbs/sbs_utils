"""Legacy-style scripted messages: 2.8 ``incoming_comms_text`` / ``big_message`` /
``incoming_message``.

These map onto the player text waterfall via the core ``comms_broadcast`` -- a
pragmatic "close enough" for a scaffold (no sender object is needed, which suits 2.8's
``from`` being just a name). For a richer presentation (portrait + comms dialog) a
mission can upgrade to ``comms_override`` + ``comms_receive`` with a real sender object.

2.8 text uses ``^`` for line breaks; :func:`_clean` converts it.
"""


def _clean(text):
    """2.8 message text -> plain text (``^`` is the line-break character)."""
    return (text or "").replace("^", "\n").strip()


# 2.8 console letters -> Cosmos console role names.
_CONSOLE_LETTER = {
    "M": "mainscreen", "H": "helm", "W": "weapons", "E": "engineering",
    "S": "science", "C": "comms", "O": "operations",
}


def console_roles(letters):
    """2.8 console letters (a subset of ``MHWESCO``) -> a Cosmos console-role csv."""
    names = [_CONSOLE_LETTER[ch] for ch in (letters or "") if ch in _CONSOLE_LETTER]
    return ",".join(dict.fromkeys(names))


def _console_targets(to):
    """Default target for info-panel cards: all console clients."""
    from sbs_utils.procedural.roles import role
    return to if to is not None else role("console")


def incoming_comms_text(message, from_name="", title=None, to=None):
    """2.8 ``incoming_comms_text`` -> an info-panel "hail" card.

    Uses ``comms_info_card`` (the promoted HTBM info-panel pattern: speaker name,
    history, auto-dismiss) rather than the text waterfall, since a 2.8
    ``incoming_comms_text`` is a hail from a named sender.

    Args:
        message (str): body text (``^`` line breaks are converted).
        from_name (str, optional): sender label -> the card title.
        title (str, optional): overrides the title (defaults to ``from_name``).
        to (optional): target console client id/set; defaults to all consoles.
    """
    from sbs_utils.procedural.comms import comms_info_card
    comms_info_card(_console_targets(to), _clean(message),
                    title=(title or from_name or None))


def big_message(title, subtitle1="", subtitle2="", to=None):
    """2.8 ``big_message`` -> a chapter-title info-panel card.

    (2.8 showed this as a main-screen chapter card; an info-panel card with a banner
    is the closest scaffold equivalent.)
    """
    from sbs_utils.procedural.comms import comms_info_card
    sub = "\n".join(p for p in (subtitle1, subtitle2) if p)
    comms_info_card(_console_targets(to), sub or None, title=title, banner=title)


def warning_popup(message, consoles=None, ship=None, title="Warning", time=8):
    """2.8 ``warning_popup_message``: a short message to specific consoles.

    Maps to an info-panel message card (``comms_info_card``) with a ``title`` and an
    auto-dismiss ``time`` -- closer to 2.8's transient warning than the waterfall. If
    ``ship`` is given the message goes to that ship's consoles; otherwise to all
    console clients. ``consoles`` (e.g. ``"HW"``) filters to those console roles.
    """
    from sbs_utils.procedural.comms import comms_info_card
    from sbs_utils.procedural.roles import role, any_role

    if ship is not None:
        from sbs_utils.procedural.links import linked_to
        from sbs_utils.procedural.query import to_id
        targets = linked_to(to_id(ship), "consoles")
    else:
        targets = role("console")
    names = console_roles(consoles)
    if names:
        targets = targets & any_role(names)
    comms_info_card(targets, _clean(message), title=title, time=time)


def incoming_message(from_name, filename, to=None):
    """2.8 ``incoming_message`` (a comms button that plays an ogg) -> play the audio.

    Simplified: 2.8 created a button; this plays the file directly. ``filename`` is
    resolved relative to the mission's media folder.
    """
    import sbs
    from sbs_utils.fs import get_mission_audio_file
    sbs.play_audio_file(0, get_mission_audio_file(filename), 1.0, 1.0)
