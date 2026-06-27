"""Legacy-style bulk terrain placement (nebulas / asteroids / mines).

Mirrors the Artemis 2.8 ``<create type="nebulas|asteroids|mines" .../>`` command,
which packs three placement modes plus determinism into one element:

  * ``start`` + ``radius``          -> a point-cloud sphere around ``start``
  * ``start`` -> ``end``            -> a distribution along a line
  * ``random_range``               -> isotropic per-object jitter
  * ``seed``                       -> reproducible placement (2.8 ``randomSeed``)
  * ``neb_type`` (nebulas)         -> a colour variant

Positions are given in **Artemis 2.8 coordinates** and converted internally via
:func:`coords.pos` (the corner-origin mirror). ``radius`` / ``random_range`` are
scalar distances and need no conversion.

This is the comfort layer; it composes the existing idiomatic Cosmos terrain spawners
(``terrain_spawn_nebula_scatter`` / ``terrain_spawn_asteroid_scatter`` /
``terrain_spawn``) -- it adds no new spawning logic. The terrain spawners are imported
lazily inside each function so the point-planning logic stays importable (and testable)
without the ``sbs`` runtime.

NOTE: the per-point ``jitter`` and ``seed`` envelope lives here for now. Promoting it
into core ``scatter`` (so any caller benefits) is the planned Layer-A follow-up.
"""

import random as _random

from sbs_utils import scatter
from sbs_utils.vec import Vec3

from .coords import pos

# 2.8 nebType 1..3 -> a Cosmos nebula colour name. Arbitrary but stable "close enough"
# choices; nebType is purely a visual variant in 2.8.
_NEB_TYPE_COLOR = {1: "red", 2: "blue", 3: "purple"}


def _to_cosmos(start, end):
    """Convert (x,y,z)-or-Vec3 ``start``/``end`` from 2.8 to Cosmos coords."""
    s = pos(*start)
    e = pos(*end) if end is not None else None
    return (s.x, s.y, s.z), ((e.x, e.y, e.z) if e is not None else None)


def _plan_points(count, start, end=None, radius=0, random_range=0):
    """Generate ``count`` Cosmos-space points (``start``/``end`` already in Cosmos).

    end given -> along the line; else radius>0 -> sphere cloud; else -> all at start.
    Then apply isotropic ``random_range`` jitter. Deterministic given the RNG state,
    so wrap with :func:`_with_seed` for reproducibility.
    """
    pts = []
    if count <= 0:
        return pts

    sx, sy, sz = start
    if end is not None:
        ex, ey, ez = end
        for v in scatter.line(count, sx, sy, sz, ex, ey, ez):
            pts.append(Vec3.create(v))
    elif radius and radius > 0:
        for v in scatter.sphere(count, sx, sy, sz, radius):
            pts.append(Vec3.create(v))
    else:
        for _ in range(count):
            pts.append(Vec3(sx, sy, sz))

    if random_range:
        rr = random_range
        for p in pts:
            p.x += _random.uniform(-rr, rr)
            p.y += _random.uniform(-rr, rr)
            p.z += _random.uniform(-rr, rr)
    return pts


def _with_seed(seed, fn):
    """Run ``fn`` with the global RNG seeded to ``seed`` (state restored after).

    Seeds the planning *and* the spawner's own internal randomness (y-scatter, type
    choice, etc.), then restores so other code is undisturbed. ``seed=None`` -> no-op.
    """
    if seed is None:
        return fn()
    state = _random.getstate()
    try:
        _random.seed(seed)
        return fn()
    finally:
        _random.setstate(state)


def create_nebulas(count, start, end=None, radius=0, random_range=0, seed=None,
                   neb_type=1, height=1000, selectable=False):
    """Spawn ``count`` nebula clusters (2.8 ``create type="nebulas"``).

    Args:
        count (int): number of clusters.
        start (Vec3 | tuple): origin in 2.8 coords.
        end (Vec3 | tuple, optional): if given, distribute start->end (line mode).
        radius (float, optional): sphere-cloud radius when ``end`` is None.
        random_range (float, optional): isotropic per-cluster jitter.
        seed (int, optional): reproducible placement (2.8 randomSeed).
        neb_type (int, optional): 2.8 nebType 1..3 -> colour.
        height (int, optional): vertical scatter passed to the spawner.
        selectable (bool, optional): selectable on 2D radar.

    Returns:
        list: the spawned nebula objects.
    """
    from sbs_utils.procedural.terrain import terrain_spawn_nebula_scatter

    cs, ce = _to_cosmos(start, end)
    color = _NEB_TYPE_COLOR.get(int(neb_type), "red")

    def go():
        pts = _plan_points(count, cs, ce, radius, random_range)
        return terrain_spawn_nebula_scatter(pts, height, cluster_color=color,
                                            selectable=selectable)

    return _with_seed(seed, go)


def create_asteroids(count, start, end=None, radius=0, random_range=0, seed=None,
                     height=1000, selectable=False):
    """Spawn ``count`` asteroids (2.8 ``create type="asteroids"``). See
    :func:`create_nebulas` for the shared argument meanings."""
    from sbs_utils.procedural.terrain import terrain_spawn_asteroid_scatter

    cs, ce = _to_cosmos(start, end)

    def go():
        pts = _plan_points(count, cs, ce, radius, random_range)
        return terrain_spawn_asteroid_scatter(pts, height, selectable=selectable)

    return _with_seed(seed, go)


def create_mines(count, start, end=None, radius=0, random_range=0, seed=None,
                 damage=5, blast_radius=1000):
    """Spawn ``count`` mines (2.8 ``create type="mines"``).

    Cosmos has no bulk-mine helper, so this places each mine with ``terrain_spawn``
    and sets ``damage_done`` / ``blast_radius`` on its data_set.
    """
    from sbs_utils.procedural.spawn import terrain_spawn

    cs, ce = _to_cosmos(start, end)

    def go():
        ret = []
        for p in _plan_points(count, cs, ce, radius, random_range):
            mine = terrain_spawn(p.x, p.y, p.z, None, "#,mine", "danger_1a", "behav_mine")
            mine.data_set.set("damage_done", damage)
            mine.data_set.set("blast_radius", blast_radius)
            ret.append(mine)
        return ret

    return _with_seed(seed, go)
