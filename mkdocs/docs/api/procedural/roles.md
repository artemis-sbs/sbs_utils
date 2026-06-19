# The roles system

Tag agents with named labels for targeting, querying, and conditional logic.

## Overview

Roles are string tags attached to an agent's in-memory role set. Unlike `side` (which is a single engine-level value), roles are dynamic, stackable, and invisible to the simulation engine itself — they live entirely in the Python/MAST layer.

Common uses:

- **Targeting** — `closest(ship_id, role("enemy"))` finds the nearest enemy.
- **Filtering** — `broad_test_around(pos, 1000) & role("station")` finds all stations in range.
- **State flags** — add `"__damaged__"` or `"exploded"` to track object state.
- **Class membership** — ship art IDs are automatically added as roles, so `role("cruiser")` matches all cruisers.
- **Side** — the object's side string is also included as a role, so `role("tsn")` matches all TSN objects.

`role()` returns a set of IDs that have the given role, usable in set operations. Multiple roles can be combined with `&` (intersection) or `|` (union).

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        add_role(enemy_id, "target_priority")

    == targeting ==
        nearest = closest(ship_id, role("target_priority"))
        target(ship_id, nearest)

    == on_explosion ==
        add_role(ship_id, "exploded")
        remove_role(ship_id, "target_priority")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.roles import add_role, remove_role, has_role, role

    add_role(enemy_id, "target_priority")
    remove_role(enemy_id, "target_priority")

    if has_role(enemy_id, "target_priority"):
        log("Still a priority target")

    priority_stations = role("target_priority") & role("station")
    targets = role("enemy") | role("hostile")
    ```

## Using with targeting

```
close = closest(ship_id, role("spy"))
close = closest(ship_id, role("station"))   # ship class names are roles
close = closest(ship_id, role("tsn"))        # side is also a role
```

## System roles

Some roles are managed automatically by the engine and library:

| Role | Set by |
|---|---|
| `"__undamaged__"` / `"__damaged__"` | `grid_rebuild_grid_objects` / `grid_damage_grid_object` |
| `"exploded"` | `explode_player_ship` |
| `"_moving_"` | grid movement system |
| `"damcons"`, `"lifeform"` | `grid_restore_damcons` |
| ship art ID (e.g. `"tsn_battle_cruiser"`) | `spawn_npc` / `spawn_player` |

## API

::: sbs_utils.procedural.roles
