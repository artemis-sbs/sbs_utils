# Prefabs

Reusable MAST labels that make something: a ship, a station, a fleet, a nebula, a
lifeform, a side.

## Overview

A prefab is a label run as its own task by `prefab_spawn` (or as a sub-task by
`prefab_extends`). Whatever you hand it in `data` becomes its variables, it does its spawn
and setup, and it ends by yielding what it made.

Prefabs are the recommended way to define reusable things that are made many times with
different settings - and they are how AMD content creates everything it creates (see
[Creating things from AMD](../build/prefabs-from-amd.md)).

See the [prefab procedural API](../api/procedural/prefab.md) for the full function reference.

## Declaring a prefab label

By convention a prefab label is named `prefab_...` and carries a metadata block with its
**type** and its **arguments**:

```
=== prefab_enemy_fighter
metadata: ``` yaml
type: prefab/npc/fighter
display_text: Fighter
side_value: raider
art: kralien_fighter
```
    default name = "Fighter"
    obj = npc_spawn(START_X, START_Y, START_Z, name, side_value + ", fighter", art, "behav_npcship")
    brain_add(to_id(obj), patrol_label)
    yield result to_id(obj)
```

- **`type: prefab/...`** is how the prefab is found by kind: the GM spawn menu lists
  `labels_get_type("prefab/npc")`, and AMD's `Prefab: npc/fighter` resolves it.
- **Metadata keys are arguments with defaults.** They become task variables, and anything
  the caller passes overrides them. So does every `default x = ...` in the body.
- **`yield result`** hands back what was made - an id, or a set of ids. Never
  `yield result None`: it hangs anything awaiting the prefab.

The metadata block goes above any indented body line, with its fence at column 0.

## Spawning a prefab

```
prefab_spawn(prefab_enemy_fighter, {"START_X": 5000, "START_Z": 3000, "NAME": "Fighter #"})
fighter_id = await prefab_spawn(prefab_enemy_fighter, {"START_X": 0, "START_Z": 0})
```

The prefab does not inherit the caller's variables - only what is in `data`, plus its own
metadata. The `#` in `NAME` is replaced with an incrementing number: `"Fighter 01"`,
`"Fighter 02"`, and so on.

To name a prefab by its type rather than its label, or from Python:

```
ref = prefab_resolve("npc/fighter")          # the label, or a library default
obj = prefab_create("npc/fighter", {"START_X": 0, "START_Y": 0, "START_Z": 0})
```

`prefab_create` returns what the prefab made when it finishes at once (an object, an id or
a set of ids), its task when it awaits first, and None - with a logged reason - when
nothing resolves. With `family=` and `key=` it is keyed: a second call returns what is
still alive, and a destroyed one is made again.

## Spawning multiple prefabs in parallel

```
await task_all(
    prefab_spawn(prefab_enemy_fighter, {"START_X": 1000, "START_Z": 1000, "NAME": "Alpha #"}),
    prefab_spawn(prefab_enemy_fighter, {"START_X": 2000, "START_Z": 1000, "NAME": "Beta #"}),
    prefab_spawn(prefab_enemy_fighter, {"START_X": 3000, "START_Z": 1000, "NAME": "Gamma #"}),
)
```

## Extending a prefab

`prefab_extends` runs the label as a **sub-task** of the calling task rather than as an
independent task:

```
== my_label ==
    prefab_extends(setup_subsection, data={"tier": 2})
```
