# The space_objects module

Spatial queries, targeting, positioning, and engineering value access for space objects.

## Overview

The space objects module provides the main tools for working with the simulation's 3D space: finding nearby objects, targeting, reading and writing positions, and reading engineering values (shields, energy, etc.).

**Spatial queries** use a broad-phase test (`broad_test`) that returns a set of agent IDs within a radius, filtered further by set operations with `role()`. `closest` and its variants return the nearest match. All of these work with the same role-based filtering as the rest of the procedural API.

**Targeting** functions (`target`, `target_pos`, `target_shoot`) tell an NPC which object or position to move toward or attack. `clear_target` stops the NPC.

**Position** functions (`get_pos`, `set_pos`) read and write 3D world coordinates as `Vec3` objects.

**Engineering values** (`get_engineering_value`, `set_engineering_value`) access named ship system parameters such as `"shieldStrengthFront"`, `"energy"`, `"speed"`, etc.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == patrol ==
    enemies = broad_test_around(get_pos(SHIP_ID), 2000) & role("enemy")
    nearest = closest(SHIP_ID, enemies)
    if nearest: target(SHIP_ID, nearest)
    == recharge ==
    set_engineering_value(SHIP_ID, "energy", 1000)
    set_pos(SHIP_ID, 0, 0, 0)
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.space_objects import (
        broad_test_around, closest, target, clear_target,
        get_pos, set_pos, get_engineering_value, set_engineering_value,
        delete_object,
    )
    from sbs_utils.procedural.roles import role

    # Find enemies within 2000 units
    pos = get_pos(SHIP_ID)
    enemies = broad_test_around(pos, 2000) & role("enemy")
    nearest = closest(SHIP_ID, enemies)
    if nearest:
        target(SHIP_ID, nearest)
    else:
        clear_target(SHIP_ID)

    # Teleport and recharge
    set_pos(SHIP_ID, 0, 0, 0)
    set_engineering_value(SHIP_ID, "energy", 1000)
    ```

## Spatial query functions

| Function | Returns |
|---|---|
| `broad_test(id, radius)` | Set of IDs within `radius` of `id` |
| `broad_test_around(pos, radius)` | Set of IDs within `radius` of a `Vec3` |
| `closest(id, candidates)` | Nearest agent from `candidates` to `id` |
| `closest_to_point(pos, candidates)` | Nearest agent from `candidates` to a `Vec3` |
| `closest_list(id, candidates, count)` | `count` nearest agents as a list |

## API

::: sbs_utils.procedural.space_objects
