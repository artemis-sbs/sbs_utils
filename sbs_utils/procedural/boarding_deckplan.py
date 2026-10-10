"""Boarding maps drawn from a ship's interior plan.

Engineering draws a hull's interior as a coarse node map: one plan cell per room node
(`crew-quarters`, `impulse`, `beam-port-fwd`) with open hallway between. A boarding party
walks a TILE map (``tilemap.py``), and this module draws one from the plan, so any ship
with an interior can be boarded without anyone drawing it:

- every plan cell becomes SCALE x SCALE tiles;
- a room gets the deck and the furniture of its kind (``boarding_deck_kit``): a galley
  has tables and stools, a cargo hold crates, and a system room one piece of kit per
  node - a reactor per warp node, a turret per beam node;
- a bulkhead runs wherever one room meets another, and every room gets a doorway, so the
  whole deck is one walk;
- a room's tiles carry a mark named after it (``room:impulse``), so a scene, a damage
  report or a quest can find it. The first open cell of the airlock, or else the middle
  of the hallway, is the ``entry``.

The furniture is SCENERY (``boarding_prop_is_scenery``): it blocks, and nothing offers it.
Looks are the shared Cosmos-Tiles vocabulary - the `station` pack draws them; without a
pack the map has walls and floors but no picture on them. The layout is deterministic: the
same plan always gives the same map.

    plan = boarding_deck_plan_ascii(media_read_relative_file("tsn_light_cruiser.grid"))
    boarding_deck_tileset()
    tilemap_art_use("station", tileset="deck")
    area = boarding_deck_build(plan, "artemis_deck", title="Artemis")

``boarding_deck_text`` gives the same map as a `.tiles` file, for an author who would
rather start from the generated deck than from nothing.

BOARDING A SHIP is one call, ``boarding_deck_visit(ship, target, scenes)``: the target's
deck is built under the area key ``deck``, the things a writer put aboard are stood in
rooms of the right kind, the ship's own crew is the crowd, and a party is opened onto
it. A writer says where a thing goes without knowing the hull::

    ### [Strongbox](strongbox)
    ---
    Area: deck             # whatever ship we board
    Mark: brig             # a KIND of room: brig, cargo, quarters, bridge... or
                           # `entry` / `hallway`
    ---

A hull with no such room stands it in the hallway and says so, once. One deck at a
time: the next ship boarded is built in its place.
"""
from collections import deque

from .tilemap_art import tilemap_sprite_cells

#: Tiles per plan cell. 3 leaves a 2 x 2 floor in a one-cell room once its bulkheads
#: are up - room for one piece of kit and a way past it.
SCALE = 3

HULL = "hull_metal"
WALL = "wall_metal"
DOOR = "floor_hatch"
HALL = "floor_corridor"

#: What a kind of room looks like: its deck, the furniture set along its walls, and the
#: piece of kit that stands on each of its nodes (systems only). A furniture entry is a
#: sprite key, or (key, floor tiles the room needs before it gets one). Looked up by the
#: room's roles, most specific first (``grid_room_roles``), then by words in its name.
_KITS = {
    "beam": {"floor": "floor_grate", "system": "prop:beam_emitter"},
    "torpedo": {"floor": "floor_hazard", "system": "prop:torpedo",
                "furniture": ["prop:crate_ammo"]},
    "impulse": {"floor": "floor_grate", "system": "prop:power_cell"},
    "maneuver": {"floor": "floor_grate", "system": "prop:machinery"},
    "warp": {"floor": "floor_lit", "system": "prop:reactor"},
    "jump": {"floor": "floor_lit", "system": "prop:reactor"},
    "hyper": {"floor": "floor_lit", "system": "prop:reactor"},
    "shield": {"floor": "floor_lit", "system": "prop:shield_globe"},
    "sensor": {"floor": "floor_panel", "system": "prop:sensor_array"},
    "computer": {"floor": "floor_panel",
                 "furniture": ["prop:console_bank", "prop:security_desk", "prop:terminal"]},
    "quarters": {"floor": "floor_tiles",
                 "furniture": ["prop:bunk", "prop:desk", "prop:plant", "prop:bunk"]},
    "mess": {"floor": "floor_tiles",
             "furniture": ["prop:table", "prop:stool", "prop:vending", "prop:stool",
                           "prop:table"]},
    "galley": {"floor": "floor_tiles",
               "furniture": ["prop:sink", "prop:table_square", "prop:vending", "prop:stool"]},
    "sickbay": {"floor": "floor_plain",
                "furniture": ["prop:bed", "prop:med_scanner", "prop:med_machine",
                              "prop:med_cart", "prop:cryo_bed"]},
    "lab": {"floor": "floor_plain",
            "furniture": ["prop:desk", "prop:test_tubes", "prop:med_machine", "prop:shelf"]},
    "workshop": {"floor": "floor_grate",
                 "furniture": ["prop:storage_shelf", "prop:machinery", "prop:toolbox",
                               "prop:generator"]},
    "production": {"floor": "floor_grate",
                   "furniture": ["prop:generator", "prop:machinery", "prop:storage_shelf"]},
    "cargo": {"floor": "floor_hazard",
              "furniture": ["prop:crate", "prop:crate_wide", "prop:barrel", "prop:crate_ammo",
                            "prop:crate_shield", "prop:cart_loaded"]},
    "bay": {"floor": "floor_hazard",
            "furniture": [("prop:shuttle", 14), "prop:cart", "prop:crate", "prop:barrel"]},
    "brig": {"floor": "floor_plain",
             "furniture": ["prop:brig_cell", "prop:brig_cell", "prop:toilet"]},
    "recreation": {"floor": "floor_tiles",
                   "furniture": ["prop:vr_booth", "prop:couch", "prop:bench", "prop:plant"]},
    "lounge": {"floor": "floor_tiles",
               "furniture": ["prop:couch", "prop:bar_chair", "prop:plant", "prop:table"]},
    "conference": {"floor": "floor_panel",
                   "furniture": ["prop:table_square", "prop:bridge_chair",
                                 "prop:bridge_chair"]},
    "bridge": {"floor": "floor_panel",
               "furniture": ["prop:console_bank", "prop:captain_chair", "prop:console_station",
                             "prop:bridge_chair"]},
    "airlock": {"floor": "floor_metal", "furniture": ["prop:oxygen_tank"]},
    "room": {"floor": "floor_metal", "furniture": ["prop:crate"]},
}

#: Role and name words that mean one of the kits above.
_ALIASES = {
    "gym": "recreation", "rec": "recreation", "saloon": "lounge", "school": "lounge",
    "shrine": "lounge", "vip": "quarters", "passenger": "quarters", "priest": "quarters",
    "cabin": "quarters", "med": "sickbay", "surgery": "sickbay", "shuttle": "bay",
    "fighter": "bay", "boat": "bay", "hatch": "airlock", "plunder": "cargo",
    "astro": "lab", "bio": "lab", "physics": "lab", "science": "lab", "tube": "torpedo",
    "torp": "torpedo", "gun": "beam", "weapon": "beam", "engine": "impulse",
    "berths": "quarters", "grog": "cargo", "ready": "conference",
}

#: The door that stands in a doorway, shut and open, by how the wall runs. Doors are
#: scenery that never blocks: they slide open for anyone next to them
#: (``boarding_deck_animate``). A mission may change these.
DOOR_SPRITES = {"front": ("prop:door_station", "prop:doorframe"),
                "side": ("prop:door_side", "prop:door_side_open")}

#: Legend characters for the looks the kits use; any other look gets a free character.
_CHARS = {HULL: "H", WALL: "#", DOOR: "+", HALL: ",", "floor_grate": "=",
          "floor_panel": "_", "floor_lit": "~", "floor_tiles": "t", "floor_hazard": "z",
          "floor_plain": ".", "floor_metal": "-"}

#: The area key a writer's `Area: deck` means: the deck of whatever ship is boarded.
DECK_AREA = "deck"
#: The art set that draws a generated deck.
DECK_ART = "station"
#: The role a ship wears while a party is aboard it.
TARGET_ROLE = "boarding_target"

_OVERRIDES = {}      # kit name -> fields a mission changed
_DECKS = {}          # area key -> what was built (see boarding_deck_build)
_BOARDED = {}        # the visit aboard a ship: {"area", "target", "ship", "task"} or empty
_SAID = set()        # things already said this mission


def _deck_say(message, once=None):
    """Tell the author - in the engine's debug.log and on the console - without failing
    a headless run: a hull with no brig is not a mistake in anybody's files."""
    if once is not None:
        if once in _SAID:
            return
        _SAID.add(once)
    try:
        from .execution import log
        log(message, "boarding", "warning")
    except Exception:                                    # noqa: BLE001
        pass
    try:
        from ..mast.mast import DEBUG
        DEBUG("[boarding_deck] " + message)
    except Exception:                                    # noqa: BLE001
        pass
    print("boarding_deck: " + message)


# --- plans ----------------------------------------------------------------------------

def boarding_deck_plan_ascii(text, ship_key=None):
    """A plan from an ASCII interior (`.grid`): ``{"ship", "w", "h", "cells"}`` where
    ``cells`` maps each open ``(x, y)`` to its room name, ``""`` for hallway."""
    from .grid_ascii import grid_ascii_parse
    rec = grid_ascii_parse(text, ship_key)
    cells = {(int(o["x"]), int(o["y"])): o["name"] for o in rec["entry"]["grid_objects"]}
    for c in rec.get("hallways", []):
        cells.setdefault(tuple(c), "")
    return {"ship": rec["ship"], "w": rec["w"], "h": rec["h"], "cells": cells}


def boarding_deck_plan(ship, layout=None):
    """A plan for a ship: its interior layout (grid data), with the open cells of its
    hull map as hallway. ``ship`` is a live ship, or a shipData key - which has no hull
    map. None when the hull has no interior.

    WHERE THE HALLWAYS COME FROM is ``plan["source"]``, because only the engine can say
    whether a ship nobody flies has a hull map at all:

    - ``hull map``: the engine's own open cells for this ship;
    - ``grid text``: no hull map, so the hallways its `.grid` file drew
      (``grid_get_open_cells``);
    - ``rooms only``: neither - the rooms, joined by gangways.

    The rooms are the hull's interior when it has one, else a plan kept for reading
    (``grid_plan_ascii`` - how a hull nobody flies has a deck and no interior).
    """
    from .grid import grid_get_plan_layout
    from .query import to_id, to_object
    hm = None
    key = ship
    if not isinstance(ship, str):
        so = to_object(to_id(ship))
        if so is None:
            return None
        if layout is None:
            from .inventory import get_inventory_value
            layout = get_inventory_value(so.id, "grid_layout", None)
        key = so.art_id
        try:
            from ..helpers import FrameContext
            hm = FrameContext.context.sbs.get_hull_map(so.id)
        except Exception:                                    # noqa: BLE001
            hm = None
    items = grid_get_plan_layout(key, layout)
    if not items:
        return None
    cells = {}
    for o in items:
        if isinstance(o, dict) and o.get("name") and "x" in o and "y" in o:
            cells[(int(o["x"]), int(o["y"]))] = str(o["name"])
    w = max((x for x, _ in cells), default=0) + 1
    h = max((y for _, y in cells), default=0) + 1
    source = "rooms only"
    opened = set()
    try:
        if hm is not None and getattr(hm, "w", 0) and getattr(hm, "h", 0):
            opened = {(x, y) for x in range(hm.w) for y in range(hm.h)
                      if hm.is_grid_point_open(x, y)}
    except Exception:                                        # noqa: BLE001
        opened = set()
    if opened:
        # A hull map that calls nothing open is no hull map.
        source = "hull map"
        w, h = max(w, hm.w), max(h, hm.h)
    else:
        from .grid import grid_get_plan_open_cells
        text = grid_get_plan_open_cells(key, layout)
        if text is not None:
            source = "grid text"
            w, h = max(w, int(text.get("w") or 0)), max(h, int(text.get("h") or 0))
            opened = {(int(c[0]), int(c[1])) for c in text.get("hallways") or ()}
    for c in opened:
        cells.setdefault(c, "")
    return {"ship": key, "w": w, "h": h, "cells": cells, "source": source}


# --- kits -----------------------------------------------------------------------------

def boarding_deck_kit(kind, floor=None, furniture=None, system=None):
    """Change what one kind of room looks like, for this mission. ``kind`` is a kit name
    (``cargo``, ``warp``, ``quarters``...) or a new one, which rooms whose roles or name
    contain that word will then use. Returns the kit as it now stands."""
    kind = str(kind).strip().lower()
    over = _OVERRIDES.setdefault(kind, {})
    if floor is not None:
        over["floor"] = floor
    if furniture is not None:
        over["furniture"] = list(furniture)
    if system is not None:
        over["system"] = system
    return boarding_deck_kit_for(kind)


def boarding_deck_kit_for(kind):
    """The kit of one kind of room, with this mission's changes."""
    kind = str(kind).strip().lower()
    return dict(_KITS.get(kind, {}), **_OVERRIDES.get(kind, {}))


def _words(text):
    import re
    return [w for w in re.split(r"[^a-z]+", str(text or "").lower()) if w]


def boarding_deck_room_kind(name):
    """Which kit a room of this name uses: its roles, most specific first, then the
    words of its name. ``hallway`` for a hallway, ``room`` when nothing matches."""
    if not name:
        return "hallway"
    from .grid_rooms import grid_room_roles
    kits = set(_KITS) | set(_OVERRIDES)
    words = list(reversed(_words(grid_room_roles(name.lower()) or ""))) + _words(name)
    for w in words:
        w = _ALIASES.get(w, w)
        if w in kits and w != "room":
            return w
    return "room"


# --- layout ---------------------------------------------------------------------------

def _regions(cells):
    """{cell: region id} - same-named cells joined four-ways - and each region's name."""
    region, names = {}, []
    for c in sorted(cells, key=lambda c: (c[1], c[0])):
        if c in region:
            continue
        rid = len(names)
        names.append(cells[c])
        region[c] = rid
        q = deque([c])
        while q:
            x, y = q.popleft()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in cells and n not in region and cells[n] == cells[c]:
                    region[n] = rid
                    q.append(n)
    return region, names


def _neighbours(t):
    x, y = t
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def _pieces(cells):
    """The plan's separate pieces - cells joined four-ways - biggest first."""
    left, out = set(cells), []
    while left:
        start = min(left, key=lambda c: (c[1], c[0]))
        piece = {start}
        q = deque([start])
        left.discard(start)
        while q:
            for n in _neighbours(q.popleft()):
                if n in left:
                    left.discard(n)
                    piece.add(n)
                    q.append(n)
        out.append(piece)
    return sorted(out, key=lambda p: (-len(p), min(p, key=lambda c: (c[1], c[0]))))


def _gangways(cells):
    """Join a plan that comes in pieces (a starbase's modules, a bio-ship's pods) with
    hallway across the gaps, nearest pieces first, so the deck is one walk. Returns the
    cells to add as hallway."""
    pieces = _pieces(cells)
    if len(pieces) < 2:
        return {}
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    piece_of = {c: i for i, p in enumerate(pieces) for c in p}
    joined = set(pieces[0])
    done = {0}
    added = {}
    while len(done) < len(pieces):
        # Out from the joined deck through empty space, to the nearest cell of any piece
        # not yet joined; then the path back is the gangway.
        prev = {c: None for c in joined}
        q = deque(sorted(joined, key=lambda c: (c[1], c[0])))
        hit = None
        while q and hit is None:
            cur = q.popleft()
            for n in _neighbours(cur):
                if n in prev or not (lo_x <= n[0] <= hi_x and lo_y <= n[1] <= hi_y):
                    continue
                prev[n] = cur
                if n in piece_of and piece_of[n] not in done:
                    hit = n
                    break
                if n not in cells:
                    q.append(n)
        if hit is None:
            break
        step = prev[hit]
        while step is not None and step not in joined:
            added[step] = ""
            joined.add(step)
            step = prev[step]
        i = piece_of[hit]
        done.add(i)
        joined |= pieces[i]
    return added


def boarding_deck_layout(plan, scale=SCALE):
    """Lay a plan out as tiles. Pure: no areas, no props. Returns a dict:

    - ``w``, ``h``, ``tiles``: the map, rows of LOOK names, None outside the ship;
    - ``rooms``: ``{mark: set(tiles)}``, a mark per room name (``room:cargo``) plus
      ``room:hallway``; ``doors``: the doorway tiles;
    - ``entry``: the arrival tiles; ``furniture``: ``[(sprite, x, y, system_cell)]``,
      ``system_cell`` being the plan cell a system's kit stands for (None for plain
      furniture);
    - ``cell_tiles``: ``{plan cell: its floor tiles}``;
    - ``kinds``: ``{kind: set(tiles)}``, the floor of each KIND of room that nothing
      stands on (``hallway`` included); ``floor``: every tile that can be walked.
    """
    s = max(3, int(scale))
    cells = dict(plan["cells"])
    cells.update(_gangways(cells))
    W = max(int(plan["w"]), max((x for x, _ in cells), default=0) + 1)
    H = max(int(plan["h"]), max((y for _, y in cells), default=0) + 1)
    TW, TH = W * s + 1, H * s + 1
    region, names = _regions(cells)
    kinds = [boarding_deck_room_kind(n) for n in names]
    floors = [HALL if k == "hallway" else boarding_deck_kit_for(k).get("floor", "floor_metal")
              for k in kinds]
    tiles = [[HULL] * TW for _ in range(TH)]
    tile_region = {}
    cell_tiles = {}

    def same(a, b):
        return a in region and b in region and region[a] == region[b]

    for (px, py), name in cells.items():
        rid = region[(px, py)]
        up, left, diag = (px, py - 1), (px - 1, py), (px - 1, py - 1)
        mine = []
        for j in range(s):
            for i in range(s):
                tx, ty = px * s + i, py * s + j
                if i == 0 and j == 0:
                    floor = same(up, (px, py)) and same(left, (px, py)) and same(diag, (px, py))
                    across = (up, left, diag)
                elif j == 0:
                    floor, across = same(up, (px, py)), (up,)
                elif i == 0:
                    floor, across = same(left, (px, py)), (left,)
                else:
                    floor, across = True, ()
                if floor:
                    tiles[ty][tx] = floors[rid]
                    tile_region[(tx, ty)] = rid
                    mine.append((tx, ty))
                else:
                    # A bulkhead between rooms; the hull where the ship ends.
                    tiles[ty][tx] = WALL if all(a in cells for a in across) else HULL
        cell_tiles[(px, py)] = mine

    # Doorways. Candidates: the middle of each wall segment two regions share.
    shared = {}
    for (px, py) in cells:
        rb = region[(px, py)]
        for other, door in (((px, py - 1), (px * s + s // 2, py * s)),
                            ((px - 1, py), (px * s, py * s + s // 2))):
            if other in region and region[other] != rb:
                pair = tuple(sorted((region[other], rb)))
                shared.setdefault(pair, []).append(door)
    parent = list(range(len(names)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    doors = set()

    def open_door(pair):
        cands = sorted(shared[pair], key=lambda t: (t[1], t[0]))
        d = cands[len(cands) // 2]
        doors.add(d)
        tiles[d[1]][d[0]] = DOOR
        parent[find(pair[0])] = find(pair[1])

    halls = {r for r, k in enumerate(kinds) if k == "hallway"}
    # Every room opens onto a hallway when it touches one - the one it shares most wall with.
    for r in range(len(names)):
        if r in halls:
            continue
        options = [p for p in shared if r in p and (p[0] in halls or p[1] in halls)]
        if options:
            open_door(max(options, key=lambda p: (len(shared[p]), -min(p))))
    # Then join whatever is still apart, hallway links and long shared walls first.
    for pair in sorted(shared, key=lambda p: (-(p[0] in halls or p[1] in halls),
                                              -len(shared[p]), p)):
        if find(pair[0]) != find(pair[1]):
            open_door(pair)

    # Outside the ship is nothing: keep a one-tile rim of hull and leave the rest empty,
    # so the deck reads as the ship's own shape against space.
    for ty in range(TH):
        for tx in range(TW):
            if tiles[ty][tx] != HULL:
                continue
            if not any(0 <= tx + dx < TW and 0 <= ty + dy < TH
                       and tiles[ty + dy][tx + dx] not in (HULL, None)
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                tiles[ty][tx] = None

    # Marks.
    rooms = {}
    for t, rid in tile_region.items():
        rooms.setdefault("room:" + (names[rid] or "hallway").lower(), set()).add(t)
    for d in doors:
        rooms.setdefault("door", set()).add(d)

    entry = _entry(cells, region, names, kinds, cell_tiles, W, H)

    # Furniture. Nothing stands in a doorway or beside one, and nothing is placed that
    # would cut a room in two.
    blocked = set()
    near_door = {n for d in doors for n in _neighbours(d)} | doors
    furniture = []
    entry_set = set(entry)

    def walkable(t):
        x, y = t
        return 0 <= x < TW and 0 <= y < TH and t in tile_region and t not in blocked

    def still_one(rid, foot):
        region_tiles = [u for u, r in tile_region.items() if r == rid and u not in blocked
                        and u not in foot]
        if not region_tiles:
            return False
        seen = {region_tiles[0]}
        q = deque([region_tiles[0]])
        while q:
            u = q.popleft()
            for n in _neighbours(u):
                if n not in foot and n not in seen and walkable(n) and tile_region.get(n) == rid:
                    seen.add(n)
                    q.append(n)
        return len(seen) == len(region_tiles)

    def place(sprite, t, rid, system_cell=None):
        # Every tile the piece stands on (a big one covers several - its art's `base`)
        # must be this room's floor, and clear of doors and the way in.
        foot = {(t[0] + dx, t[1] + dy) for dx, dy in tilemap_sprite_cells(sprite)}
        if any(tile_region.get(u) != rid or u in blocked or u in near_door or u in entry_set
               for u in foot) or not still_one(rid, foot):
            return False
        blocked.update(foot)
        furniture.append((sprite, t[0], t[1], system_cell))
        return True

    by_region = {}
    for (px, py), rid in region.items():
        by_region.setdefault(rid, []).append((px, py))
    for rid in range(len(names)):
        kind = kinds[rid]
        if kind == "hallway":
            continue
        kit = boarding_deck_kit_for(kind)
        mine = sorted(by_region[rid], key=lambda c: (c[1], c[0]))
        if kit.get("system"):
            for c in mine:
                ts = sorted(cell_tiles[c], key=lambda t: (t[1], t[0]))
                for t in ts:
                    if t[0] % s and t[1] % s and place(kit["system"], t, rid, c):
                        break
        pieces = kit.get("furniture") or []
        if not pieces:
            continue
        floor_tiles = [t for t in tile_region if tile_region[t] == rid]
        want = max(1, len(floor_tiles) // 5)
        # Against the north wall first - in a 3/4 view that is where furniture reads.
        spots = sorted((t for t in floor_tiles),
                       key=lambda t: (tile_region.get((t[0], t[1] - 1)) == rid, t[1], t[0]))
        n = 0
        for i in range(len(pieces) * 3):
            if n >= want:
                break
            piece = pieces[i % len(pieces)]
            sprite, need = piece if isinstance(piece, (tuple, list)) else (piece, 0)
            if len(floor_tiles) < need:
                continue
            for t in spots:
                if place(sprite, t, rid):
                    n += 1
                    break

    # A doorway in a wall that runs east-west faces the viewer; one in a north-south
    # wall is seen side-on. The door that stands in it is drawn to match.
    sides = {d: ("front" if d[1] % s == 0 else "side") for d in doors}
    # What is left to stand something on, by KIND of room (`brig`, `cargo`, `hallway`):
    # the floor nothing was put on. Room NAMES differ hull to hull - a pirate has a
    # plunder-hold where a liner has cargo-bay-2 - and the kind is the word both answer
    # to (``boarding_deck_settle``). The arrival tiles count: on a fighter the way in IS
    # the only cabin. Whoever stands something keeps off the tile the party lands on.
    free = {}
    for t, rid in tile_region.items():
        if t not in blocked:
            free.setdefault(kinds[rid], set()).add(t)
    return {"w": TW, "h": TH, "tiles": tiles, "rooms": rooms, "doors": doors,
            "door_sides": sides,
            "entry": entry, "furniture": furniture, "cell_tiles": cell_tiles,
            "scale": s, "ship": plan.get("ship"),
            "kinds": free, "floor": (set(tile_region) - blocked) | set(doors)}


def _entry(cells, region, names, kinds, cell_tiles, W, H):
    """The airlock's first cell; else the hallway cell nearest the middle of the ship;
    else the middle-most room cell. Its floor tiles."""
    def pick(cands):
        cx = sum(x for x, _ in cells) / max(1, len(cells))
        cy = sum(y for _, y in cells) / max(1, len(cells))
        return min(cands, key=lambda c: ((c[0] - cx) ** 2 + (c[1] - cy) ** 2, c[1], c[0]))
    air = sorted(c for c in cells if kinds[region[c]] == "airlock")
    if air:
        c = air[0]
    else:
        halls = [c for c in cells if kinds[region[c]] == "hallway"]
        c = pick(halls or list(cells))
    return sorted(cell_tiles[c], key=lambda t: (t[1], t[0]))


# --- as a file, and as an area ----------------------------------------------------------

def boarding_deck_text(layout, key, title=None, tileset="deck"):
    """The layout as a `.tiles` area file (kinds and the entry; room marks are added by
    ``boarding_deck_build``, so an author's copy stays readable)."""
    chars = dict(_CHARS)
    free = iter("abcdefghijklmnopqrsuvwxyABCDEFGIJKLMNOPQRSTUVWXYZ0123456789")
    for row in layout["tiles"]:
        for look in row:
            if look is not None and look not in chars:
                chars[look] = next(free)
    entry = set(layout["entry"])
    # `size:` because the rows end in the spaces outside the ship, which editors strip.
    lines = [f"area: {key}", f"title: {title or key}", f"tileset: {tileset}",
             f"size: {layout['w']}x{layout['h']}", "entry: entry", "legend:"]
    used = {look for row in layout["tiles"] for look in row}
    for look, ch in chars.items():
        if look in used:
            lines.append(f"  {ch}: {look}")
    entry_look = layout["tiles"][layout["entry"][0][1]][layout["entry"][0][0]]
    lines.append(f"  @: {entry_look} @entry")
    lines.append("---")
    for y, row in enumerate(layout["tiles"]):
        lines.append("".join("@" if (x, y) in entry else (" " if look is None else chars[look])
                             for x, look in enumerate(row)).rstrip())
    return "\n".join(lines) + "\n"


def boarding_deck_kinds():
    """The tile kinds generated decks use: every look the kits name is a kind of the same
    name, walls and hull closed - ``{kind: {walk, see, look}}``."""
    looks = {HULL, WALL, DOOR, HALL}
    for kind in set(_KITS) | set(_OVERRIDES):
        looks.add(boarding_deck_kit_for(kind).get("floor", "floor_metal"))
    kinds = {}
    for look in looks:
        closed = look in (HULL, WALL)
        kinds[look] = {"walk": not closed, "see": not closed, "look": look}
    return kinds


def boarding_deck_tileset(name="deck"):
    """Declare the tileset generated decks use (``boarding_deck_kinds``). Returns its
    name."""
    from .tilemap import tilemap_tileset
    tilemap_tileset(name, boarding_deck_kinds())
    return name


def boarding_deck_build(plan, key, title=None, scale=SCALE, tileset="deck",
                        furnish=True):
    """Build a boarding area from a plan: the tiles, a mark per room, and the furniture
    as scenery props. Declares the tileset first if nothing has. Returns the area key,
    or None when the plan has no open cell.

    Room marks are ``room:<name>`` (``room:hallway`` for hallways), plus ``entry`` and
    ``door`` - and a mark per KIND of room (``brig``, ``cargo``, ``hallway``) holding
    the floor of that kind nothing stands on. The prop keys are ``<area>_kit_<n>``.

    Built under ``DECK_AREA`` it is the deck `Area: deck` records are waiting for, and
    they are stood aboard (``boarding_deck_settle``).
    """
    from .tilemap import tilemap_load, tilemap_mark, tilemap_tileset_known
    if not plan or not plan.get("cells"):
        return None
    if not tilemap_tileset_known(tileset):
        boarding_deck_tileset(tileset)
    layout = boarding_deck_layout(plan, scale)
    area = tilemap_load(boarding_deck_text(layout, key, title, tileset))
    if area is None:
        return None
    for mark, tiles in layout["rooms"].items():
        tilemap_mark(area, mark, tiles)
    # After the rooms, so a cell still answers `tilemap_mark_at` with its room.
    for kind, tiles in sorted(layout["kinds"].items()):
        tilemap_mark(area, kind, tiles)
    props = []
    # `generated`: built for this visit, under keys that mean something else on the next
    # hull - so a saved game never hears of them (`boarding_props._props_snapshot`).
    if furnish:
        from .boarding_props import boarding_prop_add, boarding_props_place
        for n, (sprite, x, y, cell) in enumerate(layout["furniture"]):
            pkey = f"{area}_kit_{n}"
            boarding_prop_add(pkey, area, (x, y), sprite=sprite, blocks=True,
                              name=sprite.split(":", 1)[-1].replace("_", " "),
                              generated=True)
            props.append((pkey, cell))
    doors = {}
    if furnish:
        for n, d in enumerate(sorted(layout["doors"], key=lambda t: (t[1], t[0]))):
            side = layout["door_sides"].get(d, "front")
            dkey = f"{area}_door_{n}"
            boarding_prop_add(dkey, area, d, sprite=DOOR_SPRITES[side][0], blocks=False,
                              name="door", generated=True)
            doors[d] = (dkey, side)
    _DECKS[area] = {"ship": layout.get("ship"), "scale": layout["scale"],
                    "cell_tiles": layout["cell_tiles"],
                    "systems": {cell: pkey for pkey, cell in props if cell is not None},
                    "doors": doors, "open": set(), "flicker": {}, "beat": 0,
                    "kinds": {k: set(v) for k, v in layout["kinds"].items()},
                    "floor": set(layout["floor"]), "entry": list(layout["entry"]),
                    "source": plan.get("source"), "settled": {}, "fallbacks": {}}
    if area == DECK_AREA:
        # BEFORE anything is placed: a record's `Mark: brig` is also the name of a mark
        # now, and placing it by that name would stand every one of them on its first
        # cell.
        boarding_deck_settle(area, place=False)
    if furnish:
        boarding_props_place(area)
    if area == DECK_AREA:
        from .boarding_combat import boarding_hostiles_place
        boarding_hostiles_place(area)
    return area


def boarding_deck_tiles_of(area, cell):
    """The floor tiles a plan cell became - where a damaged node's sparks go."""
    rec = _DECKS.get(str(area).strip().lower())
    return list((rec or {}).get("cell_tiles", {}).get(tuple(cell), []))


def boarding_deck_system_prop(area, cell):
    """The prop key of the kit standing for a system node, or None."""
    rec = _DECKS.get(str(area).strip().lower())
    return (rec or {}).get("systems", {}).get(tuple(cell))


# --- the live ship ------------------------------------------------------------------------

#: Who crews a ship, by race: its damage-control teams are drawn as these, in turn.
#: The race is the first word of the hull's key (`kralien_cruiser`). A mission may add
#: to it; a race it does not name is crewed by humans.
RACE_CREWS = {
    "human": ["fig:crew_m", "fig:crew_f", "fig:medic_m", "fig:soldier_m"],
    "kralien": ["fig:kralien", "fig:kralien", "fig:kralien_chief"],
    "torgoth": ["fig:torgoth"],
    "ximni": ["fig:ximni"],
    "arvonian": ["fig:arvonian", "fig:arvonian_f"],
    "skaraan": ["fig:skaraan", "fig:skaraan_f"],
    "pirate": ["fig:junker_m", "fig:junker_f", "fig:hunter_f"],
    "biomech": ["fig:robot_war"],
}
_RACE_WORDS = {"xim": "ximni", "tsn": "human", "usfp": "human", "terran": "human"}
#: Kept for missions that set it: when it is not None it overrides RACE_CREWS.
DAMCON_SPRITES = None


def boarding_deck_race(ship_key):
    """The race whose crew a hull carries, from its key: ``kralien_cruiser`` ->
    ``kralien``, ``starbase_torgoth`` -> ``torgoth``. ``human`` for anything not in
    ``RACE_CREWS``."""
    words = str(ship_key or "").strip().lower().split("_")
    if words and words[0] == "starbase" and len(words) > 1:
        words = words[1:]                    # starbase_kralien is a Kralien base
    word = _RACE_WORDS.get(words[0], words[0]) if words else ""
    return word if word in RACE_CREWS else "human"


def boarding_deck_crew_sprites(ship_key):
    """The figures a hull's crew is drawn as."""
    return list(DAMCON_SPRITES or RACE_CREWS[boarding_deck_race(ship_key)])
DAMAGED_TINT = "#666"
#: The two frames a shorted system's sparks flip between, and a burning room's fire.
SPARKS = ("prop:sparks", "prop:sparks_b")
FIRE = ("prop:fire", "prop:fire_b")


def _grid_state(ship):
    """``[(grid object id, x, y, damaged, damcon, hp)]`` for a ship's interior now. The
    seam the tests replace."""
    from .grid import grid_objects
    from .query import to_blob
    from .roles import has_role
    from .inventory import get_inventory_value
    out = []
    for gid in sorted(grid_objects(ship) or ()):
        blob = to_blob(gid)
        if blob is None:
            continue
        try:
            x, y = int(blob.get("curx", 0)), int(blob.get("cury", 0))
        except (ValueError, TypeError):
            continue
        out.append((gid, x, y, has_role(gid, "__damaged__"), has_role(gid, "damcons"),
                    get_inventory_value(gid, "HP", None)))
    return out


def boarding_deck_sync(area, ship):
    """Show a ship's state on the deck built from it: a damaged node's kit goes dark
    with rubble beside it - sparks by a system, fire in any other room - a repaired one
    comes back, and each damage-control team
    stands - and walks - where Engineering has it. Call it when things change, or let
    ``boarding_deck_watch`` call it every second. Returns how many things changed."""
    from .tilemap import (tilemap_place, tilemap_where, tilemap_walk, tilemap_remove,
                          tilemap_set_pose, tilemap_is_open)
    from .boarding_props import (boarding_prop, boarding_prop_add, boarding_props_place,
                                 boarding_prop_forget)
    area = str(area).strip().lower()
    rec = _DECKS.get(area)
    if rec is None:
        return 0
    changed = 0
    rubble = rec.setdefault("rubble", {})
    sparks = rec.setdefault("sparks", {})
    teams = rec.setdefault("teams", {})
    seen_teams = set()
    damaged_cells = set()
    for gid, x, y, damaged, damcon, hp in _grid_state(ship):
        cell = (x, y)
        tiles = rec["cell_tiles"].get(cell) or []
        if damcon:
            seen_teams.add(gid)
            spot = next((t for t in sorted(tiles, key=lambda t: (t[1], t[0]))
                         if tilemap_is_open(area, t[0], t[1])), None)
            if gid not in teams:
                if spot is None:
                    continue
                crew = boarding_deck_crew_sprites(rec.get("ship"))
                sprite = crew[len(teams) % len(crew)]
                tilemap_place(gid, area, spot[0], spot[1], sprite=sprite, party=False,
                              blocks=False, speed=2.5, exits=False)
                teams[gid] = cell
                changed += 1
            elif teams[gid] != cell and spot is not None:
                tilemap_walk(gid, spot[0], spot[1])
                teams[gid] = cell
                changed += 1
            tilemap_set_pose(gid, "down" if hp is not None and hp <= 0 else None)
            continue
        if damaged:
            damaged_cells.add(cell)
    # Teams that are gone from the ship leave the deck.
    for gid in [g for g in teams if g not in seen_teams]:
        tilemap_remove(gid)
        del teams[gid]
        changed += 1
    for cell in sorted(damaged_cells | set(rubble)):
        kit = rec["systems"].get(cell)
        broken = cell in damaged_cells
        if kit:
            p = boarding_prop(kit)
            at = tilemap_where(p["id"]) if p and p.get("id") is not None else None
            if at is not None and (p.get("color") == DAMAGED_TINT) != broken:
                p["color"] = DAMAGED_TINT if broken else None
                tilemap_place(p["id"], at[0], at[1], at[2], color=p["color"] or "")
                changed += 1
        if broken and cell not in rubble:
            free = [t for t in sorted(rec["cell_tiles"].get(cell, []),
                                      key=lambda t: (-t[1], -t[0]))
                    if tilemap_is_open(area, t[0], t[1])]
            if free:
                key = f"{area}_rubble_{cell[0]}_{cell[1]}"
                # Rubble is walked over: a repair party must still get to the kit.
                boarding_prop_add(key, area, free[0], sprite="prop:debris_pile",
                                  blocks=False, name="rubble", generated=True)
                boarding_props_place(area)
                rubble[cell] = key
                changed += 1
            # A system that is hit shorts out and sparks; any other room burns.
            if len(free) > 1:
                frames = SPARKS if kit else FIRE
                key = f"{area}_{'sparks' if kit else 'fire'}_{cell[0]}_{cell[1]}"
                boarding_prop_add(key, area, free[1], sprite=frames[0], blocks=False,
                                  name="sparks" if kit else "fire", generated=True)
                boarding_props_place(area)
                sparks[cell] = key
                rec["flicker"][key] = frames
        elif not broken and cell in rubble:
            boarding_prop_forget(rubble.pop(cell))
            if cell in sparks:
                key = sparks.pop(cell)
                rec["flicker"].pop(key, None)
                boarding_prop_forget(key)
            changed += 1
    return changed


def boarding_deck_animate_step(area):
    """One beat of a deck's life: doors slide open for anyone beside them and shut
    behind them, and flickering things (sparks, fire) flip frame every other beat.
    Returns how many things changed. ``boarding_deck_animate`` runs it for you."""
    from .tilemap import tilemap_actors, tilemap_actor, tilemap_place, tilemap_where
    from .boarding_props import boarding_prop
    area = str(area).strip().lower()
    rec = _DECKS.get(area)
    if rec is None:
        return 0
    changed = 0
    near = set()
    for aid in tilemap_actors(area):
        a = tilemap_actor(aid)
        if a is None or a.get("fixed"):
            continue
        x, y = a["x"], a["y"]
        near.update(((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    for tile, (key, side) in rec.get("doors", {}).items():
        want = tile in near
        if want == (tile in rec["open"]):
            continue
        p = boarding_prop(key)
        at = tilemap_where(p["id"]) if p and p.get("id") is not None else None
        if at is None:
            continue
        shut, opened = DOOR_SPRITES[side]
        tilemap_place(p["id"], at[0], at[1], at[2], sprite=opened if want else shut)
        (rec["open"].add if want else rec["open"].discard)(tile)
        changed += 1
    rec["beat"] = rec.get("beat", 0) + 1
    if rec["beat"] % 2 == 0:
        frame = (rec["beat"] // 2) % 2
        for key, frames in list(rec.get("flicker", {}).items()):
            p = boarding_prop(key)
            at = tilemap_where(p["id"]) if p and p.get("id") is not None else None
            if at is not None:
                tilemap_place(p["id"], at[0], at[1], at[2], sprite=frames[frame])
                changed += 1
    return changed


def boarding_deck_animate(area, seconds=0.25):
    """Keep a deck alive - doors, sparks, fire (``boarding_deck_animate_step``) - every
    `seconds`, until it is cleared. Started by ``boarding_deck_watch``; call it yourself
    for a deck with no ship behind it. Returns the tick task."""
    from ..tickdispatcher import TickDispatcher
    rec = _DECKS.get(str(area).strip().lower())
    if rec is None:
        return None
    if rec.get("animate") is not None:
        return rec["animate"]

    def tick(task):
        if _DECKS.get(task.area) is not rec:
            task.stop()
            return
        boarding_deck_animate_step(task.area)

    task = TickDispatcher.do_interval(tick, seconds)
    task.area = str(area).strip().lower()
    rec["animate"] = task
    return task


def boarding_deck_watch(area, ship, seconds=1.0):
    """Keep a deck in step with its ship (``boarding_deck_sync``) every few seconds,
    until the deck is cleared or the ship is gone. Returns the tick task."""
    from ..tickdispatcher import TickDispatcher
    from .query import to_object
    rec = _DECKS.get(str(area).strip().lower())
    if rec is None:
        return None
    if rec.get("watch") is not None:
        return rec["watch"]

    def tick(task):
        if _DECKS.get(task.area) is not rec or to_object(task.ship) is None:
            task.stop()
            rec["watch"] = None
            return
        boarding_deck_sync(task.area, task.ship)

    task = TickDispatcher.do_interval(tick, seconds)
    task.area = str(area).strip().lower()
    task.ship = ship
    rec["watch"] = task
    boarding_deck_animate(area)
    boarding_deck_sync(area, ship)
    return task


def boarding_deck_for(ship, title=None, watch=True, tileset="deck"):
    """The boarding deck of a live ship: built the first time it is asked for, then kept
    in step with the ship (``boarding_deck_watch``). Returns the area key - hand it to
    ``boarding_invite(..., area=...)`` to put a party aboard - or None when the hull has
    no interior plan.

        deck = boarding_deck_for(enemy_id, title="Kralien cruiser")
        boarding_invite(player_ship, [], title="Boarding", area=deck)
    """
    from .query import to_id, to_object
    sid = to_id(ship)
    so = to_object(sid)
    if so is None:
        return None
    key = f"deck_{sid}"
    if key not in _DECKS:
        plan = boarding_deck_plan(sid)
        if plan is None:
            return None
        if boarding_deck_build(plan, key, title=title or getattr(so, "name", None),
                               tileset=tileset) is None:
            return None
    if watch:
        boarding_deck_watch(key, sid)
    return key


# --- a writer's things aboard: `Area: deck`, `Mark: <a kind of room>` ---------------------
#
# A prop's `Mark:` names a mark in an area FILE, and takes the first cell of it. Neither
# works aboard a ship nobody drew: the room names are the hull's own (a pirate has a
# plunder-hold where a liner has cargo-bay-2), and the first cell of a room is usually
# under a bunk. So aboard `Area: deck` a `Mark:` is a KIND of room - the generator's own
# word for what a room is - and each record gets a cell of its own that nothing stands on.

def boarding_deck_built(area=DECK_AREA):
    """True while a generated deck stands under this key."""
    return str(area).strip().lower() in _DECKS


def boarding_deck_mark_words():
    """The words `Mark:` takes on `Area: deck`, sorted: every kind of room the generator
    knows (and the words that mean one - ``cabin``, ``surgery``), ``entry`` and
    ``hallway``. What the linter checks a `Mark:` against."""
    return sorted(set(_KITS) | set(_OVERRIDES) | set(_ALIASES) | {"entry", "hallway"})


def _reach(floor, blocked, start):
    """The tiles of ``floor`` that can be walked to from ``start`` round ``blocked``."""
    if start is None or start in blocked or start not in floor:
        return set()
    seen = {start}
    q = deque([start])
    while q:
        for n in _neighbours(q.popleft()):
            if n in floor and n not in blocked and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def _keeps_the_way(floor, start, blockers, cell, blocks, base):
    """THE RULE for standing anything on a deck: nothing seals a room, and nothing is
    walled in. Whether ``cell`` can take something - one that blocks or one that does
    not - given the cells that already block and ``base``, what can be walked from
    ``start`` round them today.

    - something that does not block must stand where a party can walk;
    - something that blocks must leave every other tile walkable that was, must itself
      have a tile beside it to be walked up to, and must not take the last such tile
      from anything already standing.

    One rule for a writer's records (``boarding_deck_settle``) and for the ship's own
    crew (``boarding_deck_crew``), checked by walking the real floor from the entry
    every time - so it holds whatever the hull, the kinds of room and the order of the
    records, and an unrelated record can change WHERE something stands but never
    WHETHER it can be reached.
    """
    if start is None:
        return True
    if not blocks:
        return cell in base
    after = _reach(floor, blockers | {cell}, start)
    if len(after) != len(base) - (1 if cell in base else 0):
        return False
    for b in list(blockers) + [cell]:
        near = _neighbours(b)
        if not any(n in after for n in near) and (b == cell or any(n in base for n in near)):
            return False
    return True


def boarding_deck_settle(area=DECK_AREA, place=True):
    """Stand a writer's records aboard a generated deck: every prop, person and hostile
    whose `Area:` is this deck gets a cell in a room of the KIND its `Mark:` names.

    - a cell nothing stands on, and each record a cell of its own: two things marked
      ``brig`` are two cells of the brig;
    - something that blocks (`Blocks: yes`, anybody `Calm: yes`) is never stood where
      it would cut the deck in two - a one-cell room with a way through it cannot take
      one, and that is the hallway too - and nothing is stood beside a doorway while
      there is anywhere else;
    - ``entry`` is beside where the party arrives; ``hallway`` is any hallway;
    - a hull with NO such room stands it in the hallway, and says so in ONE line for
      that kind (``debug.log``, and the console) - not an error: the same mission
      boards a cruiser that has a brig and a scout that has not.

    `At: x, y` is left as written (a cell means nothing on a deck nobody has seen, and
    the linter says so). What was taken, opened or put down stays so.

    Safe to call again: a record already standing is left where it is, and only what
    has been declared since is settled. ``boarding_deck_build`` calls it for
    ``DECK_AREA``, and ``boarding_ground_load`` does when a deck is already up.

    Returns:
        dict: ``{key: (x, y)}`` for the records this call settled.
    """
    from . import boarding_props, boarding_combat
    from .tilemap import tilemap_mark_cells
    area = str(area).strip().lower()
    rec = _DECKS.get(area)
    if rec is None:
        return {}
    settled = rec["settled"]
    floor = rec["floor"]
    entry = sorted(rec.get("entry") or (), key=lambda t: (t[1], t[0]))
    start = min(entry) if entry else None            # where `tilemap_entry` stands them
    doors = set(rec.get("doors") or ())
    near_door = doors | {n for d in doors for n in _neighbours(d)}
    free_all = set().union(*rec["kinds"].values()) if rec["kinds"] else set()
    # Her own crew counts too, when a record is declared after they came aboard.
    crew = rec.get("crew") or {}
    standing = list(settled.values()) + list(crew.values())
    taken = {v["cell"] for v in standing if v.get("cell")}
    blockers = {v["cell"] for v in standing if v.get("cell") and v.get("blocks")}
    base = [None]

    def fits(cell, blocks):
        if cell in taken or cell not in floor or cell == start:
            return False
        if start is None:
            return True
        if base[0] is None:
            base[0] = _reach(floor, blockers, start)
        return _keeps_the_way(floor, start, blockers, cell, blocks, base[0])

    def crowded(c):
        return any((c[0] + dx, c[1] + dy) in taken
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)

    arrival = set(entry)

    def pick(cells, blocks, landing=False):
        # Clear of where the party lands and of the doorways while there is anywhere
        # else, and not shoulder to shoulder with the last thing stood.
        for c in sorted(cells, key=lambda c: ((c in arrival) != landing, c in near_door,
                                              crowded(c), c[1], c[0])):
            if fits(c, blocks):
                return c
        return None

    def pool(word):
        """The free cells one `Mark:` word means on this hull; empty when it has none."""
        if word == "entry":
            return arrival
        for kind in (word, _ALIASES.get(word, word)):
            if rec["kinds"].get(kind):
                return rec["kinds"][kind]
        # A mark the deck really has - `room:captains-cabin` on a brigantine. Not a kind,
        # so not every hull will have it; on the hull that does, it is honored.
        for mark in (word, "room:" + word):
            cells = set(tilemap_mark_cells(area, mark)) & free_all
            if cells:
                return cells
        return set()

    waiting = []
    for table, blocks_of in ((boarding_props._PROPS, lambda r: bool(r.get("blocks"))),
                             # Somebody calm stands where they are put, all visit.
                             # Somebody who fights comes to the party.
                             (boarding_combat._HOSTILES, lambda r: bool(r.get("calm")))):
        for key in sorted(table):
            r = table[key]
            if r.get("area") != area or key in settled or r.get("generated") \
                    or r.get("dropped") or r.get("id") is not None:
                continue
            if r.get("taken") or r.get("state") == "down":
                continue                             # gone, and it stays gone
            waiting.append((key, r, blocks_of(r)))

    out = {}
    fell = {}
    for key, r, blocks in waiting:
        at = r.get("at")
        if at is not None and not isinstance(at, str):
            settled[key] = {"cell": None, "blocks": blocks, "was": at}   # `At: x, y`
            continue
        word = str(at or "").strip().lower()
        cell = pick(pool(word), blocks, landing=(word == "entry")) if word else None
        if cell is None:
            for cells in (rec["kinds"].get("hallway") or (), free_all):
                cell = pick(cells, blocks)
                if cell is not None:
                    break
            fell.setdefault(word, []).append(r.get("name") or key)
        if cell is None:
            _deck_say("'%s' (%s) could not be stood anywhere aboard '%s': there is no "
                      "floor left where it would not shut somebody in, so it is not "
                      "aboard this ship." % (r.get("name") or key, key, rec.get("ship")))
            # NOT ABOARD, rather than stood by its mark's name: `brig` is a mark on
            # this deck, and placing by it would stand the thing on that mark's first
            # cell, on top of whatever is there. It keeps its `Mark:` for the next hull.
            settled[key] = {"cell": None, "blocks": blocks, "was": at, "off": True}
            r["deck_mark"] = at
            r["at"] = None
            continue
        settled[key] = {"cell": cell, "blocks": blocks, "was": at}
        r["deck_mark"] = at
        r["at"] = cell
        taken.add(cell)
        if blocks:
            blockers.add(cell)
            base[0] = None
        out[key] = cell

    for word, names in sorted(fell.items()):
        if word in rec["fallbacks"]:
            continue                                 # ONE line for a kind, per hull
        rec["fallbacks"][word] = list(names)
        aboard = ", ".join(sorted(k for k, v in rec["kinds"].items() if v)) or "none"
        if not word:
            why = "%s has no `Mark:`" % ", ".join("'%s'" % n for n in names)
        elif word in boarding_deck_mark_words():
            why = "the deck of '%s' has no free '%s' for %s" % (
                rec.get("ship"), word, ", ".join("'%s'" % n for n in names))
        else:
            why = "'%s' is not a kind of room (`Mark:` of %s)" % (
                word, ", ".join("'%s'" % n for n in names))
        _deck_say("%s, so the hallway it is. On `Area: deck` a `Mark:` is a kind of room; "
                  "this hull has: %s." % (why, aboard))
    if place:
        boarding_props.boarding_props_place(area)
        boarding_combat.boarding_hostiles_place(area)
    return out


def boarding_deck_release(area=DECK_AREA):
    """Take a generated deck down: its furniture, doors and crew are forgotten, anything
    dropped on it with them, and the area is unloaded. A writer's own `Area: deck`
    records are taken off the map and KEPT - `Mark: brig` again, waiting for the next
    ship - with whatever was opened, taken or put down still so.

    Returns:
        bool: True when there was a deck to take down.
    """
    from . import boarding_props, boarding_combat
    from .tilemap import tilemap_unload
    area = str(area).strip().lower()
    rec = _DECKS.pop(area, None)
    if rec is None:
        return False
    for name in ("watch", "animate"):
        _stop(rec.get(name))
    settled = rec.get("settled") or {}
    for table, remove, forget in (
            (boarding_props._PROPS, boarding_props.boarding_prop_remove,
             boarding_props.boarding_prop_forget),
            (boarding_combat._HOSTILES, boarding_combat.boarding_hostile_remove,
             boarding_combat.boarding_hostile_forget)):
        for key in list(table):
            r = table[key]
            if r.get("area") != area:
                continue
            if r.get("generated") or r.get("dropped"):
                forget(key)
                continue
            remove(key)
            if key in settled and "deck_mark" in r:
                r["at"] = r.pop("deck_mark")
    tilemap_unload(area)
    return True


# --- boarding a ship ----------------------------------------------------------------------

def boarding_deck_has_plan(ship):
    """True when this ship's hull has an interior plan to draw a deck from. Cheap - one
    lookup - so a comms route can ask it of whatever is selected."""
    from .query import to_id, to_object
    try:
        from .grid import grid_get_plan_layout
        key, layout = ship, None
        if not isinstance(ship, str):
            so = to_object(to_id(ship))
            if so is None:
                return False
            from .inventory import get_inventory_value
            key, layout = so.art_id, get_inventory_value(so.id, "grid_layout", None)
        return bool(grid_get_plan_layout(key, layout))
    except Exception:                                        # noqa: BLE001
        return False


def boarding_deck_art_ready():
    """True when the art a deck is drawn with (the ``station`` set) is installed - in
    the mission, or in a media pack pinned in its story.json."""
    try:
        from .tilemap_art import tilemap_art_find
        return tilemap_art_find(DECK_ART) is not None
    except Exception:                                        # noqa: BLE001
        return False


def boarding_deck_ready(ship):
    """Can a party be sent aboard this ship and SEE it: the hull has a plan, and the
    deck art is installed. What the "Send a boarding party" button asks."""
    return boarding_deck_has_plan(ship) and boarding_deck_art_ready()


def boarding_deck_target():
    """The ship a party is aboard (its id), or None."""
    return _BOARDED.get("target")


def boarding_deck_boarders():
    """The ship the party aboard came from (its id), or None."""
    return _BOARDED.get("ship")


def boarding_deck_source(area=DECK_AREA):
    """Where a built deck's hallways came from: ``hull map`` (the engine's own open
    cells), ``grid text`` (the hull's `.grid` file - the engine gave this ship no hull
    map) or ``rooms only``. None when no deck stands under that key. The same word the
    "was planned from" line in debug.log ends with."""
    rec = _DECKS.get(str(area).strip().lower())
    return rec.get("source") if rec else None


def _deck_art(tileset):
    """Dress the deck's tileset from the ``station`` set. Never loads a set twice: a set
    loaded again goes back on top of the sets loaded after it."""
    import json
    import os
    from .tilemap_art import (tilemap_art_find, tilemap_art_loaded, tilemap_art_use,
                              tilemap_art_ground)
    try:
        folder = tilemap_art_find(DECK_ART)
    except Exception:                                        # noqa: BLE001
        folder = None
    if folder is None:
        _deck_say("the tile art '%s' is not installed, so the deck is drawn without it - "
                  "walls and floors with no picture on them, which on the crew console "
                  "is a black map. It comes from the Cosmos-Tiles `station` pack: pin it "
                  "under `shared_media` in story.json and fetch it. Walking, scenes and "
                  "quests do not need it." % DECK_ART, once="no-art")
        return False
    if DECK_ART not in tilemap_art_loaded():
        return bool(tilemap_art_use(DECK_ART, tileset=tileset))
    try:
        from ..fs import get_mission_dir_filename
        with open(os.path.join(get_mission_dir_filename(folder), "manifest.json"),
                  encoding="utf-8") as f:
            ground = (json.load(f) or {}).get("ground") or {}
    except Exception as e:                                   # noqa: BLE001
        _deck_say("the tile art '%s': cannot read its manifest: %s" % (DECK_ART, e),
                  once="art-manifest")
        return False
    tilemap_art_ground(tileset, ground)
    return True


def boarding_deck_visit(ship, target, scenes=None, title=None, stories=None):
    """Send a boarding party from ``ship`` aboard ``target``, on a deck drawn from the
    target's own interior plan. One call::

        boarding_deck_visit(COMMS_ORIGIN_ID, COMMS_SELECTED_ID, boarding_ground_scenes())

    What it does, in order: the target's plan becomes the tile area ``deck``
    (``DECK_AREA``), dressed from the ``station`` art; every `Area: deck` record is stood
    in a room of its kind (``boarding_deck_settle``); the target's own crew comes aboard
    as its race (``boarding_deck_crew`` - calm unless the two ships are at war); the
    target wears the role ``boarding_target`` and is held where it is; and a tile-map
    visit is opened (``boarding_visit``), kept under the ship's name.

    It ends as any tile visit does - ``boarding_visit_end()``, or the game ending - and
    also when the target is gone. However it ends, the deck is taken down
    (``boarding_deck_release``) and the role comes off.

    ONE DECK AT A TIME. A deck left from the last ship is taken down first.

    A LANDING PARTY THAT IS ALL HOME IS NO OBSTACLE. A tile-map visit somewhere else - a
    landing a mission opened, which nothing but the mission ever closes - is ENDED first
    when nobody of its party is on the ground (``boarding_visit_ended`` is sent for it,
    as for any visit). It is what "the last one home ends it" means for a place that has
    no hail to decline. With somebody still down there the answer is None, as it always
    was, and nothing is touched: nobody is pulled off a planet by a button on the bridge.
    Coming back, the mission opens its own site again, as it did the first time. A text
    visit (rooms and choices) and another ship's deck are never ended for this.

    Args:
        ship: the ship the party leaves from.
        target: the ship being boarded.
        scenes: what a prop's `Scene:` and a person's `Talk scene:` name -
            ``boarding_ground_scenes()``.
        title (str, optional): the name of the place; the target's name by default.
        stories (optional): as ``boarding_visit`` - quests for one person each.

    Returns:
        dict: the invitation - or None, with nothing built and nothing opened, when the
        target is gone or its hull has no plan, or a party is already out.
    """
    from ..tickdispatcher import TickDispatcher
    from .boarding import (boarding_visit, boarding_visiting, boarding_invitation,
                           boarding_is_open)
    from .query import to_id, to_object
    from .roles import add_role, remove_role
    from .signal import signal_observe
    from .tilemap import tilemap_area
    sid, tid = to_id(ship), to_id(target)
    so = to_object(tid)
    if so is None or to_object(sid) is None:
        return None
    # A landing nobody is at: over, the moment a party is wanted somewhere else.
    _end_an_empty_landing()
    # `boarding_visit`'s own rule, asked BEFORE a deck is built for a party that cannot go.
    if boarding_visiting() is not None or boarding_invitation() is not None \
            or boarding_is_open():
        return None
    if tilemap_area(DECK_AREA) is not None and DECK_AREA not in _DECKS:
        _deck_say("this mission has a tile area of its own called '%s', and that key is "
                  "the deck of whatever ship is boarded. Nothing was opened: give the "
                  "area another key." % DECK_AREA, once="own-deck")
        return None
    plan = boarding_deck_plan(tid)
    if plan is None:
        _deck_say("'%s' (%s) has no interior plan, so there is no deck to board."
                  % (getattr(so, "name", tid), getattr(so, "art_id", "?")))
        return None
    _boarded_over()                                  # the last ship's, if any was left
    boarding_deck_release(DECK_AREA)
    boarding_deck_tileset(DECK_AREA)
    _deck_art(DECK_AREA)
    name = str(getattr(so, "name", None) or plan["ship"])
    if boarding_deck_build(plan, DECK_AREA, title=title or name) is None:
        return None
    rec = _DECKS[DECK_AREA]
    # WHICH PLAN, every time: only the engine can say whether a ship nobody flies has a
    # hull map, and this is the line that says which way it went.
    _deck_say("the deck of '%s' (%s, %d x %d cells, %d open) was planned from: %s."
              % (name, plan["ship"], plan["w"], plan["h"], len(plan["cells"]),
                 plan.get("source")))
    boarding_deck_crew(DECK_AREA, ship=tid, boarders=sid)
    add_role(tid, TARGET_ROLE)
    invite = boarding_visit(sid, scenes or {}, None, title=title or name, area=DECK_AREA,
                            place=name, stories=stories)
    if invite is None:
        remove_role(tid, TARGET_ROLE)
        boarding_deck_release(DECK_AREA)
        return None
    _BOARDED.update({"area": DECK_AREA, "target": tid, "ship": sid, "name": name,
                     "source": rec.get("source")})
    signal_observe(_boarded_on_signal)
    _BOARDED["task"] = TickDispatcher.do_interval(_boarded_tick, 1.0)
    _hold(tid)
    return invite


def _end_an_empty_landing():
    """End a TILE visit that is not a boarded ship's deck when nobody of its party is on
    the ground. True when one was ended.

    Not a text visit: it has no ground to be off, and it ends itself when its scene
    closes. Not a deck: a party aboard a ship is that ship's business
    (``boarding_deck_target``), ended by one of its three endings."""
    from .boarding import boarding_visiting, boarding_visit_end, boarding_team
    from .tilemap import tilemap_where
    visit = boarding_visiting()
    if not visit or not visit.get("tile") or _BOARDED:
        return False
    if any(tilemap_where(lf) is not None for lf in boarding_team()):
        return False                                 # somebody is still down there
    _deck_say("the landing party at '%s' is all back aboard, so that visit is over: a "
              "party is going aboard a ship." % (visit.get("title") or visit.get("area")))
    return bool(boarding_visit_end())


def _hold(target):
    """Keep a boarded ship where it is: no course, no target, no throttle. Asked again
    every second, because whatever flies it may ask otherwise."""
    try:
        from .space_objects import clear_target
        clear_target(target)
    except Exception:                                        # noqa: BLE001
        pass


def _boarded_over():
    """The party is off the ship: the role comes off, the deck comes down. Idempotent."""
    from .signal import signal_unobserve
    if not _BOARDED:
        return False
    was = dict(_BOARDED)
    _BOARDED.clear()
    _stop(was.get("task"))
    signal_unobserve(_boarded_on_signal)
    try:
        from .query import to_object
        from .roles import remove_role
        if to_object(was.get("target")) is not None:
            remove_role(was.get("target"), TARGET_ROLE)
    except Exception:                                        # noqa: BLE001
        pass
    boarding_deck_release(was.get("area") or DECK_AREA)
    return True


def _boarded_on_signal(name, data):
    """The visit ended - a choice, the mission, the game - so the deck comes down. Here
    and not on the next tick: the results screen pauses the sim, and a paused sim ticks
    nothing."""
    if name == "boarding_visit_ended" and _BOARDED:
        _boarded_over()


def _boarded_tick(t=None):
    """One look at the boarded ship. NEVER RAISES - a raising interval pauses the sim."""
    try:
        if not _BOARDED:
            _stop(t)
            return
        from .boarding import boarding_visiting, boarding_visit_end
        from .query import to_object, object_exists
        visit = boarding_visiting()
        if visit is None or visit.get("area") != _BOARDED.get("area"):
            _boarded_over()                          # ended some way that sent no signal
            return
        target = _BOARDED.get("target")
        if to_object(target) is None or not object_exists(target):
            # The ship is gone - destroyed, deleted - and there is nothing to stand on.
            boarding_visit_end()
            _boarded_over()
            return
        _hold(target)
    except Exception as e:                                   # noqa: BLE001
        try:
            from .execution import log
            log("boarding_deck: the watcher stopped: %s" % (e,), "boarding", "warning")
        finally:
            _boarded_over()


#: What a boarded ship's crew is, by stance: its guards fight, its hands keep out of it.
_CREW_ROLES = {
    "guard": {"hp": 3, "damage": 1, "notice": 5, "calm": False},
    "hand": {"hp": 2, "damage": 1, "notice": 4, "calm": True},
}


def boarding_deck_crew(area, ship=None, boarders=None, hostile=None, count=None,
                       talk_scene=None, seed=None):
    """Put a boarded ship's own crew aboard its deck, drawn as its race, as boarding
    hostiles (``boarding_combat``) - some who fight, some who do not:

    - aboard a ship at war with the boarders, about three in five are GUARDS, walking the
      hallways between two points and fighting whoever they notice; the rest are HANDS,
      calm, in the cabins and messes, who only fight back when provoked;
    - aboard any other ship everyone is a hand.

    NOBODY SEALS A ROOM. They stand still and they block, so each is stood only where
    the whole deck can still be walked from the entry and everything already aboard - a
    writer's `Area: deck` records, the crew stood before them - can still be walked up
    to (``_keeps_the_way``). A cell that fails is passed over for the next; on a hull
    with nowhere left, that one of the crew is not aboard.

    Args:
        area: the deck (``boarding_deck_build`` / ``boarding_deck_for``).
        ship, boarders: the boarded ship and the boarders' ship; ``side_are_enemies`` of
            the two decides the stance unless ``hostile`` does.
        hostile (bool): force the stance.
        count (int): how many; by default one per ten cells of the plan, 2 to 12.
        talk_scene (str): a scene key the hands can be talked to with (the mission's own
            dialogue); without one they cannot be talked to.
        seed: for a repeatable crew; the area's name by default.

    Returns:
        list: the hostile keys, ``<area>_crew_<n>``. Placed at once.
    """
    import random
    import zlib
    from .boarding_combat import boarding_hostiles_declare, boarding_hostiles_place
    from .tilemap import (tilemap_is_open, tilemap_mark_cells, tilemap_actors,
                          tilemap_actor_cells)
    area = str(area).strip().lower()
    rec = _DECKS.get(area)
    if rec is None:
        return []
    if hostile is None:
        hostile = False
        if ship is not None and boarders is not None:
            try:
                from .sides import side_are_enemies
                hostile = bool(side_are_enemies(ship, boarders))
            except Exception:                                # noqa: BLE001
                hostile = False
    cells = len(rec.get("cell_tiles") or {})
    n = count if count is not None else max(2, min(12, cells // 10))
    rng = random.Random(zlib.crc32(str(seed if seed is not None else area).encode()))
    race = boarding_deck_race(rec.get("ship"))
    looks = boarding_deck_crew_sprites(rec.get("ship"))
    taken = set(tilemap_mark_cells(area, "entry")) | set(tilemap_mark_cells(area, "door"))
    floor = rec.get("floor") or set()
    entry = sorted(rec.get("entry") or (), key=lambda t: (t[1], t[0]))
    start = min(entry) if entry else None            # as `boarding_deck_settle` has it
    crew = rec.setdefault("crew", {})
    blockers = {v["cell"] for v in list((rec.get("settled") or {}).values())
                + list(crew.values()) if v.get("cell") and v.get("blocks")}

    def stand(pool):
        """The next cell of ``pool`` somebody can stand on and seal nothing; None when
        it has none. Cells passed over stay in the pool for whoever does not block."""
        base = _reach(floor, blockers, start) if start is not None else set()
        for i in range(len(pool) - 1, -1, -1):
            c = pool[i]
            if c in taken or (floor and c not in floor):
                continue
            if _keeps_the_way(floor, start, blockers, c, True, base):
                del pool[i]
                return c
        return None

    stood_on = {c for aid in tilemap_actors(area) for c in tilemap_actor_cells(aid)}

    def free(tiles):
        # Open, and with nothing lying on it either: a keycard a writer put in the brig
        # does not block, and nobody should be standing on it.
        # (Asked of ONE pass over the actors: `tilemap_actors_at` scans them all for
        # every tile, which on a starbase is most of a second.)
        out = [t for t in sorted(tiles) if t not in taken and t not in stood_on
               and tilemap_is_open(area, *t)]
        rng.shuffle(out)
        return out
    halls = free(tilemap_mark_cells(area, "room:hallway"))
    rooms = free(t for mark in _marks_of(area) if mark.startswith("room:")
                 and mark != "room:hallway"
                 and boarding_deck_room_kind(mark[len("room:"):]) in _CALM_ROOMS
                 for t in tilemap_mark_cells(area, mark))
    guards = int(round(n * 0.6)) if hostile else 0
    children = []
    title = race.capitalize() if race != "human" else "Crew"
    for i in range(n):
        role = "guard" if i < guards else "hand"
        at = None
        for pool in ((halls,) if role == "guard" else (rooms, halls)):
            at = stand(pool)
            if at is not None:
                break
        if at is None:
            continue
        taken.add(at)
        blockers.add(at)
        # A hand stays where they are put, all visit; a guard walks off.
        crew[f"{area}_crew_{i}"] = {"cell": at, "blocks": role == "hand"}
        data = dict(_CREW_ROLES[role], area=area, at="%d, %d" % at, sprite=looks[i % len(looks)])
        data["calm"] = "yes" if data["calm"] else "no"
        if role == "guard" and halls:
            # Up and down a stretch of hallway.
            far = max(halls, key=lambda t: -abs(abs(t[0] - at[0]) + abs(t[1] - at[1]) - 6))
            data["patrol"] = "%d %d; %d %d" % (at[0], at[1], far[0], far[1])
        if role == "hand" and talk_scene:
            data["talk_scene"] = talk_scene
        children.append({"key": f"{area}_crew_{i}",
                         "display_text": f"{title} {'guard' if role == 'guard' else 'crew'}",
                         "description": "", "data": data})
    # GENERATED: the crowd of one hull, never a writer's people - a saved game does not
    # keep who among them is down (`boarding_combat._hostiles_snapshot`), and the deck
    # forgets them when the party leaves (`boarding_deck_release`).
    keys = boarding_hostiles_declare({"children": children}, generated=True)
    boarding_hostiles_place(area)
    return keys


#: Rooms the crew who are not guards are found in.
_CALM_ROOMS = {"quarters", "mess", "galley", "sickbay", "lab", "recreation", "lounge",
               "conference", "workshop", "cargo", "computer", "bridge", "room"}


def _marks_of(area):
    from .tilemap import tilemap_marks
    return tilemap_marks(area)


def _stop(task):
    if task is not None:
        try:
            task.stop()
        except Exception:                                    # noqa: BLE001
            pass                # already dropped by a reset or the end of the mission


def boarding_deck_clear():
    """The per-mission reset. Emits nothing and moves nobody."""
    from .signal import signal_unobserve
    for rec in _DECKS.values():
        for name in ("watch", "animate"):
            _stop(rec.get(name))
    _stop(_BOARDED.get("task"))
    signal_unobserve(_boarded_on_signal)
    _BOARDED.clear()
    _SAID.clear()
    _DECKS.clear()
    _OVERRIDES.clear()


def boarding_deck_count():
    """For the reset ledger."""
    return len(_DECKS) + len(_OVERRIDES) + len(_BOARDED) + len(_SAID)
