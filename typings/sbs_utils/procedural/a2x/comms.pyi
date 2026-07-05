def _clean (text):
    """2.8 message text -> plain text (``^`` is the line-break character)."""
def _console_targets (to):
    """Default target for info-panel cards: all console clients."""
def big_message (title, subtitle1='', subtitle2='', to=None, time=30):
    """2.8 ``big_message`` -> a chapter-title info-panel card.
    
    (2.8 showed this as a main-screen chapter card; an info-panel card with a banner
    is the closest scaffold equivalent.) Uses a long auto-dismiss ``time`` so the
    chapter title stays up like the 2.8 main-screen card."""
def console_roles (letters):
    """2.8 console letters (a subset of ``MHWESCO``) -> a Cosmos console-role csv."""
def incoming_comms_text (message, from_name='', title=None, to=None, time=30):
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
        time (int, optional): card auto-dismiss seconds. Defaults to 30."""
def incoming_message (from_name, filename, to=None):
    """2.8 ``incoming_message`` (a comms button that plays an ogg) -> play the audio.
    
    Simplified: 2.8 created a button; this plays the file directly. ``filename`` is
    resolved relative to the mission's media folder."""
def spawn_external_program (name, arguments='', id=None):
    """2.8 ``spawn_external_program``: launch an external program (non-blocking).
    
    In 2.8 this was the way to play cutscene videos (it launched a media player like
    VLC). ``name`` is resolved relative to the mission folder when not absolute, as in
    2.8. Best-effort: the 2.8 program paths (e.g. ``dat/VLCPortable/...``) won't exist
    under Cosmos, so update the path -- a failed launch is logged, not fatal. Returns
    the ``Popen`` handle, or ``None`` on failure."""
def warning_popup (message, consoles=None, ship=None, title='Warning', time=30):
    """2.8 ``warning_popup_message``: a short message to specific consoles.
    
    Maps to an info-panel message card (``comms_info_card``) with a ``title`` and an
    auto-dismiss ``time`` -- closer to 2.8's transient warning than the waterfall. If
    ``ship`` is given the message goes to that ship's consoles; otherwise to all
    console clients. ``consoles`` (e.g. ``"HW"``) is a 2.8 console-letter string; each
    letter selects a console role to target (see :func:`console_roles`)."""
