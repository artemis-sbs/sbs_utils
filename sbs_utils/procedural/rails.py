"""The RAIL WEB: a relic's navigation graph, solved once from its geometry.

A relic interior is a navigable VOLUME (`volume.py`) - rooms as spheres and boxes,
passages as capsules, pillars subtracted. That describes the SPACE. It does not describe
the ways THROUGH the space, and until this module every trip re-derived them::

    eva_goto -> volume_doorways (O(P^2), uncached)
             -> volume_skirts   (uncached)
             -> an N^2 visibility graph
             -> Dijkstra

measured at 96ms for the first destination a console picks and 17ms for every one after -
per console, per button press, on a bridge. And connectivity is not a per-trip question:
it is a property of the RUIN. So it is solved once, when the relic is built, and after
that a route is a Dijkstra over cached edges with no geometry touched at all.

WHAT IS AUTHORED, AND WHAT IS NOT
---------------------------------
**No edge is ever authored.** An author writes rooms and `Point:` records exactly as
before; the web is derived from them. What this module adds is DENSITY and ATTACHMENT:

* a room is no longer one node at its centre. A 2800-unit freight hall becomes a line of
  stations along its own long axis, so there is more than one way across it and a route
  can hug a wall to get round a cradle rather than having only the one path;
* everything worth flying to is IN the graph - a cache, a quest piece, a trigger point.
  A destination list built from the web therefore offers the things in the ruin, not only
  the rooms.

The one authored dial is a step size, and the one authored obstacle is a BARRIER - a
sphere that severs every edge crossing it until something opens it. A barrier is a thing
in the world, so it can be dressed, targeted and drawn. An edge cannot.

WHY THE SOLVE STAYS AFFORDABLE
------------------------------
Density multiplies the node count and the visibility test is the expensive part, so an
all-pairs pass is not acceptable even once. Three measures, in the order they matter:

1. `Volume.inside` - a visibility walk asks "is this sample in the clear", never "how far
   is the wall", so the first primitive that swallows a sample settles it.
2. **Spatial bucketing** - only pairs within `RAIL_EDGE_SPAN` are candidates at all, so
   the edge pass is near-linear in the node count rather than quadratic.
3. **A node budget** - the step grows until the web fits `RAIL_MAX_NODES`. A relic cannot
   make itself unbuildable by being large.

AND THE ONE THING THAT MUST NOT REGRESS
---------------------------------------
A denser web is worthless if it is not JOINED UP. Seven shipped relics fly today and all
seven must still fly, so `rail_build` counts connected components at the end and bridges
any split with the closest visible cross pair it can find. A relic that is genuinely in
two pieces still reports as two - that is content, not a solver failure, and `rail_stats`
is what says which.
"""
import math
import time

from .volume import (_vol_dist, _vol_resolve, _vol_seg_closest, _vol_xyz,
                     volume_doorways, volume_nearest_inside, volume_skirts,
                     volume_visible)

#: The clearance a web is built with, when a caller does not say.
#:
#: **THIS IS THE SHIP'S NUMBER, NOT THE RELIC'S.** A relic's authored `Margin:` is its
#: CONTAINMENT band - how far a hull may cross the plating before the tractor takes it -
#: and it runs to 90 on the wider ruins. Build a web at 90 and `false_choir`'s throat,
#: which meets its concourse in a slab 50 units deep, has no navigable point in it at all:
#: the router declares the only way in impassable. A suit is a person. 20 flies it, and it
#: is still most of a suit's length clear of the wall. `eva.ROUTE_MARGIN` is this same
#: number, imported rather than restated, because the two drifting apart is invisible
#: until a relic will not route.
RAIL_MARGIN = 20.0

#: How far apart spine nodes sit along a room's own axes. A little under a relic
#: passage's typical width, so a corridor gets several stations rather than one.
RAIL_STEP = 450.0

#: The node budget. Past this the step grows and the web is re-seeded - a large ruin gets
#: a coarser web rather than an unaffordable one.
RAIL_MAX_NODES = 320

#: How far apart two nodes may be and still be considered for an edge, as a multiple of
#: the step. This is what makes the edge pass near-linear: it is also the bucket size.
RAIL_EDGE_SPAN = 3.0

#: Nodes closer together than this fraction of the step are the same node. Doorways and
#: skirts land beside spine nodes constantly, and duplicates cost edges for nothing.
RAIL_MERGE = 0.45

#: Drop an edge a->c when a->b->c already exists and is no more than this much longer.
#: Keeps the real alternatives and throws away the redundant diagonals that make a web
#: unreadable in the editor and slower to walk.
RAIL_PRUNE_SLACK = 1.06

#: How many visible nodes a route attaches its start to, and how many candidates it is
#: willing to test to find them. A dense web means the nearest node is nearly always
#: visible, so this is small on purpose - it is the only geometry a route does.
RAIL_ATTACH = 4
RAIL_ATTACH_TRIES = 14

#: The most edges the build pass will look for from any one node, shortest first.
#:
#: WITHOUT THIS AN OPEN ROOM IS A COMPLETE GRAPH. `sink` is two big boxes, so every node
#: in it can see almost every other one, and the edge pass spent its whole time proving
#: things nobody needed proved - 1900 raw edges, two thirds of them then pruned. Ten short
#: legs out of a node is more than any route uses, and the degree cap is measured against
#: the SHORTEST candidates, so what gets dropped is the long diagonals a route would not
#: have taken anyway. The bridging pass is what guarantees this cannot disconnect anything.
RAIL_MAX_DEGREE = 10

#: How far from a barrier a node may sit and still count as its approach, as a multiple
#: of the barrier's own radius.
RAIL_APPROACH_REACH = 6.0

#: Node kinds.
KIND_PLACE = "place"
KIND_CONTENT = "content"
KIND_DOORWAY = "doorway"
KIND_SKIRT = "skirt"
KIND_SPINE = "spine"

_WEBS = {}


class _Web:
    """One relic's rail web. Not exported - reach it through the `rail_*` functions."""

    __slots__ = ("name", "volume", "margin", "step", "nodes", "order", "edges",
                 "barriers", "_cut", "stats")

    def __init__(self, name, volume, margin, step):
        self.name = name
        self.volume = volume
        self.margin = float(margin)
        self.step = float(step)
        self.nodes = {}        # key -> {"pos", "kind", "roles", "display", "hidden"}
        self.order = []        # keys in seed order - stable, so a dump is comparable
        self.edges = {}        # key -> {other: cost}
        self.barriers = {}     # key -> {"pos", "radius", "open", "display"}
        self._cut = None       # frozenset of severed (a, b) pairs, rebuilt lazily
        self.stats = {}

    def cut(self):
        """Every edge a SHUT barrier is currently severing, both directions.

        Rebuilt lazily rather than on each barrier write, because a barrier opening is
        the rare event and a route reading the set is the common one.
        """
        if self._cut is not None:
            return self._cut
        cut = set()
        shut = [b for b in self.barriers.values() if not b["open"]]
        if shut:
            for a, outs in self.edges.items():
                pa = self.nodes[a]["pos"]
                for b in outs:
                    if a >= b:
                        continue
                    pb = self.nodes[b]["pos"]
                    for bar in shut:
                        if _vol_seg_closest(bar["pos"], pa, pb)[0] < bar["radius"]:
                            cut.add((a, b))
                            cut.add((b, a))
                            break
        self._cut = frozenset(cut)
        return self._cut

    def dirty(self):
        self._cut = None


# --- seeding ---------------------------------------------------------------------------


def _rail_spine(prim, step):
    """Stations through one primitive, along its OWN axes.

    A room's centre is one point, and one point is one route. Subdividing is what gives a
    hall two ways across it - and it is measured off the room rather than off a global
    lattice, so a long thin corridor gets a line of nodes and a cube gets a cube of them.
    """
    kind = prim[0]
    out = []
    if kind == "sphere":
        c, r = prim[1], prim[2]
        out.append((c[0], c[1], c[2]))
        if 2.0 * r > step * 1.5:
            # A ring, not a lattice: the useful alternatives in a round chamber are
            # "round one side" and "round the other", not a grid of interior points.
            k = 6
            for i in range(k):
                a = 2.0 * math.pi * i / k
                out.append((c[0] + math.cos(a) * r * 0.58, c[1],
                            c[2] + math.sin(a) * r * 0.58))
        return out
    if kind == "capsule":
        a, b = prim[1], prim[2]
        span = _vol_dist(a, b)
        n = max(1, int(span / step))
        for i in range(n + 1):
            t = i / float(n)
            out.append((a[0] + (b[0] - a[0]) * t,
                        a[1] + (b[1] - a[1]) * t,
                        a[2] + (b[2] - a[2]) * t))
        return out
    c, h = prim[1], prim[2]
    axes = []
    for i in range(3):
        n = max(1, int(2.0 * h[i] / step))
        if n == 1:
            axes.append([c[i]])
        else:
            axes.append([c[i] - h[i] + 2.0 * h[i] * (j + 0.5) / n for j in range(n)])
    for x in axes[0]:
        for y in axes[1]:
            for z in axes[2]:
                out.append((x, y, z))
    return out


def _rail_seed(vol, step):
    """Every spine candidate. Not yet projected inside or deduplicated."""
    seeds = []
    for prim in vol.primitives():
        seeds.extend(_rail_spine(prim, step))
    return seeds


def _rail_cell(pos, grid):
    return (int(math.floor(pos[0] / grid)),
            int(math.floor(pos[1] / grid)),
            int(math.floor(pos[2] / grid)))


def _rail_bucket(nodes, order, span):
    """Uniform grid over the nodes, keyed on the edge span.

    This is what makes the edge pass affordable: a node only ever looks at its own bucket
    and the twenty-six around it, so the pass is linear in node count rather than square.
    """
    grid = {}
    for k in order:
        grid.setdefault(_rail_cell(nodes[k]["pos"], span), []).append(k)
    return grid


def _rail_neighbours(grid, pos, span):
    cx, cy, cz = _rail_cell(pos, span)
    out = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                out.extend(grid.get((cx + dx, cy + dy, cz + dz), ()))
    return out


def _rail_prune(edges):
    """Drop an edge that a two-leg path already covers.

    A dense web is full of redundant diagonals - a to c when a to b to c is the same
    journey. They cost a relaxation each and they make the editor overlay unreadable, and
    removing one cannot disconnect anything: the path that justified the removal is still
    there. Longest first, so the worst offenders go and the short legs survive.
    """
    dropped = 0
    for a in list(edges):
        for b in sorted(edges[a], key=lambda k: edges[a][k], reverse=True):
            direct = edges[a].get(b)
            if direct is None:
                continue
            for mid, first in edges[a].items():
                if mid == b or first >= direct:
                    continue
                second = edges[mid].get(b)
                if second is not None and first + second <= direct * RAIL_PRUNE_SLACK:
                    del edges[a][b]
                    edges[b].pop(a, None)
                    dropped += 1
                    break
    return dropped


def _rail_components(edges, order):
    """Connected components, as a list of sets of keys."""
    seen = set()
    out = []
    for k in order:
        if k in seen:
            continue
        stack = [k]
        comp = set()
        seen.add(k)
        while stack:
            cur = stack.pop()
            comp.add(cur)
            for nxt in edges.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        out.append(comp)
    return out


def _rail_bridge(vol, web, comps, margin, tries=40):
    """Join split components with the closest cross pair that can actually see each other.

    A denser web that is not JOINED UP is worse than the coarse one it replaces, and the
    bucketed edge pass deliberately refuses long edges - so a legitimate long hop (a
    doorway a room away from anything else) can be missed. This looks for one explicitly,
    and only between components, so it costs nothing on a relic that is already whole.
    """
    joined = 0
    nodes = web.nodes
    while len(comps) > 1:
        best = None
        for i in range(len(comps)):
            for j in range(i + 1, len(comps)):
                pairs = []
                for a in comps[i]:
                    pa = nodes[a]["pos"]
                    for b in comps[j]:
                        pairs.append((_vol_dist(pa, nodes[b]["pos"]), a, b))
                pairs.sort()
                for d, a, b in pairs[:tries]:
                    if volume_visible(vol, nodes[a]["pos"], nodes[b]["pos"], margin):
                        if best is None or d < best[0]:
                            best = (d, a, b, i, j)
                        break
        if best is None:
            break
        d, a, b, i, j = best
        web.edges[a][b] = d
        web.edges[b][a] = d
        joined += 1
        merged = comps[i] | comps[j]
        comps = [c for n, c in enumerate(comps) if n not in (i, j)] + [merged]
    return joined, comps


# --- building --------------------------------------------------------------------------


def rail_build(volume, places=None, margin=None, step=None, name=None):
    """Solve a volume's rail web and register it. Returns the stats dict, or None.

    Args:
        volume: a `Volume` or its registered name.
        places (dict, optional): the authored destinations, `key -> (x, y, z)` or
            `key -> {"pos", "roles", "display", "hidden", "kind"}`. These keep their own
            keys, so a route can end at a name a person chose.
        margin (float, optional): how far inside the wall a node and a leg must stay.
            Defaults to `RAIL_MARGIN`, which explains why it is the ship's number rather
            than the relic's.
        step (float, optional): spine spacing. Defaults to `RAIL_STEP`, and GROWS from
            there until the web fits `RAIL_MAX_NODES`.
        name (str, optional): register under this name instead of the volume's.

    Derived nodes are keyed with an ``@`` prefix (``@spine:14``), which no authored key
    can spell - so an authored place can never be shadowed by one.
    """
    t0 = time.perf_counter()
    vol = _vol_resolve(volume)
    if vol is None:
        return None
    key_name = name or getattr(vol, "name", None) or str(volume)
    margin = RAIL_MARGIN if margin is None else float(margin)
    step = float(step or RAIL_STEP)

    # Grow the step until the spine fits the budget. Counting seeds is far cheaper than
    # projecting them, so this loop is nearly free even when it runs several times.
    seeds = _rail_seed(vol, step)
    for _ in range(8):
        if len(seeds) <= RAIL_MAX_NODES:
            break
        step *= 1.5
        seeds = _rail_seed(vol, step)

    web = _Web(key_name, getattr(vol, "name", key_name), margin, step)
    merge = max(1.0, step * RAIL_MERGE)
    taken = {}

    def put(key, pos, kind, roles=None, display=None, hidden=False, force=False):
        # PROJECT EVERYTHING INSIDE FIRST. An authored point is a label on a room, not a
        # promise a ship fits there - every relic's `entrance` marker is outside the hull
        # by design, and caches sit against walls. A node outside the volume can see
        # nothing, contributes no edges, and quietly leaves the web a leg short.
        inside = volume_nearest_inside(vol, pos, margin)
        if inside is None:
            return None
        p = (float(inside[0]), float(inside[1]), float(inside[2]))
        cell = _rail_cell(p, merge)
        if not force and cell in taken:
            return taken[cell]
        taken.setdefault(cell, key)
        web.nodes[key] = {"pos": p, "kind": kind, "roles": tuple(roles or ()),
                          "display": display, "hidden": bool(hidden)}
        web.order.append(key)
        return key

    # Authored places first, so a derived node never takes the cell a named room wanted.
    # `force`, because a place must exist under its OWN key even when a spine node landed
    # on top of it - it is what a route is allowed to end at.
    for pkey, spec in (places or {}).items():
        if isinstance(spec, dict):
            put(pkey, spec.get("pos"), spec.get("kind") or KIND_PLACE,
                spec.get("roles"), spec.get("display"), spec.get("hidden"), force=True)
        else:
            put(pkey, spec, KIND_PLACE, force=True)

    for i, p in enumerate(volume_doorways(vol)):
        put("@door:%d" % i, p, KIND_DOORWAY)
    for i, p in enumerate(volume_skirts(vol)):
        put("@skirt:%d" % i, p, KIND_SKIRT)
    for i, p in enumerate(seeds):
        put("@spine:%d" % i, p, KIND_SPINE)

    # -- edges ---------------------------------------------------------------------
    span = step * RAIL_EDGE_SPAN
    grid = _rail_bucket(web.nodes, web.order, span)
    edges = {k: {} for k in web.order}
    tested = 0
    for a in web.order:
        pa = web.nodes[a]["pos"]
        # SHORTEST FIRST, and stop once this node has enough. In an open room almost
        # every pair is visible, so testing them all is work whose answer is always yes
        # and whose edges are then pruned again straight afterwards.
        cand = []
        for b in _rail_neighbours(grid, pa, span):
            if b == a:
                continue
            d = _vol_dist(pa, web.nodes[b]["pos"])
            if 0.0 < d <= span:
                cand.append((d, b))
        cand.sort()
        for d, b in cand:
            if len(edges[a]) >= RAIL_MAX_DEGREE:
                break
            if b in edges[a]:
                continue
            tested += 1
            if volume_visible(vol, pa, web.nodes[b]["pos"], margin):
                edges[a][b] = d
                edges[b][a] = d
    web.edges = edges
    raw = sum(len(v) for v in edges.values()) // 2
    dropped = _rail_prune(edges)

    # A DERIVED NODE WITH NO EDGES IS A DUD SEED, NOT A PIECE OF THE RUIN. A spine point
    # lands against a subtracted pillar, gets projected onto its surface, and ends up in a
    # pocket nothing can see - `ash_warren` made exactly one. Keeping it costs nothing at
    # runtime but it makes the component count lie, and the component count is the number
    # the lint and the editor banner are built on. An authored PLACE with no edges is
    # kept: that is a real problem and `orphans` is how it gets reported.
    strays = [k for k in web.order if k.startswith("@") and not edges.get(k)]
    for k in strays:
        edges.pop(k, None)
        web.nodes.pop(k, None)
    if strays:
        gone = set(strays)
        web.order = [k for k in web.order if k not in gone]
    orphans = [k for k in web.order if not edges.get(k)]

    comps = _rail_components(edges, web.order)
    bridged, comps = _rail_bridge(vol, web, comps, margin)

    web.stats = {
        "name": key_name, "volume": web.volume, "margin": margin, "step": step,
        "nodes": len(web.order), "edges": sum(len(v) for v in edges.values()) // 2,
        "raw_edges": raw, "pruned": dropped, "tested": tested,
        "strays": len(strays), "orphans": tuple(orphans),
        "components": len(comps), "bridged": bridged,
        "build_ms": (time.perf_counter() - t0) * 1000.0,
    }
    _WEBS[key_name] = web
    return dict(web.stats)


def rail_get(name):
    """The web registered under `name`, or None."""
    return _WEBS.get(name)


def rail_stats(name):
    """What the solve produced: nodes, edges, components, build time. A dict, or None.

    `components` is the number worth watching. More than one means part of the ruin
    cannot be flown to from the rest, which is the difference between "my router is
    wrong" and "this relic is not joined up".
    """
    web = _WEBS.get(name)
    return dict(web.stats) if web is not None else None


def rail_names():
    """Every registered web."""
    return list(_WEBS)


def rail_count():
    """Reset-ledger probe. Must NOT create anything by asking."""
    return len(_WEBS)


def rail_clear():
    """Drop every web. On the reset ledger beside `volumes`."""
    _WEBS.clear()


def rail_remove(name):
    """Drop one web - the galaxy-safe counterpart to `rail_clear`, which would take the
    ruin the crew is standing in."""
    return _WEBS.pop(name, None) is not None


# --- nodes -----------------------------------------------------------------------------


def rail_node(name, key):
    """One node's record, or None."""
    web = _WEBS.get(name)
    return None if web is None else web.nodes.get(key)


def rail_node_pos(name, key):
    """One node's position, or None."""
    rec = rail_node(name, key)
    return None if rec is None else rec["pos"]


def rail_nodes(name, kind=None, role=None, listed=None):
    """``[(key, record)]``, in seed order.

    Args:
        kind (str, optional): one of the ``KIND_*`` values.
        role (str, optional): only nodes carrying this role.
        listed (bool, optional): True for nodes a destination list should offer - not
            hidden, and not a derived waypoint. False for the rest.
    """
    web = _WEBS.get(name)
    if web is None:
        return []
    out = []
    for k in web.order:
        rec = web.nodes[k]
        if kind is not None and rec["kind"] != kind:
            continue
        if role is not None and role not in rec["roles"]:
            continue
        if listed is not None:
            is_listed = not rec["hidden"] and not k.startswith("@")
            if is_listed != listed:
                continue
        out.append((k, rec))
    return out


def rail_attach(name, key, pos, kind=KIND_CONTENT, roles=None, display=None,
                hidden=False):
    """Add a node to a web that is already built, and wire it in.

    A relic's contents do not all exist when it is built - `Starts when: reach ...` places
    a cache the first time somebody gets near the room holding it. Rebuilding the whole
    web for one new thing would be absurd, so a late node tests visibility against its own
    neighbourhood only, exactly as the build pass does.
    """
    web = _WEBS.get(name)
    if web is None:
        return False
    vol = _vol_resolve(web.volume)
    if vol is None:
        return False
    inside = volume_nearest_inside(vol, pos, web.margin)
    if inside is None:
        return False
    p = (float(inside[0]), float(inside[1]), float(inside[2]))
    if key in web.nodes:
        rail_detach(name, key)
    web.nodes[key] = {"pos": p, "kind": kind, "roles": tuple(roles or ()),
                      "display": display, "hidden": bool(hidden)}
    web.order.append(key)
    web.edges[key] = {}
    span = web.step * RAIL_EDGE_SPAN
    for other in web.order:
        if other == key:
            continue
        po = web.nodes[other]["pos"]
        d = _vol_dist(p, po)
        if d > span or d <= 0.0:
            continue
        if volume_visible(vol, p, po, web.margin):
            web.edges[key][other] = d
            web.edges[other][key] = d
    if not web.edges[key]:
        # Nothing in the neighbourhood could see it. Fall back to the nearest node that
        # can, at any range: one long leg beats a destination nobody can reach.
        order = sorted((k for k in web.order if k != key),
                       key=lambda k: _vol_dist(p, web.nodes[k]["pos"]))
        for other in order[:RAIL_ATTACH_TRIES]:
            po = web.nodes[other]["pos"]
            if volume_visible(vol, p, po, web.margin):
                d = _vol_dist(p, po)
                web.edges[key][other] = d
                web.edges[other][key] = d
                break
    web.dirty()
    return True


def rail_detach(name, key):
    """Remove a node and every edge touching it."""
    web = _WEBS.get(name)
    if web is None or key not in web.nodes:
        return False
    for other in list(web.edges.get(key, ())):
        web.edges[other].pop(key, None)
    web.edges.pop(key, None)
    web.nodes.pop(key, None)
    try:
        web.order.remove(key)
    except ValueError:
        pass
    web.dirty()
    return True


def rail_hide(name, key):
    """Take a node off the destination list without taking it out of the graph.

    A secret is still somewhere a route may pass THROUGH - stumbling into a hidden room on
    the way somewhere else is the point of having one.
    """
    rec = rail_node(name, key)
    if rec is None:
        return False
    rec["hidden"] = True
    return True


def rail_reveal(name, key):
    """Put a hidden node back on the destination list."""
    rec = rail_node(name, key)
    if rec is None:
        return False
    rec["hidden"] = False
    return True


def rail_is_hidden(name, key):
    """True only for a node that exists and is hidden."""
    rec = rail_node(name, key)
    return bool(rec and rec["hidden"])


# --- barriers --------------------------------------------------------------------------


def rail_barrier(name, key, pos, radius, display=None, is_open=False):
    """A sphere that severs every rail edge crossing it.

    This is how a relic gets a shut door WITHOUT anything authoring an edge. A barrier is
    a thing in the world - a seized hatch, a fall of rock - so it has a position and a
    size, it can be dressed with a prop and the weapons app can be pointed at it. What it
    does to the graph is derived, like everything else here.
    """
    web = _WEBS.get(name)
    if web is None:
        return False
    p = _vol_xyz(pos)
    if p is None:
        return False
    web.barriers[key] = {"pos": (float(p[0]), float(p[1]), float(p[2])),
                         "radius": float(radius), "open": bool(is_open),
                         "display": display}
    web.dirty()
    return True


def rail_barrier_open(name, key):
    """Open one. False when there is no such barrier, or it was open already."""
    web = _WEBS.get(name)
    if web is None or key not in web.barriers:
        return False
    if web.barriers[key]["open"]:
        return False
    web.barriers[key]["open"] = True
    web.dirty()
    return True


def rail_barrier_shut(name, key):
    """Close one again."""
    web = _WEBS.get(name)
    if web is None or key not in web.barriers:
        return False
    web.barriers[key]["open"] = False
    web.dirty()
    return True


def rail_barrier_is_open(name, key):
    """True only for a barrier that exists and is open."""
    web = _WEBS.get(name)
    if web is None:
        return False
    bar = web.barriers.get(key)
    return bool(bar and bar["open"])


def rail_barriers(name, shut_only=False):
    """``[(key, record)]`` - what the weapons app lists and the editor draws."""
    web = _WEBS.get(name)
    if web is None:
        return []
    return [(k, b) for k, b in web.barriers.items() if not (shut_only and b["open"])]


def rail_barrier_approach(name, key, from_pos=None):
    """The node to fly to in order to work on a barrier, or None.

    A barrier sits IN the way, so it is not a place - the node beside it is. This answers
    with the nearest end of an edge the barrier is currently severing, which is by
    construction both somewhere a route can reach and somewhere the barrier is in reach
    of.
    """
    web = _WEBS.get(name)
    if web is None or key not in web.barriers:
        return None
    bar = web.barriers[key]
    here = _vol_xyz(from_pos) if from_pos is not None else None
    best, best_d = None, float("inf")
    for a, b in web.cut():
        for k in (a, b):
            p = web.nodes[k]["pos"]
            if _vol_dist(p, bar["pos"]) > bar["radius"] * RAIL_APPROACH_REACH:
                continue
            d = _vol_dist(p, here) if here is not None else _vol_dist(p, bar["pos"])
            if d < best_d:
                best, best_d = k, d
    if best is not None:
        return best
    # Nothing severed - the way is open, so the nearest node to it will do.
    if not web.order:
        return None
    return min(web.order, key=lambda k: _vol_dist(web.nodes[k]["pos"], bar["pos"]))


# --- routing ---------------------------------------------------------------------------


def rail_leg(name, a, b):
    """The two ends of one edge, for a rope or a drift frame. None if there is no edge."""
    web = _WEBS.get(name)
    if web is None or b not in web.edges.get(a, {}):
        return None
    return (web.nodes[a]["pos"], web.nodes[b]["pos"])


def _rail_attach_points(vol, web, pos, margin, open_only):
    """The nodes a route may start from: the nearest few that can actually be seen."""
    order = sorted(web.order, key=lambda k: _vol_dist(pos, web.nodes[k]["pos"]))
    out = []
    for k in order[:RAIL_ATTACH_TRIES]:
        if volume_visible(vol, pos, web.nodes[k]["pos"], margin):
            out.append(k)
            if len(out) >= RAIL_ATTACH:
                break
    return out


def _rail_crosses_shut(web, a, b):
    """Whether a straight leg passes through a barrier that is still closed."""
    for bar in web.barriers.values():
        if bar["open"]:
            continue
        if _vol_seg_closest(bar["pos"], a, b)[0] < bar["radius"]:
            return True
    return False


def rail_route(name, start, goal, open_only=True):
    """Waypoints from a position to a node key (or to a position), along the web.

    Returns ``[]`` when there is no way - **never a straight line**. A relic has no engine
    collision at all, so answering with the direct line when the route could not be found
    means flying THROUGH the rock, which is the one thing this whole layer exists to
    prevent.

    Args:
        start: where the ship is.
        goal: a node key, or a position.
        open_only (bool): refuse to route through a shut barrier. Turn it off to ask
            "would there be a way if this opened", which is what the lint uses.
    """
    web = _WEBS.get(name)
    if web is None:
        return []
    vol = _vol_resolve(web.volume)
    if vol is None:
        return []
    s = _vol_xyz(start)
    if s is None:
        return []

    if isinstance(goal, str):
        grec = web.nodes.get(goal)
        if grec is None:
            return []
        gpos = grec["pos"]
        gkeys = [goal]
    else:
        gpos = _vol_xyz(goal)
        if gpos is None:
            return []
        gkeys = _rail_attach_points(vol, web, gpos, web.margin, open_only)
        if not gkeys:
            return []

    # One clean leg, and it is worth testing first: it is the common case for anything
    # already in the same room, and it costs a single visibility walk.
    if volume_visible(vol, s, gpos, web.margin) and \
            not (open_only and _rail_crosses_shut(web, s, gpos)):
        return [(float(gpos[0]), float(gpos[1]), float(gpos[2]))]

    starts = _rail_attach_points(vol, web, s, web.margin, open_only)
    if not starts:
        return []
    cut = web.cut() if open_only else frozenset()

    best = {k: _vol_dist(s, web.nodes[k]["pos"]) for k in starts}
    prev = {k: None for k in starts}
    todo = set(best)
    done = set()
    while todo:
        cur = min(todo, key=lambda k: best[k])
        todo.discard(cur)
        done.add(cur)
        for nxt, cost in web.edges.get(cur, {}).items():
            if nxt in done or (cur, nxt) in cut:
                continue
            c = best[cur] + cost
            if nxt not in best or c < best[nxt]:
                best[nxt], prev[nxt] = c, cur
                todo.add(nxt)

    ends = [k for k in gkeys if k in best]
    if not ends:
        return []
    last = min(ends, key=lambda k: best[k] + _vol_dist(web.nodes[k]["pos"], gpos))
    chain = []
    while last is not None:
        chain.append(web.nodes[last]["pos"])
        last = prev[last]
    chain.reverse()
    goal_t = (float(gpos[0]), float(gpos[1]), float(gpos[2]))
    if not chain or _vol_dist(chain[-1], goal_t) > 1e-6:
        chain.append(goal_t)
    return chain


def rail_reachable(name, start_key, open_only=True):
    """Every node reachable from one, as a set of keys. What the lint counts."""
    web = _WEBS.get(name)
    if web is None or start_key not in web.nodes:
        return set()
    cut = web.cut() if open_only else frozenset()
    seen = {start_key}
    stack = [start_key]
    while stack:
        cur = stack.pop()
        for nxt in web.edges.get(cur, ()):
            if nxt in seen or (cur, nxt) in cut:
                continue
            seen.add(nxt)
            stack.append(nxt)
    return seen


def rail_dump(name):
    """The whole web as plain data - the editor overlay's source, and a test's eyes."""
    web = _WEBS.get(name)
    if web is None:
        return None
    cut = web.cut()
    seen = set()
    edges = []
    for a, outs in web.edges.items():
        for b in outs:
            if (b, a) in seen:
                continue
            seen.add((a, b))
            edges.append({"a": a, "b": b, "cost": outs[b], "cut": (a, b) in cut})
    return {
        "stats": dict(web.stats),
        "nodes": [{"key": k, "pos": list(web.nodes[k]["pos"]),
                   "kind": web.nodes[k]["kind"],
                   "roles": list(web.nodes[k]["roles"]),
                   "display": web.nodes[k]["display"],
                   "hidden": web.nodes[k]["hidden"]} for k in web.order],
        "edges": edges,
        "barriers": [{"key": k, "pos": list(b["pos"]), "radius": b["radius"],
                      "open": b["open"], "display": b["display"]}
                     for k, b in web.barriers.items()],
    }
