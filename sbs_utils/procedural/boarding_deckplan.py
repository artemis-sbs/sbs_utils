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
"""
from collections import deque

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

_OVERRIDES = {}      # kit name -> fields a mission changed
_DECKS = {}          # area key -> what was built (see boarding_deck_build)


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
    map, so only its rooms are open. None when the hull has no interior."""
    from .grid import grid_get_layout
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
    items = grid_get_layout(key, layout)
    if not items:
        return None
    cells = {}
    for o in items:
        if isinstance(o, dict) and o.get("name") and "x" in o and "y" in o:
            cells[(int(o["x"]), int(o["y"]))] = str(o["name"])
    w = max((x for x, _ in cells), default=0) + 1
    h = max((y for _, y in cells), default=0) + 1
    if hm is not None and getattr(hm, "w", 0) and getattr(hm, "h", 0):
        w, h = max(w, hm.w), max(h, hm.h)
        for x in range(hm.w):
            for y in range(hm.h):
                if hm.is_grid_point_open(x, y) and (x, y) not in cells:
                    cells[(x, y)] = ""
    return {"ship": key, "w": w, "h": h, "cells": cells}


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
    - ``cell_tiles``: ``{plan cell: its floor tiles}``.
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

    def still_one(rid, t):
        region_tiles = [u for u, r in tile_region.items() if r == rid and u not in blocked
                        and u != t]
        if not region_tiles:
            return False
        seen = {region_tiles[0]}
        q = deque([region_tiles[0]])
        while q:
            u = q.popleft()
            for n in _neighbours(u):
                if n != t and n not in seen and walkable(n) and tile_region.get(n) == rid:
                    seen.add(n)
                    q.append(n)
        return len(seen) == len(region_tiles)

    def place(sprite, t, rid, system_cell=None):
        if t in blocked or t in near_door or t in entry_set or not still_one(rid, t):
            return False
        blocked.add(t)
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
    return {"w": TW, "h": TH, "tiles": tiles, "rooms": rooms, "doors": doors,
            "door_sides": sides,
            "entry": entry, "furniture": furniture, "cell_tiles": cell_tiles,
            "scale": s, "ship": plan.get("ship")}


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


def boarding_deck_tileset(name="deck"):
    """Declare the tileset generated decks use: every look the kits name is a kind of
    the same name, walls and hull tall and closed. Returns its name."""
    from .tilemap import tilemap_tileset
    looks = {HULL, WALL, DOOR, HALL}
    for kind in set(_KITS) | set(_OVERRIDES):
        looks.add(boarding_deck_kit_for(kind).get("floor", "floor_metal"))
    kinds = {}
    for look in looks:
        closed = look in (HULL, WALL)
        kinds[look] = {"walk": not closed, "see": not closed, "look": look}
    tilemap_tileset(name, kinds)
    return name


def boarding_deck_build(plan, key, title=None, scale=SCALE, tileset="deck",
                        furnish=True):
    """Build a boarding area from a plan: the tiles, a mark per room, and the furniture
    as scenery props. Declares the tileset first if nothing has. Returns the area key,
    or None when the plan has no open cell.

    Room marks are ``room:<name>`` (``room:hallway`` for hallways), plus ``entry`` and
    ``door``. The prop keys are ``<area>_kit_<n>``.
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
    props = []
    if furnish:
        from .boarding_props import boarding_prop_add, boarding_props_place
        for n, (sprite, x, y, cell) in enumerate(layout["furniture"]):
            pkey = f"{area}_kit_{n}"
            boarding_prop_add(pkey, area, (x, y), sprite=sprite, blocks=True,
                              name=sprite.split(":", 1)[-1].replace("_", " "))
            props.append((pkey, cell))
    doors = {}
    if furnish:
        for n, d in enumerate(sorted(layout["doors"], key=lambda t: (t[1], t[0]))):
            side = layout["door_sides"].get(d, "front")
            dkey = f"{area}_door_{n}"
            boarding_prop_add(dkey, area, d, sprite=DOOR_SPRITES[side][0], blocks=False,
                              name="door")
            doors[d] = (dkey, side)
        boarding_props_place(area)
    _DECKS[area] = {"ship": layout.get("ship"), "scale": layout["scale"],
                    "cell_tiles": layout["cell_tiles"],
                    "systems": {cell: pkey for pkey, cell in props if cell is not None},
                    "doors": doors, "open": set(), "flicker": {}, "beat": 0}
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

#: What a damage-control team is drawn as, by team, in order.
DAMCON_SPRITES = ["fig:crew_m", "fig:crew_f", "fig:medic_m", "fig:soldier_m"]
DAMAGED_TINT = "#666"
#: The two frames a shorted system's sparks flip between.
SPARKS = ("prop:sparks", "prop:sparks_b")


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
    with rubble beside it (and sparks, for a system), a repaired one comes back, and each
    damage-control team
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
                sprite = DAMCON_SPRITES[len(teams) % len(DAMCON_SPRITES)]
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
                                  blocks=False, name="rubble")
                boarding_props_place(area)
                rubble[cell] = key
                changed += 1
            # A system that is hit shorts out: sparks by its kit, flickering.
            if kit and len(free) > 1:
                key = f"{area}_sparks_{cell[0]}_{cell[1]}"
                boarding_prop_add(key, area, free[1], sprite=SPARKS[0], blocks=False,
                                  name="sparks")
                boarding_props_place(area)
                sparks[cell] = key
                rec["flicker"][key] = SPARKS
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


def boarding_deck_clear():
    for rec in _DECKS.values():
        for name in ("watch", "animate"):
            task = rec.get(name)
            if task is not None:
                try:
                    task.stop()
                except Exception:                            # noqa: BLE001
                    pass
    _DECKS.clear()
    _OVERRIDES.clear()


def boarding_deck_count():
    """For the reset ledger."""
    return len(_DECKS) + len(_OVERRIDES)
