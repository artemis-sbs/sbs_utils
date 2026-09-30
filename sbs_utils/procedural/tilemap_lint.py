"""Lint for tile worlds: area files (``.tiles``), tileset files (``.tileset``), and the
places a mission's AMD puts things on them.

``tilemap_load`` skips an area it cannot read and says so once, in a log nobody is
watching, and a prop whose ``Mark:`` is not on the map is simply never placed. So the
mistakes that cost a debug loop are the quiet ones: a grid character the legend lacks,
a kind the tileset never declared, an exit into an area that does not exist, a hostile
standing in rock with a patrol through a cliff, a hand-counted ``At:`` one column off.
This is what makes them loud - in ``sbs lint`` and, through the language server, as
squiggles while you type.

Walkability comes from a ``.tileset`` file (``tilemap_tileset_parse``). A mission that
still declares its tileset in Python gets every check that does not need it and no claim
about what can be walked.

Nothing here touches the tile world's module state: a lint of one mission must not load
areas into the runtime of another. Stdlib only.
"""
import glob
import os
import re

from .amd_lint import AmdFinding, ERROR, WARNING
from .tilemap import TilemapError, tilemap_parse, tilemap_tileset_parse, _norm, _xy

#: How many unknown grid characters one file reports before it stops counting.
_MAX_BAD_CELLS = 20

#: AMD archetypes that stand on a tile area.
_PLACED = ("prop", "hostile")


def _lines(text):
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _error_line(e):
    m = re.search(r"line (\d+)", str(e))
    return int(m.group(1)) if m else 1


def _at(line, severity, code, message, col=None, end_col=None):
    return AmdFinding(line, severity, code, message, col=col, end_line=line,
                      end_col=end_col if end_col is not None else
                      (col + 1 if col is not None else None))


# --- reading an area the way the parser does, but keeping line numbers --------------

def _scan(text):
    """Where the pieces of an area file are: header keys, legend entries and exits by
    line, the ``---`` line, and the map rows as the parser will see them."""
    out = {"header": {}, "legend": {}, "dupes": [], "exits": {}, "sep": None, "rows": []}
    block = None
    for n, raw in enumerate(_lines(text), 1):
        if out["sep"] is not None:
            out["rows"].append((n, raw))
            continue
        s = raw.strip()
        if s.startswith("---"):
            out["sep"] = n
            continue
        if not s or raw.startswith("#"):
            continue
        if raw[:1] not in (" ", "\t"):
            key, _, value = s.partition(":")
            key = key.strip().lower()
            if key in ("legend", "exits") and not value.strip():
                block = key
                continue
            block = None
            out["header"][key] = (n, raw)
            continue
        if block == "legend":
            ch = s[:1]
            if ch in out["legend"]:
                out["dupes"].append((ch, n, raw))
            out["legend"][ch] = (n, raw)
        elif block == "exits":
            out["exits"][_norm(s.partition(":")[0])] = (n, raw)
    while out["rows"] and not out["rows"][-1][1].strip():
        out["rows"].pop()
    return out


def _bad_cells(scan):
    """Every grid character the legend lacks: [(line, col, ch)]."""
    known = set(scan["legend"])
    return [(n, x, ch) for n, raw in scan["rows"] for x, ch in enumerate(raw)
            if ch != " " and ch not in known]


def _sanitized(text, scan):
    """The text with every unknown grid character blanked, so ONE typo does not hide
    every other problem in the file behind the parser's first complaint."""
    bad = {(n, x) for n, x, _ in _bad_cells(scan)}
    if not bad:
        return text
    out = []
    for n, raw in enumerate(_lines(text), 1):
        if any(b[0] == n for b in bad):
            raw = "".join(" " if (n, x) in bad else ch for x, ch in enumerate(raw))
        out.append(raw)
    return "\n".join(out)


def tilemap_area_lenient(text):
    """Parse an area even with unknown grid characters in it (they read as nothing).
    Returns the record, or None when the file cannot be read at all."""
    try:
        return tilemap_parse(_sanitized(text, _scan(text)))
    except TilemapError:
        return None


# --- the mission's tile world, read from files ---------------------------------------

def tilemap_world(root, texts=None):
    """Every tileset and area under a mission folder, parsed, for the checks that need
    more than one file (an exit into another area, a prop's ``Mark:``).

    Args:
        root (str): the mission folder.
        texts (dict, optional): ``{normcase(abspath): text}`` - open editor buffers,
            which win over what is on disk.

    Returns:
        dict: ``{"tilesets": {name: rec}, "areas": {key: rec},
        "area_paths": {key: path}}``. ``tilesets`` is None when the mission has no
        tileset FILE - it declares them in Python, so nothing can say what is walkable.
    """
    texts = texts or {}

    def read(path):
        key = os.path.normcase(os.path.abspath(path))
        if key in texts:
            return texts[key]
        try:
            from .amd import amd_read_text
            return amd_read_text(path)
        except Exception:                                # noqa: BLE001
            return None

    tilesets, areas, paths = {}, {}, {}
    ts_files = sorted(glob.glob(os.path.join(root, "**", "*.tileset"), recursive=True))
    for path in ts_files:
        try:
            rec = tilemap_tileset_parse(read(path) or "")
        except TilemapError:
            continue
        tilesets[rec["name"]] = rec
    for path in sorted(glob.glob(os.path.join(root, "**", "*.tiles"), recursive=True)):
        rec = tilemap_area_lenient(read(path) or "")
        if rec is not None:
            areas[rec["key"]] = rec
            paths[rec["key"]] = path
    return {"tilesets": tilesets if ts_files else None, "areas": areas, "area_paths": paths}


def _walk(world, rec, x, y):
    """Whether a cell can be walked: True / False, or None when nothing can say (no
    tileset file, or a kind the tileset lacks - reported on its own)."""
    if not (0 <= x < rec["w"] and 0 <= y < rec["h"]):
        return False
    kind = rec["tiles"][y][x]
    if kind is None:
        return False
    ts = (world.get("tilesets") or {}).get(rec["tileset"])
    if ts is None:
        return None
    spec = ts["kinds"].get(kind)
    return None if spec is None else bool(spec["walk"])


def _what(rec, x, y):
    kind = rec["tiles"][y][x] if 0 <= y < rec["h"] and 0 <= x < rec["w"] else None
    return kind or "nothing"


# --- a tileset file --------------------------------------------------------------------

def tilemap_lint_tileset(content):
    """Findings for one ``.tileset`` file."""
    try:
        tilemap_tileset_parse(content)
    except TilemapError as e:
        return [_at(_error_line(e), ERROR, "tileset-syntax", str(e))]
    return []


# --- an area file ----------------------------------------------------------------------

def tilemap_lint_area(content, world=None):
    """Findings for one ``.tiles`` area file.

    Args:
        content (str): the file's text.
        world (dict, optional): ``tilemap_world`` of its mission, for the checks that
            need the tileset or the other areas. Without it only the file itself is
            checked.
    """
    world = world or {"tilesets": None, "areas": {}}
    scan = _scan(content or "")
    findings = []

    bad = _bad_cells(scan)
    for n, x, ch in bad[:_MAX_BAD_CELLS]:
        findings.append(_at(n, ERROR, "tiles-unknown-char",
                            f"{ch!r} is not in the legend - the whole area will not load",
                            col=x))
    if len(bad) > _MAX_BAD_CELLS:
        findings.append(_at(bad[_MAX_BAD_CELLS][0], ERROR, "tiles-unknown-char",
                            f"... and {len(bad) - _MAX_BAD_CELLS} more characters the "
                            f"legend does not have"))
    for ch, n, raw in scan["dupes"]:
        findings.append(_at(n, WARNING, "tiles-legend-duplicate",
                            f"{ch!r} is in the legend twice - this line wins",
                            col=len(raw) - len(raw.lstrip())))
    try:
        rec = tilemap_parse(_sanitized(content or "", scan))
    except TilemapError as e:
        findings.append(_at(_error_line(e), ERROR, "tiles-syntax", str(e)))
        return findings

    tileset = world.get("tilesets")
    kinds = None
    if tileset is not None:
        ts = tileset.get(rec["tileset"])
        if ts is None:
            n, raw = scan["header"].get("tileset", (1, ""))
            findings.append(_at(n, WARNING, "tiles-unknown-tileset",
                                f"no {rec['tileset']}.tileset in this mission, so its "
                                f"kinds and what can be walked are not checked"))
        else:
            kinds = ts["kinds"]

    used = {ch for _, raw in scan["rows"] for ch in raw}
    for ch, (n, raw) in scan["legend"].items():
        kind, _, mark = raw.strip()[2:].strip().partition("@")
        kind, mark = _norm(kind), _norm(mark)
        col = raw.index(":") + 1
        while col < len(raw) and raw[col] in " \t":
            col += 1
        if kinds is not None and kind not in kinds:
            findings.append(_at(n, ERROR, "tiles-unknown-kind",
                                f"kind {kind!r} is not in {rec['tileset']}.tileset - "
                                f"it draws nothing and cannot be walked",
                                col=col, end_col=col + len(kind)))
        if mark and ch not in used:
            findings.append(_at(n, WARNING, "tiles-mark-unplaced",
                                f"mark @{mark} is never drawn on the map, so nothing "
                                f"can stand on it or be sent to it",
                                col=col, end_col=len(raw.rstrip())))

    findings += _lint_entry(rec, scan, world)
    findings += _lint_exits(rec, scan, world)
    return findings


def _lint_entry(rec, scan, world):
    entry = rec.get("entry")
    if not entry:
        return []
    n, raw = scan["header"]["entry"]
    col = raw.index(":") + 1
    while col < len(raw) and raw[col] in " \t":
        col += 1
    cells = rec["marks"].get(_norm(entry))
    if cells:
        # Arriving on an exit stands BESIDE it (tilemap_entry), so its own cells need
        # not be ground anybody stays on.
        if _norm(entry) in rec["exits"] or _norm(entry).startswith("to_"):
            return []
        cell = min(cells)
    else:
        cell = _xy(entry)
        if cell is None:
            return [_at(n, ERROR, "tiles-entry", f"entry {entry!r} is neither a mark on "
                                                 f"this map nor x, y", col=col,
                        end_col=len(raw.rstrip()))]
    walk = _walk(world, rec, *cell)
    if walk is False:
        return [_at(n, WARNING, "tiles-entry",
                    f"entry {cell[0]}, {cell[1]} is {_what(rec, *cell)} - nobody "
                    f"beamed there can move", col=col, end_col=len(raw.rstrip()))]
    return []


def _lint_exits(rec, scan, world):
    findings = []
    areas = world.get("areas") or {}
    cross = len(areas) > 1 or (areas and rec["key"] not in areas)
    for mark, (n, raw) in scan["exits"].items():
        spec = rec["exits"].get(mark, "")
        target, _, where = spec.partition(" ")
        target, where = _norm(target), where.strip()
        col = len(raw) - len(raw.lstrip())
        if mark not in rec["marks"]:
            findings.append(_at(n, WARNING, "tiles-exit",
                                f"exit {mark} is not a mark on this map", col=col,
                                end_col=col + len(mark)))
        if not cross:
            continue
        if target not in areas:
            findings.append(_at(n, WARNING, "tiles-exit",
                                f"exit {mark} leads to {target!r}, which is no area in "
                                f"this mission", col=col, end_col=len(raw.rstrip())))
        elif where.startswith("@") and _norm(where[1:]) not in areas[target]["marks"]:
            findings.append(_at(n, WARNING, "tiles-exit",
                                f"exit {mark} arrives at {where}, which is not a mark "
                                f"in {target}", col=col, end_col=len(raw.rstrip())))
    for ch, (n, raw) in scan["legend"].items():
        mark = _norm(raw.strip()[2:].partition("@")[2])
        if not mark:
            continue
        is_exit = mark in rec["exits"] or (mark.startswith("to_") and
                                           (not cross or mark[3:] in areas))
        if cross and mark.startswith("to_") and mark not in rec["exits"] \
                and mark[3:] not in areas:
            findings.append(_at(n, WARNING, "tiles-exit",
                                f"@{mark} is named like an exit, but there is no area "
                                f"{mark[3:]!r} (and no exits: line for it)",
                                col=raw.index("@"), end_col=len(raw.rstrip())))
        if is_exit and any(_walk(world, rec, x, y) is False
                           for x, y in rec["marks"].get(mark, ())):
            findings.append(_at(n, WARNING, "tiles-exit",
                                f"exit @{mark} is on ground nobody can walk onto",
                                col=raw.index("@"), end_col=len(raw.rstrip())))
    return findings


# --- where the AMD puts things -------------------------------------------------------------

def _fields(node):
    """``{label: (line, value col, value text)}`` from a node's fence, as authored."""
    out = {}
    for n, raw in node.fence_lines:
        label, colon, value = raw.partition(":")
        label = label.strip().lower()
        if not colon or not label or label in out:
            continue
        col = len(raw) - len(raw.lstrip(" \t")) + len(raw.lstrip(" \t").partition(":")[0]) + 1
        while col < len(raw) and raw[col] in " \t":
            col += 1
        out[label] = (n, col, value.strip())
    return out


def tilemap_lint_placements(content, world, doc=None):
    """Findings for where an AMD document's props, people and hostiles stand.

    Args:
        content (str): the ``.amd`` text.
        world (dict): ``tilemap_world`` of its mission. No areas, no findings.
        doc: an already parsed ``amd_core`` document of ``content``, to save a parse.
    """
    areas = (world or {}).get("areas") or {}
    if not areas:
        return []
    if doc is None:
        from .amd_core import parse
        doc = parse(content or "")
    findings = []
    for node in doc.nodes:
        if node.kind not in _PLACED:
            continue
        f = _fields(node)
        if "area" not in f:
            continue
        n, col, area = f["area"]
        rec = areas.get(_norm(area))
        if rec is None:
            findings.append(_at(n, WARNING, "tiles-unknown-area",
                                f"{node.key}: no tile area {area!r} in this mission",
                                col=col, end_col=col + len(area)))
            continue
        cell = None
        if "mark" in f:
            n, col, mark = f["mark"]
            cells = rec["marks"].get(_norm(mark))
            if not cells:
                findings.append(_at(n, WARNING, "tiles-unknown-mark",
                                    f"{node.key}: no mark {mark!r} in {rec['key']} - "
                                    f"it is never placed", col=col, end_col=col + len(mark)))
            else:
                cell = min(cells)
        elif "at" in f:
            n, col, at = f["at"]
            cell = _xy(at)
            if cell is None:
                findings.append(_at(n, WARNING, "tiles-at-not-a-cell",
                                    f"{node.key}: At: takes x, y - a mark name goes in "
                                    f"Mark: ({at!r} reads as nothing, so it is never placed)",
                                    col=col, end_col=col + len(at)))
            else:
                findings += _cell_findings(node, rec, world, cell, n, col, col + len(at),
                                           "At:")
        if "patrol" in f:
            n, col, patrol = f["patrol"]
            raw_line = dict(node.fence_lines).get(n, "")
            for chunk in patrol.replace(";", "  ").split("  "):
                pt = _xy(chunk)
                if pt is None:
                    continue
                c = raw_line.find(chunk.strip(), col)
                c = c if c >= 0 else col
                findings += _cell_findings(node, rec, world, pt, n, c,
                                           c + len(chunk.strip()), "Patrol")
        if cell is not None and "mark" in f and node.kind == "hostile":
            n, col, mark = f["mark"]
            findings += _cell_findings(node, rec, world, cell, n, col, col + len(mark),
                                       "Mark:")
    return findings


def _cell_findings(node, rec, world, cell, n, col, end_col, what):
    x, y = cell
    if not (0 <= x < rec["w"] and 0 <= y < rec["h"]):
        return [_at(n, WARNING, "tiles-off-map",
                    f"{node.key}: {what} {x}, {y} is off the map ({rec['key']} is "
                    f"{rec['w']} x {rec['h']})", col=col, end_col=end_col)]
    if rec["tiles"][y][x] is None:
        return [_at(n, WARNING, "tiles-unwalkable",
                    f"{node.key}: {what} {x}, {y} is nothing (a blank in the map)",
                    col=col, end_col=end_col)]
    # A prop may stand in anything - a wreck half in the rock. Someone who walks may not.
    if node.kind == "hostile" and _walk(world, rec, x, y) is False:
        return [_at(n, WARNING, "tiles-unwalkable",
                    f"{node.key}: {what} {x}, {y} is {_what(rec, x, y)}, which cannot be "
                    f"walked", col=col, end_col=end_col)]
    return []


# --- a whole mission -------------------------------------------------------------------------

def tilemap_lint_mission(root):
    """Every tile finding in a mission: ``[(path relative to root, finding)]``. Empty for
    a mission with no ``.tiles`` or ``.tileset`` files."""
    world = tilemap_world(root)
    out = []

    def rel(p):
        return os.path.relpath(p, root)

    from .amd import amd_read_text
    for path in sorted(glob.glob(os.path.join(root, "**", "*.tileset"), recursive=True)):
        out += [(rel(path), f) for f in tilemap_lint_tileset(amd_read_text(path))]
    tiles = sorted(glob.glob(os.path.join(root, "**", "*.tiles"), recursive=True))
    for path in tiles:
        out += [(rel(path), f) for f in tilemap_lint_area(amd_read_text(path), world)]
    if world["areas"]:
        for path in sorted(glob.glob(os.path.join(root, "**", "*.amd"), recursive=True)):
            out += [(rel(path), f)
                    for f in tilemap_lint_placements(amd_read_text(path), world)]
    return out
