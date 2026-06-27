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


def _player_targets(to):
    from sbs_utils.procedural.roles import role
    return to if to is not None else role("__player__")


def incoming_comms_text(message, from_name="", title=None, to=None):
    """2.8 ``incoming_comms_text`` -> a message in the players' comms waterfall.

    Args:
        message (str): body text (``^`` line breaks are converted).
        from_name (str, optional): sender label, prepended to the body.
        title (str, optional): unused at waterfall level (kept for call-site parity).
        to (optional): target id/set; defaults to all player ships.
    """
    from sbs_utils.procedural.comms import comms_broadcast
    body = _clean(message)
    if from_name:
        body = f"{from_name}: {body}"
    comms_broadcast(_player_targets(to), body)


def big_message(title, subtitle1="", subtitle2="", to=None):
    """2.8 ``big_message`` -> a title/subtitle block broadcast to players.

    (2.8 showed this as a main-screen chapter card; the waterfall is the scaffold
    equivalent -- upgrade to a real title card if the mission needs it.)
    """
    parts = [p for p in (title, subtitle1, subtitle2) if p]
    from sbs_utils.procedural.comms import comms_broadcast
    comms_broadcast(_player_targets(to), "\n".join(parts))


def incoming_message(from_name, filename, to=None):
    """2.8 ``incoming_message`` (a comms button that plays an ogg) -> play the audio.

    Simplified: 2.8 created a button; this plays the file directly. ``filename`` is
    resolved relative to the mission's media folder.
    """
    import sbs
    from sbs_utils.fs import get_mission_audio_file
    sbs.play_audio_file(0, get_mission_audio_file(filename), 1.0, 1.0)
