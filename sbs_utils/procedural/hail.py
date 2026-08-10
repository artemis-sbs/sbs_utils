"""Incoming hails - a communication the SCRIPT starts, not the player.

Comms today is always player-initiated: the player selects a contact, `//enable/comms`
runs, `//comms` paints buttons. `CommsPromise` is keyed on `(origin_id, selected_id)`
because a *selection* is what brought it into being. A hail has no selection until the
crew answers one, so it gets its own state rather than borrowing that machinery - it
only borrows comms for the transcript line.

THE STATE LIVES ON THE SHIP, exactly as `gui/viewscreen.py` keeps "on screen" state,
and for the same three reasons: a hail to the Artemis cannot be answered from the
Intrepid; `Agent.clear()` takes it, so there is no new container for the restart ledger
to police; and two consoles racing to answer arbitrate through one value rather than
through a lock.

Three ideas carry the whole design:

* **`HAIL_SEQ` is the arbitration token.** It is bumped on every accept, beat and
  answer. A console renders its buttons carrying the seq it saw; `hail_answer` refuses
  a press whose seq has moved on. That is what makes two comms officers pressing
  different choices in the same frame safe without a lock.
* **Beats and choices are resolved ONCE, at accept, and cached on the record.**
  `dialogue_beats` picks a random eligible variant per call, so re-resolving on every
  repaint would make the line flicker - and a console must never be the thing that
  decides what the choices are, or the server cannot arbitrate them.
* **Nothing here forces a screen.** Each console carries its own placement dial
  (`HAIL_WHERE`); the ship carries whether the main screen is showing it (`HAIL_MAIN`).
  Accepting a hail starts the conversation, not a takeover.

This module keeps no GUI imports at module scope - the engine-facing calls are imported
inside the functions that need them - so lint, tooling and unit tests can import it with
no engine present.
"""
from ..helpers import FrameContext
from ..mast.mast import DEBUG
from ..mast.mast_node import MastDataObject
from .amd_dialogue import (dialogue_apply, dialogue_beats, dialogue_choices,
                           dialogue_entry_for, dialogue_parse)
from .inventory import get_inventory_value, set_inventory_value
from .query import to_id, to_object
from .roles import has_role
from .signal import signal_emit


# How a hail is PRESENTED once a console puts it on screen. The writer chooses this
# (`Presentation:` in AMD); the crew chooses only WHERE it shows.
HAIL_FORMS = ("portrait", "still", "orbit")

# The answer strip is 1-4 buttons. A fifth choice could never be pressed, which is what
# `amd_lint_hails` warns about at author time and what this truncates at run time.
HAIL_MAX_CHOICES = 4

# Answered conversations kept for replay. Mirrors the comms history cap: per-mission by
# definition, and the ids in it are object ids the next mission RECYCLES.
HAIL_LOG_CAP = 40

# What a console's placement drop-down says, and what each label means. Kept HERE rather
# than in the console so the two cannot drift - the console builds its list from
# `hail_where_props()` and hands the chosen label straight back to `hail_where_for`.
# ASCII only: these are engine-rendered strings.
HAIL_WHERE_LABELS = (
    ("Off", "off"),
    ("This Console", "console"),
    ("Main Screen", "main"),
    ("Both", "both"),
)
HAIL_WHERE_VALUES = tuple(value for _label, value in HAIL_WHERE_LABELS)

# Inventory keys on the player SHIP.
KEY_QUEUE = "HAIL_QUEUE"            # pending records, priority-desc then FIFO
KEY_ACTIVE = "HAIL_ACTIVE"          # the open record, or None
KEY_SEQ = "HAIL_SEQ"                # the arbitration token
KEY_LOG = "HAIL_LOG"                # answered conversations, newest first
KEY_MAIN = "HAIL_MAIN"              # is the MAIN SCREEN showing the conversation
KEY_NEXT_ID = "HAIL_NEXT_ID"        # monotonic id source
KEY_TOOK_VIEWER = "HAIL_TOOK_VIEWER"  # this hail is what called viewscreen_set

# Inventory keys on the CONSOLE (client), not the ship.
KEY_HERE = "HAIL_HERE"              # does THIS console swap its own centre
KEY_REPLAY = "HAIL_REPLAY"          # the log id being replayed here, or None

# A mission may resolve a speaker key to a name/face/color card its own way (OU binds
# captains, LM binds cast). A LATCH, not a container: a resolver registered by the LAST
# mission names cast that no longer exists, which is why the reset ledger probes it.
_SPEAKER_RESOLVER = [None]

# Delivery surfaces (`@Speaker (over)`) -> what draws them. `amd_dialogue._SURFACES`
# already names `comms`, `over` and `card`; this is the half that renders them.
_SURFACE_RENDERERS = {}


# --- small helpers ----------------------------------------------------------
def _hail_sid(ship):
    """A ship id, or None. Accepts an Agent or an id, like every other procedural call."""
    try:
        return to_id(ship)
    except Exception:
        return None


def _hail_now():
    """Sim seconds, or 0.0 with no frame context (tests, lint, tooling)."""
    try:
        return float(FrameContext.sim_seconds or 0.0)
    except Exception:
        return 0.0


def _hail_get(ship_id, key, default):
    return get_inventory_value(ship_id, key, default)


def hail_seq(ship):
    """The ship's current arbitration token. A console stamps this onto every answer
    button it renders; `hail_answer` refuses a press carrying an older one."""
    return int(_hail_get(_hail_sid(ship), KEY_SEQ, 0) or 0)


def _hail_bump_seq(ship_id):
    seq = int(_hail_get(ship_id, KEY_SEQ, 0) or 0) + 1
    set_inventory_value(ship_id, KEY_SEQ, seq)
    return seq


def _hail_emit(ship_id, state, record=None, client_id=None, beat=None, choice=None):
    """One signal for every transition, so a listener is a single route rather than one
    per verb - the shape `viewscreen` already uses.

    `HAIL_CLIENT` is the repaint scope: None means every console of this ship, an id
    means only that one. A dial change that moved the MAIN screen is ship-wide and so
    passes None even though one console made it.
    """
    signal_emit("hail", {
        "HAIL_SHIP": ship_id,
        "HAIL_ID": (record or {}).get("id"),
        "HAIL_STATE": state,
        "HAIL_BEAT": (record or {}).get("beat") if beat is None else beat,
        "HAIL_SEQ": int(_hail_get(ship_id, KEY_SEQ, 0) or 0),
        "HAIL_CLIENT": client_id,
        # WHICH answer was given, and where it led. Without these a mission can see that
        # a hail was answered but not what the crew chose, which is the only part a
        # story usually cares about.
        "HAIL_CHOICE": (choice or {}).get("label"),
        "HAIL_TARGET": (choice or {}).get("target"),
        "HAIL_KEY": (record or {}).get("key"),
        "HAIL_SCENE": (record or {}).get("scene"),
    })


# --- seams ------------------------------------------------------------------
def hail_set_speaker_resolver(fn):
    """Set how a speaker KEY becomes a name/face/color card.

    `fn(speaker_key, ship_id)` returns a mapping (or MastDataObject) with any of
    `name`, `face`, `color`. Explicit fields on the hail record always win over this,
    and this wins over the library's own lifeform lookup - so a mission can name its
    cast however it likes and the engine stays domain-free.
    """
    _SPEAKER_RESOLVER[0] = fn


def hail_speaker_resolver_clear():
    """Drop the resolver. Called by `reset_mission_state`: one registered by the LAST
    mission resolves keys against cast that no longer exists."""
    _SPEAKER_RESOLVER[0] = None


def hail_register_surface_renderer(name, fn):
    """Register what draws a cue's delivery surface: `fn(ship_id, beat, record)`.

    `amd_dialogue` already declares the surface NAMES (`comms`, `over`, `card`); this
    is what makes one of them do something. An unregistered surface is not an error -
    the beat still plays on the default surface.
    """
    _SURFACE_RENDERERS[str(name).strip().lower()] = fn


def hail_surface_renderer(name):
    """The renderer for a surface, or None."""
    return _SURFACE_RENDERERS.get(str(name or "").strip().lower())


def hail_speaker(speaker_key, ship_id=None):
    """Resolve a speaker key to a card: `{name, face, color}`.

    Order is deliberate - the mission's resolver, then the library's own lifeform
    lookup, then a bare card carrying just the key as a name so something always
    renders. Never raises: a hail with an unresolvable speaker is still a hail.
    """
    key = str(speaker_key or "").strip()
    if not key:
        return MastDataObject({"name": "", "face": None, "color": None})
    fn = _SPEAKER_RESOLVER[0]
    if fn is not None:
        try:
            card = fn(key, ship_id)
            if card:
                return card if isinstance(card, MastDataObject) else MastDataObject(dict(card))
        except Exception as e:
            DEBUG(f"[hail] speaker resolver failed for {key!r}: {e}")
    # lifeform_speaker_of takes an AGENT ID, not a key - so it only applies when the
    # speaker IS a live agent (a spawned lifeform hailing on its own behalf). Resolving
    # a cast KEY needs the mission's records, which is exactly what the resolver seam
    # above is for; guessing here would fail silently and look like a missing face.
    if to_object(speaker_key) is not None:
        try:
            from .amd_lifeforms import lifeform_speaker_of
            card = lifeform_speaker_of(speaker_key)
            if card:
                return card
        except Exception as e:
            DEBUG(f"[hail] lifeform speaker lookup failed for {key!r}: {e}")
    return MastDataObject({"name": key, "face": None, "color": None})


def hail_reset():
    """Drop module-level hail state for a mission reset.

    The per-ship records need nothing here: they live in ship inventory and go with
    `Agent.clear()`. Only the injected resolver outlives a mission, which is why it is
    a LATCH in the reset ledger rather than a container.
    """
    hail_speaker_resolver_clear()


# --- the queue --------------------------------------------------------------
def _hail_queue(ship_id):
    q = _hail_get(ship_id, KEY_QUEUE, None)
    if q is None:
        q = []
        set_inventory_value(ship_id, KEY_QUEUE, q)
    return q


def _hail_lines_from(lines, speaker):
    """Normalize a `lines=` argument into beat dicts. Accepts a string or a sequence."""
    if lines is None:
        return []
    seq = [lines] if isinstance(lines, str) else list(lines)
    return [{"speaker": speaker, "surface": None, "direction": None, "text": str(t)}
            for t in seq if str(t).strip()]


def _hail_choices_from(choices):
    """Normalize a `choices=` argument. Accepts labels, `(label, target)` pairs, or
    dicts - so a MAST-driven hail needs no AMD document to offer an answer."""
    out = []
    for c in (choices or []):
        if isinstance(c, dict):
            out.append({"label": str(c.get("label", "")), "target": c.get("target"),
                        "outcomes": c.get("outcomes") or []})
        elif isinstance(c, (list, tuple)) and len(c) >= 2:
            out.append({"label": str(c[0]), "target": c[1], "outcomes": []})
        else:
            out.append({"label": str(c), "target": None, "outcomes": []})
    return out[:HAIL_MAX_CHOICES]


def hail_offer(ship, scene=None, speaker=None, subject=None, presentation=None,
               backdrop=None, audio=None, face=None, name=None, color=None,
               title=None, priority=0, expires=None, key=None, lines=None,
               choices=None, scenes=None):
    """Offer a hail to a ship. It waits in the queue until the crew answers it.

    Args:
        ship (Agent | int): the player ship being hailed.
        scene (str, optional): an AMD dialogue scene key (see `hail_offer_amd`).
        speaker (str, optional): who is calling - a cast/side/captain key.
        subject (Agent | int | str, optional): what an orbit shot films. May be an id
            OR a name/role resolved LATE, because the ship is usually spawned at
            runtime - the same contract `Subject:` has in AMD.
        presentation (str, optional): one of `HAIL_FORMS`.
        lines / choices (optional): a MAST-driven hail with no AMD behind it.
        key (str, optional): an idempotency key. Offering the same key twice is a
            no-op, so a re-emitted setup signal cannot queue the same hail again.

    Returns:
        int | None: the hail id, or None if the ship is unknown or `key` is a repeat.
    """
    ship_id = _hail_sid(ship)
    if ship_id is None:
        return None
    if presentation is not None and presentation not in HAIL_FORMS:
        # Reachable from authored data, so a bad value must not end the caller's task.
        DEBUG(f"[hail] unknown presentation {presentation!r}; expected one of {HAIL_FORMS}")
        presentation = None

    q = _hail_queue(ship_id)
    if key is not None:
        active = _hail_get(ship_id, KEY_ACTIVE, None)
        if any(r.get("key") == key for r in q) or (active or {}).get("key") == key:
            return None

    hail_id = int(_hail_get(ship_id, KEY_NEXT_ID, 1) or 1)
    set_inventory_value(ship_id, KEY_NEXT_ID, hail_id + 1)

    record = {
        "id": hail_id, "key": key, "scene": scene, "scenes": scenes,
        "speaker": speaker, "subject": subject if isinstance(subject, str) else (to_id(subject) or 0),
        "presentation": presentation, "backdrop": backdrop, "audio": audio,
        "face": face, "name": name, "color": color, "title": title,
        "priority": int(priority or 0), "beat": 0,
        "expires_at": (_hail_now() + float(expires)) if expires else None,
        "offered_at": _hail_now(),
        "lines": _hail_lines_from(lines, speaker), "choices": _hail_choices_from(choices),
        "resolved": lines is not None or choices is not None,
        "taken": [],
    }
    q.append(record)
    # Priority first, then the order they arrived - a stable sort keeps FIFO within a
    # priority, which is what makes "the queue" predictable to a player.
    q.sort(key=lambda r: -int(r.get("priority") or 0))
    set_inventory_value(ship_id, KEY_QUEUE, q)
    _hail_emit(ship_id, "offered", record)
    return hail_id


def hail_offer_amd(ship, scenes, speaker_key, when="hail", **overrides):
    """Offer the hail a speaker's AMD scenes declare - the AMD front door.

    Finds the scene whose `Speaker:` is `speaker_key` and whose `When:` is `hail`, then
    reads its fence for the presentation fields. Anything passed as a keyword wins over
    the document, so a mission can film a different subject without editing the script.

    Returns:
        int | None: the hail id, or None when that speaker declares no hail entry.
    """
    ship_id = _hail_sid(ship)
    if ship_id is None:
        return None
    scene_key = dialogue_entry_for(scenes or {}, speaker_key, when=when)
    if scene_key is None:
        return None
    node = (scenes or {}).get(scene_key) or {}
    data = node.get("data") or {}
    fields = {
        "scene": scene_key, "speaker": speaker_key, "scenes": scenes,
        "presentation": data.get("presentation"), "backdrop": data.get("backdrop"),
        "subject": data.get("subject"), "audio": data.get("audio"),
        "title": data.get("title"), "face": data.get("face"),
        "color": data.get("color"), "priority": data.get("priority") or 0,
    }
    fields.update({k: v for k, v in overrides.items() if v is not None})
    return hail_offer(ship_id, **fields)


def _hail_expired(record, now):
    at = record.get("expires_at")
    return at is not None and now >= at


def _hail_subject_gone(record):
    """True only for a NUMERIC subject that no longer exists. A string subject is
    resolved late by the renderer (it may be a role, or a ship not spawned yet), so it
    is never grounds for dropping a hail."""
    subject = record.get("subject")
    return bool(subject) and not isinstance(subject, str) and to_object(subject) is None


def hail_pending(ship):
    """Hails waiting to be answered, best first.

    Prunes expired hails and hails whose subject has been destroyed, lazily, here -
    which is why there is no ticker and no extra entry in the reset ledger.
    """
    ship_id = _hail_sid(ship)
    if ship_id is None:
        return []
    q = _hail_queue(ship_id)
    now = _hail_now()
    live = [r for r in q if not _hail_expired(r, now) and not _hail_subject_gone(r)]
    if len(live) != len(q):
        set_inventory_value(ship_id, KEY_QUEUE, live)
    return [MastDataObject(dict(r)) for r in live]


def hail_pending_count(ship):
    """How many hails are waiting. Drives the answer strip."""
    return len(hail_pending(ship))


def hail_cancel(ship, hail_id=None):
    """Withdraw an unanswered hail - the caller hung up, or the story moved on.

    With no `hail_id`, drops every pending hail. Does not touch an OPEN conversation;
    use `hail_close` for that.
    """
    ship_id = _hail_sid(ship)
    if ship_id is None:
        return False
    q = _hail_queue(ship_id)
    keep = [] if hail_id is None else [r for r in q if r.get("id") != hail_id]
    if len(keep) == len(q):
        return False
    set_inventory_value(ship_id, KEY_QUEUE, keep)
    _hail_emit(ship_id, "declined")
    return True


def hail_active(ship):
    """The open conversation, or None."""
    rec = _hail_get(_hail_sid(ship), KEY_ACTIVE, None)
    return MastDataObject(dict(rec)) if rec else None


def hail_is_active(ship):
    """Whether a conversation is open on this ship."""
    return _hail_get(_hail_sid(ship), KEY_ACTIVE, None) is not None


# --- driving the conversation ----------------------------------------------
def _hail_apply_scene_fields(record):
    """Adopt the fields the scene we have just BRANCHED to declares.

    A conversation is several scenes, and each is entitled to its own `Audio:`,
    `Presentation:` and title - the confrontation can be an orbit shot and the reply a
    portrait. Without this the record keeps the ENTRY scene's fields forever, so a
    branch replays the first scene's sound and never changes how it is drawn.

    Only fields the new scene actually declares are taken, so a scene that says nothing
    about presentation keeps what the conversation was already using. Called on a
    branch, not on resolve - the entry scene's fields are applied by `hail_offer_amd`,
    where an explicit override is still allowed to win.
    """
    scenes, key = record.get("scenes"), record.get("scene")
    node = (scenes or {}).get(key) if scenes else None
    data = (node or {}).get("data") or {}
    for field in ("audio", "presentation", "backdrop", "subject", "title",
                  "face", "color"):
        value = data.get(field)
        if value not in (None, ""):
            record[field] = value


def _hail_resolve_scene(ship_id, record):
    """Cache this scene's beats and choices onto the record.

    Called once per SCENE, not per repaint: `dialogue_beats` picks a random eligible
    variant every call, so a repaint that re-resolved would make the spoken line
    flicker - and the choices a console renders have to be the same list the server
    arbitrates against.
    """
    scenes, key = record.get("scenes"), record.get("scene")
    node = (scenes or {}).get(key) if scenes else None
    if node is None:
        record["resolved"] = True
        return record
    parsed = dialogue_parse(node)
    card = hail_speaker(record.get("speaker"), ship_id)
    record["lines"] = [{"speaker": b.get("speaker"), "surface": b.get("surface"),
                        "direction": b.get("direction"), "text": b.get("text")}
                       for b in dialogue_beats(parsed, ship_id, card)]
    record["choices"] = [{"label": c.get("label"), "target": c.get("target"),
                          "outcomes": c.get("outcomes") or []}
                         for c in dialogue_choices(parsed, ship_id, card)][:HAIL_MAX_CHOICES]
    record["beat"] = 0
    record["resolved"] = True
    return record


def _hail_record_beat(ship_id, rec):
    """Append the beat being spoken NOW to the conversation's transcript.

    Recorded as it is SAID, not when a scene is resolved. A scene's beats are cached at
    resolve time, but a conversation that branches resolves several scenes and a player
    who closes early never hears the rest - so resolving is the wrong moment, and
    `lines` (which each new scene overwrites) is the wrong list. This is what makes a
    replay the whole conversation rather than only its last scene.
    """
    lines = rec.get("lines") or []
    index = int(rec.get("beat") or 0)
    if not (0 <= index < len(lines)):
        return
    beat = lines[index]
    card = hail_speaker(beat.get("speaker") or rec.get("speaker"), ship_id)
    rec.setdefault("transcript", []).append({
        "kind": "line",
        "name": rec.get("name") or card.get("name", "") or beat.get("speaker") or "",
        "text": beat.get("text") or "",
    })


def hail_accept(ship, hail_id=None, client_id=None):
    """Open a waiting hail. Normally reached from an `Answer:` button on the strip.

    Takes the head of the queue unless a `hail_id` names one. Resolves and caches the
    scene, bumps the arbitration token, and plays the scene's `Audio:` once - server
    side, so five consoles do not start five copies of it.

    Does NOT force any screen: each console shows the conversation only if its own
    placement dial says to.

    Returns:
        MastDataObject | None: the opened record, or None if nothing was answerable.
    """
    ship_id = _hail_sid(ship)
    if ship_id is None:
        return None
    if client_id is not None and not _hail_may_answer(client_id):
        return None
    if _hail_get(ship_id, KEY_ACTIVE, None) is not None:
        return None                       # one conversation at a time, by design
    pending = [r for r in _hail_queue(ship_id)
               if not _hail_expired(r, _hail_now()) and not _hail_subject_gone(r)]
    if not pending:
        return None
    record = pending[0] if hail_id is None else next(
        (r for r in pending if r.get("id") == hail_id), None)
    if record is None:
        return None

    set_inventory_value(ship_id, KEY_QUEUE, [r for r in pending if r is not record])
    if not record.get("resolved"):
        _hail_resolve_scene(ship_id, record)
    set_inventory_value(ship_id, KEY_ACTIVE, record)
    _hail_record_beat(ship_id, record)
    _hail_bump_seq(ship_id)
    _hail_play_audio(record)
    _hail_presentation_apply(ship_id)
    _hail_emit(ship_id, "accepted", record, client_id=client_id)
    return MastDataObject(dict(record))


def hail_beat(ship):
    """The beat being spoken right now, or None when the beats are done.

    The card is already resolved: `speaker` is the cue key, `name`/`face`/`color` are
    what to draw with.

    NEVER assign `.text` to a bare MAST variable. Dialogue text may contain `{`, and
    MAST re-formats a string on assignment as an f-string - the failure is reported
    against the assignment line, not against the text. Pass it straight to a widget.
    """
    ship_id = _hail_sid(ship)
    rec = _hail_get(ship_id, KEY_ACTIVE, None)
    if not rec:
        return None
    lines = rec.get("lines") or []
    index = int(rec.get("beat") or 0)
    if index >= len(lines):
        return None
    beat = dict(lines[index])
    card = hail_speaker(beat.get("speaker") or rec.get("speaker"), ship_id)
    beat["name"] = rec.get("name") or card.get("name", "")
    beat["face"] = rec.get("face") or card.get("face", None)
    beat["color"] = rec.get("color") or card.get("color", None)
    return MastDataObject(beat)


def hail_more(ship):
    """Whether the conversation has another beat waiting to be heard.

    What the console asks to decide between a `Continue` button and the answers. The
    LAST beat is shown together with its choices - a line and the replies to it on
    screen at once, which is how the reference conversations read - so this is false on
    the final beat and a single-beat hail is answerable the moment it opens.
    """
    rec = _hail_get(_hail_sid(ship), KEY_ACTIVE, None)
    if not rec:
        return False
    return int(rec.get("beat") or 0) < len(rec.get("lines") or []) - 1


def hail_advance(ship, client_id=None, seq=None):
    """Move to the next beat - the crew reading on.

    Arbitrated exactly like `hail_answer`, and for the same reason: two officers
    pressing Continue in the same frame must not skip a line between them. A scripted
    or timed advance passes no `client_id` and so skips the console check.

    Returns:
        bool: True if another beat is now speaking; False when the beats are spent and
        the choices have gone live.
    """
    ship_id = _hail_sid(ship)
    rec = _hail_get(ship_id, KEY_ACTIVE, None)
    if not rec:
        return False
    if client_id is not None:
        if hail_replaying(client_id) or not _hail_may_answer(client_id):
            return False
    if seq is not None and int(seq) != int(_hail_get(ship_id, KEY_SEQ, 0) or 0):
        return False
    lines = rec.get("lines") or []
    index = int(rec.get("beat") or 0) + 1
    rec["beat"] = index
    _hail_record_beat(ship_id, rec)
    set_inventory_value(ship_id, KEY_ACTIVE, rec)
    _hail_bump_seq(ship_id)
    _hail_presentation_apply(ship_id)   # the band shows the beat, so it moves with it
    _hail_emit(ship_id, "beat", rec)
    return index < len(lines)


def hail_choices(ship):
    """The answers on offer, capped at `HAIL_MAX_CHOICES`.

    Empty until the beats have all been spoken, so a console can render the strip
    unconditionally and get the right thing at every moment of the conversation.
    """
    ship_id = _hail_sid(ship)
    rec = _hail_get(ship_id, KEY_ACTIVE, None)
    if not rec:
        return []
    if int(rec.get("beat") or 0) < len(rec.get("lines") or []) - 1:
        return []
    seq = int(_hail_get(ship_id, KEY_SEQ, 0) or 0)
    return [MastDataObject({"label": c.get("label"), "target": c.get("target"),
                            "outcomes": c.get("outcomes") or [], "index": i, "seq": seq})
            for i, c in enumerate(rec.get("choices") or [])]


def _hail_may_answer(client_id):
    """Only a comms console answers a hail.

    Enforced HERE rather than by hiding buttons: hiding is cosmetic, and a press can
    still arrive from a console that should not have one.
    """
    return bool(client_id) and has_role(client_id, "comms")


def hail_answer(ship, index, client_id=None, seq=None):
    """Take one of the offered answers. The arbitration point.

    Refuses - returning False and changing nothing - when there is no open hail, when
    this console is replaying (a replay can never rewrite what was chosen), when the
    console is not a comms console, when `index` is out of range, when `seq` is stale
    (another console already answered), or when an outcome handler refuses the pick
    because the player cannot afford it.

    A scripted answer passes no `client_id` and so skips the console check.

    Returns:
        bool: whether the answer was taken.
    """
    ship_id = _hail_sid(ship)
    if ship_id is None:
        return False
    rec = _hail_get(ship_id, KEY_ACTIVE, None)
    if not rec:
        return False
    if client_id is not None:
        if hail_replaying(client_id) or not _hail_may_answer(client_id):
            return False
    if seq is not None and int(seq) != int(_hail_get(ship_id, KEY_SEQ, 0) or 0):
        return False
    if int(rec.get("beat") or 0) < len(rec.get("lines") or []) - 1:
        return False                      # still talking; nothing is answerable yet
    choices = rec.get("choices") or []
    if not (0 <= int(index) < len(choices)):
        return False
    choice = choices[int(index)]

    # Bump BEFORE the outcome runs, so a second console pressing in the same frame is
    # already carrying a stale token by the time it gets here.
    _hail_bump_seq(ship_id)
    card = hail_speaker(rec.get("speaker"), ship_id)
    if dialogue_apply(ship_id, card, choice.get("outcomes")) is False:
        # A distinct state, not "answered": nothing was chosen, but the token HAS moved,
        # so every console still has to repaint - and a mission wants to be able to say
        # "you cannot afford that" without inspecting which branch it was.
        _hail_emit(ship_id, "refused", rec, client_id=client_id, choice=choice)
        return False

    rec.setdefault("taken", []).append(
        {"scene": rec.get("scene"), "label": choice.get("label")})
    rec.setdefault("transcript", []).append(
        {"kind": "choice", "name": "", "text": choice.get("label") or ""})
    target = choice.get("target")
    scenes = rec.get("scenes") or {}
    if target and target in scenes:
        rec["scene"] = target
        rec["resolved"] = False
        _hail_apply_scene_fields(rec)
        _hail_resolve_scene(ship_id, rec)
        _hail_record_beat(ship_id, rec)
        set_inventory_value(ship_id, KEY_ACTIVE, rec)
        _hail_play_audio(rec)
        _hail_presentation_apply(ship_id)
        _hail_emit(ship_id, "answered", rec, client_id=client_id, choice=choice)
        return True
    _hail_emit(ship_id, "answered", rec, client_id=client_id, choice=choice)
    hail_close(ship_id)
    return True


def hail_decline(ship, hail_id=None):
    """Dismiss a hail without answering it - the crew simply does not pick up."""
    ship_id = _hail_sid(ship)
    if ship_id is None:
        return False
    if hail_id is None and _hail_get(ship_id, KEY_ACTIVE, None) is not None:
        return hail_close(ship_id, declined=True)
    return hail_cancel(ship_id, hail_id)


def hail_close(ship, declined=False):
    """End the open conversation and archive it for replay.

    The next queued hail stays PENDING rather than opening itself, so the strip
    re-fills with an `Answer:` entry instead of the screen cutting to a stranger.

    Stands the main-screen shot down only if this hail is what started it
    (`HAIL_TOOK_VIEWER`) - helm may already have taken the screen back, and putting our
    idea of "before" over the top would undo their change.
    """
    ship_id = _hail_sid(ship)
    if ship_id is None:
        return False
    rec = _hail_get(ship_id, KEY_ACTIVE, None)
    if not rec:
        return False
    set_inventory_value(ship_id, KEY_ACTIVE, None)
    _hail_bump_seq(ship_id)
    _hail_band_drop(ship_id)

    log = list(_hail_get(ship_id, KEY_LOG, None) or [])
    log.insert(0, {"id": rec.get("id"), "scene": rec.get("scene"),
                   "speaker": rec.get("speaker"), "name": rec.get("name"),
                   "title": rec.get("title"), "face": rec.get("face"),
                   "color": rec.get("color"), "lines": list(rec.get("lines") or []),
                   "transcript": list(rec.get("transcript") or []),
                   "taken": list(rec.get("taken") or []),
                   "closed_at": _hail_now(), "declined": bool(declined)})
    set_inventory_value(ship_id, KEY_LOG, log[:HAIL_LOG_CAP])

    if _hail_get(ship_id, KEY_TOOK_VIEWER, False):
        set_inventory_value(ship_id, KEY_TOOK_VIEWER, False)
        try:
            from .gui.viewscreen import viewscreen_clear
            viewscreen_clear(ship_id)
        except Exception as e:
            DEBUG(f"[hail] could not stand the viewer down: {e}")
    _hail_emit(ship_id, "declined" if declined else "closed", rec)
    return True


# --- audio and presentation -------------------------------------------------
def _hail_play_audio(record):
    """Play a scene's `Audio:` once, server-side.

    Silent by design when there is no engine or no file: a missing sound must never end
    the task that opened the conversation.
    """
    name = record.get("audio")
    if not name:
        return False
    try:
        from .media import media_play_audio
        return media_play_audio(name)
    except Exception as e:
        DEBUG(f"[hail] audio {name!r} did not play: {e}")
        return False


def hail_form(ship, client_id=None):
    """How the open hail should be drawn, or None.

    On a COMMS console an `orbit` reads as `portrait` unless the comms orbit is turned
    on: driving the engine camera from a console that is not the main screen is the one
    unproven surface, so it degrades to a form that always works rather than risking a
    black centre panel.
    """
    ship_id = _hail_sid(ship)
    rec = _hail_get(ship_id, KEY_ACTIVE, None)
    if not rec:
        return None
    form = rec.get("presentation") or "portrait"
    if form == "orbit" and client_id is not None and has_role(client_id, "comms"):
        if not _hail_get(ship_id, "HAIL_COMMS_ORBIT", False):
            return "portrait"
    return form


def hail_subject(ship):
    """What an orbit shot should film. May be an id OR a late-resolved name/role."""
    rec = _hail_get(_hail_sid(ship), KEY_ACTIVE, None)
    return (rec or {}).get("subject") or 0


def _hail_band_drop(ship_id):
    """Take the orbit band down. Safe to call when there never was one."""
    try:
        from .gui.hail_gui import hail_band_clear
        hail_band_clear(ship_id)
    except Exception as e:
        DEBUG(f"[hail] could not clear the band: {e}")


def _hail_presentation_apply(ship_id):
    """Make the main screen agree with the open hail.

    Only `orbit` needs the engine: `portrait` and `still` are drawn by the console
    itself. Records `HAIL_TOOK_VIEWER` so `hail_close` only stands down a shot this
    hail actually started.
    """
    rec = _hail_get(ship_id, KEY_ACTIVE, None)
    if not rec or not _hail_get(ship_id, KEY_MAIN, False):
        _hail_band_drop(ship_id)
        return False
    if (rec.get("presentation") or "") != "orbit":
        _hail_band_drop(ship_id)
        return False
    subject = rec.get("subject")
    if not subject or isinstance(subject, str):
        return False                      # late-resolved; the renderer binds it
    try:
        from .gui.viewscreen import viewscreen_set
        from .gui.hail_gui import hail_band_show
        # viewscreen_set returns False when the shot is ALREADY what was asked for, so
        # only the first call claims the viewer - but the band is refreshed every time,
        # because the beat it is showing has usually moved on.
        if viewscreen_set(ship_id, "orbit", subject):
            set_inventory_value(ship_id, KEY_TOOK_VIEWER, True)
        hail_band_show(ship_id)
        return True
    except Exception as e:
        DEBUG(f"[hail] could not start the orbit shot: {e}")
    return False


# --- the placement dial -----------------------------------------------------
def hail_where_props(current=None):
    """The whole property string for the placement drop-down.

    The list key is `list:`, NOT `items:` - a dropdown built with the wrong key has no
    options to render and the engine dies allocating for it. `text:` is what shows
    while it is closed, so pass what this console is currently set to.
    """
    labels = ",".join(label for label, _v in HAIL_WHERE_LABELS)
    return f"text:{current or HAIL_WHERE_LABELS[0][0]};list:{labels}"


def hail_where_for(label):
    """The placement a drop-down label means. Unknown labels read as `off`."""
    for text, value in HAIL_WHERE_LABELS:
        if text == label:
            return value
    return "off"


def hail_where_label_for(value):
    """The drop-down label for a placement, so a repaint re-selects what is set."""
    for text, v in HAIL_WHERE_LABELS:
        if v == value:
            return text
    return HAIL_WHERE_LABELS[0][0]


def hail_where(client_id):
    """What this console's placement drop-down reads.

    DERIVED, not stored, and that is the whole point. The two halves live in different
    places - whether THIS console swaps its own centre is the console's own business,
    but the main screen belongs to the ship and any comms console can move it. A dial
    that only remembered its own last click would read "Off" on the second officer's
    console while the hail was plainly up on the main screen, and their "Off" would
    then be a no-op. Deriving it means every comms console agrees about the main screen
    and disagrees only about itself, which is exactly the truth.
    """
    here = bool(_hail_get(client_id, KEY_HERE, False))
    ship_id = _hail_sid(_hail_home_ship(client_id))
    main = bool(_hail_get(ship_id, KEY_MAIN, False)) if ship_id is not None else False
    if here and main:
        return "both"
    if here:
        return "console"
    if main:
        return "main"
    return "off"


def hail_where_set(client_id, where):
    """Point this console's dial somewhere.

    Writes both halves of the answer: this console's own `HAIL_WHERE`, and the SHIP's
    `HAIL_MAIN` when the value includes the main screen. Last writer wins on the ship
    half - deliberately the same arbitration science's On-Screen drop-down already has.

    A change that moved the main screen repaints EVERY console of the ship (the signal
    carries no client), so a second officer sees their own dial move rather than
    silently disagreeing with what is on screen.
    """
    if where not in HAIL_WHERE_VALUES:
        DEBUG(f"[hail] unknown placement {where!r}; expected one of {HAIL_WHERE_VALUES}")
        return False
    was = hail_where(client_id)
    if was == where:
        return False
    set_inventory_value(client_id, KEY_HERE, where in ("console", "both"))

    ship_id = _hail_sid(_hail_home_ship(client_id))
    want_main = where in ("main", "both")
    touched_main = (ship_id is not None
                    and bool(_hail_get(ship_id, KEY_MAIN, False)) != want_main)
    if ship_id is not None and touched_main:
        set_inventory_value(ship_id, KEY_MAIN, want_main)
        if want_main:
            _hail_presentation_apply(ship_id)
        else:
            # The band is the conversation on an orbit shot, so it has to go with the
            # screen - clearing only the SHOT would leave a name plate floating over a
            # view nobody asked for.
            _hail_band_drop(ship_id)
            if _hail_get(ship_id, KEY_TOOK_VIEWER, False):
                set_inventory_value(ship_id, KEY_TOOK_VIEWER, False)
                try:
                    from .gui.viewscreen import viewscreen_clear
                    viewscreen_clear(ship_id)
                except Exception as e:
                    DEBUG(f"[hail] could not stand the viewer down: {e}")
    if ship_id is not None:
        _hail_emit(ship_id, "where", _hail_get(ship_id, KEY_ACTIVE, None),
              client_id=None if touched_main else client_id)
    return True


def _hail_home_ship(client_id):
    """The ship this console belongs to.

    `viewscreen_home_ship` rather than `sbs.get_ship_of_client`: while an orbit shot is
    running the console is ASSIGNED to the subject, so the engine would answer with the
    raider that is being filmed.
    """
    try:
        from .gui.viewscreen import viewscreen_home_ship
        return viewscreen_home_ship(client_id)
    except Exception:
        return None


def hail_shows_here(client_id):
    """Whether THIS console should be drawing the conversation instead of its normal
    centre - the dial on a comms console, the ship's `HAIL_MAIN` on a main screen."""
    ship_id = _hail_sid(_hail_home_ship(client_id))
    if ship_id is None or not hail_is_active(ship_id):
        return False
    if has_role(client_id, "mainscreen"):
        return bool(_hail_get(ship_id, KEY_MAIN, False))
    return bool(_hail_get(client_id, KEY_HERE, False))


# --- what the console says --------------------------------------------------
def hail_answer_label(record):
    """The text on an `Answer:` button. ASCII, and owned here so no console can drift."""
    rec = record or {}
    who = rec.get("name") or rec.get("speaker") or "Hail"
    return f"Answer: {who}"


def hail_console_cares(client_id):
    """Whether a `hail` signal is worth a repaint on this console.

    The guard every `on signal hail:` hook uses, so four idle consoles do not rebuild
    themselves because a fifth moved its dial.
    """
    ship_id = _hail_sid(_hail_home_ship(client_id))
    if ship_id is None:
        return False
    if not (has_role(client_id, "comms") or has_role(client_id, "mainscreen")):
        return False
    return hail_is_active(ship_id) or hail_pending_count(ship_id) > 0


def hail_repaint_needed(client_id):
    """Whether the `hail` signal being handled right now should repaint THIS console.

    The one guard an `on signal hail:` hook needs. It reads the signal's own payload off
    the running task rather than making the console pass it, so a console cannot get the
    test subtly wrong, and it answers no to all three ways a repaint is wasted:

    * the signal is about another ship;
    * the signal named ONE console (a dial moved) and it was not this one;
    * this console is neither comms nor a main screen, or has nothing to show.

    Without the second test, one officer moving their own dial would rebuild every
    console on the bridge.
    """
    task = FrameContext.task
    if task is None:
        return hail_console_cares(client_id)
    ship_id = _hail_sid(_hail_home_ship(client_id))
    signal_ship = task.get_variable("HAIL_SHIP")
    if signal_ship is not None and ship_id is not None and signal_ship != ship_id:
        return False
    only = task.get_variable("HAIL_CLIENT")
    if only is not None and only != client_id:
        return False
    return hail_console_cares(client_id)


def hail_consoles(ship, consoles="comms"):
    """The consoles of one ship that a hail addresses."""
    try:
        from .gui.overlay import consoles_of
        return consoles_of(_hail_sid(ship), consoles=consoles)
    except Exception:
        return set()


# --- history and replay -----------------------------------------------------
def hail_log(ship):
    """Archived conversations, newest first. The info-panel history reads this."""
    return [MastDataObject(dict(e)) for e in (_hail_get(_hail_sid(ship), KEY_LOG, None) or [])]


def hail_log_entry(ship, log_id):
    """One archived conversation by hail id, or None."""
    for e in (_hail_get(_hail_sid(ship), KEY_LOG, None) or []):
        if e.get("id") == log_id:
            return MastDataObject(dict(e))
    return None


def hail_replay_start(client_id, log_id):
    """Show an archived conversation on this console.

    A replay is READ-ONLY, and that is enforced in `hail_answer` rather than by leaving
    the buttons out: there is no code path from a replay to an outcome.
    """
    set_inventory_value(client_id, KEY_REPLAY, log_id)
    ship_id = _hail_sid(_hail_home_ship(client_id))
    if ship_id is not None:
        _hail_emit(ship_id, "replay", None, client_id=client_id)
    return True


def hail_replay_stop(client_id):
    """Stop replaying on this console."""
    if _hail_get(client_id, KEY_REPLAY, None) is None:
        return False
    set_inventory_value(client_id, KEY_REPLAY, None)
    ship_id = _hail_sid(_hail_home_ship(client_id))
    if ship_id is not None:
        _hail_emit(ship_id, "replay", None, client_id=client_id)
    return True


def hail_replaying(client_id):
    """The log id this console is replaying, or None."""
    return _hail_get(client_id, KEY_REPLAY, None)
