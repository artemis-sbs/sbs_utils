"""Ship interiors as ASCII floor plans, read and written.

A 4-cell cargo hold is four JSON objects that happen to share a name and happen to be
adjacent. In ASCII it is ``cccc``. That is the whole idea: the structure an author thinks
in becomes the thing they type, and the shape of the ship becomes legible instead of being
3171 coordinate entries.

FORMAT::

    ship: tsn_light_cruiser
    layout: default
    size: 10x17
    damcons: 3  3,2  1,4  5,4           # optional: team COUNT and where they stand
    theme: cosmos                       # optional
    legend:
      q: crew-quarters                  # roles come from the room registry
      p: plunder-hold / room,bay,cargo  # a new room type declares its own
    ---
       .qqqq.
      .qq..qq.

Everything after the ``---`` is the map, taken verbatim, row 0 first (bow):

===== ==========================================================================
``' '`` off-hull - not a cell, and nothing can be painted there
``'.'`` open cell with no object: a hallway. Reserved, as in the tile map.
other   a legend character
===== ==========================================================================

The author never types the hull outline - it is generated pre-filled from the engine's
own hull map (see ``cosmos_dev.mock.hull_capture``), so a room CANNOT be placed off-hull.
That was the most common defect in the shipped data; here it is an unrepresentable state
rather than a validator complaint.

DELIBERATE OMISSIONS, each with a reason recorded in ``GRID_ASCII_FORMAT.md``:

* **No mirroring.** Every hull is left-right symmetric but the ROOMS are not - a half-map
  mirror corrupts 16.9% of the shipped cells, deleting `tsn_light_cruiser`'s saloon and
  turning one `beam-starboard` into a second `beam-port`, which changes what the ship can
  survive. Mirror is a tool operation an author reviews, never a load-time feature.
* **No scale.** Icons are center-anchored on a grid node, so scaling grows an icon about
  its own node instead of filling a block - it could never express room extent. Scale is
  per-icon emphasis and belongs to the theme.
* **No roles, normally.** Name -> roles is a function across the corpus (60 names, one
  exception, and that one is two authoring mistakes), so roles live in the registry and
  the legend only overrides.
* **Damcons are a HEADER key, not a map character.** A team's post coexists with whatever
  occupies its cell, and the map is one character per cell - so a post character would
  have to delete a room to make space, which on a hallway-free hull is the whole point of
  the feature. An absent ``damcons:`` declares NOTHING (not "3"), which is what keeps every
  existing floor plan on the old path. See ``GRID_ASCII_FORMAT.md`` s3.1.

Stdlib only: this parses inside Cosmos's embedded Python.
"""

from .grid_rooms import grid_room_roles, grid_room_is_known

# Reserved map characters.
OFF_HULL = " "
HALLWAY = "."

# Legend characters are chosen from the room name first, so a map stays readable; these
# are the fallback pool for collisions.
_POOL = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
         "0123456789!$%&*+=?@^~<>[]{}()/\\|;,'\"`")


class GridAsciiError(Exception):
    """The text is not a readable floor plan. Carries a line number where it can."""


def _parse_legend_line(line):
    """``q: crew-quarters`` or ``p: plunder-hold / room,bay,cargo``."""
    char, _, rest = line.partition(":")
    if not char or not rest.strip():
        return None
    name, _, roles = rest.partition("/")
    return char, name.strip(), roles.strip() or None


def grid_ascii_parse(text, ship_key=None):
    """Read a floor plan into a grid-data entry.

    Returns ``{"ship": key, "layout": name, "w": int, "h": int, "entry": {...}}`` where
    ``entry`` is exactly what ``grid_data`` holds - so it can be handed to
    ``grid_merge_mod_data`` unchanged.

    Raises GridAsciiError rather than guessing. A floor plan that quietly loses a room
    gives a ship fewer hit points than its author intended, with nothing to show for it -
    which is why an unknown map character is an error here where the tile map skips it.
    """
    if not text:
        raise GridAsciiError("empty floor plan")

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    header, legend, map_lines = {}, {}, None
    in_legend = False

    for n, raw in enumerate(lines, 1):
        if map_lines is not None:
            map_lines.append(raw)
            continue
        stripped = raw.strip()
        if stripped.startswith("---"):
            map_lines = []
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.rstrip(":").lower() == "legend" and stripped.endswith(":"):
            in_legend = True
            continue
        # A legend entry is indented under `legend:`; anything unindented ends the block.
        if in_legend and raw[:1] in (" ", "\t"):
            parsed = _parse_legend_line(stripped)
            if parsed is None:
                raise GridAsciiError(f"line {n}: cannot read legend entry {stripped!r}")
            char, name, roles = parsed
            if len(char) != 1:
                raise GridAsciiError(
                    f"line {n}: legend key {char!r} must be a single character")
            if char in (OFF_HULL, HALLWAY):
                raise GridAsciiError(
                    f"line {n}: {char!r} is reserved "
                    f"({'off-hull' if char == OFF_HULL else 'hallway'})")
            if char in legend:
                # Silently overwriting would move every cell of one room into another.
                raise GridAsciiError(
                    f"line {n}: legend key {char!r} is already "
                    f"'{legend[char][0]}'")
            legend[char] = (name, roles)
            continue
        in_legend = False
        key, _, value = stripped.partition(":")
        if value.strip():
            header[key.strip().lower()] = value.strip()

    if map_lines is None:
        raise GridAsciiError("no '---' separator, so there is no map")

    ship = ship_key or header.get("ship")
    if not ship:
        raise GridAsciiError("no 'ship:' and none supplied by the caller")

    # `size:` is authoritative: editors strip trailing whitespace, so the last cells of a
    # row routinely vanish and a width inferred from the text would be short.
    w = h = None
    if header.get("size"):
        try:
            sw, _, sh = header["size"].lower().partition("x")
            w, h = int(sw), int(sh)
        except ValueError:
            raise GridAsciiError(f"cannot read size {header['size']!r}, expected WxH")

    if h is None:
        # No declared size, so a trailing blank line is the end of the file rather than a
        # row of the ship. With a size we must NOT do this: a hull's last rows are often
        # entirely off-hull (xim_scout's bottom two, for instance), and trimming them
        # would silently shorten the grid and shift nothing else - a ship one row short.
        while map_lines and not map_lines[-1].strip():
            map_lines.pop()
        h = len(map_lines)
    else:
        while len(map_lines) > h and not map_lines[-1].strip():
            map_lines.pop()
        map_lines += [""] * (h - len(map_lines))     # pad blank tail rows back
    if w is None:
        w = max((len(r) for r in map_lines), default=0)
    if h != len(map_lines):
        raise GridAsciiError(
            f"size says {h} rows but the map has {len(map_lines)}")

    objects = []
    for y, row in enumerate(map_lines):
        row = row.ljust(w)
        if len(row) > w:
            raise GridAsciiError(f"map row {y} is {len(row)} wide, size says {w}")
        for x, ch in enumerate(row[:w]):
            if ch in (OFF_HULL, HALLWAY):
                continue
            if ch not in legend:
                raise GridAsciiError(
                    f"map row {y} column {x}: {ch!r} is not in the legend")
            name, roles = legend[ch]
            if roles is None:
                roles = grid_room_roles(name)
                if roles is None:
                    raise GridAsciiError(
                        f"'{name}' is not a known room type, so the legend must give its "
                        f"roles: '{ch}: {name} / room,...'")
            objects.append({"x": float(x), "y": float(y), "name": name, "roles": roles})

    entry = {"grid_objects": objects}
    if header.get("theme"):
        entry["theme"] = header["theme"]
    damcons = grid_ascii_parse_damcons(header.get("damcons"))
    if damcons is not None:
        entry["damcons"] = damcons
    return {"ship": ship, "layout": header.get("layout", "default"),
            "w": w, "h": h, "entry": entry}


def grid_ascii_parse_damcons(text):
    """Read a ``damcons:`` header value into ``{"count": int, "posts": [[x, y], ...]}``.

    ``None`` for an absent header, which is what keeps every existing floor plan on the
    old path: no declaration means "three teams, wherever the engine puts them".

    A damcon post COEXISTS with whatever occupies its cell, and the map is one character
    per cell - so a post cannot be a map character without deleting a room to make room
    for it, which is exactly the state issue #381 exists to support. Hence a header key.

    Whitespace-separated tokens, one rule covering both facts a hull needs to state::

        damcons: 3                  # three teams, engine-placed (today, written down)
        damcons: 5                  # five teams, engine-placed
        damcons: 3,2  1,4  5,4      # three posts -> count 3
        damcons: 5  3,2  1,4        # five teams; DC1/DC2 posted, the rest engine-placed

    More posts than the stated count raises the count: declaring four posts and asking for
    three is a typo whose only sane reading is four.
    """
    if text is None:
        return None
    count = None
    posts = []
    for token in str(text).split():
        if "," in token:
            sx, _, sy = token.partition(",")
            try:
                posts.append([int(sx), int(sy)])
            except ValueError:
                raise GridAsciiError(
                    f"cannot read damcon post {token!r}, expected X,Y")
        else:
            try:
                count = int(token)
            except ValueError:
                raise GridAsciiError(
                    f"cannot read damcon count {token!r}, expected a number or X,Y")
    if count is None:
        count = len(posts)
    count = max(count, len(posts))
    if count < 0:
        raise GridAsciiError(f"damcon count {count} is negative")
    return {"count": count, "posts": posts}


def grid_ascii_render_damcons(damcons):
    """The canonical ``damcons:`` header value, or ``None`` when there is nothing to say.

    Count first, then posts in team order, so a re-render diffs clean.
    """
    damcons = grid_normalize_damcons(damcons)
    if damcons is None:
        return None
    parts = [str(damcons["count"])]
    parts += [f"{int(x)},{int(y)}" for x, y in damcons["posts"]]
    return "  ".join(parts)


def grid_normalize_damcons(damcons):
    """Accept the short forms a JSON author will write; return the canonical dict.

    ``5`` -> ``{"count": 5, "posts": []}``; ``[[3,2],[1,4]]`` ->
    ``{"count": 2, "posts": [[3,2],[1,4]]}``. ``None`` stays ``None``, which is the
    sentinel for "this hull declares nothing".
    """
    if damcons is None:
        return None
    if isinstance(damcons, bool):
        return None
    if isinstance(damcons, int):
        return {"count": max(0, damcons), "posts": []}
    if isinstance(damcons, (list, tuple)):
        posts = [[int(p[0]), int(p[1])] for p in damcons]
        return {"count": len(posts), "posts": posts}
    if isinstance(damcons, dict):
        posts = [[int(p[0]), int(p[1])] for p in damcons.get("posts", [])]
        count = damcons.get("count")
        count = len(posts) if count is None else max(0, int(count))
        return {"count": max(count, len(posts)), "posts": posts}
    return None


# Characters a human reading a floor plan can mistake for each other. Two rooms must
# never take characters from the same group: this is a format people EDIT, and a misread
# character does not look wrong - it silently puts a room in the wrong damage pool.
_CONFUSABLE = ("Il1|", "O0o", "S5", "Z2", "B8", "G6", "q9g", "vy", "cC", "uv", "nm")


def _confusable_group(ch):
    for group in _CONFUSABLE:
        if ch in group:
            return group
    return None


def _assign_chars(names):
    """A stable character per room name, preferring letters from the name itself.

    Deterministic for a given sorted name list, so a re-render produces the same file and
    a diff shows only what actually changed.
    """
    taken, out = set(), {}
    blocked = set()                 # confusable with something already taken
    for name in names:              # caller sorts, so this is deterministic
        for candidate in list(name) + list(name.upper()) + list(_POOL):
            if not candidate.isprintable() or candidate in (OFF_HULL, HALLWAY):
                continue
            if candidate in taken or candidate in blocked:
                continue
            taken.add(candidate)
            group = _confusable_group(candidate)
            if group:
                blocked.update(group)
            out[name] = candidate
            break
        else:
            raise GridAsciiError(f"ran out of legend characters at '{name}'")
    return out


def grid_ascii_render(ship_key, objects, w, h, layout="default", theme=None,
                      open_cells=None, damcons=None):
    """Write a floor plan.

    ``open_cells`` is the hull shape (rows of booleans, row 0 first) - from the engine
    capture, so the author gets the real outline to paint inside. Without it every
    non-room cell is drawn as hallway, which is honest but loses the silhouette.

    ``damcons`` is the team declaration (see :func:`grid_ascii_parse_damcons`). ``None``
    writes no header at all rather than writing today's default out explicitly - a plan
    that declares nothing must round-trip to an entry with no ``damcons`` key, which is
    what keeps the shipped floor plans and every third-party hull on the old path.
    """
    by_cell = {}
    for o in objects:
        by_cell[(int(o["x"]), int(o["y"]))] = o

    names = sorted({o["name"] for o in objects})
    chars = _assign_chars(names)

    # Only spell out roles that differ from what the registry already says - repeating
    # them is redundancy that can drift.
    legend_lines = []
    for name in names:
        roles = None
        for o in objects:
            if o["name"] == name:
                roles = o["roles"]
                break
        known = grid_room_roles(name)
        norm = lambda r: ",".join(t.strip().lower() for t in r.split(","))
        if known is not None and norm(known) == norm(roles):
            legend_lines.append(f"  {chars[name]}: {name}")
        else:
            legend_lines.append(f"  {chars[name]}: {name} / {roles}")

    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            o = by_cell.get((x, y))
            if o is not None:
                row.append(chars[o["name"]])
            elif open_cells is not None and not open_cells[y][x]:
                row.append(OFF_HULL)
            else:
                row.append(HALLWAY)
        rows.append("".join(row).rstrip() or OFF_HULL)

    head = [f"ship: {ship_key}", f"layout: {layout}", f"size: {w}x{h}"]
    dc_text = grid_ascii_render_damcons(damcons)
    if dc_text is not None:
        head.append(f"damcons: {dc_text}")
    if theme:
        head.append(f"theme: {theme}")
    head.append("legend:")
    return "\n".join(head + legend_lines + ["---"] + rows) + "\n"


# --- validation -------------------------------------------------------------------
#
# Levels. "error" means the layout is wrong and would misbehave; "warn" means it is
# probably a mistake; "hint" means it is unusual and might be deliberate. The split
# matters: port/starboard asymmetry is NORMAL in the shipped data (17% of rooms have no
# counterpart), so flagging it as an error would bury an author in false positives.

def _validate_damcons(damcons, w, h, open_cells):
    """Findings for the ``damcons:`` declaration.

    A bad coordinate must be an AUTHORING-time failure, because at runtime the only sane
    response is to log it and let the engine pick a cell instead - one typo can never be
    allowed to leave a ship with no damage control.
    """
    damcons = grid_normalize_damcons(damcons)
    if damcons is None:
        return []
    out = []
    seen = set()
    for i, (x, y) in enumerate(damcons["posts"]):
        who = f"damcon post DC{i + 1}"
        if not (0 <= x < w and 0 <= y < h):
            out.append(("error", f"{who} at {x},{y} is outside the {w}x{h} grid"))
            continue
        if open_cells is not None and 0 <= y < len(open_cells) and 0 <= x < len(open_cells[y]):
            if not open_cells[y][x]:
                out.append(("error", f"{who} at {x},{y} is outside the hull"))
                continue
        if (x, y) in seen:
            # They stack, and so do their rally markers - one team is what the engineering
            # display then shows.
            out.append(("warn", f"{who} shares cell {x},{y} with an earlier team"))
        seen.add((x, y))
    if damcons["count"] == 0:
        out.append(("warn", "0 damcon teams - this ship can never repair itself"))
    elif damcons["count"] > 6:
        out.append(("hint", f"{damcons['count']} damcon teams is a lot for one grid"))
    return out


def grid_ascii_validate(objects, w, h, open_cells=None, ship_data=None, damcons=None):
    """Check a layout. Returns a list of ``(level, message)``.

    Args:
        objects (list): grid object dicts, as parsed.
        w, h (int): grid dimensions.
        open_cells (list, optional): hull shape, rows of booleans, row 0 first.
        ship_data (dict, optional): the shipData entry, for the weapon-count checks.
        damcons (dict, optional): the team declaration, as parsed.
    """
    out = []
    out += _validate_damcons(damcons, w, h, open_cells)
    cells = {}
    for o in objects:
        x, y = int(o["x"]), int(o["y"])
        if not (0 <= x < w and 0 <= y < h):
            out.append(("error", f"'{o['name']}' at {x},{y} is outside the {w}x{h} grid"))
            continue
        if (x, y) in cells:
            out.append(("warn", f"{x},{y} holds both '{cells[(x, y)]}' and '{o['name']}'"))
        cells[(x, y)] = o["name"]

    # Off-hull. Should be impossible to author now that the outline is pre-filled, but a
    # hand-edited file or a shipData resize can still produce it.
    if open_cells is not None:
        for (x, y), name in sorted(cells.items()):
            if 0 <= y < len(open_cells) and 0 <= x < len(open_cells[y]):
                if not open_cells[y][x]:
                    out.append(("error", f"'{name}' at {x},{y} is outside the hull"))

        total_open = sum(1 for row in open_cells for c in row if c)
        if total_open:
            fill = len(cells) / total_open
            # Measured against the ENGINE hull the shipped ships run 54-100%, median 74%.
            # (An earlier 38-75% came from the art-derived approximation's larger open-cell
            # count and was simply wrong - see GRID_REFERENCE.md s5.) So a densely packed
            # ship is NORMAL and must not be warned about.
            #
            # Only the extreme is worth a word: at 100% there is no hallway at all, and an
            # empty cell is what turns a hit into a fire instead of system damage - so a
            # fully packed ship has no soak. tsn_fighter ships that way deliberately, which
            # is why this is a hint rather than a warning.
            if fill >= 1.0:
                out.append(("hint", "every open cell is a room - with no hallway, every "
                                    "hit lands on a system instead of starting a fire"))
            elif fill < 0.50:
                out.append(("hint", f"only {fill:.0%} of the hull is rooms "
                                    "(the shipped ships run 54-100%, median 74%)"))

    # Roles: unknown room types, and known ones being redefined. Reported once per NAME,
    # not per cell - an 8-cell plunder hold is one fact about the layout, and repeating it
    # eight times buries the findings that matter.
    seen = set()
    for o in objects:
        name = o["name"]
        if name in seen:
            continue
        seen.add(name)
        known = grid_room_roles(name)
        if known is None:
            out.append(("hint", f"'{name}' is a new room type; its roles come from the "
                                "legend"))
        else:
            norm = lambda r: {t.strip().lower() for t in r.split(",")}
            if norm(known) != norm(o["roles"]):
                out.append(("hint", f"'{name}' normally means '{known}' but here it is "
                                    f"'{o['roles']}' - deliberate?"))

    # Symmetry: a HINT, never an error. 17% of shipped rooms have no counterpart.
    lonely = sorted({name for (x, y), name in cells.items()
                     if cells.get((w - 1 - x, y)) != name})
    if lonely:
        out.append(("hint", f"{len(lonely)} room type(s) have cells with no port/starboard "
                            f"counterpart: {', '.join(lonely[:6])}"
                            f"{'...' if len(lonely) > 6 else ''}"))

    # System node counts against what the ship actually carries.
    if ship_data:
        def count(role):
            return sum(1 for o in objects
                       if role in {t.strip().lower() for t in o["roles"].split(",")})
        beams = 0
        for pname, plist in (ship_data.get("hull_port_sets") or {}).items():
            if isinstance(pname, str) and pname.startswith("beam") and isinstance(plist, list):
                beams += len(plist)
        if beams and count("beam") != beams:
            out.append(("warn", f"{count('beam')} beam node(s) but shipData gives the hull "
                                f"{beams} beam port(s)"))
        tubes = ship_data.get("tubecount")
        if tubes and count("torpedo") != tubes:
            out.append(("warn", f"{count('torpedo')} torpedo node(s) but shipData gives "
                                f"tubecount {tubes}"))
        for role in ("sensor", "impulse", "maneuver"):
            if not count(role):
                out.append(("warn", f"no '{role}' node - that system can never be damaged, "
                                    "and its damage coefficient stays at full"))
        if not count("shield"):
            out.append(("hint", "no shield nodes"))
        else:
            for facing in ("fwd", "aft"):
                n = sum(1 for o in objects
                        if {"shield", facing} <= {t.strip().lower()
                                                  for t in o["roles"].split(",")})
                if not n:
                    out.append(("warn", f"no '{facing}' shield node, so that facing's "
                                        "damage coefficient never moves"))
    return out
