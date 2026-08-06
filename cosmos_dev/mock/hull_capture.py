"""Turn an engine hull-map probe dump into the capture file the mock reads.

WHY CAPTURE INSTEAD OF DERIVE. The engine's interior shape was assumed to be derivable
from the silhouette art - alpha bounding box, split into internalmapw x internalmaph, grid
row 0 at the bottom. That rule scored 0.987 against the authored interiors and was wrong:
run against the engine's own `is_grid_point_open` it agrees only **0.790**. The engine's
hull is narrower and vertically offset from anything the art alone predicts
(`pirate_brigantine` sits three rows lower than any bbox-normalized mapping), and no
constant relates the fitted cell size to `meshscale`, `internalmapscale` or the bbox.

The 0.987 was measuring the wrong thing: whether authored rooms fall INSIDE the
silhouette. They do - but that is a weaker claim than "the grid maps onto the bbox", and
the fit contained no negative evidence, so it could not fail. See `GRID_REFERENCE.md` s2.

So the shape is RECORDED from the engine rather than recomputed. The engine is the only
thing that knows it.

HOW TO REGENERATE:

    1. Run LM_TestRange in ENGINE, map "PROBE hull map" (test_hullmap_probe).
    2. python -m cosmos_dev.mock.hull_capture LM_TestRange/hullmap_probe.txt

The output is `cosmos_dev/mock/hull_maps.json`, with each hull's open cells stored as one
string per row so a diff shows exactly which cells moved.

Nothing here runs in the engine, or in production at all - in the engine, ask
`is_grid_point_open`.
"""

import json
import os
import re


CAPTURE_FILE = os.path.join(os.path.dirname(__file__), "hull_maps.json")

_KEY = re.compile(r"^key\s+(\S+)", re.M)
_ART = re.compile(r"^artfileroot\s+(\S+)", re.M)
_HULL = re.compile(
    r"^hullmap\s+w=(\d+)\s+h=(\d+)\s+grid_scale=(\S+)\s+symmetrical_flag=(\S+)", re.M)
_ROW = re.compile(r"^\s*(\d+)\s+([#.]+)$", re.M)


def parse_probe(text):
    """Parse a probe dump into ``{ship_key: {w, h, grid_scale, symmetry, open}}``.

    Blocks the engine declined to give a hull map for are skipped rather than recorded as
    empty - an absent capture falls back to the approximation, which is the right
    behavior for "we do not know", while a recorded empty would mean "this ship has no
    interior".
    """
    out = {}
    for block in text.split("=" * 68):
        key = _KEY.search(block)
        hull = _HULL.search(block)
        if not key or not hull:
            continue
        w, h = int(hull.group(1)), int(hull.group(2))
        if w <= 0 or h <= 0:
            continue
        rows = {int(y): r for y, r in _ROW.findall(block)}
        if len(rows) != h or any(len(rows[y]) != w for y in rows):
            continue                    # truncated block - better absent than wrong
        art = _ART.search(block)
        out[key.group(1)] = {
            "art": art.group(1) if art else "",
            "w": w,
            "h": h,
            "grid_scale": float(hull.group(3)),
            "symmetry": int(float(hull.group(4))),
            "open": [rows[y] for y in range(h)],
        }
    return out


def write_capture(hulls, path=CAPTURE_FILE, source=None, merge=True):
    """Write the capture file. Existing entries are kept unless re-captured.

    `merge` matters because a probe run may cover only some hulls (a partial run, or a
    mod's ships probed separately). Dropping the rest would silently un-capture ships
    that were fine.
    """
    data = {}
    if merge and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    data.pop("#meta", None)
    data.update(hulls)
    ordered = {"#meta": {
        "what": "engine is_grid_point_open, captured - NOT derived from art",
        "why": "the art-derived rule agrees with the engine only 0.79; see GRID_REFERENCE.md s2",
        "regenerate": "run LM_TestRange map test_hullmap_probe IN ENGINE, then "
                      "python -m cosmos_dev.mock.hull_capture <hullmap_probe.txt>",
        "source": source or "",
        "hulls": len(data),
    }}
    for k in sorted(data):
        ordered[k] = data[k]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ordered, f, indent=1)
        f.write("\n")
    return len(data)


_loaded = None


def load_capture(path=CAPTURE_FILE):
    """The captured hulls, or ``{}`` when there is no capture file yet."""
    global _loaded
    if _loaded is None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                _loaded = json.load(f)
            _loaded.pop("#meta", None)
        except (OSError, ValueError):
            _loaded = {}
    return _loaded


def clear_capture_cache():
    global _loaded
    _loaded = None


def captured_cells(ship_key, w, h):
    """Open-cell rows for a captured hull, or ``None``.

    Returns ``None`` when the capture's dimensions disagree with the ones asked for -
    shipData changed since the capture, so the recorded shape is for a different grid and
    using it would be worse than falling back.
    """
    entry = load_capture().get(ship_key)
    if not entry or entry.get("w") != w or entry.get("h") != h:
        return None
    rows = entry.get("open") or []
    if len(rows) != h:
        return None
    return [[c == "#" for c in row] for row in rows]


def main(argv=None):
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    probe = argv[0]
    with open(probe, "r", encoding="utf-8") as f:
        hulls = parse_probe(f.read())
    if not hulls:
        print(f"no hull maps found in {probe} - was it run in the ENGINE? "
              "(headless the mock reports its own reconstruction, and a pre-phase-3 "
              "mock reports w=0)")
        return 1
    out = argv[1] if len(argv) > 1 else CAPTURE_FILE
    total = write_capture(hulls, out, source=os.path.basename(probe))
    print(f"captured {len(hulls)} hull(s) from {probe} -> {out} ({total} total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
