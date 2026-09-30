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
    "shield": {"floor": "floor_lit", "system": "prop:shield_generator"},
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
    "brig": {"floor": "floor_plain", "furniture": ["prop:bunk", "prop:toilet"]},
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

    return {"w": TW, "h": TH, "tiles": tiles, "rooms": rooms, "doors": doors,
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
        boarding_props_place(area)
    _DECKS[area] = {"ship": layout.get("ship"), "scale": layout["scale"],
                    "cell_tiles": layout["cell_tiles"],
                    "systems": {cell: pkey for pkey, cell in props if cell is not None}}
    return area


def boarding_deck_tiles_of(area, cell):
    """The floor tiles a plan cell became - where a damaged node's sparks go."""
    rec = _DECKS.get(str(area).strip().lower())
    return list((rec or {}).get("cell_tiles", {}).get(tuple(cell), []))


def boarding_deck_system_prop(area, cell):
    """The prop key of the kit standing for a system node, or None."""
    rec = _DECKS.get(str(area).strip().lower())
    return (rec or {}).get("systems", {}).get(tuple(cell))


def boarding_deck_clear():
    _DECKS.clear()
    _OVERRIDES.clear()


def boarding_deck_count():
    """For the reset ledger."""
    return len(_DECKS) + len(_OVERRIDES)
