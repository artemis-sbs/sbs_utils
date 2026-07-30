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

## Creating player ships more than once

Every `spawn_*` call makes a **new** object, so setup that runs twice builds everything
twice. Player ships have a natural name — their **slot** — so they can be created safely:

| Function | Does |
|---|---|
| `player_ensure(slot, x, y, z, ship_key, name, side)` | The ship for that slot, creating one only if the slot is empty |
| `player_slot_id(slot)` | The live ship holding a slot, or `None` |
| `player_slots()` | Every filled slot, as `{slot: id}` |
| `players_reset()` | Delete all player ships, freeing every slot |

`player_ensure` compares against the **live game**, not a "have I run before" flag, which
is what keeps deliberate re-runs working: after `players_reset()` or a new simulation the
ships are gone and the next call rebuilds them, a destroyed ship can be remade, and a
late-joining crew's slot is filled without disturbing the others. An existing ship is
returned untouched — use `a2x_place_player` to move or rename one in place.

See [Signal routes](../../mast/routes/signals.md#running-setup-only-once) for when to
reach for this instead of a `once` route.

## API

::: sbs_utils.procedural.spawn
