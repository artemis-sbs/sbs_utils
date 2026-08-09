# Turret

An **emplacement**: an object whose whole job is to acquire a target and shoot it, and
which never moves. Deployable defense towers and autonomous weapon mounts are the same
code here - they differ only in where their position comes from ([mount](mount.md)).

The engine's beams do the firing; this module only ever writes `target_id`, through
[`target_shoot`](space_objects.md). That is what keeps a turret from chasing its victim.

!!! warning "A turret must spawn a hull the mission ships itself"
    Engine-measured (1.3.5): a `behav_station` fires **only** from a hull declared through
    `ship_data_merge_mod`. Two stock hulls stayed silent with the
    identical `target_shoot()` call; two add-on hulls fired. A turret on stock starbase
    art is a decorative box.

!!! warning "Beam stats cannot be read or tuned per object"
    `beamRange` / `beamCount` / `beamDamage` read `None` on stock engine hulls - they live
    in the engine's ship table, not the data_set. `turret_range()` returns what the author
    configured, and a turret variant with different beams needs its **own shipData entry**.
    Keep the configured range in step with the hull, because nothing can check it for you.

## Targeting policy

`turret_acquire()` is the single place the policy lives, in priority order:

| | rule |
|---|---|
| 1 | a **designated** target (a player or GM order), while it lives and is in range - never re-evaluated |
| 2 | the **current** target, until `hold_seconds` expires, while inside `range * hold_slack` |
| 3 | otherwise **scan**: nearest (or weakest) hostile matching the `targets` role expression |

Rule 2 is the whole anti-thrash rule. Without it a turret between two enemies re-picks
every scan and effectively never fires.

Allegiance comes from [`side_hostile_ships`](sides.md), so a ceasefire stops a turret with
no tag to keep in sync, and wrecks and surrendered ships are spared automatically.

## API

::: sbs_utils.procedural.turret
