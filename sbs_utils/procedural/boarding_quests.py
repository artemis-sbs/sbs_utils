"""Quests that belong to ONE crew member, and the transporter between tile areas.

PERSONAL QUESTS. A side quest in AMD names who it is for::

    ### [Patience's Heart](patience_heart)
    ---
    For: engineering            # a job word, or a crew member's name
    Done when: signal lp_hauler_fixed
    ---
    Find the three parts and fit them.

``boarding_quests_grant(section)`` grants each one to the body on the ground that
matches - it is theirs, it shows on their quest screens under their own name, and it
advances through the ordinary quest driver (signals, collects) like any other. A quest
nobody present matches goes to the whole party instead, so a short party is never
locked out of a story; a mission can make that version harder by reading
``boarding_quest_is_open(key)``.

THE TRANSPORTER. Moving a crew member between tile areas without walking:
``boarding_transport(client_id, area)``. It refuses (and says why) while jammed -
``boarding_transport_jam(True)`` is what a hostile ship in orbit does to it - and for an
area nobody has found yet.
"""
from ..agent import Agent
from .query import to_id

_OPEN = set()            # quest keys granted to the whole party for want of an owner
_GRANTED = {}            # quest key -> lifeform it went to
_JAM = {"on": False, "why": ""}


def _norm(s):
    return str(s or "").strip().lower()


def _matches(lifeform, want):
    """Is `want` this person: a job of theirs, their name, or who the ROSTER says they are.

    The roster half matters. A body is named after whatever is on the console, and a
    player may have saved a name of their own: `For: Hale` then matched nobody on the one
    machine at the table that had done so. The seat's roster member - its key, its name,
    its last name - is who the author meant, whatever the player is called.
    """
    from .boarding import boarding_jobs, boarding_client_of
    from .query import to_object
    want = _norm(want)
    if not want:
        return False
    if want in boarding_jobs(lifeform):
        return True
    names = [_norm(getattr(to_object(lifeform), "name", ""))]
    try:
        from .crew import crew_post_of, crew_roster
        client_id = boarding_client_of(lifeform)
        post = crew_post_of(client_id) if client_id is not None else None
        roster = crew_roster(getattr(post, "roster", "") or "") if post is not None else None
        key = _norm(getattr(post, "key", "")) if post is not None else ""
        if key and want == key:
            return True
        for member in (roster.get("members") if roster is not None else None) or ():
            if _norm(member.get("key")) == key:
                names.append(_norm(member.get("name")))
    except Exception:                                    # noqa: BLE001
        pass
    return any(name and (name == want or name.endswith(" " + want)) for name in names)


def boarding_quests_grant(section, team=None):
    """Grant every ``For:`` quest in a section to the crew member it names.

    Idempotent: a quest already granted is left where it went, so this can be called
    each time somebody beams down and only the newly arrived pick theirs up.

    Returns:
        dict: ``{quest key: lifeform id, or "party"}`` for what was granted this call.
    """
    from .quest_driver import quest_grant_amd
    from .boarding import boarding_team
    if section is None:
        return {}
    team = sorted(team if team is not None else boarding_team())
    out = {}
    for n in section.get("children", []) or []:
        key = _norm(n.get("key"))
        data = n.get("data") or {}
        want = data.get("for")
        if not key or not want or key in _GRANTED:
            continue
        owner = next((lf for lf in team if _matches(lf, want)), None)
        doc = {"children": [n]}
        if owner is not None:
            if key in _OPEN:
                continue                 # already the party's - do not grant it twice
            quest_grant_amd(owner, doc)
            _GRANTED[key] = owner
            out[key] = owner
    return out


def boarding_quests_open_unclaimed(section):
    """Give the whole party every ``For:`` quest nobody has claimed. Call it once the
    party is settled (not on the first beam-down, or the late arrival loses theirs)."""
    from .quest_driver import quest_grant_amd
    out = []
    for n in (section or {}).get("children", []) or []:
        key = _norm(n.get("key"))
        if not key or not (n.get("data") or {}).get("for"):
            continue
        if key in _GRANTED or key in _OPEN:
            continue
        quest_grant_amd(Agent.SHARED_ID, {"children": [n]})
        _OPEN.add(key)
        out.append(key)
    return out


def boarding_quest_owner(key):
    """The lifeform a personal quest went to, ``"party"``, or None."""
    key = _norm(key)
    if key in _GRANTED:
        return _GRANTED[key]
    return "party" if key in _OPEN else None


def boarding_quest_is_open(key):
    """True when a personal quest went to the whole party for want of its owner."""
    return _norm(key) in _OPEN


def boarding_quest_holder(client_id):
    """Point this console's quest screens at its crew member."""
    from .boarding import boarding_me
    from .quest_driver import quest_holder_set
    from .query import to_object
    me = boarding_me(client_id)
    if me is None:
        return False
    quest_holder_set(client_id, me, getattr(to_object(me), "name", "You"))
    return True


# --- the transporter ---------------------------------------------------------------

def boarding_transport_jam(on=True, why="Transporter jammed"):
    """Nobody beams anywhere while this is on."""
    _JAM["on"] = bool(on)
    _JAM["why"] = why if on else ""
    from .signal import signal_emit
    signal_emit("boarding_transport_jammed", {"BOARDING_JAMMED": _JAM["on"],
                                              "BOARDING_WHY": _JAM["why"]})


def boarding_transport_jammed():
    return _JAM["on"]


def boarding_transport_targets(client_id=None):
    """Tile areas the transporter can put someone: known, and beamable."""
    from .tilemap import tilemap_areas
    here = None
    if client_id is not None:
        from .boarding_tiles import boarding_tile_area_of
        here = boarding_tile_area_of(client_id)
    return [a for a in tilemap_areas(known_only=True, beam_only=True) if a != here]


def boarding_transport(client_id, area):
    """Beam this console's crew member to another area. Returns ``(ok, text)``."""
    from .tilemap import tilemap_known, tilemap_area, tilemap_title
    from .boarding_tiles import boarding_tile_put, boarding_tile_on
    from .boarding_combat import boarding_can_act
    from .boarding import boarding_me, boarding_channel_of, boarding_channel_leave, PARTY
    from .signal import signal_emit
    if _JAM["on"]:
        return False, _JAM["why"]
    rec = tilemap_area(area)
    if rec is None or not tilemap_known(area) or not rec["beam"]:
        return False, "No transporter lock on that site."
    me = boarding_me(client_id)
    if me is None or not boarding_tile_on(client_id):
        return False, "Nobody to beam."
    if not boarding_can_act(me):
        return False, "They cannot be moved like this - get them on their feet first."
    if boarding_channel_of(client_id) != PARTY:
        boarding_channel_leave(client_id)
    boarding_tile_put(client_id, rec["key"])
    signal_emit("boarding_transported", {"BOARDING_CLIENT": client_id, "BOARDING_WHO": me,
                                         "BOARDING_AREA": rec["key"]})
    return True, "Energizing - %s." % tilemap_title(rec["key"])


def boarding_quests_clear():
    _OPEN.clear()
    _GRANTED.clear()
    _JAM["on"] = False
    _JAM["why"] = ""


def boarding_quests_count():
    """Reset-ledger probe."""
    return len(_OPEN) + len(_GRANTED) + (1 if _JAM["on"] else 0)
