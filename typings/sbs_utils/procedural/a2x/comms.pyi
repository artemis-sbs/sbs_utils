def _clean (text):
    """2.8 message text -> plain text (``^`` is the line-break character)."""
def _cue_name (cue):
    """A cue slug -> the exact 2.8 label, via the registered callers.
    
    Falls back to title-casing the slug when a mission never registered a caster
    list. That fallback is LOSSY on purpose-built names ("gw_214" -> "Gw 214"), which
    is exactly why `comms_callers_load` exists and why the emitter writes it."""
def big_message (title, subtitle1='', subtitle2='', to=None, time=8):
    """2.8 ``big_message`` -> a cinematic Hero chapter card on every player MAIN SCREEN.
    
    2.8 showed this as a big main-screen chapter card, so the audience is the MAIN SCREEN
    of every player ship -- not every console. ``to`` defaults to ``role("__player__")``;
    the overlay layer expands each ship to its consoles, and ``consoles="mainscreen"``
    narrows that to the main screen (the same narrowing is applied to the letterbox bars,
    so the framing matches). Pass ``to`` explicitly to aim it somewhere else.
    
    Drawn as a hero card (large centred title + combined subtitles on the ``center_hero``
    slot) with cinematic ``letterbox`` bars, via the one-call ``letterbox=`` form. Both
    auto-dismiss after ``time``.
    
    ``time`` defaults to **8 seconds**. This is a full-screen card WITH LETTERBOX BARS
    over the main screen, so the default is the length of a chapter title, not of a
    message you read at leisure - it was 30, which left the bridge letterboxed for half
    a minute. The converter emits ``a2x_big_message(title, sub1, sub2)`` with no ``time``,
    so this default is what every converted 2.8 mission actually gets. Pass ``time``
    explicitly for a card that should linger.
    
    NOTE ON TIMING: this resolves its audience WHEN CALLED, and an empty console set is
    silently ignored by the overlay layer (a normal "nobody connected yet" case). A card
    fired before the crew has taken consoles therefore goes nowhere without any error --
    so a mission-opening card belongs on ``//shared/signal/game_started``, not in the map
    task's start block."""
def caller_face (from_name):
    """A stable face for a 2.8 sender LABEL, or None if there is no label.
    
    Prefers a real one: if the mission has a lifeform of that name, that character's
    face wins. Otherwise a face is generated once and cached, picking the race from the
    label when it names one ("Kralien Warship Zeta") and a terran otherwise - most 2.8
    callers are command, stations and human captains.
    
    The caller stores the result on each ship as ``face_<from_name>``, and only when that
    key is unset, so a mission's own portrait always wins over this one.
    
    Stable for the run, not across runs: it is a portrait for a name 2.8 never gave one
    to, so consistency within a session is what matters."""
def comms_callers_load (section):
    """Register the callers: a record per 2.8 ``from`` label, key = its slug.
    
    A cue has to be a slug (`RE_CUE` is `[\w.\-]+`), but "GW 214" and
    "CyberSecurity Suite IV" are what the crew must actually READ - and title-casing a
    slug back mangles both. So the exact label lives on the record's display text and
    is looked up here, which also gives a human one obvious place to attach a face or
    a color to a caller later."""
def comms_scene (key, to=None, side=None):
    """Play a registered dialogue scene as a run of 2.8 comms messages.
    
    One call replaces the contiguous run of ``incoming_comms_text`` tags it was built
    from, IN PLACE - which is why this is safe: 6096 of the corpus's 6112 comms-bearing
    events keep their comms in a single unbroken block, so nothing moves relative to
    the spawns and timers around it.
    
    Each beat's ``@cue`` is the 2.8 ``from`` label, and the scene's ``Title:`` / ``Side:``
    carry the ``type`` / ``sideValue`` the whole run shared. A run whose tags DISAGREED
    about either is not converted at all - it stays a sequence of direct calls - so this
    never has to guess."""
def comms_scenes_clear ():
    """Drop every registered scene and caller (per-mission state - an unreset
    module-level container is how a mission's second run goes wrong; see the reset
    ledger in handlerhooks)."""
def comms_scenes_load (section):
    """Register a dialogue section's scenes so ``comms_scene`` can play them by key.
    
    A converted 2.8 mission repeats the same comms run relentlessly - once per player
    ship, once per branch - so the emitter dedupes identical runs into ONE scene and
    every event that used it just names it. 6128 runs in the corpus collapse to 770
    scenes, so this is mostly about making converted missions editable: the words live
    in one place, and editing them is editing a script rather than hunting call sites."""
def console_roles (letters):
    """2.8 console letters (a subset of ``MHWESCO``) -> a Cosmos console-role csv."""
def incoming_comms_text (message, from_name='', title=None, to=None, time=8, consoles='mainscreen', side=None):
    """2.8 ``incoming_comms_text`` -> a comms message on the addressed player ships.
    
    JUST COMMS, JUST ONCE. It used to also throw a lower-third subtitle over the live
    view. In practice that was the wrong presentation - a 2.8 comms text is a message
    the crew reads and answers on Comms, not a film subtitle - and it arrived several
    times over, because the converter hung these bodies on a per-console route. The
    overlay is gone; the emitter now puts the body on a `//shared/signal` route so it
    runs once on the server.
    
    It goes out on the INTERNAL channel (``comms_receive_internal``). A 2.8 ``from`` is
    a LABEL with no object behind it - "TSN Command", a Kralien warship - and internal
    is exactly the channel built for a named sender that is not a ship you can select:
    it resolves the portrait from the receiving ship's own ``face_<from_name>`` key. So
    the label gets a face, which 2.8 never had.
    
    We seed that key with a generated face the first time a caller speaks (see
    :func:`caller_face`), and only if it is unset - so a mission that pre-registers
    ``face_TSN Command`` on its ships keeps its own portrait.
    
    ``comms_message`` renders the bar as ``<from>: <title>``, so a hail reads
    ``Dragon Tooth Refuge: ALERT``, coloured by the type (see :func:`type_title_color`).
    
    Args:
        message (str): body text (``^`` line breaks are converted).
        from_name (str, optional): the 2.8 ``from`` label -> the sender name and the
            key its portrait is stored under.
        title (str, optional): the 2.8 ``type`` -> the title bar and its colour.
        to (optional): audience; defaults to the player ships selected by ``side``.
        side (optional): the 2.8 ``sideValue`` this hail is addressed to. Narrows the
            audience to the player ships of that faction, which is what 2.8 meant by it -
            3247 of the corpus's 4318 tags carry one, and without it a hail meant for one
            team is read by everybody. Omitted / ``None`` = every player ship.
        time, consoles: accepted and IGNORED. They sized the old subtitle overlay; kept
            so an already-generated mission that passes them still loads."""
def incoming_message (from_name, filename, to=None):
    """2.8 ``incoming_message`` (a comms button that plays an ogg) -> play the audio.
    
    Simplified: 2.8 created a button; this plays the file directly. ``filename`` is
    resolved relative to the mission's media folder."""
def set_gm_instructions (title, text=''):
    """2.8 ``gm_instructions`` -> the Cosmos GM console instruction panel.
    
    Sets the shared ``GAMEMASTER_INSTRUCTIONS`` variable that ``gamemaster_panel_instructions``
    renders (via ``gui_text_area``; ``^`` = line break). The 2.8 title becomes the first line.
    Shared scope so the GM console's render task sees it."""
def spawn_external_program (name, arguments='', id=None):
    """2.8 ``spawn_external_program``: launch an external program (non-blocking).
    
    In 2.8 this was the way to play cutscene videos (it launched a media player like
    VLC). ``name`` is resolved relative to the mission folder when not absolute, as in
    2.8. Best-effort: the 2.8 program paths (e.g. ``dat/VLCPortable/...``) won't exist
    under Cosmos, so update the path -- a failed launch is logged, not fatal. Returns
    the ``Popen`` handle, or ``None`` on failure."""
def type_title_color (kind):
    """2.8 ``type`` -> a title colour, or None when it says nothing useful."""
def warning_popup (message, consoles=None, ship=None, title='Warning', time=30):
    """2.8 ``warning_popup_message``: a short message to specific consoles.
    
    Maps to an info-panel message card (``comms_info_card``) with a ``title`` and an
    auto-dismiss ``time`` -- closer to 2.8's transient warning than the waterfall. If
    ``ship`` is given the message goes to that ship's consoles; otherwise to all
    console clients. ``consoles`` (e.g. ``"HW"``) is a 2.8 console-letter string; each
    letter selects a console role to target (see :func:`console_roles`)."""
