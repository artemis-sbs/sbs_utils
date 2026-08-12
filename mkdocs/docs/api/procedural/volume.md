# Volume

Navigable volumes — a structure a ship can fly **inside**, modelled as the space rather
than the walls.

## Overview

The engine has exactly one collision primitive: `exclusion_radius`, a **keep-out sphere**
("other objects cannot be closer to me than this"). A hollow structure is the
*complement* of a sphere, so it cannot be built out of solid objects — approximating a
shell with many spheres is not just expensive, the boundary never lines up with the art.
Inscribe the spheres and corners are passable; circumscribe them and the ship stops in
empty space.

So a volume describes the **navigable space** instead:

| primitive | is | authored as |
|---|---|---|
| chamber | a sphere | centre + radius |
| passage | a capsule | two endpoints + radius |
| box | an axis-aligned rectangle | centre + **half**-extents |
| solid | any of the above, **subtracted** | the pillar in the middle of the room |

A ship is inside if it is inside any navigable primitive and outside every solid. A dozen
branching chambers is ~30 primitives rather than ~10,000 voxels, the boundary is smooth,
and **no engine collision is involved at all** — every prop that dresses the structure
ships `exclusion_radius = 0`.

Because containment is our own signed-distance maths, the engine's sphere-only limit does
not apply. Any shape with a distance function is available.

!!! warning "A fly-through prop must be TERRAIN"
    An AI behavior (`behav_npcship`, `behav_typhon`, …) carrying `exclusion_radius = 0`
    NaNs the engine and asserts — measured on 1.3.5 as both
    `Simulation.cpp:739 !isnan(so->pos.x)` and
    `SpaceObjectAITyphon.cpp:111 !isnan(obj->rotQuat.x)`. Terrain is passive, so it has no
    steering or rotation solve to go wrong, and a zero radius is safe there.

The same graph doubles as a **navmesh**: brains steer by writing `target_pos_*` and know
nothing about walls, so `volume_path` is what keeps them out of the rock.

## Quick example

=== ":mast-icon: {{ab.m}}"

    ```
    volume_define("relic", chambers, passages)
    volume_solid("relic", "sphere", 0, 0, 0, 320)
    volume_watch("relic", margin=60, block_jump=True)
    ```

=== ":simple-python: {{ab.pm}}"

    ```python
    volume_load("relic", layout, origin=(12000, 0, -8000))
    volume_watch("relic", margin=60)
    ```

Containment returns a **signed depth** — negative inside — so the response is graded
rather than a wall-slam:

| depth | tier | what happens |
|---|---|---|
| `< 0` | inside | free flight |
| `0 .. scrape_band` | scrape | signalled; the ship can still fly out |
| `>= scrape_band` | breach | throttle governed, then held inside |

The hold defaults to an engine-side **tractor**, not a `set_pos` clamp. A clamp is correct
on the server and looks wrong from the helm seat — the client predicts its own position,
so the ship visibly leaves and snaps back.

Damage is **not** applied here. The library emits `volume_scrape`, `volume_breach` and
`volume_recovered` on tier *change*; what they mean is the mission's call.

!!! note "The numbers behind the defaults"
    Engine 1.3.5: the MAST task cadence is **~15 Hz**, not the 5 Hz usually quoted, and a
    playership travels **60 units per tick at full warp**. That is the whole tunneling
    budget, and it is why `scrape_band` defaults to 120 — two ticks of travel, so a
    warping ship cannot skip the scrape tier entirely.

For authoring a relic as data rather than code, see
[Relic interiors](../../build/relics.md).

## API

::: sbs_utils.procedural.volume
