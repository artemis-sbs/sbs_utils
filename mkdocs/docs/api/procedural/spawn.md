# The spawn module

Create and delete space objects, NPCs, grid objects, and client agents.

## Overview

The spawn module wraps the engine's object-creation calls and registers each new object with the `Agent` system so it can be queried, linked, and targeted by the rest of the procedural API.

Every spawn function returns either an `Agent` object or a `SpawnData` handle you can pass to `to_id` / `to_object`. Use `delete_object` to remove objects when no longer needed — the engine and agent registry are both cleaned up.

Key helpers:

- **`spawn_npc`** — the most common call; creates an enemy or friendly ship.
- **`spawn_player`** — creates a player ship for a client console.
- **`grid_spawn`** — creates an engineering-grid object on a ship.
- **`spawn_nebula` / `spawn_monster`** — terrain and special NPC variants.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == spawn_enemies ==
    e1 = spawn_npc("Hive Emperor", "tsc", 5000, 0, 3000, "Raider 01")
    add_role(e1, "enemy")
    brain_add(e1, patrol_label)
    station = spawn_station("Generic Station", "tsn", 0, 0, 0, "Starbase Alpha")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.spawn import spawn_npc, spawn_station, delete_object

    enemy = spawn_npc("Hive Emperor", "tsc", 5000, 0, 3000, "Raider 01")
    station = spawn_station("Generic Station", "tsn", 0, 0, 0, "Starbase Alpha")

    # ... later ...
    delete_object(enemy)
    ```

## Spawn functions overview

| Function | Creates |
|---|---|
| `spawn_npc` | NPC ship (enemy, friendly, neutral) |
| `spawn_player` | Player-controlled ship |
| `spawn_station` | Station / base |
| `spawn_nebula` | Nebula terrain object |
| `spawn_monster` | Monster / special NPC |
| `spawn_generic` | Generic space object by art ID |
| `grid_spawn` | Engineering-grid object on a ship |
| `delete_object` | Removes any space object |

## API

::: sbs_utils.procedural.spawn
