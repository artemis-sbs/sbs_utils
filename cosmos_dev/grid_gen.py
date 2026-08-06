"""Generate a systems-only interior for a hull that has none.

A hull with no interior has a DEAD Engineering console: `grid_rebuild_grid_objects`
returns early, so there are no system nodes, no damcons, and `system_max_damage` is never
set. 23 hulls in shipData are in that state - every Torgoth, Skaraan, Kralien, Biomech and
Pirate ship among them.

Fixing that needs no authoring, because a systems-only layout is DERIVED rather than
designed. Every node in it comes from data already present: beam count from
`hull_port_sets`, tubes from `tubecount`, shields per facing, sensors, impulse, maneuver,
and the drive from the faction. Position comes from the zone grammar measured over the
authored ships (`GRID_REFERENCE.md` s5) and from the engine's own hull map.

That is the distinction worth holding on to. A generator that tried to reproduce a FULL
interior would be imitating statistics - it would reproduce the averages, lose the reasons,
and make every ship look like the same ship. A systems-only layout imitates nothing: the
ship really does have four beams, and they really do belong forward and outboard.

Output is an ASCII floor plan, so it is an editable artifact rather than a runtime
behavior. A bad placement is a one-character fix.

Dev-only. Run it, review the diff, commit the result.
"""

from cosmos_dev.mock import hull_capture

# Where each system sits, as (fore->aft 0..1, center->edge 0..1), measured over the 3171
# authored objects. See GRID_REFERENCE.md s5.
_ZONES = {
    "fwd-shield":    (0.23, 0.36),
    "aft-shield":    (0.75, 0.42),
    "sensors":       (0.38, 0.55),
    "beam":          (0.21, 0.71),
    "torpedo-tube":  (0.34, 0.25),
    "impulse":       (0.72, 0.40),
    "maneuver":      (0.56, 0.63),
    "warp":          (0.90, 0.56),
    "jump-drive":    (0.55, 0.27),
}

# Ximni ships jump; everything else warps. Arvonian authored ships have NEITHER, so they
# are left driveless rather than given one they never had.
_JUMP_SIDES = {"Ximni"}
_NO_DRIVE_SIDES = {"Arvonian"}


def _counts(entry, open_n):
    """How many of each node, from what the ship actually carries.

    Sizes scale with the hull because a system's node count IS its hit-point pool: a
    dreadnought that loses impulse to one hit would be absurd.
    """
    size = 0 if open_n < 40 else (1 if open_n < 100 else 2)

    beams = 0
    for pname, plist in (entry.get("hull_port_sets") or {}).items():
        if isinstance(pname, str) and pname.startswith("beam") and isinstance(plist, list):
            beams += len(plist)

    out = {
        "beam": beams,
        "torpedo-tube": int(entry.get("tubecount") or 0),
        "sensors": (1, 2, 4)[size],
        "impulse": (2, 4, 6)[size],
        "maneuver": 2,
        "fwd-shield": (1, 2, 2)[size],
        "aft-shield": (1, 2, 2)[size],
    }
    side = entry.get("side")
    if side not in _NO_DRIVE_SIDES:
        drive = "jump-drive" if side in _JUMP_SIDES else "warp"
        out[drive] = (2, 4, 4)[size]
    return out


def _candidates(open_cells, w, h, fore_aft, center_edge):
    """Open cells sorted by how well they match a zone target."""
    mid = (w - 1) / 2.0
    out = []
    for y in range(h):
        for x in range(w):
            if not open_cells[y][x]:
                continue
            fy = y / (h - 1) if h > 1 else 0.0
            fx = abs(x - mid) / mid if mid else 0.0
            out.append((abs(fy - fore_aft) * 1.6 + abs(fx - center_edge), x, y))
    out.sort()
    return out


def generate_systems_layout(ship_key, entry, open_cells):
    """Return grid objects for a systems-only interior, or ``None`` without a hull map."""
    if not open_cells:
        return None
    h = len(open_cells)
    w = len(open_cells[0]) if h else 0
    open_n = sum(1 for row in open_cells for c in row if c)
    if not open_n:
        return None

    from sbs_utils.procedural.grid_rooms import grid_room_roles

    taken = set()
    objects = []
    mid = (w - 1) / 2.0

    # Weapons and drives first: they have the strongest positional intent, and the
    # softer systems should give way to them rather than the other way round.
    order = ["beam", "torpedo-tube", "warp", "jump-drive", "fwd-shield", "aft-shield",
             "sensors", "impulse", "maneuver"]
    counts = _counts(entry, open_n)

    for name in order:
        want = counts.get(name, 0)
        if not want:
            continue
        zone = _ZONES[name]
        placed = 0
        for _score, x, y in _candidates(open_cells, w, h, *zone):
            if placed >= want:
                break
            if (x, y) in taken:
                continue
            mx = w - 1 - x
            # Place port/starboard together so the ship reads symmetric, which is what
            # every authored hull does for system nodes.
            pair = [(x, y)]
            if mx != x and (mx, y) not in taken and open_cells[y][mx] and placed + 1 < want:
                pair.append((mx, y))
            for px, py in pair:
                if placed >= want:
                    break
                taken.add((px, py))
                # A beam's name records its side, matching the authored convention.
                nm = name
                if name == "beam":
                    nm = ("beam-fwd" if px == int(mid) and mid == int(mid)
                          else ("beam-port-fwd" if px < mid else "beam-starboard-fwd"))
                roles = grid_room_roles(nm) or grid_room_roles(name)
                objects.append({"x": float(px), "y": float(py),
                                "name": nm, "roles": roles})
                placed += 1
    return objects


def systems_layout_for(ship_key, entry):
    """Convenience: fetch the captured hull map and generate."""
    w, h = entry.get("internalmapw"), entry.get("internalmaph")
    if not w or not h:
        return None
    return generate_systems_layout(ship_key, entry,
                                   hull_capture.captured_cells(ship_key, int(w), int(h)))
