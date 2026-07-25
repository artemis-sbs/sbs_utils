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


def incoming_comms_text(message, from_name="", title=None, to=None, time=30):
    """2.8 ``incoming_comms_text`` -> an info-panel "hail" card plus a comms message.

    Shows a ``comms_info_card`` (the promoted HTBM info-panel pattern: speaker name,
    history, auto-dismiss) and also delivers the text as an incoming comms message via
    ``comms_receive_internal`` (a ``comms_message`` whose sender/receiver are the player
    ship). The 2.8 ``from`` is just the sender label, not an object reference, so it is
    used purely as the message's ``from_name`` (the comms title) -- there is no sender
    ship to attach.

    Args:
        message (str): body text (``^`` line breaks are converted).
        from_name (str, optional): sender label -> the card title and comms ``from_name``.
        title (str, optional): overrides the card title (defaults to ``from_name``).
        to (optional): target console client id/set for the card; defaults to all consoles.
        time (int, optional): card auto-dismiss seconds. Defaults to 30.
    """
    from sbs_utils.procedural.comms import comms_info_card, comms_receive_internal
    from sbs_utils.procedural.roles import role
    targets = _console_targets(to)
    text = _clean(message)
    comms_info_card(targets, text, title=(title or from_name or None), time=time)
    # incoming comms message on the player ship(s); the 2.8 `from` is the sender label.
    comms_receive_internal(text, role("__PLAYER__"), from_name=(from_name or None))


def big_message(title, subtitle1="", subtitle2="", to=None, time=30):
    """2.8 ``big_message`` -> a cinematic Hero overlay chapter card with letterbox bars.

    2.8 showed this as a big main-screen chapter card; the closest Cosmos equivalent is the
    hero overlay (a large centered title + combined subtitles, on the ``center_hero`` slot)
    dressed with cinematic ``letterbox`` bars (the ``fullscreen`` slot -- the two slots
    coexist). Both auto-dismiss after ``time``. (Replaces the older info-panel card.)
    """
    from sbs_utils.procedural.gui.overlay import overlay_hero, overlay_letterbox
    tgt = _console_targets(to)
    sub = "\n".join(p for p in (subtitle1, subtitle2) if p)
    overlay_letterbox(to=tgt, seconds=time)
    overlay_hero(title, subtitle=sub or None, to=tgt, seconds=time)


def set_gm_instructions(title, text=""):
    """2.8 ``gm_instructions`` -> the Cosmos GM console instruction panel.

    Sets the shared ``GAMEMASTER_INSTRUCTIONS`` variable that ``gamemaster_panel_instructions``
    renders (via ``gui_text_area``; ``^`` = line break). The 2.8 title becomes the first line.
    Shared scope so the GM console's render task sees it.
    """
    from sbs_utils.procedural.execution import set_shared_variable
    body = title or ""
    if text:
        body = f"{body}^{text}" if body else text
    set_shared_variable("GAMEMASTER_INSTRUCTIONS", body)


def warning_popup(message, consoles=None, ship=None, title="Warning", time=30):
    """2.8 ``warning_popup_message``: a short message to specific consoles.

    Maps to an info-panel message card (``comms_info_card``) with a ``title`` and an
    auto-dismiss ``time`` -- closer to 2.8's transient warning than the waterfall. If
    ``ship`` is given the message goes to that ship's consoles; otherwise to all
    console clients. ``consoles`` (e.g. ``"HW"``) is a 2.8 console-letter string; each
    letter selects a console role to target (see :func:`console_roles`).
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


def spawn_external_program(name, arguments="", id=None):
    """2.8 ``spawn_external_program``: launch an external program (non-blocking).

    In 2.8 this was the way to play cutscene videos (it launched a media player like
    VLC). ``name`` is resolved relative to the mission folder when not absolute, as in
    2.8. Best-effort: the 2.8 program paths (e.g. ``dat/VLCPortable/...``) won't exist
    under Cosmos, so update the path -- a failed launch is logged, not fatal. Returns
    the ``Popen`` handle, or ``None`` on failure.
    """
    import os
    import shlex
    import subprocess
    from sbs_utils.fs import get_mission_dir_filename
    from sbs_utils.procedural.execution import log

    path = name if os.path.isabs(name) else get_mission_dir_filename(name)
    args = shlex.split(arguments) if arguments else []
    try:
        return subprocess.Popen([path, *args])
    except Exception as exc:  # noqa: BLE001 -- a missing player must not crash the mission
        log(f"a2x spawn_external_program failed ({name}): {exc}")
        return None


def incoming_message(from_name, filename, to=None):
    """2.8 ``incoming_message`` (a comms button that plays an ogg) -> play the audio.

    Simplified: 2.8 created a button; this plays the file directly. ``filename`` is
    resolved relative to the mission's media folder.
    """
    import sbs
    from sbs_utils.fs import get_mission_audio_file
    sbs.play_audio_file(0, get_mission_audio_file(filename), 1.0, 1.0)
