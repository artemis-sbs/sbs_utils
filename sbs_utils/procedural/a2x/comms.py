"""Legacy-style scripted messages: 2.8 ``incoming_comms_text`` / ``big_message`` /
``warning_popup_message``.

Each maps onto the presentation Cosmos has for that KIND of message, rather than all
three onto one text channel (they used to go to the player text waterfall via
``comms_broadcast``, which lost the distinction between a chapter card and a warning):

* ``big_message`` -> a ``hero`` card + letterbox bars: the cinematic chapter card.
* ``incoming_comms_text`` -> a ``lower_third`` name-plate + subtitle, plus the durable
  comms-log message.
* ``warning_popup_message`` -> an info-panel card on the addressed consoles.

The overlay-backed ones are MAIN SCREEN by default: a hero card and a lower third are
both "over the live view" presentations. They also resolve their audience when called,
so a message fired before the crew has taken consoles goes nowhere -- see the timing
note on :func:`big_message`.

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


def incoming_comms_text(message, from_name="", title=None, to=None, time=30,
                        consoles="mainscreen"):
    """2.8 ``incoming_comms_text`` -> a lower-third subtitle plus a comms message.

    Two channels, deliberately, because 2.8's one message did two jobs:

    * the **transient** one is an ``overlay_lower_third`` -- the broadcast-TV name-plate
      and subtitle over the live view (speaker on top, line underneath). That is what a
      hail reads as, and unlike the info card it does not cover the view or need
      dismissing. A line too long for the plate is measured against the client's screen
      and shown in timed parts rather than clipped, which is what subtitles want anyway.
    * the **durable** one is a ``comms_message`` on each player ship, so the crew can
      re-read it and Comms sees every message. The overlay shows only the LATEST line
      (one slot); the comms log is what keeps the history.

    The durable side uses ``comms_message`` rather than ``comms_receive_internal``: the
    latter is the INTERNAL crew channel (a ship talking to itself, engineering to bridge)
    and resolves its portrait from the ship's own ``face_<from_name>`` inventory key. A 2.8
    ``from`` is an outside caller -- "TSN Command", a Kralien warship -- not a department,
    so it is passed as the message's ``from_name`` label instead.

    Audience follows :func:`big_message`: the player ships' MAIN SCREEN, since a lower
    third only makes sense over the live view -- on a Science data page it would just be
    text in the wrong place. Pass ``consoles=None`` to put it on every console instead,
    or ``to`` to aim it somewhere else entirely.

    Like every overlay this resolves its audience WHEN CALLED, and an empty console set is
    ignored silently -- see the timing note on :func:`big_message`.

    Args:
        message (str): body text (``^`` line breaks are converted).
        from_name (str, optional): sender label -> the name plate and comms ``from_name``.
            The 2.8 ``from`` is just a label, not an object, so there is no sender ship.
        title (str, optional): overrides the name plate (defaults to ``from_name``).
        to (optional): audience; defaults to every player ship.
        time (int, optional): subtitle auto-dismiss seconds. Defaults to 30.
        consoles (str, optional): console-role narrowing. Defaults to ``"mainscreen"``.
    """
    from sbs_utils.procedural.comms import comms_message
    from sbs_utils.procedural.gui.overlay import overlay_lower_third
    from sbs_utils.procedural.roles import role

    text = _clean(message)
    tgt = to if to is not None else role("__player__")
    overlay_lower_third(title or from_name or "", text, to=tgt, consoles=consoles,
                        seconds=time)
    # ...and the comms message itself. 2.8 gives a sender LABEL and no sender object, so
    # the message is addressed to each player ship with from_name carrying the label.
    players = role("__player__")
    comms_message(text, players, players, title=title, is_receive=True,
                  from_name=(from_name or None))


def big_message(title, subtitle1="", subtitle2="", to=None, time=30):
    """2.8 ``big_message`` -> a cinematic Hero chapter card on every player MAIN SCREEN.

    2.8 showed this as a big main-screen chapter card, so the audience is the MAIN SCREEN
    of every player ship -- not every console. ``to`` defaults to ``role("__player__")``;
    the overlay layer expands each ship to its consoles, and ``consoles="mainscreen"``
    narrows that to the main screen (the same narrowing is applied to the letterbox bars,
    so the framing matches). Pass ``to`` explicitly to aim it somewhere else.

    Drawn as a hero card (large centred title + combined subtitles on the ``center_hero``
    slot) with cinematic ``letterbox`` bars, via the one-call ``letterbox=`` form. Both
    auto-dismiss after ``time``.

    NOTE ON TIMING: this resolves its audience WHEN CALLED, and an empty console set is
    silently ignored by the overlay layer (a normal "nobody connected yet" case). A card
    fired before the crew has taken consoles therefore goes nowhere without any error --
    so a mission-opening card belongs on ``//shared/signal/game_started``, not in the map
    task's start block.
    """
    from sbs_utils.procedural.gui.overlay import overlay_hero
    from sbs_utils.procedural.roles import role

    tgt = to if to is not None else role("__player__")
    sub = "\n".join(p for p in (subtitle1, subtitle2) if p)
    overlay_hero(title, subtitle=sub or None, to=tgt, consoles="mainscreen",
                 seconds=time, letterbox=True)


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
