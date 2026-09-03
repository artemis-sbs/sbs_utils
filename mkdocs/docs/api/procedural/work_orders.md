# Work orders and maintenance

What a damage-control team has been told to go and do - and why systems now need
looking after, not only fixing.

## Overview

A grid node has two independent things going on.

**Damage** is the pair of roles the engine and every existing query already use:
`__damaged__` or `__undamaged__`. A damaged node is broken and contributes nothing.

**Condition** is wear on top of that, and `__worn__` is its role. Wear runs `0.0`
(perfect) to `1.0` (worn out), and lands a node in one of four tiers:

| tier | wear | draws | worth |
|---|---|---|---|
| damaged | - | the theme's `damage_colors` (Crimson) | 0 |
| worn | `>= 0.60` | the theme's `worn_colors` (Gold) | 0.75 |
| nominal | between | the node's own healthy color | 1.0 |
| tuned | `<= 0.10` | the theme's `tuned_colors` (cyan) | 1.10 |

**A worn node keeps `__undamaged__`.** The two axes never merge: `__worn__` only ever
coexists with `__undamaged__`, never with `__damaged__`. That is what keeps the
explode check, `system_damage[]` and every mission's own `role("__undamaged__")`
query meaning exactly what they always meant - **an all-worn ship cannot blow up**.

**Nothing happens until something writes wear.** An untouched node reads
`WEAR_NOMINAL` and weighs exactly `1.0`, so `set_damage_coefficients` produces
numbers identical to the `undamaged / total` fraction it replaced. A mission that
never opts in sees no change at all.

## Where the work comes from

Nothing invents maintenance. **A damage-control team patches a room; it does not
rebuild it** - so a node a team repaired comes back `__worn__` and wants a
maintenance order before it is itself again. A dockyard repair (docking, or
`grid_repair_system_damage`) restores it fully. `grid_repair_grid_objects` tells the
two apart by whether it was given a repairer.

`LegendaryMissions/damage/wear.mast` adds three more sources - firing, taking hits,
and a per-minute beat for time and travel. A mission can wire its own instead, or
none at all.

## Orders

An order is a **link**: `link(dc, "work-order", node)`. That has always been the
model and still is - missions outside this repo file orders that way and every one
of them keeps working.

> **An order is a property of the TARGET; the link is the assignment.**

A node carries at most one order - a kind and a priority, in its own inventory. Any
number of teams link to it. A target with links but no record **synthesizes** one, so
a bare `link()` reads back as an ordinary order.

Two kinds: `KIND_REPAIR` for a damaged node, `KIND_MAINTAIN` for a worn **or
nominal** one. `work_order_kind_wanted` answers what a node would *accept*, not what
it needs - **a healthy system can be tuned**, and that is how the tuned tier is
earned at all. Only an already-tuned node answers `None`. Maintenance is satisfied
when the node is TUNED, not merely when it stopped being worn; reading it the other
way made an order on a nominal node complete on its first read and get purged before
anyone moved.

A maintenance order marks its target with `MAINTENANCE_ROLE` (`__maintenance__`) so a
brain can match on it. It has to: the brain picks its idle room by role, and a
nominal node is not `__worn__`. A bare `link()` never carries it, which is right -
a bare link has always meant a repair. If a node under a tune order breaks, the order
is **promoted** to a repair at normal priority rather than left as a tune job on
something in pieces.
Priorities are plain numbers with four named rungs - `PRIORITY_LOW` (10), `NORMAL`
(50), `HIGH` (80), `CRITICAL` (100) - so a mission can invent its own and
`work_order_bump` still moves sensibly from the nearest rung.

### Orders are purged as they are read

They never used to be. `Agent._remove` clears the role and link *registries* when a
node dies, but not the entry in another agent's own link set - so a team's order on a
deleted room outlived it forever and every count drawn from it was wrong.

`work_orders_for` drops an order when the target was deleted, its host is gone or
exploding, it belongs to another ship (a grid rebuild replaces every id), the work is
already done, the worker's ship exploded, or the worker itself is dead. It walks one
team's link set - normally nought to three ids - and every caller already runs per
damcon, so there is no sweep to schedule and no module state to reset.

Repair closes a job for **every** team on it. Dropping only the repairer's link left a
second team walking to a room that was already fixed.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    # Send a team, and let the kind default to what the node needs
    work_order_add(dc_id, room_id)

    # Make it urgent - the brain preempts its current target once
    work_order_set_priority(room_id, 100)

    # What the console shows, highest priority first
    for row in work_order_rows(SHIP_ID):
        print(f"{row['name']} {row['kind']} {row['priority']} {row['workers']}")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.work_orders import (work_order_add, work_order_best,
                                                  KIND_MAINTAIN, PRIORITY_HIGH)

    work_order_add(dc_id, node_id, KIND_MAINTAIN, PRIORITY_HIGH)
    target = work_order_best(dc_id, committed)   # what the team should walk to
    ```

## Choosing what to do next

`work_order_best(worker, committed, room)` picks the closest order in the highest
live priority band - **but keeps the commit it already made unless something strictly
outranks it**. That is not a nicety: recomputing the straight-line closest every tick
makes the choice flip as a team walks the corridor between two orders. With every
order at the default priority it behaves exactly as the plain nearest-first pick it
replaced.

Preemption happens once, because the new choice is committed too. Two equal orders
can never trade a team back and forth.

## Tuning

Every threshold and arrival rate is a module global, and `grid_set_wear_tuning`
moves them at runtime:

```python
grid_set_wear_tuning(tuned_bonus=0.0)      # maintenance, but no over-unity
grid_set_wear_tuning(upkeep_rate=0)        # no time-based wear at all
grid_set_wear_tuning(beam_hit=0.0005, warp_minute=0.05)
```

Rates are named by their short name (`beam_hit` -> `WEAR_PER_BEAM_HIT`). **An unknown
name warns rather than silently doing nothing** - a typo in a dial otherwise reads
exactly like "the dial has no effect".

| dial | default | events to wear a node out |
|---|---|---|
| `beam_hit` | 0.002 | ~175 hits landed |
| `tube_shot` | 0.01 | ~35 launches |
| `shield_hit` | 0.004 | ~88 hits taken on that facing |
| `impulse_minute` | 0.004 | ~88 min at full impulse |
| `warp_minute` | 0.02 | ~18 min at warp 1 |
| `upkeep_rate` | 0.005 | ~70 min, every node |

## Themes

`worn_colors` and `tuned_colors` are optional theme maps beside `colors` and
`damage_colors`. **No shipped theme has them**, and every lookup falls back to
`GRID_WORN_COLOR` / `GRID_TUNED_COLOR`, so the tiers work out of the box. A mission
re-skins them the usual way - `extra_grid_theme.json`, or `grid_merge_mod_theme`:

```json
{"name": "cosmos",
 "worn_colors":  {"default": "#FFC83C"},
 "tuned_colors": {"default": "#40E0E0"}}
```

## Gotchas

- **`work_order_kind_wanted` answers `None` only for an already-tuned node.** Gate a
  menu on that, not on `__damaged__`, or maintenance can never be offered at all.
- **A brain node that filters on `room: __damaged__` will never see a maintenance
  order.** `ai_lifeform_move_to_work_order` defaults to no filter for that reason,
  and the idle room matches `__maintenance__` rather than `__worn__`.
- **Only a tier change recomputes coefficients.** Wear moving *within* a band costs
  one dict write, which is what makes a per-minute sweep over every node cheap.
- **`grid_wear_system` picks nodes at random** rather than spreading wear evenly. Even
  spreading would move a whole pool across the threshold together, so a ship would go
  from fine to fully worn in one tick with nothing in between.

::: sbs_utils.procedural.work_orders
