# The query module

Resolve and convert agent IDs, objects, and collections between formats.

## Overview

All procedural API functions accept agents in multiple forms — raw integer IDs, `Agent` objects, `CloseData` (returned by `closest`), or `SpawnData` (returned by spawn calls). The query module provides the conversion functions that make this work.

The most commonly used functions:

- **`to_id`** — extract an integer ID from anything.
- **`to_object`** — resolve to an `Agent` object (returns `None` if destroyed).
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

## Engine data-set (blob)

Space and grid objects have an engine-level data blob for engine-readable attributes (e.g. `dock_state`, `system_damage`). Use `to_blob` / `to_data_set` to get the blob, then call `.get(key)` / `.set(key, value, index)`:

```python
blob = to_blob(ship_id)
damage = blob.get("system_damage", 0)  # index defaults to 0
blob.set("dock_state", "docked", 0)
```

## API

::: sbs_utils.procedural.query
