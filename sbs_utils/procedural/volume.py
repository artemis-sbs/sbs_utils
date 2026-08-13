"""Navigable volumes - model the VOID, not the walls.

For a structure a ship can fly INTO (a relic interior, a canyon, a docking throat),
the instinct is to build the walls out of solid objects. The engine cannot do that
well: `exclusion_radius` is a single KEEP-OUT sphere per object ("other objects
cannot be closer to me than this"), and a hollow shell is the *complement* of a
sphere. Approximating one with many spheres is not merely expensive - the boundary
never lines up with the art. Inscribe the spheres and corners are passable;
circumscribe them and the ship stops in empty space.

So this module describes the **navigable space** instead, as signed distance fields:

    chamber  = a sphere   (center, radius)
    passage  = a capsule  (endpoint A, endpoint B, radius)
    box      = an axis-aligned rectangle (center, half-extents)
    solid    = any of the above, SUBTRACTED - the pillar in the middle of the room

A ship is inside the volume if it is inside any navigable primitive and outside every
solid. A dozen branching chambers is ~30 primitives rather than ~10,000 voxels, the
boundary is smooth, and **no engine collision is involved at all** - every prop that
dresses the structure ships `exclusion_radius = 0`.

**The engine's sphere-only limit does not apply here.** `exclusion_radius` is the
engine's single collider, but nothing in this module uses engine collision, so the
shape vocabulary is only limited by what has a signed distance function. Spheres and
capsules came first because they match rooms and corridors; boxes read as BUILT rather
than eroded; subtraction is the one thing a union can never fake.

Two consequences worth knowing:

* **Props must be TERRAIN**, never an AI behavior. A `behav_*` AI object carrying
  `exclusion_radius = 0` NaNs the engine and asserts (measured 1.3.5: both
  `Simulation.cpp:739 !isnan(so->pos.x)` and
  `SpaceObjectAITyphon.cpp:111 !isnan(obj->rotQuat.x)`). Terrain is passive - no
  steering, no rotation solve, nothing to NaN - so a zero radius is safe there.
* **The same graph is a navmesh.** Brains steer by writing `target_pos_*` and know
  nothing about walls, so inside a voxel structure they fly straight through it.
  Chamber-to-chamber routing here is a plain graph search (`volume_path`).

Containment is enforced by script, on a signed depth rather than a boolean, so a
caller can scale its response: scrape damage near the wall, a `playerThrottle`
governor further out, and a hard projection back inside as the backstop. Engine
1.3.5 measurements behind that design: a playership travels **60 units per MAST
tick at full warp** (the tick is ~15 Hz, not the 5 Hz usually quoted), and script
position writes **do** stick on a playership - clamping to a 3000u sphere held a
ship at 3058.6, one tick of travel and no more.

Geometry here is plain Python. `sbs.distance_point_line` exists and is documented
"for checking potential collisions", but its tuple is an UNCLAMPED line measure
whose contract has not been verified against a capsule, and a wrong clamp is worse
than ten float ops. The cost does not matter: 8 players x 30 primitives at 15 Hz is
~3600 distance tests a second, which is noise.
"""

import math
import random

# EVERY module-level function here becomes a MAST global, in one flat mission-wide
# namespace - and a LEADING UNDERSCORE IS NOT PRIVATE. An unprefixed helper therefore
# collides with any script variable of the same name, and the failure is brutal: MAST
# reports "Variable assignment to a keyword <name>", the file fails to COMPILE, and a
# story that does not compile runs ZERO labels.
#
# This is not hypothetical. A helper called `_dist` here broke
# LegendaryMissions/ai/npc_brains.mast:202 (`_dist = _pos - _target_point`) and with it
# every mission loading LM's ai addon. Hence the `_vol_` prefix on all of them, and note
# grav_tether.py uses `_distance` rather than `_dist` for exactly this reason.
#
# `sbs lint` catches this as ns-mast-var-collision. Run it after adding a helper.

_VOLUMES = {}


def _vol_xyz(p):
    """Coerce a position: Vec3, tuple/list, engine vec3, Agent, or agent id."""
    if p is None:
        return None
    x = getattr(p, "x", None)
    if x is not None:
        return (float(x), float(p.y), float(p.z))
    if isinstance(p, (tuple, list)) and len(p) >= 3:
        return (float(p[0]), float(p[1]), float(p[2]))
    # An agent or an id - imported lazily so the geometry stays unit-testable
    # with no FrameContext and no sim.
    from .space_objects import get_pos
    pos = get_pos(p)
    return None if pos is None else (float(pos.x), float(pos.y), float(pos.z))


def _vol_seg_closest(p, a, b):
    """Closest point on segment AB to P. Returns (distance, (cx, cy, cz)).

    Clamped to the segment - that is what makes a capsule a capsule rather than an
    infinite cylinder.
    """
    abx, aby, abz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    apx, apy, apz = p[0] - a[0], p[1] - a[1], p[2] - a[2]
    ab2 = abx * abx + aby * aby + abz * abz
    if ab2 <= 1e-9:                       # degenerate segment - treat as a point
        return (math.sqrt(apx * apx + apy * apy + apz * apz), a)
    t = (apx * abx + apy * aby + apz * abz) / ab2
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    c = (a[0] + abx * t, a[1] + aby * t, a[2] + abz * t)
    dx, dy, dz = p[0] - c[0], p[1] - c[1], p[2] - c[2]
    return (math.sqrt(dx * dx + dy * dy + dz * dz), c)


def _vol_dist(p, q):
    dx, dy, dz = p[0] - q[0], p[1] - q[1], p[2] - q[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _vol_push_out(p, anchor, radius):
    """A point on the sphere of `radius` about `anchor`, in the direction of p.

    When p IS the anchor there is no direction to preserve, so +x is chosen - an
    arbitrary but finite answer. Returning the anchor itself would leave a ship at
    a primitive's exact center, which is the zero-distance case that NaNs AI
    objects.
    """
    d = _vol_dist(p, anchor)
    if d <= 1e-9:
        return (anchor[0] + radius, anchor[1], anchor[2])
    k = radius / d
    return (anchor[0] + (p[0] - anchor[0]) * k,
            anchor[1] + (p[1] - anchor[1]) * k,
            anchor[2] + (p[2] - anchor[2]) * k)


# -- primitives -------------------------------------------------------------------
#
# Every shape is a signed distance function: negative inside, zero on the surface,
# positive outside. That is the whole reason this module is not stuck with spheres -
# the ENGINE only has one collision sphere per object, but nothing here uses engine
# collision, so any shape with an SDF is available.
#
# A primitive is a plain tuple tagged by kind:
#   ("sphere",  (x, y, z), radius)
#   ("capsule", a_xyz, b_xyz, radius)
#   ("box",     (x, y, z), (hx, hy, hz))     axis-aligned, HALF-extents


def _vol_sdf(prim, p):
    """Signed distance from p to the primitive's surface. Negative inside."""
    kind = prim[0]
    if kind == "sphere":
        return _vol_dist(p, prim[1]) - prim[2]
    if kind == "capsule":
        return _vol_seg_closest(p, prim[1], prim[2])[0] - prim[3]
    # Box: the standard exact SDF. `q` is the per-axis overshoot past the half-extent;
    # the outside term is the length of its positive part, the inside term is the
    # largest (least negative) axis, which is the distance to the nearest FACE.
    c, h = prim[1], prim[2]
    qx = abs(p[0] - c[0]) - h[0]
    qy = abs(p[1] - c[1]) - h[1]
    qz = abs(p[2] - c[2]) - h[2]
    ox, oy, oz = max(qx, 0.0), max(qy, 0.0), max(qz, 0.0)
    outside = math.sqrt(ox * ox + oy * oy + oz * oz)
    inside = min(max(qx, qy, qz), 0.0)
    return outside + inside


def _vol_project(prim, p, margin=0.0):
    """The nearest point INSIDE the primitive by at least `margin`.

    Per-kind on purpose. A box cannot be projected by pushing towards a centre - that
    would collapse a rectangular hall to its inscribed sphere and make the corners
    unreachable. Clamping per axis is both exact and cheaper.
    """
    kind = prim[0]
    if kind == "sphere":
        keep = prim[2] - margin
        return _vol_push_out(p, prim[1], keep if keep > 0.0 else prim[2] * 0.5)
    if kind == "capsule":
        c = _vol_seg_closest(p, prim[1], prim[2])[1]
        keep = prim[3] - margin
        return _vol_push_out(p, c, keep if keep > 0.0 else prim[3] * 0.5)
    c, h = prim[1], prim[2]
    out = []
    for i in range(3):
        half = h[i] - margin
        if half <= 0.0:
            half = h[i] * 0.5
        lo, hi = c[i] - half, c[i] + half
        out.append(lo if p[i] < lo else (hi if p[i] > hi else p[i]))
    return (out[0], out[1], out[2])


def _vol_push_solid_out(prim, p, margin=0.0):
    """The nearest point at least `margin` OUTSIDE a solid - how you leave a pillar."""
    kind = prim[0]
    if kind == "sphere":
        return _vol_push_out(p, prim[1], prim[2] + margin)
    if kind == "capsule":
        c = _vol_seg_closest(p, prim[1], prim[2])[1]
        return _vol_push_out(p, c, prim[3] + margin)
    # Box: leave by the NEAREST face, which is the axis with the least penetration.
    c, h = prim[1], prim[2]
    best_axis, best_pen = 0, None
    for i in range(3):
        pen = (h[i] + margin) - abs(p[i] - c[i])     # how far in, on this axis
        if best_pen is None or pen < best_pen:
            best_axis, best_pen = i, pen
    out = [p[0], p[1], p[2]]
    reach = h[best_axis] + margin
    out[best_axis] = c[best_axis] + (reach if p[best_axis] >= c[best_axis] else -reach)
    return (out[0], out[1], out[2])


def _vol_rope(prim, p, margin=0.0):
    """``(anchor, rope_len)`` for a tractor hold against this primitive.

    Sphere and capsule return the MEDIAL AXIS point and the primitive's radius, so a
    rope of that length about that point IS the containment constraint - the shape the
    engine run validated, kept exactly.

    A box has no such single sphere, so it returns the projected interior point with a
    short rope: while breached the ship is outside anyway, and the tether is released
    the moment it is back inside, so pulling it to the nearest safe point is the same
    behavior expressed for a shape that has no centre-and-radius.
    """
    kind = prim[0]
    if kind == "sphere":
        keep = prim[2] - margin
        return (prim[1], keep if keep > 0.0 else prim[2] * 0.5)
    if kind == "capsule":
        c = _vol_seg_closest(p, prim[1], prim[2])[1]
        keep = prim[3] - margin
        return (c, keep if keep > 0.0 else prim[3] * 0.5)
    target = _vol_project(prim, p, margin)
    return (target, max(margin, 1.0))


class Volume:
    """A navigable space built from primitives, minus any solids carved out of it.

    Navigable: `chambers` (spheres), `passages` (capsules), `boxes` (axis-aligned).
    `solids` are SUBTRACTED - the pillar in the middle of the room.
    """

    __slots__ = ("name", "chambers", "passages", "boxes", "solids", "_bound")

    def __init__(self, name):
        self.name = name
        self.chambers = {}     # name -> (x, y, z, radius)
        self.passages = []     # (a_xyz, b_xyz, radius, a_name, b_name)
        self.boxes = {}        # name -> ((x, y, z), (hx, hy, hz))
        self.solids = []       # primitives subtracted from the navigable space
        self._bound = None     # ((x, y, z), radius) - whole-volume bounding sphere

    # -- construction ------------------------------------------------------------

    def add_chamber(self, name, x, y, z, radius):
        r = float(radius)
        if not r > 0.0:
            raise ValueError(
                f"volume {self.name!r}: chamber {name!r} has radius {radius!r}; "
                f"a chamber must have a positive radius or it encloses nothing")
        self.chambers[name] = (float(x), float(y), float(z), r)
        self._bound = None
        return self

    def _endpoint(self, e):
        """Resolve a passage endpoint: a chamber name, or an explicit point."""
        if isinstance(e, str):
            if e not in self.chambers:
                known = ", ".join(sorted(self.chambers)) or "none"
                raise ValueError(
                    f"volume {self.name!r}: passage endpoint {e!r} is not a chamber "
                    f"(known chambers: {known}). A bare KeyError here used to be the "
                    f"only clue that a relic had a typo in one passage.")
            return self.chambers[e][:3]
        p = _vol_xyz(e)
        if p is None:
            raise ValueError(
                f"volume {self.name!r}: passage endpoint {e!r} is neither a chamber "
                f"name nor an (x, y, z) point")
        return p

    def add_passage(self, a, b, radius):
        """Join two chambers by name, or two explicit points, with a capsule."""
        r = float(radius)
        if not r > 0.0:
            raise ValueError(
                f"volume {self.name!r}: passage {a!r}->{b!r} has radius {radius!r}; "
                f"a passage must have a positive radius or nothing can fly down it")
        a_name = a if isinstance(a, str) else None
        b_name = b if isinstance(b, str) else None
        a_xyz = self._endpoint(a)
        b_xyz = self._endpoint(b)
        self.passages.append((a_xyz, b_xyz, r, a_name, b_name))
        self._bound = None
        return self

    # -- geometry ----------------------------------------------------------------

    def add_box(self, name, x, y, z, hx, hy, hz):
        """An axis-aligned rectangular space. Half-extents, so hx is HALF the width.

        A box reads as BUILT rather than eroded - a vault with flat walls and real
        corners, which spheres and capsules cannot express at all. Not rotatable:
        arbitrary orientation needs a quaternion in the SDF, and every relic so far
        wanted axis-aligned rooms.
        """
        for label, h in (("hx", hx), ("hy", hy), ("hz", hz)):
            if not float(h) > 0.0:
                raise ValueError(
                    f"volume {self.name!r}: box {name!r} has {label}={h!r}; half-extents "
                    f"must be positive (they are HALF the width, not the width)")
        self.boxes[name] = ((float(x), float(y), float(z)),
                            (float(hx), float(hy), float(hz)))
        self._bound = None
        return self

    def add_solid(self, prim):
        """SUBTRACT a shape from the navigable space - a pillar, a spire, a solid hub.

        Union alone can only ever ADD space, so without this a chamber with a column
        in the middle has to be faked by routing capsules around where the column
        goes. Takes any primitive tuple; see `volume_solid` for the friendly form.
        """
        self.solids.append(prim)
        self._bound = None
        return self

    def primitives(self):
        """Every NAVIGABLE primitive, uniformly tagged."""
        out = []
        for (x, y, z, r) in self.chambers.values():
            out.append(("sphere", (x, y, z), r))
        for (a, b, r, _an, _bn) in self.passages:
            out.append(("capsule", a, b, r))
        for (c, h) in self.boxes.values():
            out.append(("box", c, h))
        return out

    def bound(self):
        """Bounding sphere of the whole volume.

        Used to size a relic's nebula. NOT wired into `nearest` as an early-out - at
        tens of primitives the walk is already noise, and a stale claim that it was
        would be worse than none. If a volume ever reaches thousands, this is the hook.
        """
        if self._bound is not None:
            return self._bound
        pts = []
        for prim in self.primitives():
            if prim[0] == "sphere":
                pts.append((prim[1], prim[2]))
            elif prim[0] == "capsule":
                pts.append((prim[1], prim[3]))
                pts.append((prim[2], prim[3]))
            else:
                c, h = prim[1], prim[2]
                pts.append((c, math.sqrt(h[0] ** 2 + h[1] ** 2 + h[2] ** 2)))
        if not pts:
            self._bound = ((0.0, 0.0, 0.0), 0.0)
            return self._bound
        n = len(pts)
        c = (sum(q[0][0] for q in pts) / n,
             sum(q[0][1] for q in pts) / n,
             sum(q[0][2] for q in pts) / n)
        self._bound = (c, max(_vol_dist(c, q[0]) + q[1] for q in pts))
        return self._bound

    def nearest(self, pos):
        """``(depth, anchor, rope)`` - signed depth plus a tractor hold target.

        Depth is the SDF of the whole volume: the union of the navigable primitives,
        with every solid subtracted. In SDF algebra, subtracting S is
        ``max(d_union, -d_S)`` - so a point inside a pillar reports positive (outside
        the navigable space), and a point near one correctly measures its distance to
        the pillar as its distance to the nearest wall.

        A point inside a solid is anchored AGAINST THE SOLID, not the room it sits in:
        the way out of a pillar is away from the pillar.
        """
        p = _vol_xyz(pos)
        if p is None:
            return (float("inf"), None, 0.0)
        best_d = float("inf")
        best = (None, 0.0)
        for prim in self.primitives():
            d = _vol_sdf(prim, p)
            if d < best_d:
                best_d, best = d, _vol_rope(prim, p, 0.0)
        for solid in self.solids:
            ds = _vol_sdf(solid, p)
            if -ds > best_d:
                best_d = -ds
                # Push clear of the solid's surface rather than towards a room centre.
                anchor, _r = _vol_rope(solid, p, 0.0)
                best = (anchor, 0.0)
        return (best_d, best[0], best[1])

    def depth(self, pos):
        """Signed distance to the boundary. NEGATIVE inside, positive outside.

        An empty volume is all wall, reporting +inf rather than pretending everything
        is contained.
        """
        return self.nearest(pos)[0]

    def nearest_inside(self, pos, margin=0.0):
        """The closest point that is inside by at least `margin`.

        Returns the position unchanged when it already satisfies that, so this is safe
        to call every tick. A HARD geometric projection, deliberately - not a
        proportional pull. `orbit.py` measured a proportional-only controller
        spiralling against real engine 1.3.5 rather than settling.
        """
        p = _vol_xyz(pos)
        if p is None:
            return None
        prims = self.primitives()
        if not prims:
            return p
        if self.depth(p) <= -margin:
            return p
        # Inside a solid, the only correct move is out of THAT solid - projecting onto
        # the enclosing room would leave the ship still buried in the pillar.
        for solid in self.solids:
            ds = _vol_sdf(solid, p)
            if ds < margin:
                out = _vol_push_solid_out(solid, p, margin)
                if out is not None:
                    return out
        best_d = float("inf")
        best = None
        for prim in prims:
            d = _vol_sdf(prim, p)
            if d < best_d:
                best_d, best = d, prim
        return _vol_project(best, p, margin)

    # -- the navmesh half --------------------------------------------------------

    def neighbors(self, chamber):
        out = []
        for _a, _b, _r, an, bn in self.passages:
            if an == chamber and bn is not None:
                out.append(bn)
            elif bn == chamber and an is not None:
                out.append(an)
        return out

    def path(self, start, goal):
        """Chamber names from `start` to `goal` inclusive, or [] if unreachable.

        Breadth-first: passages have no meaningful cost yet, and with a dozen
        chambers a weighted search would be ceremony.
        """
        if start not in self.chambers or goal not in self.chambers:
            return []
        if start == goal:
            return [start]
        seen = {start}
        queue = [[start]]
        while queue:
            route = queue.pop(0)
            for nxt in self.neighbors(route[-1]):
                if nxt in seen:
                    continue
                if nxt == goal:
                    return route + [nxt]
                seen.add(nxt)
                queue.append(route + [nxt])
        return []


# -- registry ---------------------------------------------------------------------
#
# Module-level and per-mission, so it is on the reset ledger. An unregistered
# container of this shape is exactly the second-run bug the ledger exists to catch:
# `cosmos_dev` reuses one interpreter across missions, so last mission's chambers
# would still be here on run 2.

def _vol_shift(point, origin):
    """Translate an (x, y, z) by the origin. Identity when there is no origin."""
    if origin is None:
        return point
    return (point[0] + origin[0], point[1] + origin[1], point[2] + origin[2])


def volume_define(name, chambers=None, passages=None, boxes=None, solids=None,
                  origin=None):
    """Create (or replace) a named volume.

    Declarative form - `chambers` maps a name to (x, y, z, radius), `passages` is a
    sequence of (a, b, radius) where a and b are chamber names or explicit points:

        volume_define("relic",
                      chambers={"hub": (0, 0, 0, 1200)},
                      passages=[("hub", "spine", 300)])

    `origin` PLACES the whole layout: every coordinate is treated as relative to it.
    That is what lets one authored layout be dropped at two different points in a
    system - without it a layout is welded to the absolute coordinates it was written
    at, and a second copy means editing every number. Radii and half-extents are
    sizes, not positions, so they are never shifted; a passage naming a chamber needs
    no shift either, since the chamber it names has already moved.
    """
    vol = Volume(name)
    # Chambers first, always, so a declarative block does not have to be ordered -
    # passages may name chambers that appear later in the same dict.
    for cname, c in (chambers or {}).items():
        if len(c) < 4:
            raise ValueError(
                f"volume {name!r}: chamber {cname!r} needs (x, y, z, radius), "
                f"got {c!r}")
        cx, cy, cz = _vol_shift((c[0], c[1], c[2]), origin)
        vol.add_chamber(cname, cx, cy, cz, c[3])
    for p in (passages or []):
        if len(p) < 3:
            raise ValueError(
                f"volume {name!r}: passage needs (a, b, radius), got {p!r}")
        # A named endpoint resolves to a chamber that has already been placed; only an
        # explicit point needs shifting.
        a = p[0] if isinstance(p[0], str) else _vol_shift(_vol_xyz(p[0]), origin)
        b = p[1] if isinstance(p[1], str) else _vol_shift(_vol_xyz(p[1]), origin)
        vol.add_passage(a, b, p[2])
    for bname, b in (boxes or {}).items():
        if len(b) < 6:
            raise ValueError(
                f"volume {name!r}: box {bname!r} needs (x, y, z, hx, hy, hz), got {b!r}")
        bx, by, bz = _vol_shift((b[0], b[1], b[2]), origin)
        vol.add_box(bname, bx, by, bz, b[3], b[4], b[5])
    for sl in (solids or []):
        if not sl:
            raise ValueError(f"volume {name!r}: empty solid entry")
        # Pass the OBJECT, not the name (`_vol_resolve` takes either). Publishing mid-loop
        # so that `volume_solid` could look the name up meant a solid that raised - a zero
        # radius, say - left a HALF-BUILT volume registered with the previous good one
        # already discarded. Harmless when a volume is built once at map setup; not
        # harmless once the relic editor re-defines on every drag, where a number typed
        # through zero would destroy the relic you were looking at.
        volume_solid(vol, sl[0], *_vol_shift_solid(sl[0], sl[1:], origin))
    # Publish once, fully built. Until this line the previous volume of this name is still
    # the live one, so a raise anywhere above leaves it untouched.
    _VOLUMES[name] = vol
    return vol


def _vol_capsule_args(args):
    """Accept a capsule as either two POINTS plus a radius, or seven FLAT numbers.

    The Python API reads better as points - `volume_solid(v, "capsule", (0,-800,0),
    (0,800,0), 60)` - but a declarative source has no tuples: an authored
    `Solid: capsule, 0, -800, 0, 0, 800, 0, 60` arrives as a flat row. Supporting both
    here means the AMD reader needs no special case and neither does the caller.
    """
    if len(args) == 3:
        return args
    if len(args) >= 7:
        return ((args[0], args[1], args[2]), (args[3], args[4], args[5]), args[6])
    raise ValueError(
        "a solid capsule needs two points and a radius, or seven numbers; got "
        + repr(args))


def _vol_shift_solid(kind, args, origin):
    """Translate a solid's POSITION arguments, leaving its size arguments alone.

    Each kind carries a different arg shape, which is why this cannot be one generic
    slice: sphere is (x, y, z, r), box is (x, y, z, hx, hy, hz), and capsule is two
    POINTS plus a radius.
    """
    if origin is None:
        return args
    if kind == "capsule":
        a, b, r = _vol_capsule_args(args)
        return (_vol_shift(_vol_xyz(a), origin), _vol_shift(_vol_xyz(b), origin), r)
    x, y, z = _vol_shift((args[0], args[1], args[2]), origin)
    return (x, y, z) + tuple(args[3:])


def volume_box(volume, name, x, y, z, hx, hy, hz):
    """Add an axis-aligned rectangular space. Half-extents, not widths."""
    vol = _vol_resolve(volume)
    return None if vol is None else vol.add_box(name, x, y, z, hx, hy, hz)


def volume_solid(volume, kind, *args):
    """SUBTRACT a shape from the navigable space.

    Three forms - a pillar, a bar, a block::

        volume_solid(v, "sphere",  x, y, z, radius)
        volume_solid(v, "capsule", (ax, ay, az), (bx, by, bz), radius)
        volume_solid(v, "box",     x, y, z, hx, hy, hz)

    Union alone can only ADD space, so this is what buys a column in the middle of a
    chamber, a spire, or a torus with a genuinely solid hub.
    """
    vol = _vol_resolve(volume)
    if vol is None:
        return None
    if kind == "sphere":
        x, y, z, r = args
        if not float(r) > 0.0:
            raise ValueError(f"volume {vol.name!r}: solid sphere radius must be positive")
        return vol.add_solid(("sphere", (float(x), float(y), float(z)), float(r)))
    if kind == "capsule":
        a, b, r = _vol_capsule_args(args)
        if not float(r) > 0.0:
            raise ValueError(f"volume {vol.name!r}: solid capsule radius must be positive")
        return vol.add_solid(("capsule", _vol_xyz(a), _vol_xyz(b), float(r)))
    if kind == "box":
        x, y, z, hx, hy, hz = args
        for label, h in (("hx", hx), ("hy", hy), ("hz", hz)):
            if not float(h) > 0.0:
                raise ValueError(
                    f"volume {vol.name!r}: solid box {label}={h!r} must be positive")
        return vol.add_solid(("box", (float(x), float(y), float(z)),
                              (float(hx), float(hy), float(hz))))
    raise ValueError(
        f"volume {vol.name!r}: unknown solid kind {kind!r} "
        f"(expected 'sphere', 'capsule' or 'box')")


def volume_load(name, data, origin=None):
    """Define a volume from one parsed block - a MAST `metadata:` yaml section, or a
    mission yaml file.

    Takes the shape yaml actually parses to (lists, not tuples), so a relic can be
    authored declaratively rather than as a wall of calls::

        metadata: ``` yaml
        chambers:
            hub:   [0, 0, 0, 1200]
            spine: [4000, 0, 0, 900]
        passages:
            - [hub, spine, 300]
        ```

    then ``volume_load("relic", {"chambers": chambers, "passages": passages})`` - or
    pass the whole parsed mapping straight in.

    Two more keys, both optional::

        boxes:                             # axis-aligned, x y z then HALF-extents
            vault: [4000, 0, 0, 900, 400, 900]
        solids:                            # SUBTRACTED - pillars, spires, solid hubs
            - [sphere, 4000, 0, 0, 250]
            - [box, 0, 0, 0, 100, 800, 100]
    """
    data = data or {}
    return volume_define(name, data.get("chambers"), data.get("passages"),
                         data.get("boxes"), data.get("solids"), origin=origin)


def volume_get(name):
    """The named volume, or None."""
    return _VOLUMES.get(name)


def _vol_resolve(volume):
    return volume if isinstance(volume, Volume) else _VOLUMES.get(volume)


def volume_chamber(volume, name, x, y, z, radius):
    """Add one chamber to a volume (by object or by name)."""
    vol = _vol_resolve(volume)
    return None if vol is None else vol.add_chamber(name, x, y, z, radius)


def volume_passage(volume, a, b, radius):
    """Join two chambers (or two points) with a capsule."""
    vol = _vol_resolve(volume)
    return None if vol is None else vol.add_passage(a, b, radius)


def volume_depth(volume, pos):
    """Signed distance to the wall: NEGATIVE inside, positive outside.

    The number the graded response is built on - scrape near zero, govern the
    throttle further out, clamp as the backstop.
    """
    vol = _vol_resolve(volume)
    return float("inf") if vol is None else vol.depth(pos)


def volume_contains(volume, pos):
    """True if the position is inside any chamber or passage."""
    return volume_depth(volume, pos) < 0.0


def volume_nearest_inside(volume, pos, margin=0.0):
    """Closest point inside by at least `margin`; the position itself if already so."""
    vol = _vol_resolve(volume)
    return None if vol is None else vol.nearest_inside(pos, margin)


def volume_path(volume, start, goal):
    """Chamber names from start to goal inclusive, or [] if unreachable."""
    vol = _vol_resolve(volume)
    return [] if vol is None else vol.path(start, goal)


# ---------------------------------------------------------------------------
# Sampling
#
# A volume says where space IS. To make it visible a mission scatters props over that
# boundary - and the maths for "evenly, over a sphere, a capsule at any orientation, and
# the faces of a box" is the part that is hard, general, and easy to get subtly wrong.
# So the LIBRARY samples and the MISSION decorates: nothing here chooses art, scale, roles
# or behaviours, and nothing here spawns anything.
#
# It lives beside the geometry because it IS geometry: the same primitives, walked the
# other way round.
# ---------------------------------------------------------------------------

# How far inside the union a sampled point may be before it counts as buried in
# another primitive rather than sitting on the shell.
_VOL_BURIED = 1.0


def _vol_even_sphere(n):
    """`n` roughly-even directions on the unit sphere - a golden-angle spiral.

    Even beats random here, and the difference is visible: uniform sampling clumps, and a
    clumped shell has holes you can see straight out through. `scatter.sphere` already
    samples a shell but draws pitch as `uniform(-pi, pi)`, which piles points at the poles
    and covers the equator twice - this is the sampler that defect calls for.
    """
    out = []
    step = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        y = 1.0 - (2.0 * i + 1.0) / n
        r = math.sqrt(max(0.0, 1.0 - y * y))
        a = step * i
        out.append((math.cos(a) * r, y, math.sin(a) * r))
    return out


def _vol_frame(u):
    """Two unit vectors perpendicular to `u`, and to each other.

    The helper axis is swapped when `u` is near vertical, because the cross product of two
    parallel vectors is zero and the frame collapses. Getting this wrong is why a vertical
    capsule can end up dressed as a flat disc - the axis-naive version assumes a corridor
    is never a shaft.
    """
    ux, uy, uz = u
    hx, hy, hz = (0.0, 1.0, 0.0) if abs(uy) < 0.9 else (1.0, 0.0, 0.0)
    px, py, pz = (uy * hz - uz * hy, uz * hx - ux * hz, ux * hy - uy * hx)
    pl = math.sqrt(px * px + py * py + pz * pz) or 1.0
    px, py, pz = px / pl, py / pl, pz / pl
    qx, qy, qz = (uy * pz - uz * py, uz * px - ux * pz, ux * py - uy * px)
    return (px, py, pz), (qx, qy, qz)


def _vol_prim_area(prim):
    """Rough surface area of a primitive, for splitting a budget between them.

    Rough is the point: it decides how many props each room gets, so a chamber twice the
    size gets about twice as many. Exactness would buy nothing a author would notice.
    """
    kind = prim[0]
    if kind == "sphere":
        return 4.0 * math.pi * prim[2] * prim[2]
    if kind == "capsule":
        a, b, r = prim[1], prim[2], prim[3]
        length = _vol_dist(a, b)
        return 2.0 * math.pi * r * length + 4.0 * math.pi * r * r
    if kind == "box":
        hx, hy, hz = prim[2]
        return 8.0 * (hx * hy + hy * hz + hz * hx)
    return 0.0


def _vol_share(prims, n):
    """Split `n` points between primitives by area, giving every one at least 1."""
    areas = [_vol_prim_area(p) for p in prims]
    total = sum(areas)
    if total <= 0.0 or not prims:
        return [0] * len(prims)
    out = [max(1, int(round(n * a / total))) for a in areas]
    return out


def _vol_sphere_surface(prim, count, rng, out):
    c, r = prim[1], prim[2]
    for (dx, dy, dz) in _vol_even_sphere(count):
        j = r * out * rng.uniform(0.99, 1.02)
        yield (c[0] + dx * j, c[1] + dy * j, c[2] + dz * j, dx, dy, dz)


def _vol_capsule_surface(prim, count, rng, out, per_ring=6):
    a, b, r = prim[1], prim[2], prim[3]
    length = _vol_dist(a, b)
    u = [(b[i] - a[i]) / max(length, 1e-6) for i in range(3)]
    p, q = _vol_frame(u)
    rings = max(2, int(count / max(1, per_ring)))
    for ring in range(rings + 1):
        t = ring / float(rings)
        c = [a[i] + (b[i] - a[i]) * t for i in range(3)]
        for k in range(per_ring):
            # The twist stops rings lining up into visible corridors down the tube.
            ang = (2.0 * math.pi * k / per_ring) + ring * 0.4
            rr = r * out * rng.uniform(0.99, 1.04)
            nx = p[0] * math.cos(ang) + q[0] * math.sin(ang)
            ny = p[1] * math.cos(ang) + q[1] * math.sin(ang)
            nz = p[2] * math.cos(ang) + q[2] * math.sin(ang)
            yield (c[0] + nx * rr, c[1] + ny * rr, c[2] + nz * rr, nx, ny, nz)


def _vol_box_surface(prim, count, rng, out):
    """FACES, not a shell. A box dressed as a sphere of props reads as a cave again and
    hides the corners that are the whole reason it is a box."""
    c, h = prim[1], prim[2]
    per_face = max(1, count // 6)
    for axis in range(3):
        for sign in (1.0, -1.0):
            for _ in range(per_face):
                p = [0.0, 0.0, 0.0]
                n = [0.0, 0.0, 0.0]
                for i in range(3):
                    if i == axis:
                        p[i] = c[i] + sign * h[i] * out * rng.uniform(0.99, 1.02)
                        n[i] = sign
                    else:
                        p[i] = c[i] + rng.uniform(-h[i], h[i])
                yield (p[0], p[1], p[2], n[0], n[1], n[2])

def volume_surface_points(volume, n, seed=None, out=1.06, kinds=None, clip=True):
    """`n` points spread over the volume's BOUNDARY, with an outward normal each.

    Returns `[(x, y, z, nx, ny, nz)]` in world coordinates. This is the shell: what a
    mission scatters props over to turn a described space into a visible one.

    The budget is split between primitives BY AREA, so a chamber twice the size gets about
    twice the props and density reads as uniform across the whole relic rather than per
    part. `out` pushes points just clear of the true surface - props belong outside the
    space you fly in, or they are obstacles you cannot see coming.

    Deterministic in `(seed, n)`: the same call gives the same shell, so a relic looks the
    same every time a mission runs, and a rebuild after an edit only changes what the edit
    changed.

    `kinds` narrows to some of `"sphere"`, `"capsule"`, `"box"` - the chambers alone, say.

    `clip` drops points that are BURIED - inside the union rather than on the outside of
    it. Each primitive is sampled on its own surface, so where two overlap, one shape's
    wall runs through the other's open space: the ring where a passage meets a chamber puts
    rock in the middle of the corridor. The shell wanted is the outside of the union, not
    the union of the surfaces. Costs one depth() per point and returns fewer than `n`,
    which is the honest trade - ask for more if a count matters.
    """
    vol = _vol_resolve(volume)
    if vol is None or n <= 0:
        return []
    prims = [p for p in vol.primitives() if kinds is None or p[0] in kinds]
    if not prims:
        return []
    rng = random.Random(seed)
    counts = _vol_share(prims, n)
    pts = []
    for prim, count in zip(prims, counts):
        if count <= 0:
            continue
        if prim[0] == "sphere":
            pts.extend(_vol_sphere_surface(prim, count, rng, out))
        elif prim[0] == "capsule":
            pts.extend(_vol_capsule_surface(prim, count, rng, out))
        elif prim[0] == "box":
            pts.extend(_vol_box_surface(prim, count, rng, out))
    if clip:
        # A tolerance, not zero: a point ON its own surface reads as a hair inside or out
        # depending on floating point, and dropping half a shell to rounding would be a
        # cure worse than the disease.
        pts = [p for p in pts if vol.depth(p[:3]) > -_VOL_BURIED]
    return pts


def volume_inside_points(volume, n, seed=None, margin=0.0, tries=40):
    """`n` points INSIDE the volume - the fill, for debris, cargo, anything floating.

    Rejection sampled in the bounding sphere against `depth(p) < -margin`, which is
    wasteful in principle and exact in practice: it is the only test that respects
    subtracted solids, so nothing lands inside a pillar. A relic is mostly empty bounding
    sphere, so `tries` caps the work rather than looping forever on a layout with no room
    in it; a short return means the volume could not hold that many.

    Deterministic in `(seed, n)`, like the shell.
    """
    vol = _vol_resolve(volume)
    if vol is None or n <= 0:
        return []
    (cx, cy, cz), br = vol.bound()
    if br <= 0.0:
        return []
    rng = random.Random(seed)
    pts = []
    for _ in range(n * max(1, tries)):
        if len(pts) >= n:
            break
        # Cube-root of a uniform draw, or the points pile up near the middle.
        u = rng.random() ** (1.0 / 3.0) * br
        yy = rng.uniform(-1.0, 1.0)
        rr = math.sqrt(max(0.0, 1.0 - yy * yy))
        aa = rng.uniform(0.0, 2.0 * math.pi)
        p = (cx + math.cos(aa) * rr * u, cy + yy * u, cz + math.sin(aa) * rr * u)
        if vol.depth(p) < -margin:
            pts.append(p)
    return pts


def volume_solid_points(volume, n, seed=None, inward=0.94):
    """`n` points on the surface of the SUBTRACTED masses, facing outward.

    A solid that is not dressed is an invisible obstacle: containment stops you at
    something with nothing there to see, which reads as the relic being broken rather than
    as a pillar. `inward` keeps the props just inside the solid's own surface, because you
    look at a pillar from outside it - the opposite of the shell, where they sit just
    outside the space you fly in.
    """
    vol = _vol_resolve(volume)
    if vol is None or n <= 0 or not vol.solids:
        return []
    rng = random.Random(seed)
    counts = _vol_share(vol.solids, n)
    pts = []
    for prim, count in zip(vol.solids, counts):
        if count <= 0:
            continue
        if prim[0] == "sphere":
            pts.extend(_vol_sphere_surface(prim, count, rng, inward))
        elif prim[0] == "capsule":
            pts.extend(_vol_capsule_surface(prim, count, rng, inward))
        elif prim[0] == "box":
            pts.extend(_vol_box_surface(prim, count, rng, inward))
    return pts


def volume_names():
    """Every defined volume name."""
    return list(_VOLUMES.keys())


def volume_count():
    """Number of defined volumes. The reset-ledger probe."""
    return len(_VOLUMES)


def volume_clear():
    """Drop every volume and stop every watcher. Called by reset_mission_state()."""
    for name in list(_WATCHERS.keys()):
        volume_unwatch(name)
    _vol_anchors_clear()
    _VOLUMES.clear()


# =================================================================================
# Containment - the graded response
# =================================================================================
#
# Engine 1.3.5 measurements this is built on (data/missions/relic_spike):
#
#   * A playership travels 60 units per MAST tick at full warp, and the tick is
#     ~15 Hz - NOT the 5 Hz usually quoted. So the tunneling budget is small and no
#     swept test is needed: a wall thicker than ~72u cannot be crossed between two
#     consecutive checks.
#   * Script position writes STICK on a playership. Clamping to a 3000u sphere held
#     a ship at 3058.6 max - one tick of travel past the wall, never more.
#   * Writing `playerThrottle` back down suppresses warp: ONE write took a ship from
#     60 to 10.7 u/tick, because the value stays put until a helm changes it.
#     `max_throttle` does NOT do this - measured, it made no difference at all.
#
# Three tiers, so the response is graded rather than a wall-slam:
#
#   inside   depth < 0                    free flight
#   scrape   0 <= depth < scrape_band     in the wall; the ship can still fly out
#   breach   depth >= scrape_band         governed and clamped back inside
#
# Damage is deliberately NOT applied here. LM computes its own consequence model in
# `collisions/collision.mast` (speed -> shield facing -> internal damage); baking that
# in would make this unusable anywhere else. The library owns detection and positional
# enforcement, the mission owns what it means.

TIER_INSIDE = "inside"
TIER_SCRAPE = "scrape"
TIER_BREACH = "breach"

HOLD_NONE = "none"
HOLD_CLAMP = "clamp"
HOLD_TRACTOR = "tractor"

# ship id -> anchor object id. Module-level and per-mission, so it is on the ledger.
_ANCHORS = {}

_WATCHERS = {}


def volume_tier(volume, pos, scrape_band=120.0):
    """Which response tier a position falls in. Pure - the testable seam.

    `scrape_band` defaults to 120u: two ticks of warp travel at the measured 60
    u/tick, so a glancing clip scrapes while a determined exit breaches.
    """
    d = volume_depth(volume, pos)
    if d < 0.0:
        return TIER_INSIDE
    if d < scrape_band:
        return TIER_SCRAPE
    return TIER_BREACH


ENGAGE_ENTERED = "entered"
ENGAGE_ALWAYS = "always"


class _Watcher:
    __slots__ = ("volume", "agents", "scrape_band", "margin", "govern", "clamp",
                 "hold", "speed_limit", "block_jump", "task", "tiers", "engage",
                 "inside")

    def __init__(self, volume, agents, scrape_band, margin, govern, clamp, hold,
                 speed_limit, block_jump, engage=ENGAGE_ENTERED):
        self.volume = volume
        self.agents = agents
        self.scrape_band = scrape_band
        self.margin = margin
        self.govern = govern
        self.clamp = clamp
        self.hold = hold
        self.speed_limit = speed_limit
        self.block_jump = block_jump
        self.engage = engage
        # Ids that have BEEN inside this volume. A ship is contained once it has been in,
        # and released when it leaves the bounding sphere - see volume_watch.
        self.inside = set()
        self.task = None
        self.tiers = {}        # agent id -> last tier, so signals fire on CHANGE only


def _vol_default_agents():
    """Players and fighters, minus anything docked.

    The candidate set LM's black-hole lethal ticker uses: LM strips `__player__`
    from fighters so they carry `cockpit`, and docked craft carry `standby` - which
    are excluded so a carrier's own bay is not a hazard.
    """
    from .roles import any_role, role
    return any_role("__player__,cockpit") - role("standby")


def _vol_resolve_agents(agents):
    if agents is None:
        return _vol_default_agents()
    if callable(agents):
        return agents()
    return agents


def volume_watch(volume, agents=None, scrape_band=120.0, margin=0.0,
                 govern=True, clamp=True, seconds=0, hold=HOLD_TRACTOR,
                 speed_limit=None, block_jump=False, engage=ENGAGE_ENTERED):
    """Start enforcing containment for a volume. Replaces any existing watch.

    ENGAGEMENT - who this applies to, which is not the same question as who is watched.

    A tier is a pure depth test, so a ship that has never been near the relic reads
    BREACH exactly like one that just punched through a wall: measured, a ship 80,000
    units away came back BREACH and, under the default agent set of every player, was
    tractored toward the relic. That is not containment, it is a fishing net.

    So a ship is contained ONCE IT HAS BEEN INSIDE, and released when it leaves the
    bounding sphere. Fly in through a mouth - a chamber or passage that reaches out past
    the hull - and you are inside the volume before you are deep in it, so the latch
    catches without a breach ever happening. Fly out and away and it lets go. A ship that
    never entered is never touched, which is what makes an entrance possible at all and
    what stops a relic in one corner of a system grabbing everything in it.

    `engage="always"` restores the old behaviour for a volume that IS the playfield.

    Args:
        volume: Volume or its name.
        agents: None for players+fighters (the default set), a CALLABLE returning a
            set - re-evaluated every tick, so arrivals and departures need no
            wiring - or a static set.
        scrape_band (float): how far past the wall a scrape becomes a breach.
        margin (float): how far inside the wall the clamp puts a breached ship.
        govern (bool): cap `playerThrottle` to impulse while breached.
        clamp (bool): project a breached ship back inside.
        seconds (int): tick interval; 0 = every tick, which is what containment
            wants - it is a handful of float ops per agent.

    Signals fire on tier CHANGE only, never per tick, each carrying
    ``{"volume": name, "id": agent_id, "depth": float}``:
        ``volume_scrape``    - entered the wall
        ``volume_breach``    - went past the scrape band
        ``volume_recovered`` - back inside

    Route the consequences: ``//shared/signal/volume_scrape`` for damage or scoring
    (server-once), ``//signal/volume_scrape`` only for per-console display.
    """
    vol = _vol_resolve(volume)
    if vol is None:
        return None
    volume_unwatch(vol.name)
    w = _Watcher(vol.name, agents, float(scrape_band), float(margin), govern, clamp,
                 hold, speed_limit, block_jump, engage)
    _WATCHERS[vol.name] = w
    # Latch whoever is ALREADY inside, now, rather than waiting for a tick to notice.
    # A mission places its crew in the relic and then starts the watch - if the first tick
    # is what engages them, a ship that is moved out in the same frame is never contained.
    if w.engage == ENGAGE_ENTERED:
        from .query import to_object
        for agent in _vol_resolve_agents(agents):
            so = to_object(agent)
            pos = _vol_xyz(so) if so is not None else None
            if pos is not None and vol.depth(pos) < 0.0:
                w.inside.add(so.id)
    from ..tickdispatcher import TickDispatcher
    w.task = TickDispatcher.do_interval(volume_containment_tick, seconds)
    return w


def volume_unwatch(name):
    """Stop enforcing containment for a volume."""
    w = _WATCHERS.pop(name, None)
    if w is not None and w.task is not None:
        try:
            w.task.stop()
        except Exception:
            pass
    return w is not None


def volume_engaged(volume):
    """The ids containment is currently applying to - the ships that are IN this relic.

    Also the answer to a question missions ask for their own reasons: is the crew inside
    the ruin yet? A quest that starts when they arrive, a door that closes behind them, an
    ambush that waits until they are committed - all of them want this set, and computing
    it from depth per tick would duplicate the latch the watcher already keeps.

    Empty for an unwatched volume, and for `engage="always"`, where the question does not
    apply because containment is not gated on having been inside.
    """
    w = _WATCHERS.get(_vol_resolve(volume).name if _vol_resolve(volume) else volume)
    return frozenset(w.inside) if w is not None else frozenset()


def volume_watching(name):
    """True if a volume is currently enforced."""
    return name in _WATCHERS


def volume_watch_count():
    """Number of live watchers. The reset-ledger probe."""
    return len(_WATCHERS)


def _vol_govern_throttle(so, cap=1.0):
    """Cap a player's throttle. Only ever lowers it, never raises.

    Engine-measured: ONE write is enough, because `playerThrottle` stays where it is
    put until a helm changes it - and `max_throttle` does NOT do this (measured, it
    made no difference at all).

    A cap of 1.0 forbids WARP for free, since warp simply is `playerThrottle > 1.0`.
    Below 1.0 it is a genuine speed limit - a relic interior at 0.5 flies like a tight
    space rather than open sky, which also shrinks the tunneling budget.
    """
    try:
        if (so.data_set.get("playerThrottle", 0) or 0.0) > cap:
            so.data_set.set("playerThrottle", cap, 0)
            return True
    except Exception:
        pass
    return False


def _vol_block_jump(so):
    """Try to hold the jump/warp drives inactive.

    ENGINE-VERIFIED (2026-08-12, from the helm seat): writing these DOES stop the drive
    engaging, so a volume can genuinely forbid jumping out. Still opt-in, because
    confiscating a drive is a gameplay decision rather than a containment necessity.
    """
    try:
        so.data_set.set("jump_drive_active", 0, 0)
        so.data_set.set("warp_drive_active", 0, 0)
    except Exception:
        pass


def volume_anchor(volume, pos):
    """``(depth, anchor, radius)`` of the nearest primitive - the local containment
    sphere. Exposed because a tractor hold needs the anchor, not just the projection."""
    vol = _vol_resolve(volume)
    return (float("inf"), None, 0.0) if vol is None else vol.nearest(pos)


def volume_anchor_count():
    """Live tractor anchor objects. The reset-ledger probe."""
    return len(_ANCHORS)


def _vol_anchor_object(ship_id):
    """The invisible object a ship's containment tractor pulls against.

    One per ship, kept alive for the duration of the watch - spawning and deleting one
    per breach would churn objects, and `delete_object` frees the C++ side
    synchronously.

    `behav_station` on purpose: it is the object type grav_tether_spike uses as its
    anchor, and a station does not steer - an AI behavior here would be the
    `exclusion_radius`-zero NaN hazard. The radius is 1 rather than 0 for the same
    reason: it keeps the ship from ever reaching the anchor's exact center.
    """
    aid = _ANCHORS.get(ship_id)
    from .query import to_object
    if aid is not None and to_object(aid) is not None:
        return aid
    from .spawn import npc_spawn
    from .query import to_id
    anchor = npc_spawn(0, 0, 0, "", "#,volume_anchor", "invisible", "behav_station")
    if anchor is None:
        return None
    obj = to_object(to_id(anchor))
    if obj is None:
        return None
    try:
        obj.engine_object.exclusion_radius = 1
    except Exception:
        pass
    _ANCHORS[ship_id] = obj.id
    return obj.id


def _vol_tractor_hold(vol, ship_id, pos, margin):
    """Hold a ship inside the volume with an engine-side tractor.

    Why not `set_pos`: measured from the helm seat, a per-tick teleport clamp is
    correct on the server and looks WRONG on the client - the client predicts its own
    position, so the ship visibly leaves the volume and snaps back. A tractor moves
    the ship inside the engine's own physics, so client prediction follows it.

    `grav_tether_rope`, not a raw connection: engine-confirmed, a STATIC tether reels
    the target fully in regardless of `pull_distance` (1500 -> ~165). The rope-toggle
    pulls only when beyond the rope length and releases inside it, which held
    798/801/801 at `rope_len=800` - so inside the volume the ship still flies free.
    """
    _depth, anchor_pt, radius = vol.nearest(pos)
    if anchor_pt is None:
        return False
    aid = _vol_anchor_object(ship_id)
    if aid is None:
        return False
    from .space_objects import set_pos
    from .grav_tether import grav_tether_rope
    set_pos(aid, anchor_pt[0], anchor_pt[1], anchor_pt[2])
    rope = radius - margin
    if rope <= 0.0:
        rope = radius * 0.5
    grav_tether_rope(aid, ship_id, rope)
    return True


def _vol_tractor_release(ship_id):
    aid = _ANCHORS.get(ship_id)
    if aid is None:
        return
    try:
        from .grav_tether import grav_tether_release
        grav_tether_release(aid, ship_id)
    except Exception:
        pass


def _vol_anchors_clear():
    """Release every tractor and delete every anchor object.

    Deletion is `space_objects.delete_object`, NOT `sim.delete_object` - the simulation
    has no such method, so the old call raised AttributeError straight into the `except`
    below and every anchor survived: invisible (nothing draws them), unowned, and one
    more per watched ship on every unwatch and every mission reload.

    The `except` stays, because releasing a tractor on a ship that has since been
    destroyed is a legitimate no-op, but it no longer covers the delete.
    """
    from .query import to_object
    from .space_objects import delete_object
    for ship_id, aid in list(_ANCHORS.items()):
        _vol_tractor_release(ship_id)
        if to_object(aid) is not None:
            delete_object(aid)
    _ANCHORS.clear()


def volume_containment_tick(t=None):
    """One containment pass over every watched volume. Also directly callable."""
    if not _WATCHERS:
        return
    from .query import to_object
    from .signal import signal_emit
    from .space_objects import set_pos
    for name in list(_WATCHERS.keys()):
        w = _WATCHERS.get(name)
        vol = _VOLUMES.get(name)
        if w is None or vol is None:        # volume dropped from under the watch
            volume_unwatch(name)
            continue
        live = set()
        for agent in _vol_resolve_agents(w.agents):
            so = to_object(agent)
            if so is None:
                continue
            pos = _vol_xyz(so)
            if pos is None:
                continue
            aid = so.id
            live.add(aid)
            tier = volume_tier(vol, pos, w.scrape_band)

            # THE LATCH. Inside means engaged, from now until it leaves the relic's
            # bounding sphere entirely - which is the only "away" a volume can define,
            # since the volume itself is a graph of rooms rather than a ball.
            if w.engage == ENGAGE_ENTERED:
                if tier == TIER_INSIDE:
                    w.inside.add(aid)
                elif aid in w.inside:
                    # Released a WHOLE RELIC clear of it, not merely outside the wall.
                    # The bounding sphere of a one-room volume IS that room, so releasing
                    # at the bound would let go exactly when containment is supposed to
                    # grip - the ship is breaching, which is the case this exists for.
                    # Twice the bound is unambiguous: a held ship never gets there,
                    # because the hold puts it back inside every tick.
                    (bc, br) = vol.bound()
                    if _vol_dist(pos, bc) > br * 2.0:
                        w.inside.discard(aid)
                        _vol_tractor_release(aid)
                        w.tiers.pop(aid, None)
                if aid not in w.inside:
                    # Never been in. Not our ship: no envelope, no hold, and NO tier
                    # signals either - a passer-by must not fire volume_breach.
                    continue
            # The flight ENVELOPE applies the whole time a ship is in the volume, not
            # only when it misbehaves: a relic is a tight space, and a slower ship also
            # has a smaller tunneling budget to defeat the containment with.
            if w.speed_limit is not None:
                _vol_govern_throttle(so, w.speed_limit)
            if w.block_jump:
                _vol_block_jump(so)
            if tier == TIER_BREACH:
                if w.govern:
                    _vol_govern_throttle(so)
                if w.hold == HOLD_TRACTOR:
                    _vol_tractor_hold(vol, aid, pos, w.margin)
                elif w.hold == HOLD_CLAMP and w.clamp:
                    target = vol.nearest_inside(pos, w.margin)
                    if target is not None:
                        set_pos(aid, target[0], target[1], target[2])
            elif aid in _ANCHORS:
                # Back inside: let go, so the ship is not still roped while it flies.
                _vol_tractor_release(aid)
            was = w.tiers.get(aid, TIER_INSIDE)
            if tier != was:
                w.tiers[aid] = tier
                if tier == TIER_INSIDE:
                    event = "volume_recovered"
                elif tier == TIER_SCRAPE:
                    event = "volume_scrape"
                else:
                    event = "volume_breach"
                signal_emit(event, {"volume": name, "id": aid,
                                    "depth": vol.depth(pos)})
        # Forget agents that left the candidate set, or the tier map grows unbounded
        # across a long mission and a returning ship carries a stale tier. The latch goes
        # with it: a destroyed or docked ship is not still "inside", and an id can be
        # recycled onto something that has never been near the relic.
        for gone in [k for k in w.tiers if k not in live]:
            del w.tiers[gone]
        for gone in [k for k in w.inside if k not in live]:
            w.inside.discard(gone)
