"""Legacy-style scripted messages: 2.8 ``incoming_comms_text`` / ``big_message`` /
``warning_popup_message``.

Each maps onto the presentation Cosmos has for that KIND of message, rather than all
three onto one text channel (they used to go to the player text waterfall via
``comms_broadcast``, which lost the distinction between a chapter card and a warning):

* ``big_message`` -> a ``hero`` card + letterbox bars: the cinematic chapter card.
* ``incoming_comms_text`` -> a comms message, and ONLY that. It briefly also drew a
  lower-third subtitle; that was the wrong presentation for a message the crew reads
  and answers on Comms, so it was removed.
* ``warning_popup_message`` -> an info-panel card on the addressed consoles.

``big_message`` is MAIN SCREEN by default -- a hero card is an "over the live view"
presentation -- and it resolves its audience WHEN CALLED, so a card fired before the
crew has taken consoles goes nowhere. See the timing note on :func:`big_message`.

All three belong on a ``//shared/signal`` route: they address an audience themselves,
so running them once per console just sends the same message several times over.

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


# 2.8 `type` -> the colour of the comms title. The type is the only thing 2.8 tells us
# about the CHARACTER of a hail, and without it every message is the same colour, so an
# enemy threat and a friendly status read identically. Palette matches a2x.sides
# (enemy #F00 / friendly #07F / neutral #FFF) so a hail agrees with the 2D map.
_TYPE_COLOR = {
    "ENEMY":   "#F00",
    "ALERT":   "#F80",     # urgency, not a faction - amber
    "FRIEND":  "#07F",
    "STATION": "#0FF",
    "STATUS":  "#FFF",
}
# 2.8 combines them ("ALERT FRIEND", "ALERT STATION"). Most urgent token wins.
_TYPE_PRECEDENCE = ("ENEMY", "ALERT", "STATION", "FRIEND", "STATUS")


def type_title_color(kind):
    """2.8 ``type`` -> a title colour, or None when it says nothing useful."""
    toks = {t for t in str(kind or "").upper().replace(",", " ").split()}
    for name in _TYPE_PRECEDENCE:
        if name in toks:
            return _TYPE_COLOR[name]
    return None


# A 2.8 `from` is a LABEL with no object behind it, so there is no face to look up. We
# invent one and REMEMBER it, keyed by the label, so a recurring caller keeps the same
# portrait for the run instead of changing appearance every hail.
_CALLER_FACES = {}

# Race words that may appear in a 2.8 sender label; anything else reads as human.
_RACE_WORDS = ("kralien", "torgoth", "arvonian", "skaraan", "ximni")


def caller_face(from_name):
    """A stable face for a 2.8 sender LABEL, or None if there is no label.

    Prefers a real one: if the mission has a lifeform of that name, that character's
    face wins. Otherwise a face is generated once and cached, picking the race from the
    label when it names one ("Kralien Warship Zeta") and a terran otherwise - most 2.8
    callers are command, stations and human captains.

    The caller stores the result on each ship as ``face_<from_name>``, and only when that
    key is unset, so a mission's own portrait always wins over this one.

    Stable for the run, not across runs: it is a portrait for a name 2.8 never gave one
    to, so consistency within a session is what matters.
    """
    name = (from_name or "").strip()
    if not name:
        return None
    if name in _CALLER_FACES:
        return _CALLER_FACES[name]

    face = None
    try:                                    # a real character of that name wins
        from sbs_utils.procedural.query import to_object_list
        from sbs_utils.procedural.roles import role
        from sbs_utils.faces import get_face
        for obj in to_object_list(role("lifeform")):
            if str(getattr(obj, "name", "")).strip().lower() == name.lower():
                face = get_face(obj.id)
                break
    except Exception:
        face = None

    if not face:
        from sbs_utils.faces import random_face
        low = name.lower()
        race = next((r for r in _RACE_WORDS if r in low), "terran")
        face = random_face(race)

    _CALLER_FACES[name] = face
    return face


def incoming_comms_text(message, from_name="", title=None, to=None, time=8,
                        consoles="mainscreen", side=None):
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
            so an already-generated mission that passes them still loads.
    """
    from sbs_utils.procedural.comms import comms_receive_internal
    from sbs_utils.procedural.roles import role
    from sbs_utils.procedural.query import to_object_list
    from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
    from sbs_utils.procedural.a2x.sides import side_key

    text = _clean(message)
    # `to` used to aim only the overlay while the comms message always went to every
    # player ship, so an aimed hail was logged fleet-wide.
    if to is not None:
        tgt = to
    elif side is not None:
        tgt = role("__player__") & role(side_key(side))
    else:
        tgt = role("__player__")

    # Give the caller a portrait, once per ship, WITHOUT overwriting one the mission
    # registered itself - then let the internal channel resolve it the normal way.
    caller = (from_name or "").strip()
    if caller:
        face = caller_face(caller)
        for ship in to_object_list(tgt):
            if get_inventory_value(ship.id, f"face_{caller}", None) is None:
                set_inventory_value(ship.id, f"face_{caller}", face)

    comms_receive_internal(text, tgt, from_name=(caller or None), title=title,
                           title_color=type_title_color(title))


_COMMS_SCENES = {}
_COMMS_CALLERS = {}


def comms_callers_load(section):
    """Register the callers: a record per 2.8 ``from`` label, key = its slug.

    A cue has to be a slug (`RE_CUE` is `[\\w.\\-]+`), but "GW 214" and
    "CyberSecurity Suite IV" are what the crew must actually READ - and title-casing a
    slug back mangles both. So the exact label lives on the record's display text and
    is looked up here, which also gives a human one obvious place to attach a face or
    a color to a caller later."""
    from sbs_utils.procedural.amd_doc import amd_records
    for rec in amd_records(section):
        key = rec.get("key")
        if key:
            _COMMS_CALLERS[key] = rec.get("display") or key
    return len(_COMMS_CALLERS)


def comms_scenes_load(section):
    """Register a dialogue section's scenes so ``comms_scene`` can play them by key.

    A converted 2.8 mission repeats the same comms run relentlessly - once per player
    ship, once per branch - so the emitter dedupes identical runs into ONE scene and
    every event that used it just names it. 6128 runs in the corpus collapse to 770
    scenes, so this is mostly about making converted missions editable: the words live
    in one place, and editing them is editing a script rather than hunting call sites.
    """
    from sbs_utils.procedural.amd_dialogue import dialogue_scenes, dialogue_parse
    for key, node in dialogue_scenes(section).items():
        _COMMS_SCENES[key] = (dialogue_parse(node), node.get("data") or {})
    return len(_COMMS_SCENES)


def comms_scenes_clear():
    """Drop every registered scene and caller (per-mission state - an unreset
    module-level container is how a mission's second run goes wrong; see the reset
    ledger in handlerhooks)."""
    _COMMS_SCENES.clear()
    _COMMS_CALLERS.clear()


def comms_scene(key, to=None, side=None):
    """Play a registered dialogue scene as a run of 2.8 comms messages.

    One call replaces the contiguous run of ``incoming_comms_text`` tags it was built
    from, IN PLACE - which is why this is safe: 6096 of the corpus's 6112 comms-bearing
    events keep their comms in a single unbroken block, so nothing moves relative to
    the spawns and timers around it.

    Each beat's ``@cue`` is the 2.8 ``from`` label, and the scene's ``Title:`` / ``Side:``
    carry the ``type`` / ``sideValue`` the whole run shared. A run whose tags DISAGREED
    about either is not converted at all - it stays a sequence of direct calls - so this
    never has to guess.
    """
    entry = _COMMS_SCENES.get(str(key))
    if entry is None:
        from sbs_utils.procedural.execution import log
        log(f"comms scene {key!r} is not registered - nothing said", "a2x", "warning")
        return
    scene, data = entry
    title = data.get("title")
    scene_side = data.get("side") if side is None else side
    for beat in scene.get("beats") or ():
        speaker = beat.get("speaker") or ""
        for text, _gate, _direction in beat["lines"]:
            if not text:
                continue
            incoming_comms_text(text, from_name=_cue_name(speaker), title=title,
                                to=to, side=scene_side)


def _cue_name(cue):
    """A cue slug -> the exact 2.8 label, via the registered callers.

    Falls back to title-casing the slug when a mission never registered a caster
    list. That fallback is LOSSY on purpose-built names ("gw_214" -> "Gw 214"), which
    is exactly why `comms_callers_load` exists and why the emitter writes it."""
    key = str(cue or "")
    known = _COMMS_CALLERS.get(key)
    if known:
        return known
    return " ".join(w.capitalize() for w in key.split("_") if w)


def big_message(title, subtitle1="", subtitle2="", to=None, time=8):
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
