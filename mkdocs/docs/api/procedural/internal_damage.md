# The internal damage system

Manage player ship engineering grid damage, repair, and ship destruction.

## Overview

The internal damage system maps 3D world hit positions to grid cells on a player ship's engineering layout. Grid objects are tagged `__undamaged__` or `__damaged__` as system roles, and damage coefficients (beam, torpedo, impulse, warp, etc.) are recomputed after every change to keep the engine in sync.

A typical damage event flows like this:

1. `//damage/internal` route fires with `EVENT.source_point`
2. Call `grid_take_internal_damage_at(DAMAGE_TARGET_ID, EVENT.source_point)` to map the hit to the nearest grid cell and damage it
3. If all undamaged system nodes are gone, `explode_player_ship` is called automatically and the `player_ship_destroyed` signal is emitted

`grid_rebuild_grid_objects` recreates the entire grid from the ship's art-ID JSON (called at mission start or respawn). `grid_restore_damcons` resets or creates the three damcon-team crew members.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    //damage/internal
        grid_take_internal_damage_at(DAMAGE_TARGET_ID, EVENT.source_point)

    //signal/player_ship_destroyed
        log("A ship has been destroyed!")
        jump game_over
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.internal_damage import (
        grid_rebuild_grid_objects,
        grid_damage_system,
        grid_repair_system_damage,
        explode_player_ship,
        respawn_player_ship,
    )

    # At mission start
    grid_rebuild_grid_objects(ship_id)

    # Programmatic damage (e.g. random engine hit)
    grid_damage_system(ship_id, "engine")

    # Repair one node
    grid_repair_system_damage(ship_id, "engine")

    # Manual destroy / respawn
    explode_player_ship(ship_id)
    respawn_player_ship(ship_id)
    ```

## Key signals

| Signal | Data keys |
|---|---|
| `player_ship_destroyed` | `DESTROYED_ID` |
| `life_form_died` | `SHIP_ID`, `LIFE_FORM_NAME` |
| `life_form_hp_changed` | `SHIP_ID`, `LIFE_FORM_ID`, `HP` |

## API

::: sbs_utils.procedural.internal_damage
