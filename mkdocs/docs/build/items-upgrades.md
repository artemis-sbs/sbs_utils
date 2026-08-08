# Items & upgrades

Discoverable **items** are collected in space and applied through the **upgrade**
system, all driven by a data registry &mdash; so adding a new pickup is data, not
code.

- **Items** &mdash; spawn pickups; collecting one applies its effect. See the
  [items API](../api/procedural/items.md).
- **Upgrades** &mdash; apply effects to a ship, shown in a generic Upgrades GUI.
  `upgrade_add` emits an `upgrade_activated` signal
  (`UPGRADE_AGENT`, `UPGRADE_AGENT_ID`, `UPGRADE`). See the
  [upgrades API](../api/procedural/upgrades.md).
- **Modifiers** &mdash; upgrades often adjust ship `data_set` coefficients through
  [modifiers](../api/procedural/modifiers.md) (flat / additive / multiplicative).

```
//signal/upgrade_activated
    log(f"Upgrade collected")
```

## What a kill leaves behind

A drop table says what an object drops when it dies, keyed by **role** — because loot
follows from what a ship *is*. Write it as a `Drops` section in AMD, one record per
role:

```amd
## [Drops](drops)

### [Condemned Hulk](target_drone)
---
Drops: none
---
Practice targets carry nothing.

### [Raider](raider)
---
Drops: salvage x2-4, contraband 20%
---
```

Each entry is a key plus optional count and chance, in any order:

| Form | Means |
|---|---|
| `salvage` | one, always |
| `salvage x3` | three, always |
| `salvage x2-4` | between two and four |
| `contraband 20%` | one, 20% of the time |
| `salvage x2-4 20%` | both |
| `none` | nothing at all |

The record **key is the role** the table applies to, and the **first authored role
wins** — so a specific role written above a general one overrides it.

!!! warning "No table and an empty table are different"
    A role with **no** table drops whatever it always dropped (the library's
    hand-written defaults — a hostile leaves a random trade good, a wreck rolls an
    upgrade by race). `Drops: none` means **this one drops nothing**. Collapsing the
    two would make `Drops: none` a no-op, which is the whole reason the field exists:
    condemned hulks on a live-fire range were leaving contraband, because they are
    spawned hostile so Weapons can lock them.

`sbs lint` checks the keys: a drop naming no item is reported as `dangling-drop`,
because otherwise a typo is a table that silently yields nothing. It only checks when it
can see what an item *is* -- an item declared in the mission's own `.mast` (`type: item/`
with a `key:`) or as an AMD record. A mission whose items all live in an add-on the
linter cannot read gets no drop warnings rather than a wrong one.

## One pickup, several units

A pickup is normally worth one of its item. `qty` makes a single object worth several
— a salvage cache, an ore seam:

```
item_spawn("salvage", x, y, z, qty=24)
```

Without it a bulk resource needs one object per unit: a job wanting 24 salvage would
scatter 24 collectibles across the map, which is both object churn and a tedious flight
rather than a pickup. Collecting one credits the whole quantity at once (and says so).
Pickups that don't pass `qty` are unchanged — absent means one.
