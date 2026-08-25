# The query module

Resolve and convert agent IDs, objects, and collections between formats.

## Overview

All procedural API functions accept agents in multiple forms — raw integer IDs, `Agent` objects, `CloseData` (returned by `closest`), or `SpawnData` (returned by spawn calls). The query module provides the conversion functions that make this work.

The most commonly used functions:

- **`to_id`** — extract an integer ID from anything.
- **`to_object`** — resolve to an `Agent` object (returns `None` if destroyed).
- **`to_agent_list`** — resolve a collection for a **write**, the server console included.
- **`to_set`** — normalise any collection into a `set[int]` of IDs.
- **`to_list`** — normalise any collection into a `list`.
- **`object_exists`** — check if an object is still alive in the simulation.

The `is_*` functions test which ID category a value belongs to. This matters because clients, space objects, grid objects, and tasks all share the same ID space but use different high bits.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == check_target ==
        enemy_id = to_id(closest_enemy)
        obj = to_object(enemy_id)
        if object_exists(enemy_id): target(ship_id, enemy_id)
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.query import (
        to_id, to_object, to_set, object_exists,
        is_space_object_id, is_client_id,
        get_comms_selection, set_science_selection,
    )

    enemy_id = to_id(spawn_data_or_agent_or_int)
    obj = to_object(enemy_id)

    if object_exists(enemy_id):
        target(ship_id, enemy_id)

    comms_target = get_comms_selection(ship_id)
    set_science_selection(ship_id, enemy_id)
    ```

## ID type detection

| Function | True when |
|---|---|
| `is_space_object_id(id)` | NPC, player ship, station, nebula, etc. |
| `is_grid_object_id(id)` | Engineering-grid object |
| `is_client_id(id)` | Player console / client |
| `is_task_id(id)` | MAST task |
| `is_story_id(id)` | Story agent (e.g. Fleets) |

## The two meanings of id 0

Id `0` is the **server** — its console, and the agent a mission hangs mission-wide state
on. It is *also* the value a script uses to mean **"no object"**. Both readings are
correct, and which one applies is decided by what the caller does with the answer, not by
the value:

| | id 0 resolves to | Because |
|---|---|---|
| `to_object` / `to_object_list` | `None` | For a space object, 0 means "no target". `->END if to_object(target_id) is None` is everywhere in MAST, and it has to keep working. |
| `to_agent_list`, `to_client_object` | the server's agent | A write has to be able to reach the server console. |

So the **state** functions all take `0` to mean the server:

```
add_role(0, "console, mainscreen")
set_inventory_value(0, "CONSOLE_TYPE", "mainscreen")
set_timer(0, "mission_clock", minutes=20)
start_counter(0, "Mission_Elapsed_Time")
link(0, "watching", ship_id)
```

while `to_object(0)` stays `None` so an unset target id still reads as "nothing there".

!!! warning "Writers use `to_agent_list`"
    If you add a function that resolves a collection in order to **write** to it, resolve
    with `to_agent_list`, not `to_object_list` — otherwise it silently skips the server
    and the failure looks like "the feature just doesn't work on the server window".
    `to_object_list` is for space-object queries, where dropping 0 is the point.

## Engine data-set (blob)

Space and grid objects have an engine-level data blob for engine-readable attributes (e.g. `dock_state`, `system_damage`). Use `to_blob` / `to_data_set` to get the blob, then call `.get(key)` / `.set(key, value, index)`:

```python
blob = to_blob(ship_id)
damage = blob.get("system_damage", 0)  # index defaults to 0
blob.set("dock_state", "docked", 0)
```

## API

::: sbs_utils.procedural.query
