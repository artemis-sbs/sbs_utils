# The prefab system

Reusable MAST labels that spawn entities and configure them in one call.

## Overview

A prefab is a MAST label treated as a self-contained spawn template. `prefab_spawn` runs the label as an independent task (not a child of the caller) and injects `START_X`, `START_Y`, `START_Z`, and `NAME` from the `data` dict so the label can position and name its object without needing arguments. The `OFFSET_*` params shift the spawn position without modifying the original data.

`prefab_extends` is the sub-task variant — it attaches to the calling task instead of running independently. Both set `self` and `prefab` variables so the prefab label can call back to its own task.

`prefab_autoname` is applied automatically when `NAME` contains a `#` placeholder — it replaces `#` with an auto-incrementing zero-padded integer, making it easy to produce unique names like `"Enemy 01"`, `"Enemy 02"`.

A `PrefabAll` promise (returned from grouping multiple `prefab_spawn` calls via `task_all`) collects the spawned agent IDs into a set once all tasks complete.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == spawn_enemy_wave ==
    prefab_spawn(enemy_prefab, {"START_X": 5000, "START_Z": 3000, "NAME": "Raider #"})
    prefab_spawn(enemy_prefab, {"START_X": 5500, "START_Z": 3000, "NAME": "Raider #"})
    == enemy_prefab ==
    id = spawn_enemy(START_X, START_Y, START_Z, NAME)
    add_role(id, "enemy")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.prefab import prefab_spawn, prefab_extends, prefab_autoname

    # Spawn at position with auto-numbered name
    task = prefab_spawn(enemy_prefab, {
        "START_X": 5000, "START_Z": 3000, "NAME": "Raider #"
    })

    # Spawn with position offset
    prefab_spawn(station_prefab, {"START_X": 0, "START_Z": 0}, OFFSET_X=2000, OFFSET_Z=1000)

    # Run as sub-task of current label
    prefab_extends(setup_subsection, data={"color": "red"})
    ```

## `NAME` auto-numbering

If `data["NAME"]` contains `#`, the `#` is replaced with a sequential counter:

```
"Fighter #"  →  "Fighter 01", "Fighter 02", ...
"Drone ###"  →  "Drone 001", "Drone 002", ...
```

## API

::: sbs_utils.procedural.prefab
