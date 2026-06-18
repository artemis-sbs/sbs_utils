# Prefabs

Reusable MAST labels that encapsulate spawn logic for entities.

## Overview

A prefab is any MAST label invoked via `prefab_spawn` or `prefab_extends`. The prefab label receives `START_X`, `START_Y`, `START_Z`, `NAME`, and any additional keys from the caller's `data` dict as task variables, then runs its own spawn and setup logic.

Prefabs are the recommended way to define reusable entity templates — NPC ships, stations, grid objects, or any complex multi-step spawn sequence — that can be instantiated many times with different parameters.

See the [prefab procedural API](../api/procedural/prefab.md) for the full function reference.

## Declaring a prefab label

Any label can act as a prefab. By convention, prefab labels are named with a `prefab_` prefix:

```
== prefab_enemy_fighter ==
~~ id = spawn_npc("fighter", "tsc", START_X, 0, START_Z, NAME) ~~
~~ add_role(id, "enemy") ~~
~~ brain_add(id, patrol_label) ~~
```

## Spawning a prefab

```
~~ prefab_spawn(prefab_enemy_fighter, {"START_X": 5000, "START_Z": 3000, "NAME": "Fighter #"}) ~~
```

The `#` in `NAME` is automatically replaced with an incrementing number: `"Fighter 01"`, `"Fighter 02"`, etc.

## Spawning multiple prefabs in parallel

```
await task_all(
    prefab_spawn(prefab_enemy_fighter, {"START_X": 1000, "START_Z": 1000, "NAME": "Alpha #"}),
    prefab_spawn(prefab_enemy_fighter, {"START_X": 2000, "START_Z": 1000, "NAME": "Beta #"}),
    prefab_spawn(prefab_enemy_fighter, {"START_X": 3000, "START_Z": 1000, "NAME": "Gamma #"}),
)
```

## Extending a prefab

`prefab_extends` runs the label as a **sub-task** of the calling task rather than as an independent task:

```
== my_label ==
~~ prefab_extends(setup_subsection, data={"tier": 2}) ~~
```
