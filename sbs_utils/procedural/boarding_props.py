"""Things on the ground a boarding party can use: props, doors, pickups - and a pack.

A tile area is somewhere to walk. Props make it somewhere to DO things: a wrecked drone to
search, a ledger to read, a hatch that will not open, a coil lying in the dust. Each is an
actor on the tile map (so it is drawn, can block a cell, and is hidden by fog like
anything else), declared as data::

    ## [Props](props)

    ### [Survey drone](drone)
    ---
    Area: ridge
    Mark: drone_wreck              # a mark in the area file (`At: x, y` is a cell)
    Sprite: prop:drone
    Scene: drone_search            # opens this dialogue for whoever uses it
    Blocks: yes
    Scan: Flight recorder intact.  # what the xESS Scan app says about it
    ---
    A colony survey drone, nose-down in the scree.

    ### [Depot shutter](depot_door)
    ---
    Area: colony
    Mark: depot_door
    Sprite: prop:door
    Open sprite: prop:door_open
    Opens with: key depot_key, check engineering 9, cut
    Blocks: yes
    ---

    ### [Injector](injector)
    ---
    Area: flats
    At: 22, 14
    Sprite: prop:part
    Item: injector
    Hidden until: crate_forced     # not on the map until that signal
    ---

WHERE IT STANDS is `Mark:` - a mark named in the area file - or `At: x, y`, a cell. Not a
mark name in `At:`: that field is a coordinate everywhere in AMD, so a word written there
reaches this module as nothing and the prop is never placed.

USING ONE. Clicking a prop within ``Reach`` (default 1) uses it; clicking one further off
walks up to it first and uses it on arrival. Using, in order: a hidden prop cannot be used;
a shut door tries each ``Opens with`` the user can satisfy; an ``Item`` is picked up into
the user's pack; a ``Scene`` opens a conversation for that console (and whoever is standing
with them). ``boarding_interacted`` reports what happened.

``Opens with`` terms: ``key <item>`` (someone holding it - the item is kept), ``check
<skill> <dc>`` (the user rolls), ``cut`` (a CUT or FULL shot opens it - see
``boarding_combat``), ``signal <name>`` (only that signal opens it - a bridge action).

A SHOT NEVER REMOVES A PROP. One that lists ``cut`` is opened by it; every other prop is
immune to weapons - scorched, and still there (``boarding_combat.boarding_tile_fire``).

SIGNALS ARE HEARD HERE. A door that ``Opens with: signal power_on`` opens when
``power_on`` is emitted, and a prop that is ``Hidden until: crate_forced`` is put on the
map when ``crate_forced`` is - by this module, which listens for exactly the names its
props wrote and stops listening on the mission reset. A mission wires nothing.

THE PACK is per BODY: what each crew member is carrying, on their lifeform's inventory.
Guards read it (``if holding medkit``, ``if party coil >= 3``) and outcome verbs change it
(``give medkit``, ``take coil``).
"""
from .inventory import get_inventory_value, set_inventory_value
from .query import to_id

PACK_KEY = "BOARDING_PACK"
_PROPS = {}             # key -> record
_BY_ID = {}             # actor id -> key
_NEXT_ID = [0x7E00000000000000]
_SCENES = {"doc": None}
_HEARD = set()          # the signal names some prop's `Opens with` / `Hidden until` wrote
# What a SAVED GAME says about props, by key: which were opened and which were taken.
# A ledger rather than a write into `_PROPS`, because a save is handed back before the
# site it describes has been declared - the ground is loaded when the crew arrives. A
# prop reads it as it is declared and again as it is placed. See the provider below.
_SAVED = {"opened": set(), "taken": set()}


def _norm(s):
    return str(s or "").strip().lower()


def _yes(v, default=False):
    """One authored yes/no - the schema's own parser, so there is one reading of it."""
    from .amd_schema import amd_yes
    return amd_yes(v, default)


# --- the pack ------------------------------------------------------------------------

def boarding_pack(lifeform):
    """``{item: count}`` this character is carrying."""
    return dict(get_inventory_value(to_id(lifeform), PACK_KEY, None) or {})


def boarding_give(lifeform, item, n=1):
    """Put ``n`` of ``item`` in a character's pack. Returns the new count."""
    lf = to_id(lifeform)
    pack = boarding_pack(lf)
    item = _norm(item)
    pack[item] = pack.get(item, 0) + int(n)
    set_inventory_value(lf, PACK_KEY, pack)
    from .signal import signal_emit
    signal_emit("boarding_pack_changed", {"BOARDING_WHO": lf, "BOARDING_ITEM": item,
                                          "BOARDING_COUNT": pack[item]})
    return pack[item]


def boarding_take_item(lifeform, item, n=1):
    """Take ``n`` of ``item`` out of a pack. False (and nothing taken) if short."""
    lf = to_id(lifeform)
    pack = boarding_pack(lf)
    item = _norm(item)
    if pack.get(item, 0) < int(n):
        return False
    pack[item] -= int(n)
    if pack[item] <= 0:
        del pack[item]
    set_inventory_value(lf, PACK_KEY, pack)
    from .signal import signal_emit
    signal_emit("boarding_pack_changed", {"BOARDING_WHO": lf, "BOARDING_ITEM": item,
                                          "BOARDING_COUNT": pack.get(item, 0)})
    return True


def boarding_holding(lifeform, item):
    return boarding_pack(lifeform).get(_norm(item), 0)


def boarding_party_holding(item):
    """How many of ``item`` the whole party is carrying between them."""
    from .boarding import boarding_team
    return sum(boarding_holding(lf, item) for lf in boarding_team())


def boarding_hand_over(giver, taker, item, n=1):
    """One crew member passes something to another."""
    if not boarding_take_item(giver, item, n):
        return False
    boarding_give(taker, item, n)
    return True


# --- props ---------------------------------------------------------------------------

def boarding_props_scenes(scenes):
    """The dialogue scenes a prop's ``Scene:`` names (from ``dialogue_scenes``)."""
    _SCENES["doc"] = scenes


def _opens(value):
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    out = []
    for part in str(value or "").split(","):
        bits = part.split()
        if bits:
            out.append([_norm(bits[0])] + bits[1:])
    return out


def boarding_field_number(value, default, label, name, key, whole=False):
    """A number a writer typed in a fence, or ``default`` when it is not one - said ONCE,
    in a writer's words, in ``mast.runtime.log``. NEVER RAISES: `Qty: two` used to raise
    inside the load, and a mission with one bad number had no ground at all.

    Args:
        value: what was written (None or empty is simply "not written").
        default: what the game uses instead.
        label (str): the field as the writer spells it - ``Qty``.
        name, key: the record, for the sentence.
        whole (bool): a count of things or cells - a fraction is not one.
    """
    if value is None or str(value).strip() == "":
        return default
    try:
        n = float(value)
        if whole and n != int(n):
            raise ValueError(value)
        return int(n) if whole else n
    except (TypeError, ValueError):
        pass
    try:
        from .boarding_ground import _say
        _say("'%s' (%s): `%s: %s` is not a %s, so it is read as %s. Write %s: `%s: %s`."
             % (name or key, key, label, value, "whole number" if whole else "number",
                default, "a whole number" if whole else "a number", label, default),
             once="number:%s:%s:%s" % (key, label, value), loud=True)
    except Exception:                                    # noqa: BLE001
        pass
    return default


def _pack_outcome_check(verb):
    """What `; give` / `; take` must look like - ``<item>`` or ``<item> <how many>`` -
    as a check that runs BEFORE any outcome of the answer is applied."""
    def check(tokens):
        tokens = [str(t) for t in tokens]
        if not tokens:
            return "`%s` names no item. Write `; %s <item>`." % (verb, verb)
        if len(tokens) == 1:
            return None
        if len(tokens) == 2:
            try:
                int(tokens[1])
                return None
            except ValueError:
                pass
        joined = "_".join(tokens)
        if len(tokens) >= 3:
            return ("`%s %s`: `%s` takes an item and, at most, how many - so the rest is "
                    "either part of the item's key (an item key is ONE word: `%s %s`) or "
                    "another outcome with the comma missing in front of it (`%s %s, %s`)."
                    % (verb, " ".join(tokens), verb, verb, joined, verb, tokens[0],
                       " ".join(tokens[1:])))
        return ("`%s %s`: an item key is ONE word, and `%s` is not how many of it. "
                "Write `%s %s`." % (verb, " ".join(tokens), tokens[1], verb, joined))
    return check


def boarding_prop_records(section):
    """Prop records from an AMD section, as plain dicts."""
    out = []
    if section is None:
        return out
    for n in section.get("children", []) or []:
        d = n.get("data") or {}

        def g(*names, _d=d):
            for name in names:
                if _d.get(name) not in (None, ""):
                    return _d.get(name)
            return None
        out.append({
            "key": _norm(n.get("key")),
            "name": n.get("display_text") or n.get("key"),
            "desc": (n.get("description") or "").strip(),
            "area": _norm(g("area")),
            # `Mark:` names a mark in the area file; `At:` is a coordinate. `At:` is a
            # global coord2 field, so a word written there reaches here as nothing.
            "at": g("mark") or g("at"),
            "sprite": g("sprite"),
            "open_sprite": g("open_sprite"),
            "color": g("color"),
            "scene": g("scene"),
            "item": _norm(g("item")) or None,
            "qty": boarding_field_number(g("qty"), 1, "Qty", n.get("display_text"),
                                         _norm(n.get("key")), whole=True),
            "reach": boarding_field_number(g("reach"), 1, "Reach", n.get("display_text"),
                                           _norm(n.get("key")), whole=True),
            "blocks": _yes(g("blocks"), False),
            "opens": _opens(g("opens_with")),
            "hidden": g("hidden_until"),
            "once": _yes(g("once"), False),
            "needs": g("needs"),
            # What the xESS Scan app says. It read `rec.get("scan")` all along and the
            # record never carried one, so every prop scanned as its description.
            "scan": g("scan"),
        })
    return out


def _listen(rec):
    """Hear the signals this prop wrote: `Opens with: signal X`, `Hidden until: X`."""
    names = {_norm(t[1]) for t in rec.get("opens") or () if t[0] == "signal" and len(t) > 1}
    if rec.get("hidden"):
        names.add(_norm(rec["hidden"]))
    names.discard("")
    if not names:
        return
    _HEARD.update(names)
    from .signal import signal_observe
    signal_observe(_on_ground_signal)


def _on_ground_signal(name, data):
    """Every emit, as it happens. One set lookup for a name no prop wrote."""
    name = _norm(name)
    if name not in _HEARD:
        return
    boarding_props_signal(name)
    for rec in list(_PROPS.values()):
        if not rec["shown"] and _norm(rec.get("hidden")) == name:
            boarding_prop_reveal(rec["key"])


def boarding_props_declare(section):
    """Remember every prop in a section. Returns the keys. Nothing is placed yet."""
    keys = []
    for rec in boarding_prop_records(section):
        if not rec["key"]:
            continue
        rec.update({"id": None, "open": not rec["opens"], "taken": False,
                    "used": False, "shown": not rec["hidden"]})
        _saved_apply(rec)
        _PROPS[rec["key"]] = rec
        _listen(rec)
        keys.append(rec["key"])
    return keys


def boarding_prop_add(key, area, at, **fields):
    """Declare one prop from code. Fields as in the AMD (snake_case)."""
    rec = {"key": _norm(key), "name": fields.pop("name", key), "desc": fields.pop("desc", ""),
           "area": _norm(area), "at": at, "sprite": None, "open_sprite": None,
           "color": None, "scene": None, "item": None, "qty": 1, "reach": 1,
           "blocks": False, "opens": [], "hidden": None, "once": False, "needs": None,
           "scan": None}
    for k, v in fields.items():
        rec[k] = _opens(v) if k == "opens" else v
    rec.update({"id": None, "open": not rec["opens"], "taken": False, "used": False,
                "shown": not rec["hidden"]})
    _saved_apply(rec)
    _PROPS[rec["key"]] = rec
    _listen(rec)
    return rec["key"]


def _cell(rec):
    from .tilemap import tilemap_mark_cells, _xy
    at = rec.get("at")
    if at is None:
        return None
    # A MARK first - `glyph_2` has a digit in it and is still a name, not a coordinate.
    if isinstance(at, str):
        cells = tilemap_mark_cells(rec["area"], at)
        if cells:
            return cells[0]
    return _xy(at)


def boarding_props_place(area=None):
    """Put declared props onto their tile areas. Returns how many were placed.

    Safe to call again: a prop already placed is left where it is.
    """
    from .tilemap import tilemap_place, tilemap_area
    placed = 0
    for rec in _PROPS.values():
        if rec["id"] is None:
            _saved_apply(rec)       # a save restored AFTER the ground was declared
        if rec["id"] is not None or rec["taken"] or not rec["shown"]:
            continue
        if area is not None and rec["area"] != _norm(area):
            continue
        if tilemap_area(rec["area"]) is None:
            continue
        cell = _cell(rec)
        if cell is None and rec.get("at") is None and "deck_mark" in rec:
            continue        # not aboard THIS hull, and `boarding_deck_settle` said so
        if cell is None:
            from .execution import log
            log(f"prop '{rec['key']}' has no cell in '{rec['area']}'", "boarding", "warning")
            continue
        _NEXT_ID[0] += 1
        rec["id"] = _NEXT_ID[0]
        _BY_ID[rec["id"]] = rec["key"]
        sprite = rec["open_sprite"] if (rec["open"] and rec["opens"] and rec["open_sprite"]) \
            else rec["sprite"]
        tilemap_place(rec["id"], rec["area"], cell[0], cell[1], sprite=sprite,
                      color=rec["color"], party=False, fixed=True,
                      blocks=rec["blocks"] and not (rec["opens"] and rec["open"]))
        placed += 1
    return placed


def boarding_prop(key):
    """The prop record, or None."""
    return _PROPS.get(_norm(key))


def boarding_prop_of(actor_id):
    """The prop key standing as this tile actor, or None."""
    return _BY_ID.get(actor_id)


def boarding_props(area=None):
    return sorted(k for k, r in _PROPS.items() if area is None or r["area"] == _norm(area))


def boarding_prop_is_scenery(rec):
    """True for a prop with nothing to it - no scene, item, lock, need or description.

    Scenery furnishes a map (a bunk, a console bank, a barrel) and blocks like any prop,
    but nothing lists it or offers to use it, and a click on it walks toward it."""
    if isinstance(rec, str):
        rec = _PROPS.get(_norm(rec))
    if rec is None:
        return False
    return not (rec.get("scene") or rec.get("item") or rec.get("opens")
                or rec.get("needs") or rec.get("desc"))


def boarding_prop_at(area, x, y):
    from .tilemap import tilemap_actors_at
    for aid in tilemap_actors_at(area, x, y):
        if aid in _BY_ID:
            return _BY_ID[aid]
    return None


def boarding_props_near(lifeform, reach=1):
    """Props within ``reach`` of this character, nearest first. Scenery is left out. A big
    prop is measured to its nearest cell, so the far end of a car is as near as the end
    you are standing by."""
    from .tilemap import tilemap_where, tilemap_actor_distance
    at = tilemap_where(lifeform)
    if at is None:
        return []
    out = []
    for key, rec in _PROPS.items():
        if rec["id"] is None or rec["area"] != at[0] or boarding_prop_is_scenery(rec):
            continue
        p = tilemap_where(rec["id"])
        if p is None or p[0] != at[0]:
            continue
        d = tilemap_actor_distance(rec["id"], at[1], at[2])
        if d <= max(reach, rec["reach"]):
            out.append((d, key))
    return [k for _, k in sorted(out)]


def boarding_prop_reveal(key):
    """A hidden prop can now be found."""
    rec = _PROPS.get(_norm(key))
    if rec is None:
        return False
    rec["shown"] = True
    boarding_props_place(rec["area"])
    return True


def boarding_prop_open(key, how="opened"):
    """Open a door or hatch: its cell can be walked and it draws open."""
    from .tilemap import tilemap_place, tilemap_where
    rec = _PROPS.get(_norm(key))
    if rec is None or rec["open"]:
        return False
    rec["open"] = True
    _saved_touch()
    if rec["id"] is not None:
        at = tilemap_where(rec["id"])
        if at:
            tilemap_place(rec["id"], at[0], at[1], at[2],
                          sprite=rec["open_sprite"] or rec["sprite"], blocks=False)
    from .signal import signal_emit
    signal_emit("boarding_prop_opened", {"BOARDING_PROP": rec["key"], "BOARDING_HOW": how})
    return True


def boarding_props_signal(name):
    """Open every prop whose ``Opens with`` names ``signal <name>``. Returns the keys.

    What a bridge action is wired to: the ship powers the Lantern, the Lantern's doors
    open. The library calls this itself when the signal is emitted (see ``_listen``); a
    mission calls it only to open those doors WITHOUT the signal.
    """
    opened = []
    for key, rec in _PROPS.items():
        if any(t[0] == "signal" and len(t) > 1 and _norm(t[1]) == _norm(name)
               for t in rec["opens"]):
            if boarding_prop_open(key, "signal"):
                opened.append(key)
    return opened


def boarding_prop_is_open(key):
    rec = _PROPS.get(_norm(key))
    return bool(rec and rec["open"])


def boarding_prop_remove(key):
    """Take a prop off the map (picked up, destroyed)."""
    from .tilemap import tilemap_remove
    rec = _PROPS.get(_norm(key))
    if rec is None or rec["id"] is None:
        return False
    tilemap_remove(rec["id"])
    _BY_ID.pop(rec["id"], None)
    rec["id"] = None
    return True


def boarding_prop_forget(key):
    """Take a prop off the map AND forget it - for something that was only ever there
    for a while (rubble on a node that has been repaired). A removed prop keeps its
    record, so ``boarding_props_place`` would put it back."""
    boarding_prop_remove(key)
    return _PROPS.pop(_norm(key), None) is not None


def _try_open(rec, lf):
    """Try each way this door opens that the user can manage. The first that works."""
    from .boarding import boarding_team
    notes = []
    for term in rec["opens"]:
        how = term[0]
        if how == "key" and len(term) > 1:
            if boarding_holding(lf, term[1]) or boarding_party_holding(term[1]):
                boarding_prop_open(rec["key"], "key")
                return "opened", f"{term[1].replace('_', ' ')} fits"
            notes.append(f"needs {term[1].replace('_', ' ')}")
        elif how == "check" and len(term) > 2:
            from .boarding_checks import boarding_check
            result = boarding_check(lf, term[1], int(term[2]))
            if result["ok"]:
                boarding_prop_open(rec["key"], "check")
                return "opened", result["text"]
            return "failed", result["text"]
        elif how == "cut":
            notes.append("could be cut")
        elif how == "signal":
            notes.append("will not open from here")
    return "locked", "; ".join(notes) or "locked"


def boarding_interact(client_id, key):
    """Use a prop. Returns ``(result, text)``.

    Results: ``hidden``, ``refused``, ``opened``, ``failed``, ``locked``, ``picked``,
    ``scene``, ``looked``. Emits ``boarding_interacted`` with the result.
    """
    from .boarding import boarding_me, boarding_encounter
    from .signal import signal_emit
    rec = _PROPS.get(_norm(key))
    lf = boarding_me(client_id)
    if rec is None or lf is None:
        return "refused", ""
    result, text = "looked", rec["desc"]
    if not rec["shown"] or rec["id"] is None:
        result, text = "hidden", ""
    elif rec["once"] and rec["used"]:
        result, text = "looked", rec["desc"]
    elif rec["needs"] and not _needs_ok(rec["needs"], lf):
        result, text = "refused", f"You would need {rec['needs']} for that."
    elif rec["opens"] and not rec["open"]:
        result, text = _try_open(rec, lf)
    elif rec["item"]:
        boarding_give(lf, rec["item"], rec["qty"])
        rec["taken"] = True
        _saved_touch()
        boarding_prop_remove(rec["key"])
        try:
            from .quest_driver import quest_on_collect
            quest_on_collect(lf, rec["item"])
        except Exception:                                # noqa: BLE001
            pass
        result, text = "picked", f"Picked up {rec['name']}."
        _pickup_note(client_id, lf, rec)
    elif rec["scene"] and _SCENES["doc"] is not None:
        # Whoever is standing with them hears it too.
        from .tilemap import tilemap_actors_near
        from .boarding import boarding_client_of
        others = [boarding_client_of(a) for a in tilemap_actors_near(lf, 2)]
        ch = boarding_encounter(_SCENES["doc"], rec["scene"], client_id,
                                channel=f"prop:{rec['key']}",
                                members=[c for c in others if c is not None])
        result, text = ("scene", rec["name"]) if ch else ("looked", rec["desc"])
    was = (rec["used"], rec.get("touched"))
    rec["used"] = rec["used"] or result in ("opened", "picked", "scene")
    rec["touched"] = True
    if (rec["used"], True) != was:
        # Dealt with: repaint so the map stops badging it as unexplored.
        from .tilemap import tilemap_touch
        tilemap_touch(rec["area"])
    signal_emit("boarding_interacted", {"BOARDING_CLIENT": client_id, "BOARDING_WHO": lf,
                                        "BOARDING_PROP": rec["key"],
                                        "BOARDING_RESULT": result, "BOARDING_TEXT": text})
    _note(client_id, text)
    return result, text


def _pickup_note(client_id, lf, rec):
    """What was picked up, in this console's Act transcript - with its picture, which is
    the sprite it lay on the map with."""
    from .boarding import boarding_find_note
    boarding_find_note(client_id, lf, f"picked up {rec['name']}.", rec.get("sprite"))


def _needs_ok(needs, lf):
    from .amd_dialogue import dialogue_guard_ok
    guard = str(needs).strip()
    if not any(op in guard for op in ("<", ">", "=")):
        guard = f"{guard} >= 1"
    return bool(dialogue_guard_ok(guard, lf, None))


_NOTES = {}


def _note(client_id, text):
    if text:
        _NOTES[client_id] = text


def boarding_last_note(client_id):
    """The last thing this console was told by a prop - for the device to show."""
    return _NOTES.get(client_id, "")


def boarding_prop_click(client_id, area, x, y):
    """The tile-click handler: use a prop in reach, or walk up to one and use it there."""
    from .boarding import boarding_me
    from .tilemap import tilemap_where, tilemap_actor_distance, tilemap_actor_cells
    key = boarding_prop_at(area, x, y)
    if key is None or boarding_prop_is_scenery(key):
        return False                       # not a prop to use: the click walks there
    rec = _PROPS[key]
    lf = boarding_me(client_id)
    at = tilemap_where(lf)
    if at is None:
        return False
    if tilemap_actor_distance(rec["id"], at[1], at[2]) <= rec["reach"]:
        boarding_interact(client_id, key)
        return True
    _walk_beside(client_id, lf, area, x, y, rec["reach"],
                 lambda _agent, _c=client_id, _k=key: boarding_interact(_c, _k),
                 cells=tilemap_actor_cells(rec["id"]))
    return True


def _walk_beside(client_id, lf, area, x, y, reach, intent, cells=None):
    """Walk to the nearest open cell within ``reach`` of (x, y) - or of any of ``cells``,
    for something bigger than one - and run ``intent`` there."""
    from collections import deque
    from .tilemap import tilemap_where, tilemap_walk, tilemap_is_open
    at = tilemap_where(lf)
    targets = set(cells or ()) | {(x, y)}
    near = set()
    for tx, ty in targets:
        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                if abs(dx) + abs(dy) <= reach and (tx + dx, ty + dy) not in targets:
                    near.add((tx + dx, ty + dy))
    # ONE search outward from where they stand: the first ring holding any of those cells
    # is the nearest, and the lowest (x, y) in it wins a tie. (A search per candidate was
    # one per cell round a barn.)
    start = (at[1], at[2])
    dist = {start: 0}
    q = deque([start])
    found, best_d = [], None
    while q:
        cur = q.popleft()
        d = dist[cur]
        if best_d is not None and d > best_d:
            break
        if cur in near and tilemap_is_open(area, *cur, ignore=lf):
            found.append(cur)
            best_d = d
            continue
        cx, cy = cur
        for nxt in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if nxt not in dist and tilemap_is_open(area, *nxt, ignore=lf):
                dist[nxt] = d + 1
                q.append(nxt)
    if not found:
        from .signal import signal_emit
        signal_emit("tilemap_blocked", {"TILEMAP_AGENT": lf, "TILEMAP_AREA": area,
                                        "TILEMAP_X": x, "TILEMAP_Y": y})
        return False
    best = min(found)
    tilemap_walk(lf, best[0], best[1], intent=intent)
    return True


# --- dialogue --------------------------------------------------------------------------

def _give_outcome(agent_id, speaker, tokens):
    if tokens:
        boarding_give(agent_id, tokens[0], int(tokens[1]) if len(tokens) > 1 else 1)
    return None


def _take_outcome(agent_id, speaker, tokens):
    if tokens:
        n = int(tokens[1]) if len(tokens) > 1 else 1
        if not boarding_take_item(agent_id, tokens[0], n):
            return False                                 # refuse the choice
    return None


# `open` and `reveal` are ONE verb each, shared by every body model: the registry keeps a
# single handler per verb, so a relic registering its own would silently have replaced the
# props'. A prop key wins; anything else is tried as a relic barrier (`open`) or a relic
# point (`reveal`) - the relic the actor's suit is in first, then any relic that has it.

def _open_outcome(agent_id, speaker, tokens):
    if tokens:
        if boarding_prop(tokens[0]) is not None:
            boarding_prop_open(tokens[0], "scene")
        else:
            _relic_verb("open", agent_id, tokens[0])
    return None


def _reveal_outcome(agent_id, speaker, tokens):
    if tokens:
        if boarding_prop(tokens[0]) is not None:
            boarding_prop_reveal(tokens[0])
        else:
            _relic_verb("reveal", agent_id, tokens[0])
    return None


def _relic_verb(verb, agent_id, name):
    """`open <barrier>` / `reveal <point>` against a relic. Never raises."""
    try:
        from .amd_relics import relic_open_barrier, relic_reveal_point, relic_find_part
        relic = relic_find_part(name, near=agent_id)
        if relic is None:
            return False
        if verb == "open":
            return relic_open_barrier(relic, name)
        return relic_reveal_point(relic, name)
    except Exception as e:                               # noqa: BLE001
        from .execution import log
        log(f"`{verb} {name}`: {e}", "boarding", "warning")
        return False


def _holding_metric(rest, agent_id):
    return boarding_holding(agent_id, rest) if agent_id is not None else 0


def _party_metric(rest, agent_id):
    return boarding_party_holding(rest)


from .amd_dialogue import dialogue_register_outcome  # noqa: E402
from .boarding import boarding_metric_word  # noqa: E402
dialogue_register_outcome("give", _give_outcome, check=_pack_outcome_check("give"))
dialogue_register_outcome("take", _take_outcome, check=_pack_outcome_check("take"))
dialogue_register_outcome("open", _open_outcome)
dialogue_register_outcome("reveal", _reveal_outcome)
boarding_metric_word("holding", _holding_metric)
boarding_metric_word("party", _party_metric)


def boarding_props_install():
    """Make map clicks reach props. Idempotent; a mission calls it once."""
    from .boarding_tiles import boarding_tile_click_handler
    boarding_tile_click_handler(boarding_prop_click)


# --- kept by a saved game --------------------------------------------------------------
#
# WHAT IS KEPT: a door that was opened, and a thing that was picked up, by the prop's key.
# Not where a thing was dropped, not what is in a pack, not a hidden prop that has been
# revealed (the signal that reveals it is the story's to send again).
#
# RESTORED STATE IS NOT NEWS: a prop that comes back open is simply open - no
# `boarding_prop_opened`, no `boarding_interacted`, and a taken prop is not handed to
# anybody a second time.

def _saved_touch():
    try:
        from .persistence import persist_provider_touch
        persist_provider_touch("boarding_props")
    except Exception:                                    # noqa: BLE001
        pass


def _saved_apply(rec):
    """Make one declared prop agree with the saved game. Silent, and only ever opens or
    takes: a save cannot shut a door the crew has opened since."""
    if rec.get("generated"):
        return                      # made by code for one visit: a save never names it
    key = rec.get("key")
    if key in _SAVED["taken"]:
        rec["taken"] = True
        rec["used"] = True
    if key in _SAVED["opened"] and rec.get("opens"):
        rec["open"] = True
        rec["used"] = True


def _props_snapshot():
    """Every prop that is open or taken now - plus what the save said about props that
    have not been declared this session (a site the crew did not go back to)."""
    opened = set(_SAVED["opened"])
    taken = set(_SAVED["taken"])
    for key, rec in _PROPS.items():
        # GENERATED props are not a writer's: a boarded ship's furniture and doors
        # (`boarding_deckplan`) are built for one visit under keys that mean a different
        # thing on the next hull, so nothing about them is worth keeping.
        if rec.get("generated"):
            continue
        if rec.get("opens") and rec.get("open"):
            opened.add(key)
        if rec.get("taken"):
            taken.add(key)
    out = {}
    if opened:
        out["opened"] = sorted(opened)
    if taken:
        out["taken"] = sorted(taken)
    return out


def _props_restore(blob):
    """REPLACE the ledger with what a save says, and bring anything already declared
    into line with it. Announces nothing."""
    blob = blob if isinstance(blob, dict) else {}
    _SAVED["opened"] = {_norm(k) for k in (blob.get("opened") or ())}
    _SAVED["taken"] = {_norm(k) for k in (blob.get("taken") or ())}
    for rec in _PROPS.values():
        if rec["id"] is None:
            _saved_apply(rec)


def boarding_props_saved_count():
    """Reset-ledger probe: how many props a saved game is still speaking for."""
    return len(_SAVED["opened"]) + len(_SAVED["taken"])


from .persistence import persist_provider_register as _persist_provider_register  # noqa: E402
_persist_provider_register("boarding_props", _props_snapshot, _props_restore, library=True)


def boarding_props_clear():
    from .signal import signal_unobserve
    signal_unobserve(_on_ground_signal)
    _HEARD.clear()
    _PROPS.clear()
    _BY_ID.clear()
    _NOTES.clear()
    _SAVED["opened"] = set()
    _SAVED["taken"] = set()
    _SCENES["doc"] = None


def boarding_props_count():
    """Reset-ledger probe."""
    return len(_PROPS) + len(_HEARD)
