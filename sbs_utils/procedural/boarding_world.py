"""A boarding party's WORLD: several areas, each on its own host, and walking between them.

`boarding_site.py` puts bodies on ONE interior. An away mission worth playing has more than
one place - a landing ridge, a colony, a cave - and a party that splits up across them. The
shape that needs no new engine feature is the one the engine already has: **an area is a
space object with an interior, and which area a console sees is only which object that
console is assigned to.** Two consoles on two hosts are simply two consoles looking at two
different interiors.

THIS MODULE OWNS FOUR THINGS:

1. **Zones** - a named area, its host object, its title, where you arrive, and its exits.
   A zone either spawns a hidden host (a `starbase_civil` is a blank, fully open 41x40
   floor) or adopts an object that already exists, such as a real ship you can board.
2. **Blocking** - the engine has no API to close a cell of an interior, so a rock, a wall
   or a locked door is a cell the LIBRARY refuses to route through. A floor plan marks one
   with a legend role (`#: rock / blocker`).
3. **Walking around blockers** - the path is found here (breadth-first, four-connected)
   and handed to the engine one STRAIGHT LEG at a time. A straight leg is the only route
   the engine can take between two cells in one row or column (any other is longer), so a
   figure walking legs never cuts through a blocker the engine cannot see.
4. **Moving between zones** - stepping onto an exit cell, or a mission call, moves the
   console's body to another host and points the console at it.

Stdlib only; no threading. The walk is driven by one tick task (`boarding_world_watch`).
"""
from collections import deque

from ..agent import Agent
from .inventory import get_inventory_value, set_inventory_value
from .query import to_id, to_object
from .roles import add_role, has_role, role

#: The role a zone's host wears, and the inventory key naming its zone.
ZONE_ROLE = "boarding_zone"
ZONE_KEY = "BOARDING_ZONE"

#: Legend roles with meaning to the world. `blocker` cells cannot be walked;
#: `exit` cells move whoever stops on one to another zone.
BLOCKER_ROLE = "blocker"
EXIT_ROLE = "exit"

_ZONES_KEY = "__BOARDING_ZONES__"        # {zone key: record}
_BLOCKED_KEY = "__BOARDING_BLOCKED__"    # {host id: set((x, y))}
_EXITS_KEY = "__BOARDING_EXITS__"        # {host id: {(x, y): room name}}
_WATCH_KEY = "__BOARDING_WORLD_TASK__"

# On the CLIENT, like everything a console drives.
KEY_LEGS = "BOARDING_LEGS"               # [(x, y), ...] corners still to walk
KEY_SPEED = "BOARDING_LEG_SPEED"
KEY_LAST_GOOD = "BOARDING_LAST_GOOD"     # last cell the figure stood on that was open
KEY_INTENT = "BOARDING_INTENT"           # what to do on arrival (see boarding_on_arrive)

# Where hidden hosts are parked: far below the play plane, spaced apart, so they are never
# something the bridge flies near. An engine-verification item: hidden hosts must not
# show on radar or be targetable.
HIDDEN_ORIGIN = (0.0, -200000.0, 0.0)
HIDDEN_SPACING = 20000.0


# --- zones --------------------------------------------------------------------------

def _zones():
    return Agent.SHARED.get_inventory_value(_ZONES_KEY, None) or {}


def _set_zones(table):
    Agent.SHARED.set_inventory_value(_ZONES_KEY, table)


def _cells_table(key):
    return Agent.SHARED.get_inventory_value(key, None) or {}


def _norm(key):
    return str(key or "").strip().lower()


def _xy(value):
    """`(x, y)` from `"20, 39"`, `"20 39"`, a list or a tuple. None when unreadable."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        parts = str(value).replace(",", " ").split()
    try:
        return int(float(parts[0])), int(float(parts[1]))
    except (IndexError, TypeError, ValueError):
        return None


def _exit_spec(value):
    """An `Exits:` target: `"colony"` or `"colony 20,39"` -> (zone, (x, y) | None)."""
    text = str(value or "").strip()
    if not text:
        return None, None
    zone, _, rest = text.partition(" ")
    return _norm(zone), _xy(rest) if rest.strip() else None


def boarding_zone_build(key, grid_text=None, host=None, title=None, entry=None,
                        exits=None, beam=True, known=True, hidden=True, pos=None):
    """Make one area of the world. Returns its host object, or None.

    Args:
        key (str): the zone's name - what exits and missions call it.
        grid_text (str, optional): an ASCII floor plan (see ``grid_ascii``). Its `ship:`
            is the hull the host is spawned as and its `layout:` is merged and built.
        host (optional): an object that already exists - a ship the party can board -
            instead of spawning a hidden one.
        title (str, optional): what the area is called on screen.
        entry (optional): the cell a party arrives on, `(x, y)` or `"x, y"`. Defaults
            to the floor plan's `access` room, then the middle of the floor.
        exits (dict, optional): `{room name: "zone [x,y]"}`. A room named `to_<zone>`
            needs no entry here - the name says where it goes.
        beam (bool): whether the transporter can put people here.
        known (bool): whether the party knows the zone exists yet.
        hidden (bool): for a spawned host, whether to draw it as nothing.
        pos (optional): where to park a spawned host.
    """
    from .boarding_site import boarding_site_build
    from .grid import grid_merge_ascii
    key = _norm(key)
    layout = None
    ship_key = "starbase_civil"
    if grid_text:
        from .grid_ascii import grid_ascii_parse, GridAsciiError
        try:
            parsed = grid_ascii_parse(grid_text)
        except GridAsciiError as e:
            from .execution import log
            log(f"zone '{key}': floor plan not readable: {e}", "boarding", "warning")
            return None
        ship_key = parsed["ship"]
        layout = parsed["layout"] if parsed["layout"] != "default" else None
        grid_merge_ascii(grid_text)
    so = to_object(host) if host is not None else None
    if so is None:
        so = _spawn_hidden_host(key, title, ship_key, pos, hidden)
    if so is None:
        return None
    set_inventory_value(so.id, ZONE_KEY, key)
    add_role(so, ZONE_ROLE)
    boarding_site_build(so, layout)
    zones = dict(_zones())
    zones[key] = {
        "key": key,
        "host": so.id,
        "title": title or so.name or key,
        "entry": _xy(entry),
        "exits": {_norm(k): v for k, v in (exits or {}).items()},
        "beam": bool(beam),
        "known": bool(known),
    }
    _set_zones(zones)
    _scan_world_cells(so.id)
    return so


def _spawn_hidden_host(key, title, ship_key, pos, hidden):
    from .spawn import npc_spawn
    if pos is None:
        n = len(_zones())
        ox, oy, oz = HIDDEN_ORIGIN
        pos = (ox + n * HIDDEN_SPACING, oy, oz)
    x, y, z = (list(pos) + [0, 0, 0])[:3]
    # HIDDEN BY DISTANCE, NOT BY ART. The interior is cut from the hull's art (the
    # engine reads the silhouette's alpha; the mock looks the hull up by the art key),
    # so swapping the art for "invisible" would take the floor away with it. A host
    # parked far below the play plane is never near anything the bridge does.
    so = to_object(npc_spawn(x, y, z, title or key, "#," + ZONE_ROLE, ship_key,
                             "behav_station"))
    return so


def _scan_world_cells(host_id):
    """Read the blocker and exit cells a floor plan drew onto this host."""
    from .grid import grid_objects, grid_pos_data
    from .boarding_site import boarding_room_name
    blocked = set()
    exits = {}
    for node in grid_objects(host_id):
        if has_role(node, BLOCKER_ROLE):
            at = grid_pos_data(node)
            if at and at[0] is not None:
                blocked.add((int(at[0]), int(at[1])))
        elif has_role(node, EXIT_ROLE):
            at = grid_pos_data(node)
            so = to_object(node)
            if at and at[0] is not None and so is not None:
                exits[(int(at[0]), int(at[1]))] = _norm(boarding_room_name(so.name))
    table = dict(_cells_table(_BLOCKED_KEY))
    table[host_id] = blocked | set(table.get(host_id, set()))
    Agent.SHARED.set_inventory_value(_BLOCKED_KEY, table)
    etable = dict(_cells_table(_EXITS_KEY))
    etable[host_id] = exits
    Agent.SHARED.set_inventory_value(_EXITS_KEY, etable)


def boarding_zones_build(section, load=None):
    """Build every zone an AMD section declares. Returns ``{zone key: host}``.

    One heading per zone; the heading key is the zone key and its text the title::

        # [Landing Ridge](ridge)
        ---
        Grid: surface/ridge.grid
        Entry: 20, 36
        Exits: to_colony -> colony 20,2
        Beam: yes
        Known: yes
        ---

    Args:
        section: the AMD section node (from ``document_get_amd_file``).
        load (callable, optional): reads a floor plan file. Defaults to
            ``media_read_relative_file``.
    """
    if load is None:
        from .media import media_read_relative_file as load
    out = {}
    for rec in boarding_zone_records(section):
        text = load(rec["grid"]) if rec.get("grid") else None
        host = None
        if rec.get("host"):
            host = _find_host(rec["host"])
        so = boarding_zone_build(rec["key"], text, host=host, title=rec.get("title"),
                                 entry=rec.get("entry"), exits=rec.get("exits"),
                                 beam=rec.get("beam", True), known=rec.get("known", True))
        if so is not None:
            out[rec["key"]] = so
    return out


def _find_host(name):
    """A `Host:` - an object id, or the name of a space object that exists already."""
    try:
        return to_object(int(name))
    except (TypeError, ValueError):
        pass
    from .query import to_object_list
    from .roles import role as _role
    for so in to_object_list(_role("__npc__") | _role("__player__")):
        if _norm(so.name) == _norm(name):
            return so
    return None


def _yes(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("yes", "true", "1", "on")


def boarding_zone_records(section):
    """Zone records from an AMD section - plain dicts, for tests and tools."""
    out = []
    if section is None:
        return out
    for n in section.get("children", []) or []:
        data = n.get("data") or {}
        raw = data.get("exits")
        # `Exits: to_colony -> colony 20,2, to_flats -> flats` - split on the arrows,
        # since a coordinate carries its own comma. The default coercion may already
        # have split the line on its commas, so join it back first.
        text = ", ".join(str(i) for i in raw) if isinstance(raw, (list, tuple)) \
            else str(raw or "")
        exits = dict(_arrow_pairs(text)) if "->" in text else {}
        out.append({
            "key": _norm(n.get("key")),
            "title": n.get("display_text") or n.get("key"),
            "grid": str(data.get("grid") or "").strip() or None,
            "host": str(data.get("host") or "").strip() or None,
            "entry": data.get("entry"),
            "exits": exits,
            "beam": _yes(data.get("beam"), True),
            "known": _yes(data.get("known"), True),
            "desc": (n.get("description") or "").strip(),
        })
    return out


def _arrow_pairs(text):
    """`a -> zone 1,2, b -> other` -> [("a", "zone 1,2"), ("b", "other")]."""
    chunks = [c.strip() for c in text.split("->")]
    pairs = []
    name = chunks[0]
    for i in range(1, len(chunks)):
        body = chunks[i]
        if i < len(chunks) - 1:
            # The last comma-separated word is the next exit's name.
            head, _, nxt = body.rpartition(",")
            pairs.append((_norm(name), head.strip()))
            name = nxt.strip()
        else:
            pairs.append((_norm(name), body.strip()))
    return pairs


def boarding_zone_host(key):
    """The host object id of a zone, or None."""
    rec = _zones().get(_norm(key))
    return rec.get("host") if rec else None


def boarding_zone_of(target):
    """The zone key of a host - or of the host a CONSOLE is standing on. None if neither."""
    from .boarding_site import boarding_my_host
    tid = to_id(target)
    key = get_inventory_value(tid, ZONE_KEY, None) if tid is not None else None
    if key:
        return key
    host = boarding_my_host(tid)
    if host:
        return get_inventory_value(host, ZONE_KEY, None)
    return None


def boarding_zone_title(key):
    rec = _zones().get(_norm(key))
    return rec.get("title") if rec else None


def boarding_zones(known_only=False, beam_only=False):
    """Zone keys, in the order they were built."""
    out = []
    for k, rec in _zones().items():
        if known_only and not rec.get("known"):
            continue
        if beam_only and not rec.get("beam"):
            continue
        out.append(k)
    return out


def boarding_zone_reveal(key, beam=None):
    """The party now knows this zone exists (a scan found it). Optionally set `beam`."""
    zones = dict(_zones())
    rec = zones.get(_norm(key))
    if rec is None:
        return False
    rec = dict(rec)
    rec["known"] = True
    if beam is not None:
        rec["beam"] = bool(beam)
    zones[_norm(key)] = rec
    _set_zones(zones)
    from .signal import signal_emit
    signal_emit("boarding_zone_revealed", {"BOARDING_ZONE": _norm(key),
                                           "BOARDING_HOST": rec.get("host")})
    return True


def boarding_zone_known(key):
    rec = _zones().get(_norm(key))
    return bool(rec and rec.get("known"))


def boarding_zone_entry(key):
    """Where a party arrives in a zone: its `Entry:`, else the floor plan's airlock."""
    from .boarding_site import boarding_entry_cell
    rec = _zones().get(_norm(key))
    if rec is None:
        return None
    if rec.get("entry"):
        return tuple(rec["entry"])
    return boarding_entry_cell(rec["host"])


# --- blocking -----------------------------------------------------------------------

def boarding_blocked_cells(host):
    """Every cell of this host the library will not route through, as a set."""
    return set(_cells_table(_BLOCKED_KEY).get(to_id(host), set()))


def boarding_block(host, cells):
    """Close cells: a door shut, a rockfall, a hostile standing guard."""
    hid = to_id(host)
    table = dict(_cells_table(_BLOCKED_KEY))
    table[hid] = set(table.get(hid, set())) | {tuple(c) for c in cells}
    Agent.SHARED.set_inventory_value(_BLOCKED_KEY, table)


def boarding_unblock(host, cells):
    """Open cells again: a door opened, a rock cut away."""
    hid = to_id(host)
    table = dict(_cells_table(_BLOCKED_KEY))
    table[hid] = set(table.get(hid, set())) - {tuple(c) for c in cells}
    Agent.SHARED.set_inventory_value(_BLOCKED_KEY, table)


def boarding_is_blocked(host, x, y):
    return (int(x), int(y)) in boarding_blocked_cells(host)


def boarding_exit_at(host, x, y):
    """The exit room name at a cell of this host, or None."""
    return (_cells_table(_EXITS_KEY).get(to_id(host)) or {}).get((int(x), int(y)))


def boarding_exit_cells(host):
    """``{(x, y): room name}`` for this host's exits."""
    return dict(_cells_table(_EXITS_KEY).get(to_id(host)) or {})


def _open(hm, blocked, x, y):
    if not (0 <= x < hm.w and 0 <= y < hm.h):
        return False
    if (x, y) in blocked:
        return False
    return bool(hm.is_grid_point_open(x, y))


def _hull_map(host):
    from ..helpers import FrameContext
    try:
        hm = FrameContext.context.sbs.get_hull_map(to_id(host))
    except Exception:                                    # noqa: BLE001
        return None
    if hm is None or not getattr(hm, "w", 0) or not getattr(hm, "h", 0):
        return None
    return hm


def boarding_path(host, start, goal):
    """The cells from ``start`` to ``goal``, four-connected, around every blocker.

    Returns:
        list: the cells to walk AFTER ``start``, ending at the goal - or, when the goal
        cannot be reached (a blocker, a closed door), ending at the reachable cell
        nearest it. Empty when already there or nothing is reachable. None when the
        host has no floor.
    """
    hm = _hull_map(host)
    if hm is None:
        return None
    blocked = boarding_blocked_cells(host)
    start = (int(start[0]), int(start[1]))
    goal = (int(goal[0]), int(goal[1]))
    prev = {start: None}
    q = deque([start])
    best, best_d = start, abs(start[0] - goal[0]) + abs(start[1] - goal[1])
    while q:
        cur = q.popleft()
        if cur == goal:
            best = cur
            break
        d = abs(cur[0] - goal[0]) + abs(cur[1] - goal[1])
        if d < best_d:
            best, best_d = cur, d
        x, y = cur
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nxt in prev or not _open(hm, blocked, nxt[0], nxt[1]):
                continue
            prev[nxt] = cur
            q.append(nxt)
    path = []
    cur = best
    while cur is not None and cur != start:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def boarding_legs(path, start):
    """A path as the corners where it turns, plus its end - the legs to issue one by one."""
    if not path:
        return []
    legs = []
    prev = tuple(start)
    for i, cell in enumerate(path):
        nxt = path[i + 1] if i + 1 < len(path) else None
        if nxt is None:
            legs.append(tuple(cell))
            break
        d_in = (cell[0] - prev[0], cell[1] - prev[1])
        d_out = (nxt[0] - cell[0], nxt[1] - cell[1])
        if d_in != d_out:
            legs.append(tuple(cell))
        prev = cell
    return legs


# --- walking ------------------------------------------------------------------------

def boarding_world_walk(client_id, x, y, speed=None):
    """Walk this console's figure to a cell, around blockers. False when not boarded.

    Emits ``boarding_blocked`` when the cell cannot be reached, after sending the figure
    as close as it can get - so the device can say "the way is blocked" rather than
    looking broken.
    """
    from .boarding_site import (boarding_my_figure, boarding_my_host, boarding_where,
                                WALK_SPEED)
    from .grid import grid_object_valid
    fig = boarding_my_figure(client_id)
    host = boarding_my_host(client_id)
    if not fig or not host or not grid_object_valid(fig):
        return False
    here = boarding_where(client_id)
    if here is None:
        return False
    path = boarding_path(host, here, (x, y))
    if path is None:
        return False
    set_inventory_value(client_id, KEY_SPEED, speed or WALK_SPEED)
    legs = boarding_legs(path, here)
    set_inventory_value(client_id, KEY_LEGS, legs)
    if not path or tuple(path[-1]) != (int(x), int(y)):
        from .signal import signal_emit
        signal_emit("boarding_blocked", {"BOARDING_CLIENT": client_id,
                                         "BOARDING_HOST": host,
                                         "BOARDING_X": int(x), "BOARDING_Y": int(y)})
    _issue_next_leg(client_id, fig)
    boarding_world_watch()
    return True


def _issue_next_leg(client_id, fig):
    from .grid import grid_target_pos
    legs = list(get_inventory_value(client_id, KEY_LEGS, None) or [])
    if not legs:
        return False
    x, y = legs[0]
    grid_target_pos(fig, x, y, get_inventory_value(client_id, KEY_SPEED, None))
    return True


def boarding_walking(client_id):
    """Whether this console's figure still has legs to walk."""
    return bool(get_inventory_value(client_id, KEY_LEGS, None))


def boarding_stop(client_id):
    """Forget any walk in progress. The figure stops at the end of its current leg."""
    set_inventory_value(client_id, KEY_LEGS, None)
    set_inventory_value(client_id, KEY_INTENT, None)


def boarding_on_arrive(client_id, intent):
    """Remember what this console meant by walking - run when the walk finishes.

    ``intent`` is a callable ``fn(client_id)``. Replaced by the next call, and dropped
    when a new walk starts elsewhere (`boarding_stop`).
    """
    set_inventory_value(client_id, KEY_INTENT, intent)


def boarding_world_watch(seconds=0.1):
    """Start the tick that drives walks, keeps figures off blocked cells and follows
    exits. Idempotent. Returns the tick task."""
    from ..tickdispatcher import TickDispatcher
    task = Agent.SHARED.get_inventory_value(_WATCH_KEY, None)
    if task is not None:
        return task
    task = TickDispatcher.do_interval(boarding_world_tick, seconds)
    Agent.SHARED.set_inventory_value(_WATCH_KEY, task)
    return task


def boarding_world_unwatch():
    task = Agent.SHARED.get_inventory_value(_WATCH_KEY, None)
    if task is not None:
        try:
            task.stop()
        except Exception:                                # noqa: BLE001
            pass
    Agent.SHARED.set_inventory_value(_WATCH_KEY, None)


def _drivers():
    from .boarding_site import _DRIVERS_KEY
    return set(Agent.SHARED.get_inventory_value(_DRIVERS_KEY, set()) or set())


def boarding_world_tick(t=None):
    """One pass over every console that is driving a figure."""
    from .boarding_site import boarding_my_figure, boarding_my_host, boarding_where
    from .grid import grid_object_valid, grid_target_pos
    for cid in sorted(_drivers()):
        fig = boarding_my_figure(cid)
        host = boarding_my_host(cid)
        if not fig or not host or not grid_object_valid(fig):
            continue
        at = boarding_where(cid)
        if at is None:
            continue
        # THE SAFETY NET. The engine cannot see a blocker, so a figure should never be
        # on one - but a door can close ON somebody, and a leg the engine took some other
        # way would put them there. Send them back to where they last stood clear.
        if boarding_is_blocked(host, *at):
            good = get_inventory_value(cid, KEY_LAST_GOOD, None)
            set_inventory_value(cid, KEY_LEGS, None)
            if good:
                grid_target_pos(fig, good[0], good[1],
                                get_inventory_value(cid, KEY_SPEED, None))
            continue
        set_inventory_value(cid, KEY_LAST_GOOD, at)
        legs = list(get_inventory_value(cid, KEY_LEGS, None) or [])
        if legs:
            if tuple(legs[0]) == tuple(at):
                legs.pop(0)
                set_inventory_value(cid, KEY_LEGS, legs or None)
                if legs:
                    _issue_next_leg(cid, fig)
                    continue
            else:
                continue                     # still walking this leg
        # STANDING STILL. Arrived somewhere - an exit, or somewhere a click meant.
        exit_room = boarding_exit_at(host, *at)
        if exit_room:
            boarding_exit_follow(cid, exit_room)
            continue
        intent = get_inventory_value(cid, KEY_INTENT, None)
        if intent is not None:
            set_inventory_value(cid, KEY_INTENT, None)
            try:
                intent(cid)
            except Exception as e:                       # noqa: BLE001
                from .execution import log
                log(f"arrival intent failed: {e}", "boarding", "warning")


# --- between zones ------------------------------------------------------------------

def boarding_exit_target(host, room_name):
    """Where an exit room leads: ``(zone key, (x, y) | None)``, or (None, None).

    The zone's `Exits:` table first; failing that a room called `to_<zone>` goes there.
    """
    key = get_inventory_value(to_id(host), ZONE_KEY, None)
    rec = _zones().get(key) if key else None
    name = _norm(room_name)
    if rec is not None and name in (rec.get("exits") or {}):
        return _exit_spec(rec["exits"][name])
    if name.startswith("to_"):
        zone = name[3:]
        if zone in _zones():
            return zone, None
    return None, None


def _arrival_cell(zone, came_from):
    """Where somebody walking in from `came_from` stands: beside the way back, never ON
    it - arriving on an exit would send them straight back out."""
    host = boarding_zone_host(zone)
    back = None
    for cell, name in boarding_exit_cells(host).items():
        target, _ = boarding_exit_target(host, name)
        if target == came_from:
            back = cell
            break
    if back is None:
        return boarding_zone_entry(zone)
    hm = _hull_map(host)
    if hm is None:
        return back
    blocked = boarding_blocked_cells(host)
    exits = boarding_exit_cells(host)
    seen = {back}
    q = deque([back])
    while q:
        x, y = q.popleft()
        for nxt in ((x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)):
            if nxt in seen:
                continue
            seen.add(nxt)
            if not (0 <= nxt[0] < hm.w and 0 <= nxt[1] < hm.h):
                continue
            if _open(hm, blocked, *nxt) and nxt not in exits:
                return nxt
            if _open(hm, blocked, *nxt):
                q.append(nxt)
    return boarding_zone_entry(zone)


def boarding_exit_follow(client_id, room_name):
    """Take this console through an exit room. True when it moved."""
    from .boarding_site import boarding_my_host
    host = boarding_my_host(client_id)
    if not host:
        return False
    zone, cell = boarding_exit_target(host, room_name)
    if zone is None:
        return False
    from_zone = get_inventory_value(host, ZONE_KEY, None)
    if cell is None:
        cell = _arrival_cell(zone, from_zone)
    return boarding_site_move(client_id, zone, *(cell or (None, None))) is not None


def boarding_site_move(client_id, target, x=None, y=None):
    """Move this console's body to another area and point the console at it.

    Args:
        client_id: the console moving.
        target: a zone key, or a host object.
        x, y (optional): where to stand. Defaults to the zone's entry.

    Returns:
        The new figure, or None when the console is not boarded or the target is unknown.
    """
    from .boarding import boarding_held, boarding_channel_leave, boarding_channel_of, PARTY
    from .boarding_site import boarding_my_host, boarding_my_figure
    from .gui.boarding_gui import boarding_go_down
    from .signal import signal_emit
    if not boarding_held(client_id):
        return None
    host = boarding_zone_host(target) if isinstance(target, str) else to_id(target)
    if host is None or to_object(host) is None:
        return None
    if x is None or y is None:
        zone = get_inventory_value(host, ZONE_KEY, None)
        at = boarding_zone_entry(zone) if zone else None
    else:
        at = (int(x), int(y))
    from_host = boarding_my_host(client_id)
    boarding_stop(client_id)
    # A side conversation happens SOMEWHERE. Leaving the area leaves it.
    if boarding_channel_of(client_id) != PARTY:
        boarding_channel_leave(client_id)
    boarding_go_down(client_id, host, at=at)
    signal_emit("boarding_moved", {
        "BOARDING_CLIENT": client_id,
        "BOARDING_FROM": from_host,
        "BOARDING_HOST": host,
        "BOARDING_ZONE": get_inventory_value(host, ZONE_KEY, None),
        "BOARDING_FROM_ZONE": get_inventory_value(from_host, ZONE_KEY, None)
                              if from_host else None,
    })
    return boarding_my_figure(client_id)


def boarding_zone_clients(key):
    """The consoles standing in a zone right now."""
    from .boarding_site import boarding_my_host
    host = boarding_zone_host(key)
    return {c for c in _drivers() if host is not None and boarding_my_host(c) == host}


# --- reset --------------------------------------------------------------------------

def boarding_world_clear():
    """The per-mission reset: no zones, no blockers, no walks."""
    boarding_world_unwatch()
    for cid in _drivers():
        set_inventory_value(cid, KEY_LEGS, None)
        set_inventory_value(cid, KEY_INTENT, None)
        set_inventory_value(cid, KEY_LAST_GOOD, None)
    _set_zones({})
    Agent.SHARED.set_inventory_value(_BLOCKED_KEY, {})
    Agent.SHARED.set_inventory_value(_EXITS_KEY, {})


def boarding_zone_count():
    """Reset-ledger probe: zones still declared."""
    return len(_zones())


def boarding_zone_role():
    """The role a zone host wears - `"boarding_zone"`."""
    return ZONE_ROLE


def boarding_world_routes(host):
    """Whether walks on this host go through the library's router (a zone, or a host
    with blockers) rather than straight to the engine."""
    hid = to_id(host)
    return bool(hid) and (has_role(hid, ZONE_ROLE) or bool(boarding_blocked_cells(hid)))
