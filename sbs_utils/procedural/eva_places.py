"""Places in a relic that SAY something when a suit gets there.

The EVA half of a boarding party's props. On the ground, walking up to a terminal opens
its scene in the Act app; in a relic the crew fly by destination, so the moment that
matters is ARRIVING - and until this, arriving somewhere in a ruin did nothing but stop
the suit. A place authored with ``Scene:`` now opens that scene, on the arriving
console's Act app, with whoever else is floating nearby joined in::

    ### [the concourse](at_concourse)
    ---
    Relic: voice
    Point: -1200, 0, 600
    Roles: voice_concourse
    Scene: voice_concourse_look
    Scan: A hall the size of a hangar deck, lit by nothing.
    ---

The scene lives in the relic file's own ``## Dialogue`` section (``relics_load``
registers it), so its ``Speaker:`` gives it a face and its ``Backdrop:`` a picture - the
same transcript a prop's scene gets. Choices may ``check`` a skill, ``open`` a barrier or
``reveal`` a hidden place: those verbs fall through from the props' to the relic's.

ONCE PER PLACE, NOT PER CONSOLE. A place is a moment in the story of the ruin: the first
suit there opens it and anyone near joins; a second visit, or a later console, gets the
place's ``Scan:`` text as a note instead of the scene again. That matches how a prop's
scene behaves and it is what keeps six suits arriving together from opening six copies.
"""
from .boarding import (boarding_encounter, boarding_is_open, boarding_channel_join,
                       boarding_reader_note, boarding_clients)
from .execution import log
from .query import to_object
from .signal import signal_emit

#: How close another suit must be to be pulled into a place's scene - the same working
#: distance a suit reaches with its tools.
PLACE_JOIN_RADIUS = 600.0

_PLAYED = {}            # (relic, point) -> channel it was played on
_ENABLED = {"on": True}


def eva_places_enabled(on=None):
    """Whether arriving at a place opens its scene. Pass a value to set it; a mission
    that runs its own arrival beats turns it off."""
    if on is not None:
        _ENABLED["on"] = bool(on)
    return _ENABLED["on"]


def eva_place_channel(relic_key, point):
    """The channel a place's scene plays on."""
    return f"place:{relic_key}:{point}"


def eva_place_played(relic_key, point):
    """Whether a place's scene has been opened this mission."""
    return (relic_key, point) in _PLAYED


def _near_consoles(client_id, relic_key):
    """Other consoles whose suits are close to this console's suit, in the same relic."""
    from .eva import eva_drivers, eva_my_relic, eva_my_suit
    mine = to_object(eva_my_suit(client_id))
    if mine is None:
        return []
    here = mine.pos
    r2 = PLACE_JOIN_RADIUS * PLACE_JOIN_RADIUS
    team = boarding_clients()
    out = []
    for cid in eva_drivers():
        if cid == client_id or cid not in team or eva_my_relic(cid) != relic_key:
            continue
        other = to_object(eva_my_suit(cid))
        if other is None:
            continue
        p = other.pos
        if (p.x - here.x) ** 2 + (p.y - here.y) ** 2 + (p.z - here.z) ** 2 <= r2:
            out.append(cid)
    return out


def eva_place_arrive(client_id, relic_key=None, point=None, first_visit=True):
    """A suit has arrived at a place: open its scene, or leave a note. Returns the
    channel when a scene is open for this console, else None.

    Called by the autopilot the moment a route ends (`eva_tick`), before `eva_arrived` is
    emitted - so a mission's own `//signal/eva_arrived` sees the scene already open.

    ``first_visit`` is whether THIS console had been here before; a returning console gets
    no note, a new one gets the place's ``Scan:`` when its scene has already been played.
    """
    from .amd_relics import relic_part_scene, relic_part_scan
    from .amd_dialogue import dialogue_registered_scenes
    from .eva import eva_my_relic
    if not _ENABLED["on"] or not point:
        return None
    relic_key = relic_key or eva_my_relic(client_id)
    if not relic_key:
        return None
    scene = relic_part_scene(relic_key, point)
    key = (relic_key, point)
    if scene and key not in _PLAYED:
        scenes = dialogue_registered_scenes()
        if scene not in scenes:
            # Lint catches this in a linted mission; a mission run without linting would
            # otherwise just have a silent place. Say it once.
            # Through `_relic_say`, the way the rest of a ruin reports itself: the `eva`
            # log category has no handler, so this line reached nothing and a misspelled
            # `Scene:` was a place that silently said nothing.
            _PLAYED[key] = None
            from .amd_relics import _relic_say
            _relic_say(f"relic '{relic_key}': place '{point}' names scene '{scene}', which "
                       f"is not a scene the game has read, so the place says nothing. "
                       f"Check the spelling, and that the scene is in the file's "
                       f"## Dialogue section.")
            return None
        ch = boarding_encounter(scenes, scene, client_id,
                                channel=eva_place_channel(relic_key, point),
                                members=_near_consoles(client_id, relic_key))
        _PLAYED[key] = ch
        if ch:
            signal_emit("eva_place_scene", {"EVA_CLIENT": client_id, "EVA_RELIC": relic_key,
                                            "EVA_POINT": point, "EVA_SCENE": scene,
                                            "EVA_CHANNEL": ch})
        return ch
    ch = _PLAYED.get(key)
    if ch and boarding_is_open(ch):
        # Still going: join the conversation rather than start a second one.
        boarding_channel_join(client_id, ch)
        return ch
    if first_visit:
        text = relic_part_scan(relic_key, point)
        if text:
            boarding_reader_note(client_id, str(text))
    return None


def eva_places_clear():
    """Forget which places have played - the per-mission reset."""
    _PLAYED.clear()
    _ENABLED["on"] = True


def eva_places_count():
    """Reset-ledger probe. Must not create anything by asking."""
    return len(_PLAYED)
