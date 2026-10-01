"""A tile world: areas drawn as ASCII, actors that walk them, and what the party has seen.

An away mission's ground is not a ship interior. The engineering grid draws a hull's
silhouette and nothing else, so an outdoor place - a ridge, a canyon, a salt flat - has
no floor there. This is the ground as DATA instead: each area is a grid of named tile
kinds, every actor's position is owned here as ``(area, x, y)``, and a console draws its
own view of it (``gui_tilemap``). Nothing here is a space object.

AN AREA FILE::

    area: ridge
    title: Landing Ridge
    tileset: surface
    entry: landing                  # a mark name, or "x, y"
    legend:
      .: dirt
      ,: scrub
      #: rock
      ~: water
      L: dirt @landing              # a tile kind, and a MARK on the cell
      c: path @to_colony            # a mark named to_<area> is an exit there
    exits:
      to_colony: colony @to_ridge   # optional - where an exit leads, and to which mark
    ---
    ###########
    #...,,..c.#
    #..L......#

Everything after ``---`` is the map, row 0 first. A space is ``nothing`` (never walked,
drawn black). ``#`` is fine as a legend key: a comment is only a ``#`` in column 0.

THE PIECES:

- **Tile kinds** belong to a TILESET: what a kind looks like (an atlas key) and whether it
  can be walked and seen through. ``tilemap_tileset``, or a ``.tileset`` file read with
  ``tilemap_tileset_load`` - the file is what the linter and the editor read, so a
  mission that writes one gets both. By convention ``tileset: X`` names ``X.tileset``
  in the same folder as the area.
- **Marks** name cells: a place a scene belongs to, where a prop stands, an exit. A mark
  can cover many cells. Stepping onto a mark emits ``tilemap_entered``.
- **Actors** are agents (a crew body, a hostile, a survivor) placed on a cell. They walk
  one cell per step at their own speed, around anything that cannot be walked. A big
  one - a parked car, a barn - covers every cell its sprite's ``base`` covers
  (``tilemap_sprite_cells``): it blocks them all, and it is AT each of them.
- **Blocked cells** close a walkable tile for now: a shut door, a rockfall.
- **Fog.** Party actors reveal what they can SEE (line of sight through see-through tiles,
  within a radius). A view draws what was never seen as black and what was seen but is not
  in sight now as dim, and never shows an actor out of sight - a map must not leak what
  the crew does not know.

Signals (route them with ``//shared/signal``):

``tilemap_entered``   TILEMAP_AGENT, TILEMAP_AREA, TILEMAP_MARK, TILEMAP_X, TILEMAP_Y
``tilemap_arrived``   an actor finished a walk: TILEMAP_AGENT, TILEMAP_AREA, TILEMAP_X/Y
``tilemap_blocked``   a walk could not reach its goal: TILEMAP_AGENT, TILEMAP_X/Y
``tilemap_moved``     an actor changed area: TILEMAP_AGENT, TILEMAP_FROM, TILEMAP_AREA

Stdlib only; no threading. One tick task walks every actor (``tilemap_watch``).
"""
from collections import deque

from ..agent import Agent
from .query import to_id
from .tilemap_art import tilemap_sprite_cells, tilemap_sprite_twin

# --- state ---------------------------------------------------------------------------
#
# Module tables, all emptied by `tilemap_clear` and audited by the reset ledger.
_TILESETS = {}      # name -> {kind: {"cell", "walk", "see", "color"}}
_AREAS = {}         # key -> area record
_ACTORS = {}        # agent id -> actor record
_REV = {}           # area key -> revision; moves whenever something in it changes
_LISTENERS = []     # fn(area_key) called when an area changes (views)
_WATCH = {"task": None}
_CLOCK = {"now": None}   # tests set a clock; None reads the sim

DEFAULT_SPEED = 4.0      # cells per second
SIGHT = 7                # how far a party actor sees, in cells


def _now():
    if _CLOCK["now"] is not None:
        return _CLOCK["now"]
    from ..helpers import FrameContext
    try:
        return FrameContext.sim_seconds
    except Exception:                                    # noqa: BLE001
        return 0.0


def tilemap_set_clock(now):
    """Drive time by hand (tests). ``None`` goes back to sim time."""
    _CLOCK["now"] = now


def _norm(key):
    return str(key or "").strip().lower()


def _bump(area):
    area = _norm(area)
    _REV[area] = _REV.get(area, 0) + 1
    for fn in list(_LISTENERS):
        try:
            fn(area)
        except Exception:                                # noqa: BLE001
            pass


def tilemap_revision(area):
    """Moves whenever anything in the area changes - an actor steps, a door opens."""
    return _REV.get(_norm(area), 0)


def tilemap_touch(area):
    """Say something about an area changed that the tiles do not show - a prop was used,
    a person spoken to - so views of it repaint."""
    _bump(area)


def tilemap_listen(fn):
    """Call ``fn(area_key)`` whenever an area changes. Views use this to repaint."""
    if fn not in _LISTENERS:
        _LISTENERS.append(fn)


def tilemap_unlisten(fn):
    if fn in _LISTENERS:
        _LISTENERS.remove(fn)


# --- tilesets ------------------------------------------------------------------------

def tilemap_tileset(name, kinds):
    """Declare what tile kinds look like and how they behave.

    Args:
        name (str): the tileset's name, as an area's ``tileset:`` names it.
        kinds (dict): ``{kind: {"cell": atlas key, "walk": bool, "see": bool,
            "color": tint, "variants": [atlas key, ...], "look": art ground name}}``.
            ``look`` names the ground an ART SET draws this kind with (see
            ``tilemap_art``) - so a map keeps its own kind names (``dust``) and still
            gets a shared pack's ground (``dirt_arid``). ``walk`` defaults True,
            ``see`` defaults to ``walk``. ``variants`` are other looks for the same
            kind, picked per cell so a field of one kind does not repeat in a grid.
    """
    table = {}
    for kind, spec in (kinds or {}).items():
        spec = dict(spec or {})
        walk = bool(spec.get("walk", True))
        table[_norm(kind)] = {"cell": spec.get("cell"), "walk": walk,
                              "see": bool(spec.get("see", walk)),
                              "color": spec.get("color"),
                              "variants": [spec.get("cell")] + list(spec.get("variants") or []),
                              "edges": spec.get("edges"), "shade": spec.get("shade"),
                              "tall": bool(spec.get("tall", False)),
                              "look": spec.get("look"), "grid": spec.get("grid"),
                              "fringe": spec.get("fringe"), "over": spec.get("over")}
    _TILESETS[_norm(name)] = table
    return table


#: A `.tileset` kind line: the rules a kind HAS, and the values it carries.
_TILESET_FLAGS = ("walk", "see", "tall")
_TILESET_VALUES = ("look", "cell", "color", "over")


def tilemap_tileset_known(name):
    """Whether a tileset of this name has been declared."""
    return _norm(name) in _TILESETS


def tilemap_tileset_parse(text):
    """Read a tileset file. Raises TilemapError rather than guessing.

    A TILESET FILE::

        tileset: mereth
        title: Mereth surface
        kinds:
          dust:   walk see   look=dirt      # walked and seen across
          brine:  see        look=water     # seen across, never walked
          rock:              look=rock      # neither
          door:   walk       color=#a86

    Each word on a kind line is a rule the kind HAS, so a kind that names neither
    ``walk`` nor ``see`` blocks both - a typo is an error, never a silent wall. ``tall``
    stands up (the kind south of it takes its ``shade``). ``look=`` names the ground an
    art set draws it with, ``cell=`` a sprite key to draw without one, ``color=`` a tint,
    ``over=`` which of two kinds' fringes goes on top. A ``#`` that starts a word ends
    the line, so ``color=#a86`` is a color and ``  # note`` a comment.

    Returns:
        dict: ``{"name", "title", "kinds": {kind: spec}, "lines": {kind: line number}}``
        - ``kinds`` is what ``tilemap_tileset`` takes; ``lines`` is for tools.
    """
    if not text:
        raise TilemapError("empty tileset")
    header, kinds, lines = {}, {}, {}
    block = None
    for n, raw in enumerate(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), 1):
        stripped = raw.strip()
        # Unlike an area's legend, no key here is one character, so a `#` line is a
        # comment however far it is indented.
        if not stripped or stripped.startswith("#"):
            continue
        if raw[:1] not in (" ", "\t"):
            key, _, value = stripped.partition(":")
            key = key.strip().lower()
            if key == "kinds" and not value.strip():
                block = key
                continue
            block = None
            header[key] = value.strip()
            continue
        if block != "kinds":
            raise TilemapError(f"line {n}: indented line outside kinds:")
        kind, colon, rest = stripped.partition(":")
        kind = _norm(kind)
        if not colon or not kind or " " in kind:
            raise TilemapError(f"line {n}: a kind line is 'name: rules' - got {stripped!r}")
        if kind in kinds:
            raise TilemapError(f"line {n}: kind {kind!r} is declared twice")
        spec = {"walk": False, "see": False}
        for word in rest.split():
            if word.startswith("#"):
                break
            name, eq, value = word.partition("=")
            name = name.lower()
            if not eq and name in _TILESET_FLAGS:
                spec[name] = True
            elif eq and name in _TILESET_VALUES and value:
                if name == "over":
                    try:
                        value = int(value)
                    except ValueError:
                        raise TilemapError(f"line {n}: over= wants a whole number, "
                                           f"got {value!r}")
                spec[name] = value
            else:
                raise TilemapError(
                    f"line {n}: {word!r} is not a rule - a kind line takes "
                    f"{', '.join(_TILESET_FLAGS)} and "
                    f"{', '.join(v + '=' for v in _TILESET_VALUES)}")
        kinds[kind] = spec
        lines[kind] = n
    name = _norm(header.get("tileset"))
    if not name:
        raise TilemapError("no 'tileset:' name")
    if not kinds:
        raise TilemapError("no kinds: block, so the tileset has no kinds")
    return {"name": name, "title": header.get("title") or name,
            "kinds": kinds, "lines": lines}


def tilemap_tileset_load(text):
    """Read a tileset file and declare it (``tilemap_tileset``). Returns its name, or
    None when it cannot be read - logged, like an area that cannot be."""
    try:
        rec = tilemap_tileset_parse(text)
    except TilemapError as e:
        from .execution import log
        log(f"tileset not loaded: {e}", "tilemap", "warning")
        return None
    tilemap_tileset(rec["name"], rec["kinds"])
    return rec["name"]


def tilemap_kind(area, x, y):
    """The tile kind at a cell, or None off the map or on nothing."""
    rec = _AREAS.get(_norm(area))
    if rec is None or not (0 <= x < rec["w"] and 0 <= y < rec["h"]):
        return None
    return rec["tiles"][y][x]


def _kind_spec(rec, kind):
    if kind is None:
        return None
    return (_TILESETS.get(rec["tileset"]) or {}).get(kind)


def _by_position(looks, x, y):
    """One look of an n x n GRID picked by where the cell is, so the pieces of one big
    texture always sit next to each other the same way. A single key is itself."""
    if isinstance(looks, str) or not looks:
        return looks
    n = int(round(len(looks) ** 0.5))
    if n * n != len(looks):
        return looks[0]
    return looks[(y % n) * n + (x % n)]


#: Neighbor bits for ``edges`` masks: which sides have the SAME kind.
EDGE_N, EDGE_E, EDGE_S, EDGE_W = 1, 2, 4, 8


#: Which fringe strip sits along which edge of the RECEIVING cell, for a neighbour on
#: each side.
_FRINGE_SIDES = (("n", 0, -1), ("e", 1, 0), ("s", 0, 1), ("w", -1, 0))
_FRINGE_CORNERS = (("ne", 1, -1), ("se", 1, 1), ("sw", -1, 1), ("nw", -1, -1))


def tilemap_cell_fringes(area, x, y):
    """The fringe strips drawn over one cell where its ground meets another: for each
    side whose neighbour is a kind that goes OVER this one (a higher ``over``) and has a
    ``fringe``, that kind's strip for this edge. Lowest first, so the one on top is
    drawn last. ``[]`` for a cell with nothing to blend.

    This is how two kinds of ground meet softly - salt crust spilling onto dirt, a path
    frayed at its sides - where one tile per cell could only meet in a straight seam."""
    rec = _AREAS.get(_norm(area))
    if rec is None or not (0 <= x < rec["w"] and 0 <= y < rec["h"]):
        return []
    here = _kind_spec(rec, rec["tiles"][y][x])
    if here is None:
        return []
    mine = here.get("over")
    if mine is None or here.get("tall"):
        return []
    def spec_at(dx, dy):
        nx, ny = x + dx, y + dy
        if not (0 <= nx < rec["w"] and 0 <= ny < rec["h"]):
            return None
        return _kind_spec(rec, rec["tiles"][ny][nx])

    out = []
    for side, dx, dy in _FRINGE_SIDES:
        there = spec_at(dx, dy)
        if there is None or there is here or not there.get("fringe"):
            continue
        if (there.get("over") or 0) > mine and there["fringe"].get(side):
            out.append((there["over"], there["fringe"][side]))
    # CORNERS: a higher kind only diagonally across gets a corner piece, so a convex
    # corner of it does not end in a square notch. Skipped when either side along
    # that corner is the same kind - its edge strip already covers the corner.
    for side, dx, dy in _FRINGE_CORNERS:
        there = spec_at(dx, dy)
        if there is None or there is here or not there.get("fringe"):
            continue
        if spec_at(dx, 0) is there or spec_at(0, dy) is there:
            continue
        if (there.get("over") or 0) > mine and there["fringe"].get(side):
            out.append((there["over"], there["fringe"][side]))
    return [k for _, k in sorted(out)]


def tilemap_cell_look(spec, x, y, area=None):
    """The atlas key a kind is drawn with at one cell.

    With the area given, a kind's art can depend on its neighbors:

    - ``edges`` - ``{mask: key or [keys]}`` where the mask is which sides have the same kind
      (N=1, E=2, S=4, W=8). A wall run, a cliff edge, a pool's bank. A mask with no
      entry falls through to the plain look.
    - ``shade`` - the look of this kind lying just SOUTH of a ``tall`` kind, in its
      shadow, which is what makes a wall read as standing up. A key, or a grid.
    - ``grid`` - n x n keys cut from one texture bigger than a tile; each cell takes
      the piece for its position (x % n, y % n). Seamless, and the texture keeps a
      believable scale where squeezing it into one tile would shrink it to noise.

    Otherwise a fixed pick among the kind's variants, so the same cell always looks the
    same.
    """
    rec = _AREAS.get(_norm(area)) if area is not None else None
    if rec is not None:
        kind = rec["tiles"][y][x] if 0 <= y < rec["h"] and 0 <= x < rec["w"] else None
        edges = spec.get("edges")
        if edges:
            mask = 0
            for bit, (dx, dy) in ((EDGE_N, (0, -1)), (EDGE_E, (1, 0)),
                                  (EDGE_S, (0, 1)), (EDGE_W, (-1, 0))):
                nx, ny = x + dx, y + dy
                if 0 <= ny < rec["h"] and 0 <= nx < rec["w"] and rec["tiles"][ny][nx] == kind:
                    mask |= bit
            look = edges.get(str(mask)) or edges.get(mask)
            if isinstance(look, (list, tuple)):
                # Several looks for one mask (a cliff face in variants): a fixed pick by
                # position, so a long cliff does not repeat the same face every cell.
                looks = [v for v in look if v]
                look = looks[_cell_hash(x, y) % len(looks)] if looks else None
            if look:
                return look
        if spec.get("shade") and y > 0:
            above = _kind_spec(rec, rec["tiles"][y - 1][x])
            if above is not None and above.get("tall"):
                return _by_position(spec["shade"], x, y)
    if spec.get("grid"):
        return _by_position(spec["grid"], x, y)
    looks = [v for v in (spec.get("variants") or []) if v] or [spec.get("cell")]
    if len(looks) == 1:
        return looks[0]
    return looks[_cell_hash(x, y) % len(looks)]


def _cell_hash(x, y):
    """A fixed number per cell: how a cell picks among variants, the same every time."""
    return ((x * 73856093) ^ (y * 19349663)) >> 3


def tilemap_kind_spec(area, kind):
    """The tileset entry for a kind in this area's tileset, or None."""
    rec = _AREAS.get(_norm(area))
    return _kind_spec(rec, _norm(kind)) if rec else None


# --- areas ---------------------------------------------------------------------------

class TilemapError(Exception):
    """An area file that cannot be read. Carries a line number where it can."""


def tilemap_parse(text):
    """Read an area file into a record. Raises TilemapError rather than guessing."""
    if not text:
        raise TilemapError("empty area")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    header, legend, exits, rows = {}, {}, {}, None
    block = None
    for n, raw in enumerate(lines, 1):
        if rows is not None:
            rows.append(raw)
            continue
        stripped = raw.strip()
        if stripped.startswith("---"):
            rows = []
            continue
        if not stripped or raw.startswith("#"):
            continue
        indented = raw[:1] in (" ", "\t")
        if not indented:
            key, _, value = stripped.partition(":")
            key = key.strip().lower()
            if key in ("legend", "exits") and not value.strip():
                block = key
                continue
            block = None
            header[key] = value.strip()
            continue
        if block is None:
            raise TilemapError(f"line {n}: indented line outside legend/exits")
        if block == "legend":
            # The KEY IS ONE CHARACTER, then a colon - so `:: dust` makes `:` a key and
            # `#: rock` makes `#` one, where splitting on the first colon would not.
            key, value = stripped[:1], stripped[1:]
            if not value.startswith(":"):
                raise TilemapError(f"line {n}: legend key must be one character, "
                                   f"then ':' - got {stripped!r}")
            kind, _, mark = value[1:].strip().partition("@")
            legend[key] = (_norm(kind), _norm(mark) or None)
        else:
            key, _, value = stripped.partition(":")
            exits[_norm(key)] = value.strip()
    if rows is None:
        raise TilemapError("no '---' line, so there is no map")
    while rows and not rows[-1].strip():
        rows.pop()
    h = len(rows)
    w = max((len(r) for r in rows), default=0)
    if header.get("size"):
        try:
            sw, _, sh = header["size"].lower().partition("x")
            w, h = int(sw), int(sh)
        except ValueError:
            raise TilemapError(f"cannot read size {header['size']!r}")
        rows = (rows + [""] * h)[:h]
    tiles, marks, mark_at = [], {}, {}
    for y, row in enumerate(rows):
        out = []
        for x in range(w):
            ch = row[x] if x < len(row) else " "
            if ch == " ":
                out.append(None)
                continue
            if ch not in legend:
                raise TilemapError(f"map row {y} column {x}: {ch!r} is not in the legend")
            kind, mark = legend[ch]
            out.append(kind)
            if mark:
                marks.setdefault(mark, set()).add((x, y))
                mark_at[(x, y)] = mark
        tiles.append(out)
    key = _norm(header.get("area"))
    if not key:
        raise TilemapError("no 'area:' name")
    return {
        "key": key,
        "title": header.get("title") or key,
        "tileset": _norm(header.get("tileset") or "default"),
        "entry": header.get("entry"),
        "w": w, "h": h, "tiles": tiles,
        "marks": marks, "mark_at": mark_at, "exits": exits,
        "blocked": set(), "explored": set(), "tints": {},
        "known": header.get("known", "yes").strip().lower() not in ("no", "false", "0"),
        "beam": header.get("beam", "yes").strip().lower() not in ("no", "false", "0"),
    }


def tilemap_load(text):
    """Parse an area file and add it to the world. Returns the area key, or None.

    A file that cannot be read is logged and skipped - one bad area should not take a
    mission down - so the linter and the tests are what make it loud.
    """
    try:
        rec = tilemap_parse(text)
    except TilemapError as e:
        from .execution import log
        log(f"tile area not loaded: {e}", "tilemap", "warning")
        return None
    _AREAS[rec["key"]] = rec
    _bump(rec["key"])
    return rec["key"]


def tilemap_generate(key, w, h, cell, tileset="default", title=None):
    """Build an area from code rather than a file - or rebuild it.

    For a world too big or too procedural to write down: a window onto an endless galaxy,
    regenerated around whatever the console is looking at.

    Args:
        key (str): the area's name. Generating the same key again replaces it.
        w, h (int): its size, in cells.
        cell (callable): ``fn(x, y)`` -> a kind, ``(kind, tint)``, or None for nothing.
        tileset (str): the tileset the kinds come from.
        title (str, optional): defaults to the key.

    A rebuild that comes out IDENTICAL changes nothing and repaints nothing, so a caller
    may regenerate every tick and pay only when the world moved. Actors in the area stay
    where they are - moving them is the caller's business - and while the size is
    unchanged the area keeps what it held besides its tiles (explored cells, marks,
    blocked cells).

    Returns:
        str: the area key.
    """
    key = _norm(key)
    w, h = max(0, int(w)), max(0, int(h))
    tileset = _norm(tileset or "default")
    tiles, tints = [], {}
    for y in range(h):
        row = []
        for x in range(w):
            got = cell(x, y)
            kind, tint = (tuple(got) + (None,))[:2] if isinstance(got, (tuple, list)) \
                else (got, None)
            row.append(_norm(kind) or None)
            if tint:
                tints[(x, y)] = tint
        tiles.append(row)
    title = title or key
    old = _AREAS.get(key)
    same_size = old is not None and old["w"] == w and old["h"] == h
    if same_size and old["tileset"] == tileset and old["title"] == title and \
            old["tiles"] == tiles and old.get("tints", {}) == tints:
        return key
    keep = old if same_size else {}
    _AREAS[key] = {
        "key": key, "title": title, "tileset": tileset, "entry": keep.get("entry"),
        "w": w, "h": h, "tiles": tiles, "tints": tints,
        "marks": keep.get("marks", {}), "mark_at": keep.get("mark_at", {}),
        "exits": keep.get("exits", {}), "blocked": keep.get("blocked", set()),
        "explored": keep.get("explored", set()),
        "known": keep.get("known", True), "beam": keep.get("beam", True),
    }
    _bump(key)
    return key


def tilemap_unload(area):
    """Drop an area and every actor in it. False when there was no such area."""
    area = _norm(area)
    if _AREAS.pop(area, None) is None:
        return False
    for aid in [a for a, r in _ACTORS.items() if r["area"] == area]:
        del _ACTORS[aid]
    _bump(area)
    return True


def tilemap_tint(area, cells, color=None):
    """Tint cells - an owner's color, a selection, a warning - over their kind's own.

    ``color=None`` clears the tint, back to the kind's. Repaints once, and only when a
    cell actually changed. False for an unknown area.
    """
    rec = _AREAS.get(_norm(area))
    if rec is None:
        return False
    tints = rec.setdefault("tints", {})
    changed = False
    for c in cells:
        cell = (int(c[0]), int(c[1]))
        if color:
            if tints.get(cell) != color:
                tints[cell] = color
                changed = True
        elif tints.pop(cell, None) is not None:
            changed = True
    if changed:
        _bump(rec["key"])
    return True


def tilemap_tint_at(area, x, y):
    """A cell's own tint, or None when it wears its kind's color."""
    rec = _AREAS.get(_norm(area))
    return (rec.get("tints") or {}).get((int(x), int(y))) if rec else None


def tilemap_areas(known_only=False, beam_only=False):
    """Area keys, in load order."""
    return [k for k, r in _AREAS.items()
            if (not known_only or r["known"]) and (not beam_only or r["beam"])]


def tilemap_area(key):
    """The area record (read-only by convention), or None."""
    return _AREAS.get(_norm(key))


def tilemap_title(key):
    rec = _AREAS.get(_norm(key))
    return rec["title"] if rec else None


def tilemap_size(key):
    rec = _AREAS.get(_norm(key))
    return (rec["w"], rec["h"]) if rec else (0, 0)


def tilemap_reveal_area(key, beam=None):
    """The party now knows the area exists (a scan found it)."""
    rec = _AREAS.get(_norm(key))
    if rec is None:
        return False
    rec["known"] = True
    if beam is not None:
        rec["beam"] = bool(beam)
    _bump(rec["key"])
    from .signal import signal_emit
    signal_emit("tilemap_area_revealed", {"TILEMAP_AREA": rec["key"]})
    return True


def tilemap_known(key):
    rec = _AREAS.get(_norm(key))
    return bool(rec and rec["known"])


def tilemap_mark_cells(area, mark):
    """Every cell a mark covers, sorted."""
    rec = _AREAS.get(_norm(area))
    return sorted((rec or {}).get("marks", {}).get(_norm(mark), set()))


def tilemap_mark(area, mark, cells):
    """Add cells to a mark after the area is loaded - how a generated map names its
    rooms without spending a legend character on each. A cell keeps the mark its file
    gave it (an exit, the entry) as the one ``tilemap_mark_at`` answers. False for an
    unknown area."""
    rec = _AREAS.get(_norm(area))
    if rec is None:
        return False
    mark = _norm(mark)
    for c in cells:
        cell = (int(c[0]), int(c[1]))
        rec["marks"].setdefault(mark, set()).add(cell)
        rec["mark_at"].setdefault(cell, mark)
    _bump(rec["key"])
    return True


def tilemap_mark_at(area, x, y):
    """The mark on a cell, or None."""
    rec = _AREAS.get(_norm(area))
    return (rec or {}).get("mark_at", {}).get((int(x), int(y)))


def tilemap_marks(area):
    rec = _AREAS.get(_norm(area))
    return sorted((rec or {}).get("marks", {}))


def _xy(value):
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


def tilemap_entry(area):
    """Where somebody arriving by transporter stands: `entry:` (a mark or x,y), else the
    first walkable cell nearest the middle."""
    rec = _AREAS.get(_norm(area))
    if rec is None:
        return None
    spec = rec.get("entry")
    if spec:
        cells = rec["marks"].get(_norm(spec))
        if cells:
            if tilemap_exit_target(rec["key"], spec)[0]:
                # Entering AT an exit: stand beside it, or arriving is leaving again.
                for x, y in sorted(cells):
                    for n in ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)):
                        if n not in cells and tilemap_is_open(rec["key"], *n) and \
                                not tilemap_mark_at(rec["key"], *n):
                            return n
            return min(cells)
        at = _xy(spec)
        if at:
            return at
    cx, cy = rec["w"] // 2, rec["h"] // 2
    best = None
    for y in range(rec["h"]):
        for x in range(rec["w"]):
            if tilemap_is_open(rec["key"], x, y):
                d = abs(x - cx) + abs(y - cy)
                if best is None or d < best[0]:
                    best = (d, (x, y))
    return best[1] if best else (0, 0)


# --- walkability ---------------------------------------------------------------------

def tilemap_block(area, cells):
    """Close cells for now: a shut door, a rockfall."""
    rec = _AREAS.get(_norm(area))
    if rec is None:
        return
    rec["blocked"] |= {(int(c[0]), int(c[1])) for c in cells}
    _bump(rec["key"])


def tilemap_unblock(area, cells):
    """Open cells again."""
    rec = _AREAS.get(_norm(area))
    if rec is None:
        return
    rec["blocked"] -= {(int(c[0]), int(c[1])) for c in cells}
    _bump(rec["key"])


def tilemap_is_blocked(area, x, y):
    rec = _AREAS.get(_norm(area))
    return bool(rec) and (int(x), int(y)) in rec["blocked"]


def tilemap_set_tile(area, x, y, kind):
    """Change a tile: a door drawn open, rubble cleared."""
    rec = _AREAS.get(_norm(area))
    if rec is None or not (0 <= x < rec["w"] and 0 <= y < rec["h"]):
        return False
    rec["tiles"][y][x] = _norm(kind) if kind else None
    _bump(rec["key"])
    return True


def _body_key(rec):
    """The sprite whose GROUND an actor stands on: its own, or the mirrored twin a still
    prop is drawn with on this cell (see ``tilemap_sprite_look``)."""
    key = rec["sprite"]
    if key and rec.get("fixed"):
        twin = tilemap_sprite_twin(key)
        if twin and _cell_hash(rec["x"], rec["y"]) % 2:
            return twin
    return key


def _covers(a, x, y):
    """Whether an actor record covers a cell: its own, or one under its sprite's base."""
    dx, dy = x - a["x"], y - a["y"]
    return (dx == 0 and dy == 0) or (dx, dy) in tilemap_sprite_cells(_body_key(a))


def _blocking_actor_at(area, x, y, ignore=None):
    for aid, a in _ACTORS.items():
        if aid != ignore and a["blocks"] and a["area"] == area and _covers(a, x, y):
            return True
    return False


def tilemap_is_open(area, x, y, ignore=None):
    """Whether a cell can be walked: on the map, a walkable tile, not blocked, and no
    blocking actor (a boulder, a sentry holding a door) standing there."""
    area = _norm(area)
    rec = _AREAS.get(area)
    if rec is None or not (0 <= x < rec["w"] and 0 <= y < rec["h"]):
        return False
    spec = _kind_spec(rec, rec["tiles"][y][x])
    if spec is None or not spec["walk"]:
        return False
    if (x, y) in rec["blocked"]:
        return False
    return not _blocking_actor_at(area, x, y, ignore)


def _see_through(rec, x, y):
    if not (0 <= x < rec["w"] and 0 <= y < rec["h"]):
        return False
    spec = _kind_spec(rec, rec["tiles"][y][x])
    return bool(spec and spec["see"])


def tilemap_path(area, start, goal, ignore=None):
    """The cells from ``start`` to ``goal`` (after start), four-connected.

    When the goal cannot be reached the path ends at the reachable cell nearest it. Empty
    when already there or boxed in; None for an unknown area.
    """
    area = _norm(area)
    rec = _AREAS.get(area)
    if rec is None:
        return None
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
            if nxt in prev or not tilemap_is_open(area, nxt[0], nxt[1], ignore):
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


# --- actors --------------------------------------------------------------------------

def tilemap_place(agent, area, x=None, y=None, sprite=None, color=None, party=None,
                  blocks=None, speed=None, exits=None, fixed=None):
    """Put an actor on a cell - or move it there, from anywhere.

    Args:
        agent: who (any agent id).
        area (str): the area.
        x, y (optional): the cell. Defaults to the area's entry.
        sprite (str, optional): the atlas key it is drawn with.
        color (str, optional): a tint.
        party (bool, optional): whether it is one of the crew - party actors reveal the
            map, and only they follow exits.
        blocks (bool, optional): whether others must walk round it.
        speed (float, optional): cells per second.
        exits (bool, optional): whether stopping on an exit takes it there. Defaults to
            ``party``.
        fixed (bool, optional): a thing that does not move (a prop). It stays drawn once
            its cell has been SEEN, where something that moves is drawn only while in
            sight.

    Returns:
        The actor record, or None for an unknown area.
    """
    aid = to_id(agent)
    area = _norm(area)
    if aid is None or area not in _AREAS:
        return None
    if x is None or y is None:
        x, y = tilemap_entry(area)
    old = _ACTORS.get(aid)
    rec = old or {"sprite": None, "color": None, "party": False, "blocks": False,
                  "speed": DEFAULT_SPEED, "path": [], "next": 0.0, "intent": None,
                  "mark": None, "exits": None, "fixed": False,
                  "facing": "s", "stride": 0, "pose": None}
    from_area = rec.get("area")
    rec.update({"area": area, "x": int(x), "y": int(y), "path": [], "intent": None,
                "mark": tilemap_mark_at(area, x, y)})
    if sprite is not None:
        rec["sprite"] = sprite
    if color is not None:
        rec["color"] = color
    if party is not None:
        rec["party"] = bool(party)
    if blocks is not None:
        rec["blocks"] = bool(blocks)
    if speed is not None:
        rec["speed"] = float(speed)
    if exits is not None:
        rec["exits"] = bool(exits)
    if fixed is not None:
        rec["fixed"] = bool(fixed)
    _ACTORS[aid] = rec
    if rec["party"]:
        tilemap_reveal(area, x, y)
    if from_area and from_area != area:
        _bump(from_area)
        from .signal import signal_emit
        signal_emit("tilemap_moved", {"TILEMAP_AGENT": aid, "TILEMAP_FROM": from_area,
                                      "TILEMAP_AREA": area})
    _bump(area)
    return rec


def tilemap_remove(agent):
    """Take an actor off the map."""
    rec = _ACTORS.pop(to_id(agent), None)
    if rec is not None:
        _bump(rec["area"])
    return rec is not None


def tilemap_where(agent):
    """``(area, x, y)`` for an actor, or None."""
    rec = _ACTORS.get(to_id(agent))
    return (rec["area"], rec["x"], rec["y"]) if rec else None


def tilemap_actor(agent):
    """The actor record, or None."""
    return _ACTORS.get(to_id(agent))


def _id_order(aid):
    """Sort key for actor ids: agent ids in number order, then any NAMED actors (a map
    token that stands for something, not an agent) - mixed, a plain sort would raise."""
    return (isinstance(aid, str), aid)


def tilemap_actors(area=None):
    """Actor ids - all, or in one area - sorted."""
    area = _norm(area) if area else None
    return sorted((a for a, r in _ACTORS.items() if area is None or r["area"] == area),
                  key=_id_order)


def tilemap_actors_at(area, x, y):
    """Actors covering a cell - standing on it, or a big prop whose base reaches it."""
    area = _norm(area)
    x, y = int(x), int(y)
    return sorted((a for a, r in _ACTORS.items() if r["area"] == area and _covers(r, x, y)),
                  key=_id_order)


def tilemap_actor_cells(agent):
    """The cells an actor covers: its own, plus any its sprite's base reaches."""
    rec = _ACTORS.get(to_id(agent))
    if rec is None:
        return []
    return sorted((rec["x"] + dx, rec["y"] + dy)
                  for dx, dy in tilemap_sprite_cells(_body_key(rec)))


def tilemap_actor_distance(agent, x, y):
    """Steps (Manhattan) from a cell to the nearest cell an actor covers - so standing
    beside a car's bumper is beside the car. None for an unknown actor."""
    cells = tilemap_actor_cells(agent)
    if not cells:
        return None
    return min(abs(cx - int(x)) + abs(cy - int(y)) for cx, cy in cells)


def tilemap_actors_near(agent, reach=1):
    """Actors within ``reach`` steps (Manhattan) of this one, in its area - measured to
    the nearest cell each covers, so a big prop is near from any side."""
    me = _ACTORS.get(to_id(agent))
    if me is None:
        return []
    return sorted((a for a, r in _ACTORS.items()
                   if a != to_id(agent) and r["area"] == me["area"]
                   and min(abs(r["x"] + dx - me["x"]) + abs(r["y"] + dy - me["y"])
                           for dx, dy in tilemap_sprite_cells(_body_key(r))) <= reach),
                  key=_id_order)


def _facing(dx, dy):
    """The compass word for a step: the larger axis wins, ties go to north/south - a
    figure seen from the 3/4 view reads best facing the camera or away from it."""
    if dx == 0 and dy == 0:
        return None
    if abs(dx) > abs(dy):
        return "e" if dx > 0 else "w"
    return "s" if dy > 0 else "n"


def tilemap_face(agent, x, y):
    """Turn an actor toward a cell - someone it is talking to, or shooting at. The
    view draws the facing when the sprite has one (``<sprite>_<n|e|s|w>...``)."""
    rec = _ACTORS.get(to_id(agent))
    if rec is None:
        return False
    face = _facing(int(x) - rec["x"], int(y) - rec["y"])
    if face and face != rec.get("facing"):
        rec["facing"] = face
        _bump(rec["area"])
    return True


def tilemap_set_pose(agent, pose=None):
    """A pose the sprite set may draw instead of standing - ``"down"`` for a crew
    member at 0 HP (``<sprite>_down``). ``None`` stands it back up."""
    rec = _ACTORS.get(to_id(agent))
    if rec is None:
        return False
    if rec.get("pose") != pose:
        rec["pose"] = pose
        _bump(rec["area"])
    return True


def tilemap_sprite_look(rec):
    """The atlas key an actor is drawn with right now.

    A sprite names a BASE key; an art set may add looks named after it, and the first
    one that is registered wins::

        <base>_down                         when the pose is "down"
        <base>_<facing>_<idle|a|b>          a facing and a stride frame
        <base>_<facing>                     a facing
        <base>                              the one look everything has

    So a plain one-cell sprite draws exactly as it always did, and a set that only has
    some of the looks falls back cell by cell rather than showing nothing. A prop that
    stands still (``fixed``) and has a mirrored twin (``"mirror": true``) is drawn as the
    twin on about half the cells - the same cells every time.
    """
    base = rec.get("sprite")
    if not base:
        return None
    if "x" in rec:
        base = _body_key(rec)
    from .gui.image import ImageAtlas
    have = ImageAtlas.all
    if rec.get("pose"):
        key = f"{base}_{rec['pose']}"
        if key in have:
            return key
    facing = rec.get("facing") or "s"
    frame = ("idle", "a", "b")[rec.get("stride") or 0]
    for key in (f"{base}_{facing}_{frame}", f"{base}_{facing}"):
        if key in have:
            return key
    return base


def tilemap_set_sprite(agent, sprite=None, color=None):
    rec = _ACTORS.get(to_id(agent))
    if rec is None:
        return False
    if sprite is not None:
        rec["sprite"] = sprite
    if color is not None:
        rec["color"] = color
    _bump(rec["area"])
    return True


def tilemap_walk(agent, x, y, intent=None):
    """Send an actor walking to a cell. Returns the path length, or -1 if it cannot.

    ``intent`` is a callable ``fn(agent)`` run when the walk ENDS at the goal - walking up
    to a door in order to open it. Emits ``tilemap_blocked`` (and still walks as close as
    it can) when the goal is out of reach.
    """
    aid = to_id(agent)
    rec = _ACTORS.get(aid)
    if rec is None:
        return -1
    path = tilemap_path(rec["area"], (rec["x"], rec["y"]), (x, y), ignore=aid)
    if path is None:
        return -1
    reached = (not path and (rec["x"], rec["y"]) == (int(x), int(y))) or \
              (path and path[-1] == (int(x), int(y)))
    rec["path"] = list(path)
    rec["intent"] = intent if reached else None
    rec["goal"] = (int(x), int(y))
    if rec["next"] < _now():
        rec["next"] = _now()
    if not reached:
        from .signal import signal_emit
        signal_emit("tilemap_blocked", {"TILEMAP_AGENT": aid, "TILEMAP_AREA": rec["area"],
                                        "TILEMAP_X": int(x), "TILEMAP_Y": int(y)})
    if not path:
        _arrive(aid, rec)
    tilemap_watch()
    return len(path)


def tilemap_stop(agent):
    rec = _ACTORS.get(to_id(agent))
    if rec is not None:
        rec["path"] = []
        rec["intent"] = None
        if rec.get("stride"):
            rec["stride"] = 0              # standing still again
            _bump(rec["area"])


def tilemap_walking(agent):
    rec = _ACTORS.get(to_id(agent))
    return bool(rec and rec["path"])


def _step(aid, rec):
    """One cell along the path. False when the way ahead has closed."""
    nx, ny = rec["path"][0]
    if not tilemap_is_open(rec["area"], nx, ny, ignore=aid):
        # Something closed the way since the path was found - try again round it.
        goal = rec.get("goal")
        path = tilemap_path(rec["area"], (rec["x"], rec["y"]), goal, ignore=aid) \
            if goal else []
        if not path or not tilemap_is_open(rec["area"], path[0][0], path[0][1], ignore=aid):
            rec["path"] = []
            rec["intent"] = None
            from .signal import signal_emit
            signal_emit("tilemap_blocked", {"TILEMAP_AGENT": aid,
                                            "TILEMAP_AREA": rec["area"],
                                            "TILEMAP_X": nx, "TILEMAP_Y": ny})
            return False
        rec["path"] = path
        nx, ny = path[0]
    rec["path"].pop(0)
    # Which way it is walking, and which foot: the view draws both when the sprite set
    # has them. The stride alternates per STEP, so it animates at walking pace with no
    # repaint of its own.
    rec["facing"] = _facing(nx - rec["x"], ny - rec["y"]) or rec.get("facing") or "s"
    rec["stride"] = 2 if rec.get("stride") == 1 else 1
    rec["x"], rec["y"] = nx, ny
    if rec["party"]:
        tilemap_reveal(rec["area"], nx, ny)
    mark = tilemap_mark_at(rec["area"], nx, ny)
    if mark and mark != rec["mark"]:
        from .signal import signal_emit
        signal_emit("tilemap_entered", {"TILEMAP_AGENT": aid, "TILEMAP_AREA": rec["area"],
                                        "TILEMAP_MARK": mark, "TILEMAP_X": nx,
                                        "TILEMAP_Y": ny})
    rec["mark"] = mark
    return True


def _arrive(aid, rec):
    from .signal import signal_emit
    rec["stride"] = 0                      # standing: the idle frame
    area = rec["area"]
    signal_emit("tilemap_arrived", {"TILEMAP_AGENT": aid, "TILEMAP_AREA": area,
                                    "TILEMAP_X": rec["x"], "TILEMAP_Y": rec["y"]})
    follows = rec["exits"] if rec["exits"] is not None else rec["party"]
    mark = tilemap_mark_at(area, rec["x"], rec["y"])
    if follows and mark and tilemap_exit_target(area, mark)[0]:
        tilemap_exit_follow(aid, mark)
        return
    intent, rec["intent"] = rec["intent"], None
    if intent is not None:
        try:
            intent(aid)
        except Exception as e:                           # noqa: BLE001
            from .execution import log
            log(f"arrival intent failed: {e}", "tilemap", "warning")


def tilemap_tick(t=None):
    """Advance every walking actor. Registered by :func:`tilemap_watch`.

    Each actor steps when its own clock comes due, so a fast one and a slow one walk
    side by side. Guarded per actor: a bad one is dropped from its walk rather than
    raising out of the tick, which would pause the whole mission.
    """
    now = _now()
    touched = set()
    for aid, rec in list(_ACTORS.items()):
        if not rec["path"]:
            continue
        try:
            steps = 0
            while rec["path"] and rec["next"] <= now and steps < 4:
                if not _step(aid, rec):
                    break
                rec["next"] += 1.0 / max(0.1, rec["speed"])
                steps += 1
                touched.add(rec["area"])
                if not rec["path"]:
                    _arrive(aid, rec)
            if rec["next"] < now - 1.0:
                rec["next"] = now                        # do not bank a pause
        except Exception as e:                           # noqa: BLE001
            rec["path"] = []
            from .execution import log
            log(f"tile actor {aid} stopped: {e}", "tilemap", "warning")
    for area in touched:
        _bump(area)


def tilemap_watch(seconds=0.1):
    """Start walking actors. Idempotent. Returns the tick task."""
    from ..tickdispatcher import TickDispatcher
    if _WATCH["task"] is not None:
        return _WATCH["task"]
    _WATCH["task"] = TickDispatcher.do_interval(tilemap_tick, seconds)
    return _WATCH["task"]


def tilemap_unwatch():
    task, _WATCH["task"] = _WATCH["task"], None
    if task is not None:
        try:
            task.stop()
        except Exception:                                # noqa: BLE001
            pass


# --- exits ---------------------------------------------------------------------------

def tilemap_exit_target(area, mark):
    """Where an exit mark leads: ``(area, arrive mark or (x, y) or None)``.

    The area's ``exits:`` table first; a mark called ``to_<area>`` needs no entry.
    """
    rec = _AREAS.get(_norm(area))
    mark = _norm(mark)
    if rec is None:
        return None, None
    spec = rec["exits"].get(mark)
    if spec:
        target, _, where = spec.partition(" ")
        where = where.strip()
        if where.startswith("@"):
            return _norm(target), _norm(where[1:])
        return _norm(target), _xy(where) if where else None
    if mark.startswith("to_") and mark[3:] in _AREAS:
        return mark[3:], None
    return None, None


def _arrival_cell(area, came_from, where=None):
    """Where somebody walking in stands: beside the way back, never ON it - arriving on
    an exit would send them straight back out."""
    rec = _AREAS[area]
    if isinstance(where, tuple):
        return where
    cells = set()
    if where:
        cells = set(rec["marks"].get(where, set()))
    if not cells:
        for mark in rec["marks"]:
            if tilemap_exit_target(area, mark)[0] == came_from:
                cells = set(rec["marks"][mark])
                break
    if not cells:
        return tilemap_entry(area)
    exits = {c for m in rec["marks"] if tilemap_exit_target(area, m)[0]
             for c in rec["marks"][m]}
    seen = set(cells)
    q = deque(sorted(cells))
    while q:
        x, y = q.popleft()
        for nxt in ((x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)):
            if nxt in seen:
                continue
            seen.add(nxt)
            if tilemap_is_open(area, *nxt):
                if nxt not in exits:
                    return nxt
                q.append(nxt)
    return tilemap_entry(area)


def tilemap_exit_follow(agent, mark):
    """Take an actor through an exit mark in its area. True when it moved."""
    rec = _ACTORS.get(to_id(agent))
    if rec is None:
        return False
    target, where = tilemap_exit_target(rec["area"], mark)
    if target is None or target not in _AREAS:
        return False
    cell = _arrival_cell(target, rec["area"], where)
    # Somewhere a crew member has walked into is somewhere the party knows about.
    if rec["party"] and not _AREAS[target]["known"]:
        tilemap_reveal_area(target)
    return tilemap_place(agent, target, cell[0], cell[1]) is not None


# --- fog -----------------------------------------------------------------------------

def _line(x0, y0, x1, y1):
    """Bresenham cells from (x0, y0) to (x1, y1), both ends included."""
    cells = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        cells.append((x0, y0))
        if (x0, y0) == (x1, y1):
            return cells
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def tilemap_sees(area, x0, y0, x1, y1):
    """Whether (x1, y1) can be seen from (x0, y0): every cell BETWEEN them lets sight
    through. The far cell itself need not - you can see a wall."""
    rec = _AREAS.get(_norm(area))
    if rec is None:
        return False
    for cx, cy in _line(x0, y0, x1, y1)[1:-1]:
        if not _see_through(rec, cx, cy):
            return False
    return True


def _visible_from(rec, x, y, radius):
    out = set()
    for cy in range(max(0, y - radius), min(rec["h"], y + radius + 1)):
        for cx in range(max(0, x - radius), min(rec["w"], x + radius + 1)):
            if (cx - x) ** 2 + (cy - y) ** 2 > radius * radius:
                continue
            if tilemap_sees(rec["key"], x, y, cx, cy):
                out.add((cx, cy))
    return out


def tilemap_reveal(area, x, y, radius=None):
    """Mark what can be seen from a cell as explored."""
    rec = _AREAS.get(_norm(area))
    if rec is None:
        return set()
    seen = _visible_from(rec, int(x), int(y), SIGHT if radius is None else radius)
    rec["explored"] |= seen
    return seen


def tilemap_reveal_all(area):
    """The whole area is known (a map found, an orbital survey)."""
    rec = _AREAS.get(_norm(area))
    if rec is None:
        return
    rec["explored"] |= {(x, y) for y in range(rec["h"]) for x in range(rec["w"])}
    _bump(rec["key"])


def tilemap_explored(area, x, y):
    rec = _AREAS.get(_norm(area))
    return bool(rec) and (int(x), int(y)) in rec["explored"]


def tilemap_visible(area):
    """The cells some party actor in this area can see RIGHT NOW."""
    area = _norm(area)
    rec = _AREAS.get(area)
    if rec is None:
        return set()
    out = set()
    for a in _ACTORS.values():
        if a["party"] and a["area"] == area:
            out |= _visible_from(rec, a["x"], a["y"], SIGHT)
    return out


# --- reset ---------------------------------------------------------------------------

def tilemap_clear():
    """The per-mission reset: no areas, no actors, no walks, no listeners."""
    tilemap_unwatch()
    _AREAS.clear()
    _ACTORS.clear()
    _REV.clear()
    _LISTENERS.clear()
    _CLOCK["now"] = None


def tilemap_clear_tilesets():
    """Tilesets too. Separate: a tileset is usually declared once, by an addon."""
    _TILESETS.clear()


def tilemap_count():
    """Reset-ledger probe: areas plus actors still held."""
    return len(_AREAS) + len(_ACTORS)
