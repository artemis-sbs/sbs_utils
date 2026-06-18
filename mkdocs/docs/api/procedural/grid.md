# Grid object system

Query, move, and theme engineering-grid objects on player ships.

## Overview

Engineering-grid objects are the nodes visible on the damage-control console: system rooms (weapon, engine, sensor, shield), hallways, damcon-team crew, markers, and tools. Each is an `Agent` with a host ship ID and a position in a 2D grid coordinate space.

Common tasks:

- **`grid_objects(ship_id)`** — get the set of all grid-object IDs on a ship. Combine with `role()` to filter by type: `grid_objects(ship_id) & role("engine")`.
- **`grid_objects_at(ship_id, x, y)`** — get objects at a specific cell.
- **`grid_closest(id, candidates)`** — find the nearest grid object to another.
- **`grid_move(id, x, y)`** — path the grid object to a target cell.
- **`grid_pos_data(id)`** — get current `(x, y, path_length)` of a moving object.

The **theme system** controls icon appearance. `grid_get_grid_theme` and `grid_get_item_theme_data` look up icon indices, colors, and damage colors by role, falling back to `"default"` entries.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == repair_run ==
        damaged = grid_objects(ship_id) & role("__damaged__")
        if len(damaged) == 0: jump done
        target_go = to_object(next(iter(damaged)))
        x, y, _ = grid_pos_data(target_go.id)
        grid_move(damcon_id, int(x), int(y))
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.grid import (
        grid_objects, grid_objects_at, grid_closest,
        grid_move, grid_pos_data, grid_get_grid_theme,
    )
    from sbs_utils.procedural.roles import role

    damaged_engines = grid_objects(ship_id) & role("__damaged__") & role("engine")
    grid_move(damcon_id, target_x, target_y)
    curx, cury, path_len = grid_pos_data(damcon_id)
    ```

## Grid roles

| Role | Objects |
|---|---|
| `"weapon"` | Weapon system nodes |
| `"engine"` | Engine system nodes |
| `"sensor"` | Sensor system nodes |
| `"shield"` | Shield system nodes |
| `"damcons"` / `"lifeform"` | Damcon crew members |
| `"marker"` | Position marker |
| `"rally_point"` | Damcon idle point |
| `"hallway"` | Damage-fire hallway markers |
| `"__undamaged__"` / `"__damaged__"` | Damage state |

## API

::: sbs_utils.procedural.grid
