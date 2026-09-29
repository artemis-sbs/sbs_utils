"""Trouble on the ground: the xESS weapon on a tile world, hostiles, and getting hurt.

THE WEAPON is the same three-setting ladder as on an interior (`boarding_site`): STUN
stops somebody for a while, CUT opens a thing and wounds a person, FULL destroys. Aimed
by a map click while armed, one shot per arming, within ``FIRE_RANGE`` cells and a clear
line of sight. It reports through ``xess_fired`` exactly as the interior weapon does.

HOSTILES are declared as data and walk the tile map as actors::

    ## [Hostiles](hostiles)

    ### [Glassback](glassback_1)
    ---
    Area: caves
    At: 12, 8
    Sprite: lp:glassback
    HP: 2
    Damage: 1
    Notice: 5            # cells
    Stun: 10             # seconds a stun holds
    Patrol: 12,8  18,8  18,14
    Drops: coil
    Talk scene: vhesk_parley      # optional: clicking it talks instead of fighting
    Calm: no
    ---

One tick (``boarding_hostiles_watch``) runs them all: idle or patrolling until a crew
member is within ``Notice`` and in sight, then chasing, then striking when adjacent every
``Cooldown`` seconds. A stunned hostile stands still; a calmed one never attacks; at 0 HP
one is down and drops what it carried.

CREW take damage as HP on the body (``BOARDING_HP``, ``CREW_HP`` by default). At 0 a crew
member is DOWN - they cannot walk or act - until someone uses a medkit on them or a
medical choice revives them (``boarding_revive``). The whole party down emits
``boarding_party_down``; what that means is the mission's to say.

Signals: ``boarding_hostile_noticed``, ``boarding_hostile_struck``, ``boarding_hostile_down``,
``boarding_crew_hurt``, ``boarding_crew_down``, ``boarding_crew_revived``,
``boarding_party_down``. A downed hostile also emits ``hostile_down_<key>``, so a quest can
wait on it with an ordinary ``signal`` goal.
"""
from .inventory import get_inventory_value, set_inventory_value
from .query import to_id

FIRE_RANGE = 6
CREW_HP = 3
HP_KEY = "BOARDING_HP"
DOWN_ROLE = "boarding_down"

_HOSTILES = {}           # key -> record
_BY_ID = {}              # actor id -> key
_NEXT_ID = [0x7F00000000000000]
_WATCH = {"task": None}
_STUNNED = {}            # actor id (crew) -> until
_DROP = {"sprite": None}


def boarding_drop_sprite(sprite):
    """The atlas key a dropped item is drawn with."""
    _DROP["sprite"] = sprite


def _norm(s):
    return str(s or "").strip().lower()


def _now():
    from .tilemap import _now as tnow
    return tnow()


# --- crew health ---------------------------------------------------------------------

def boarding_hp(lifeform):
    return int(get_inventory_value(to_id(lifeform), HP_KEY, CREW_HP))


def boarding_is_down(lifeform):
    from .roles import has_role
    return has_role(to_id(lifeform), DOWN_ROLE)


def boarding_hurt(lifeform, amount=1, by=None):
    """Wound a crew member. Returns the HP left."""
    from .roles import add_role
    from .signal import signal_emit
    from .tilemap import tilemap_stop, tilemap_set_sprite
    lf = to_id(lifeform)
    if boarding_is_down(lf):
        return 0
    hp = max(0, boarding_hp(lf) - int(amount))
    set_inventory_value(lf, HP_KEY, hp)
    # SAY SO. Losing health used to be invisible until a crew member found they could not
    # move. The console hears it in words; the device's bar carries the number.
    _tell(lf, "Hit by %s - %s." % (_name(by), "you are DOWN" if hp <= 0
                                   else "%d of %d left" % (hp, CREW_HP)))
    signal_emit("boarding_crew_hurt", {"BOARDING_WHO": lf, "BOARDING_HP": hp,
                                       "BOARDING_BY": by})
    if hp <= 0:
        add_role(lf, DOWN_ROLE)
        tilemap_stop(lf)
        tilemap_set_sprite(lf, color="#555")
        # Drawn lying down when the art has a `_down` look; the grey stays the tell
        # either way.
        from .tilemap import tilemap_set_pose
        tilemap_set_pose(lf, "down")
        signal_emit("boarding_crew_down", {"BOARDING_WHO": lf, "BOARDING_BY": by})
        # Everyone ON THE GROUND - a crew member still aboard is not down there to help.
        from .boarding import boarding_team
        from .tilemap import tilemap_where
        team = [m for m in boarding_team() if tilemap_where(m) is not None]
        if team and all(boarding_is_down(m) for m in team):
            signal_emit("boarding_party_down", {})
    return hp


def _name(who):
    rec = _HOSTILES.get(who) if isinstance(who, str) else None
    if rec is not None:
        return rec["name"]
    if who == "orbit":
        return "fire from orbit"
    from .query import to_object
    return getattr(to_object(who), "name", None) or "something"


def _tell(lifeform, text):
    from .boarding import boarding_client_of
    from .boarding_props import _note
    cid = boarding_client_of(lifeform)
    if cid is not None:
        _note(cid, text)


def boarding_revive(lifeform, hp=None, by=None):
    """Bring a downed crew member back to their feet (default: half health)."""
    from .roles import remove_role
    from .signal import signal_emit
    from .tilemap import tilemap_set_sprite
    lf = to_id(lifeform)
    if not boarding_is_down(lf):
        return False
    remove_role(lf, DOWN_ROLE)
    set_inventory_value(lf, HP_KEY, int(hp if hp is not None else max(1, CREW_HP // 2 + 1)))
    tilemap_set_sprite(lf, color=get_inventory_value(lf, "BOARDING_COLOR", None) or "#4cf")
    from .tilemap import tilemap_set_pose
    tilemap_set_pose(lf, None)
    signal_emit("boarding_crew_revived", {"BOARDING_WHO": lf, "BOARDING_BY": by})
    return True


def boarding_heal(lifeform, amount=1):
    lf = to_id(lifeform)
    if boarding_is_down(lf):
        return boarding_revive(lf)
    set_inventory_value(lf, HP_KEY, min(CREW_HP, boarding_hp(lf) + int(amount)))
    return True


def boarding_stun_crew(lifeform, seconds):
    from .tilemap import tilemap_stop
    _STUNNED[to_id(lifeform)] = _now() + float(seconds)
    tilemap_stop(lifeform)


def boarding_crew_stunned(lifeform):
    return _STUNNED.get(to_id(lifeform), 0) > _now()


def boarding_can_act(lifeform):
    """Up, and not stunned."""
    return not boarding_is_down(lifeform) and not boarding_crew_stunned(lifeform)


# --- hostiles ------------------------------------------------------------------------

def _num(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _cells(value):
    from .tilemap import _xy
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        value = "  ".join(str(v) for v in value)
    out = []
    for chunk in str(value).replace(";", "  ").split("  "):
        at = _xy(chunk)
        if at:
            out.append(at)
    return out


def boarding_hostile_records(section):
    out = []
    if section is None:
        return out
    for n in section.get("children", []) or []:
        d = n.get("data") or {}
        out.append({
            "key": _norm(n.get("key")),
            "name": n.get("display_text") or n.get("key"),
            "desc": (n.get("description") or "").strip(),
            "area": _norm(d.get("area")),
            "at": d.get("mark") or d.get("at"),     # see boarding_props: Mark vs At
            "sprite": d.get("sprite"),
            "color": d.get("color"),
            "hp": int(_num(d.get("hp"), 2)),
            "damage": int(_num(d.get("damage"), 1)),
            "notice": int(_num(d.get("notice"), 5)),
            "stun": _num(d.get("stun"), 8),
            "cooldown": _num(d.get("cooldown"), 2),
            "speed": _num(d.get("speed"), 2.5),
            "patrol": _cells(d.get("patrol")),
            "drops": [_norm(x) for x in str(d.get("drops") or "").replace(",", " ").split()],
            "talk": d.get("talk_scene"),
            "calm": str(d.get("calm") or "").strip().lower() in ("yes", "true", "1"),
            "hidden": d.get("hidden_until"),
        })
    return out


def boarding_hostiles_declare(section):
    keys = []
    for rec in boarding_hostile_records(section):
        if rec["key"]:
            rec.update({"id": None, "state": "calm" if rec["calm"] else "idle",
                        "hp_left": rec["hp"], "stunned_until": 0.0, "next_strike": 0.0,
                        "target": None, "leg": 0, "shown": not rec["hidden"],
                        "talked": False})
            _HOSTILES[rec["key"]] = rec
            keys.append(rec["key"])
    return keys


def boarding_hostiles_place(area=None):
    """Put declared hostiles on their areas. Safe to call again."""
    from .tilemap import tilemap_place, tilemap_area, tilemap_mark_cells, _xy
    placed = 0
    for rec in _HOSTILES.values():
        if rec["id"] is not None or rec["state"] == "down" or not rec["shown"]:
            continue
        if area is not None and rec["area"] != _norm(area):
            continue
        if tilemap_area(rec["area"]) is None:
            continue
        at = rec["at"]
        cell = None
        if isinstance(at, str):                # a mark first; see boarding_props._cell
            cells = tilemap_mark_cells(rec["area"], at)
            cell = cells[0] if cells else None
        if cell is None:
            cell = _xy(at)
        if cell is None:
            continue
        _NEXT_ID[0] += 1
        rec["id"] = _NEXT_ID[0]
        _BY_ID[rec["id"]] = rec["key"]
        tilemap_place(rec["id"], rec["area"], cell[0], cell[1], sprite=rec["sprite"],
                      color=rec["color"], party=False, blocks=True, speed=rec["speed"],
                      exits=False)
        placed += 1
    boarding_hostiles_watch()
    return placed


def boarding_hostile(key):
    return _HOSTILES.get(_norm(key))


def boarding_hostile_of(actor_id):
    return _BY_ID.get(actor_id)


def boarding_hostile_state(key):
    rec = _HOSTILES.get(_norm(key))
    return rec["state"] if rec else None


def boarding_hostile_calm(key, calm=True):
    """Stand a hostile down (a parley worked) - or set it off again."""
    rec = _HOSTILES.get(_norm(key))
    if rec is None or rec["state"] == "down":
        return False
    from .tilemap import tilemap_stop
    rec["state"] = "calm" if calm else "idle"
    rec["target"] = None
    if rec["id"] is not None:
        tilemap_stop(rec["id"])
    return True


def boarding_hostile_reveal(key):
    rec = _HOSTILES.get(_norm(key))
    if rec is None:
        return False
    rec["shown"] = True
    boarding_hostiles_place(rec["area"])
    return True


def boarding_hostiles(area=None, alive=True):
    return sorted(k for k, r in _HOSTILES.items()
                  if (area is None or r["area"] == _norm(area))
                  and (not alive or r["state"] != "down"))


def _party_in(area):
    from .boarding import boarding_team
    from .tilemap import tilemap_where
    out = []
    for lf in boarding_team():
        at = tilemap_where(lf)
        if at and at[0] == area and not boarding_is_down(lf):
            out.append((lf, at[1], at[2]))
    return out


def _hostile_step(rec, now):
    from .tilemap import tilemap_where, tilemap_walk, tilemap_stop, tilemap_sees
    from .signal import signal_emit
    at = tilemap_where(rec["id"])
    if at is None or rec["state"] in ("down", "calm"):
        return
    if _in_parley(at[0]):
        tilemap_stop(rec["id"])
        return
    if rec["stunned_until"] > now:
        tilemap_stop(rec["id"])
        return
    area, x, y = at
    # Who can it see?
    best = None
    for lf, px, py in _party_in(area):
        d = abs(px - x) + abs(py - y)
        if d <= rec["notice"] and tilemap_sees(area, x, y, px, py):
            if best is None or d < best[0]:
                best = (d, lf, px, py)
    if best is None:
        if rec["state"] in ("chase", "attack"):
            rec["state"] = "idle"
            rec["target"] = None
        if rec["patrol"] and not _walking(rec):
            rec["leg"] = (rec["leg"] + 1) % len(rec["patrol"])
            px, py = rec["patrol"][rec["leg"]]
            tilemap_walk(rec["id"], px, py)
        return
    d, lf, px, py = best
    if rec["target"] != lf:
        rec["target"] = lf
        signal_emit("boarding_hostile_noticed", {"BOARDING_HOSTILE": rec["key"],
                                                 "BOARDING_WHO": lf})
    if d <= 1:
        rec["state"] = "attack"
        tilemap_stop(rec["id"])
        from .tilemap import tilemap_face
        tilemap_face(rec["id"], px, py)
        if now >= rec["next_strike"]:
            rec["next_strike"] = now + rec["cooldown"]
            signal_emit("boarding_hostile_struck", {"BOARDING_HOSTILE": rec["key"],
                                                    "BOARDING_WHO": lf})
            boarding_hurt(lf, rec["damage"], by=rec["key"])
    else:
        rec["state"] = "chase"
        tilemap_walk(rec["id"], px, py)


def _walking(rec):
    from .tilemap import tilemap_walking
    return tilemap_walking(rec["id"])


def boarding_hostiles_tick(t=None):
    """One pass over every hostile. Guarded per hostile - one bad record must not stop
    the tick, which would pause the mission."""
    now = _now()
    for rec in list(_HOSTILES.values()):
        if rec["id"] is None:
            continue
        try:
            _hostile_step(rec, now)
        except Exception as e:                           # noqa: BLE001
            from .execution import log
            log(f"hostile {rec['key']} stopped: {e}", "boarding", "warning")
            rec["state"] = "calm"


def boarding_hostiles_watch(seconds=0.5):
    from ..tickdispatcher import TickDispatcher
    if _WATCH["task"] is not None:
        return _WATCH["task"]
    _WATCH["task"] = TickDispatcher.do_interval(boarding_hostiles_tick, seconds)
    return _WATCH["task"]


def boarding_hostiles_unwatch():
    task, _WATCH["task"] = _WATCH["task"], None
    if task is not None:
        try:
            task.stop()
        except Exception:                                # noqa: BLE001
            pass


def _hostile_hit(rec, setting, by=None):
    """What a shot does to a hostile, by setting."""
    from .signal import signal_emit
    from .tilemap import tilemap_stop, tilemap_remove, tilemap_where
    if setting == "stun":
        rec["stunned_until"] = _now() + rec["stun"]
        tilemap_stop(rec["id"])
        return "stunned"
    rec["hp_left"] = 0 if setting == "full" else rec["hp_left"] - 1
    if rec["hp_left"] > 0:
        return "wounded"
    at = tilemap_where(rec["id"])
    rec["state"] = "down"
    tilemap_remove(rec["id"])
    _BY_ID.pop(rec["id"], None)
    rec["id"] = None
    # What it carried lands where it fell, as a pickup anyone can walk over and take.
    if at and rec["drops"]:
        from .boarding_props import boarding_prop_add, boarding_props_place
        for i, item in enumerate(rec["drops"]):
            boarding_prop_add(f"drop_{rec['key']}_{i}", at[0], (at[1], at[2]),
                              name=item.replace("_", " "), item=item, sprite=_DROP["sprite"])
        boarding_props_place(at[0])
    signal_emit("boarding_hostile_down", {"BOARDING_HOSTILE": rec["key"], "BOARDING_BY": by})
    signal_emit(f"hostile_down_{rec['key']}", {"BOARDING_HOSTILE": rec["key"]})
    return "down"


#: How close you must be to talk to someone. Talking from across a salt flat let a
#: crew member open a parley while the other side's guns were still up.
TALK_REACH = 2


def boarding_talk(client_id, key):
    """Open this person's talk scene for this console. True when it opened."""
    from .boarding_props import _SCENES
    from .boarding import boarding_encounter
    rec = _HOSTILES.get(_norm(key))
    if rec is None or not rec["talk"] or _SCENES["doc"] is None:
        return False
    opened = boarding_encounter(_SCENES["doc"], rec["talk"], client_id,
                                channel=f"talk:{rec['key']}") is not None
    if opened:
        # Face each other.
        from .boarding import boarding_me
        from .tilemap import tilemap_face, tilemap_where
        me = boarding_me(client_id)
        mine, theirs = tilemap_where(me), tilemap_where(rec["id"]) if rec["id"] else None
        if mine and theirs and mine[0] == theirs[0]:
            tilemap_face(me, theirs[1], theirs[2])
            tilemap_face(rec["id"], mine[1], mine[2])
    if opened and not rec.get("talked"):
        # Spoken to: the map stops badging this person as somebody new.
        rec["talked"] = True
        if rec.get("area"):
            from .tilemap import tilemap_touch
            tilemap_touch(rec["area"])
    return opened


def boarding_hostile_click(client_id, area, x, y):
    """Tile-click handler: a person with a ``Talk scene`` is TALKED to when clicked -
    from close up. Further off, the crew member walks over and talks on arrival."""
    from .tilemap import tilemap_actors_at, tilemap_where
    from .boarding import boarding_me
    for aid in tilemap_actors_at(area, x, y):
        key = _BY_ID.get(aid)
        rec = _HOSTILES.get(key) if key else None
        if not (rec and rec["talk"]):
            continue
        me = boarding_me(client_id)
        at = tilemap_where(me) if me is not None else None
        if at is None:
            return False
        if abs(at[1] - x) + abs(at[2] - y) <= TALK_REACH:
            return boarding_talk(client_id, key)
        from .boarding_props import _walk_beside
        _walk_beside(client_id, me, area, x, y, TALK_REACH,
                     lambda _a, _c=client_id, _k=key: boarding_talk(_c, _k))
        return True
    return False


def _in_parley(area):
    """Whether some crew member in this area is mid-conversation with someone here.
    Nobody fights while that is going on - a parley that gets you shot is not one."""
    from .boarding import boarding_channels, boarding_channel_members, boarding_me
    from .tilemap import tilemap_where
    for ch in boarding_channels():
        if not str(ch).startswith("talk:"):
            continue
        for cid in boarding_channel_members(ch):
            at = tilemap_where(boarding_me(cid))
            if at is not None and at[0] == area:
                return True
    return False


# --- the weapon on a tile map --------------------------------------------------------

def boarding_tile_fire(client_id, x, y):
    """Shoot the cell this console clicked. A shot disarms, whatever happens.

    Returns True when something was hit, and always reports through ``xess_fired``.
    """
    from .boarding import boarding_me
    from .boarding_site import boarding_setting, boarding_disarm
    from .signal import signal_emit
    from .tilemap import tilemap_where, tilemap_sees, tilemap_actors_at
    lf = boarding_me(client_id)
    setting = boarding_setting(client_id)
    boarding_disarm(client_id)
    at = tilemap_where(lf) if lf is not None else None

    def report(hit, what, reason=None, effect=None):
        signal_emit("xess_fired", {
            "XESS_CLIENT": client_id, "XESS_SITE": at[0] if at else None,
            "XESS_SETTING": setting, "XESS_X": int(x), "XESS_Y": int(y),
            "XESS_HIT": what, "XESS_REASON": reason, "XESS_EFFECT": effect,
            "XESS_DESTROYED": bool(hit and setting == "full")})
        return hit

    if at is None:
        return report(False, None, "no body")
    if not boarding_can_act(lf):
        return report(False, None, "cannot act")
    area = at[0]
    if abs(at[1] - x) + abs(at[2] - y) > FIRE_RANGE:
        return report(False, None, "out of range")
    from .tilemap import tilemap_face
    tilemap_face(lf, x, y)                 # turn to shoot, hit or miss
    if not tilemap_sees(area, at[1], at[2], int(x), int(y)):
        return report(False, None, "no line of sight")
    from .boarding import boarding_team
    team = set(boarding_team())
    for aid in tilemap_actors_at(area, x, y):
        if aid == lf:
            continue
        key = _BY_ID.get(aid)
        if key:
            return report(True, key, None, _hostile_hit(_HOSTILES[key], setting, lf))
        if aid in team:
            if setting == "stun":
                boarding_stun_crew(aid, 8)
                return report(True, aid, None, "stunned")
            boarding_hurt(aid, 99 if setting == "full" else 1, by=lf)
            return report(True, aid, None, "wounded")
        from .boarding_props import boarding_prop_of, _PROPS, boarding_prop_open, \
            boarding_prop_remove
        pkey = boarding_prop_of(aid)
        if pkey:
            rec = _PROPS[pkey]
            if setting == "stun":
                return report(True, pkey, None, "nothing")
            if rec["opens"] and not rec["open"] and \
                    any(t[0] == "cut" for t in rec["opens"]):
                boarding_prop_open(pkey, "cut")
                return report(True, pkey, None, "opened")
            if setting == "full":
                boarding_prop_remove(pkey)
                return report(True, pkey, None, "destroyed")
            return report(True, pkey, None, "scorched")
    return report(False, None, "nothing there")


def boarding_strike(area, x, y, radius=2, setting="full"):
    """Fire support from orbit: everything hostile within ``radius`` of a cell.

    Crew caught in it are hurt too - the bridge is firing blind at a point on a map.
    Returns the hostile keys that went down.
    """
    from .tilemap import tilemap_actors
    from .boarding import boarding_team
    from .signal import signal_emit
    from .tilemap import tilemap_where
    down = []
    team = set(boarding_team())
    for aid in tilemap_actors(area):
        at = tilemap_where(aid)
        if at is None or abs(at[1] - x) + abs(at[2] - y) > radius:
            continue
        key = _BY_ID.get(aid)
        if key and _hostile_hit(_HOSTILES[key], setting, "orbit") == "down":
            down.append(key)
        elif aid in team:
            boarding_hurt(aid, 1, by="orbit")
    signal_emit("boarding_strike", {"BOARDING_AREA": area, "BOARDING_X": x,
                                    "BOARDING_Y": y, "BOARDING_DOWN": down})
    return down


def boarding_combat_install():
    """Make map clicks reach talkable hostiles. Idempotent."""
    from .boarding_tiles import boarding_tile_click_handler
    boarding_tile_click_handler(boarding_hostile_click)


def boarding_combat_clear():
    boarding_hostiles_unwatch()
    _HOSTILES.clear()
    _BY_ID.clear()
    _STUNNED.clear()


def boarding_combat_count():
    """Reset-ledger probe."""
    return len(_HOSTILES) + len(_STUNNED) + (1 if _WATCH["task"] else 0)


# --- dialogue verbs: a conversation changes who is hostile --------------------------

def boarding_hostile_dismiss(key):
    """Take an actor off the map without a fight - an NPC who leaves, a youngster who
    goes with the party."""
    from .tilemap import tilemap_remove
    rec = _HOSTILES.get(_norm(key))
    if rec is None or rec["id"] is None:
        return False
    tilemap_remove(rec["id"])
    _BY_ID.pop(rec["id"], None)
    rec["id"] = None
    rec["state"] = "down"
    return True


def _calm_outcome(agent_id, speaker, tokens):
    for key in tokens:
        boarding_hostile_calm(key, True)
    return None


def _rouse_outcome(agent_id, speaker, tokens):
    for key in tokens:
        boarding_hostile_calm(key, False)
    return None


def _dismiss_outcome(agent_id, speaker, tokens):
    for key in tokens:
        boarding_hostile_dismiss(key)
    return None


def _summon_outcome(agent_id, speaker, tokens):
    for key in tokens:
        boarding_hostile_reveal(key)
    return None


from .amd_dialogue import dialogue_register_outcome  # noqa: E402
dialogue_register_outcome("calm", _calm_outcome)
dialogue_register_outcome("rouse", _rouse_outcome)
dialogue_register_outcome("dismiss", _dismiss_outcome)
dialogue_register_outcome("summon", _summon_outcome)
