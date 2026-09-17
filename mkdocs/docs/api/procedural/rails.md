# Rails

The **rail web** — a relic's navigation graph, solved once from its geometry.

## Overview

A [volume](volume.md) describes the *space*. It does not describe the ways **through** the
space, and until this module every trip re-derived them:

```
eva_goto -> volume_doorways   (O(P^2), uncached)
         -> volume_skirts     (uncached)
         -> an N^2 visibility graph
         -> Dijkstra
```

Measured on the shipped ruins, that was **96 ms for the first destination a console picked
and 17 ms for every one after** — per console, per button press, on a bridge. And
connectivity is not a per-trip question: it is a property of the ruin. So it is solved when
the relic is built, and after that a route is a Dijkstra over cached edges:

| | before | after |
|---|---|---|
| first route | 96 ms | **0.83 ms** |
| every later route | 17 ms | **0.83 ms** |
| solving the web | — | 92 ms, **once per relic** |

## Nothing about the web is authored

There is no `Link:`, no edge list and no hand-drawn graph. An author writes rooms and
`Point:` records exactly as before; the web is derived from them. What this adds is
**density** and **attachment**:

- a room is no longer one node at its center. A 2800-unit freight hall becomes a line of
  stations along its own long axis, so there is more than one way across it and a route can
  hug a wall to get round a pillar rather than having only the one path;
- everything worth flying to is **in** the graph — a cache, a quest piece, a trigger point.
  A destination list built from the web therefore offers the things in the ruin, not only
  the rooms.

Five kinds of node, and only the first is authored:

| kind | comes from | offered as a destination |
|---|---|---|
| `place` | a `Point:` record | yes, unless `Hidden:` |
| `content` | an `Item:` or `Spawn:` when it is placed | yes |
| `doorway` | measured where two primitives overlap | no |
| `skirt` | a ring clear of each subtracted mass | no |
| `spine` | subdividing each room along its own axes | no |

Derived nodes are keyed with an `@` prefix (`@spine:14`), which no authored key can spell.

## Keeping the solve affordable

Density multiplies the node count and the visibility test is the expensive part, so an
all-pairs pass is not acceptable even once. Four measures, in the order they matter:

1. **`Volume.inside`** — a visibility walk asks "is this sample in the clear", never "how
   far is the wall", so the first primitive that swallows a sample settles it.
2. **Spatial bucketing** — only pairs within `RAIL_EDGE_SPAN` are candidates at all, so the
   edge pass is near-linear in the node count rather than quadratic.
3. **A degree cap** — without it an open room is a complete graph. Ten short legs out of a
   node is more than any route uses, and the cap is measured against the *shortest*
   candidates, so what is dropped is the long diagonals a route would not take.
4. **A node budget** — the step grows until the web fits `RAIL_MAX_NODES`. A relic cannot
   make itself unbuildable by being large.

`Rail step:` on the relic is the one dial over it: units between spine nodes, default 450,
smaller is denser.

## It must stay joined up

A denser web is worthless if part of it cannot be reached, so `rail_build` counts connected
components at the end and bridges any split with the closest visible cross pair it can find.
A relic that is genuinely in two pieces still reports as two — that is content, not a solver
failure, and `rail_stats` is what says which.

```python
stats = rail_stats("voice")
stats["components"]    # 1 is what you want
stats["orphans"]       # authored places nothing can see
```

`sbs lint` runs this at author time: `relic-disconnected`, `relic-unreachable-node` and
`relic-barrier-seals` build the web the way the game will and report what came out, so
"part of this relic cannot be flown to" is a line number rather than something a player
discovers.

## Barriers

A **barrier** is how a relic gets a shut door without anything authoring an edge. It is a
sphere in the world with a position and a size — so it can be dressed with a prop and
pointed at by a suit's tools — and what it does to the graph is derived, like everything
else here: every leg crossing it is severed until it opens.

```amd
### [the seized hatch](hatch)
---
Relic: voice
Barrier: 900, -1600, 0, 240
Clear with: beam
---
A pressure hatch, seized shut across the shaft. The bay is below it - and there is a long
way round through the sorting floor, if you would rather not cut.
```

`Opens when:` uses the same trigger grammar as `Starts when:`. A barrier with neither
`Opens when:` nor `Clear with:` can never open, which is a legitimate thing to author and
which lint reports if it walls anything off.

## Hidden places

`Hidden: yes` on a `Point:` takes it off the destination list until it is found — by flying
near it, or by anything that calls `rail_reveal`. It is a property of the **list**, never of
the graph: a route still passes *through* a hidden place, because stumbling into a secret on
the way somewhere else is the point of having one.

## Routing

```python
rail_route(name, start, goal, open_only=True)
```

`goal` is a node key or a position. It returns `[]` when there is no way — **never a
straight line**. A relic has no engine collision at all, so answering with the direct line
when the route could not be found means flying *through* the rock, which is the one thing
this whole layer exists to prevent.

`open_only=False` asks "would there be a way if this opened", which is what the lint uses.

## Diagnostics

In a running session, over the debug channel:

```
{"action": "rails"}                 # stats for every web
{"action": "rails", "name": "voice", "full": true}   # nodes, edges and barriers
```

`rail_dump(name)` is the same data in-process — the editor overlay's source, and a test's
eyes.

## See also

- [Volume](volume.md) — the space the web is solved from
- [Relic interiors](../../build/relics.md) — authoring one

::: sbs_utils.procedural.rails
