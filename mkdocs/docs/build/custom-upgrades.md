# Adding an item or upgrade

Discoverable items and upgrades are **data, not code**: each is a small prefab
label tagged with a `type:` in its metadata, so the system finds it via
`labels_get_type("item/")` &mdash; no registration or new syntax.

## Define the item

Write a `prefab_item_<name>` label with a metadata block and an effect body:

```
=== prefab_item_carapaction_coil
metadata: ``` yaml
type: item/upgrade/defense      # discovered by labels_get_type("item/")
key: carapaction_coil           # stable id (pickup role / inventory key)
display_text: Carapaction Coil
art: alien_2a                   # pickup art
mode: consumable                # consumable | install | resource
targets: ship, cockpit          # what it can apply to
consoles: weapons, engineering  # who may activate it (omit = any)
duration: 300                   # consumable effect length (seconds)
desc: Reinforces shields for a time.
```
    # The body is the effect. It runs server-side when the item is activated,
    # with UPGRADE_AGENT_ID (the holder) and the metadata fields as variables.
    modifier_add(UPGRADE_AGENT_ID, "all_shield_upgrade_coeff", 2.0, key, duration=duration)
    ->END
```

The effect uses [`modifier_add`](../api/procedural/modifiers.md) on the engine's
`*_upgrade_coeff` data-set keys (each defaults to `1.0`; the value is added as a
bonus fraction). Passing `duration=` makes a consumable auto-expire. Common keys:
`all_shield_upgrade_coeff`, `impulse_upgrade_coeff`, `turn_upgrade_coeff`,
`shield_max_val` (see [object_data documentation](../api/procedural/modifiers.md)).

## Spawn it as a pickup

```
item_spawn("carapaction_coil", x, y, z)          # by key
item_spawn("salvage", x, y, z, qty=5)            # one crate worth several units
```

(`pickup_spawn(x, y, z, key)` is the older argument order and still works.)

Collecting the pickup puts it in the ship's inventory; the crew then activates it from
the Upgrades tab, which calls `upgrade_add` and runs the prefab body. An item can also
apply itself the instant it is collected &mdash; give it a `pickup_trigger:` naming who it
fires for.

## Three metadata fields decide where an item comes from

This is the part that surprises people: `type:`, `price:` and `mode:` are read by
*different* systems, and two of them look like pure description.

| field | who reads it | effect |
|---|---|---|
| `type:` segments | `_item_spawn_pool` | an `upgrade` or `resource` segment puts the item in the **random world scatter** that `terrain_spawn_items` / `terrain_spawn_pickups` sample |
| `price:` | `market_purchasable` | any positive price stocks it at **station markets**, with no type check at all |
| `mode: install` | `_item_spawn_pool`, `item_activate` | **never scattered**, and **not consumed** when activated |

So `type: item/quest/rescue` on the Escape Pod is not a label, it is what keeps a carried
objective out of the loot table; and an item is buyable purely because someone wrote a
`price:`.

!!! warning "An `install` item is not consumed, so the crate survives the fitting"
    `item_activate` skips the decrement for `mode: install`. Left alone, the crate stays
    in the hold after the upgrade is bolted on and a station will buy it back at half
    price while the fitting stays fitted &mdash; which quietly halves what the upgrade
    cost. If the item represents something *fitted*, spend the crate in the body:

    ```
    set_inventory_value(UPGRADE_AGENT_ID, "grav_tug_rig_fitted", 1)
    set_inventory_value(UPGRADE_AGENT_ID, "grav_tug_rig", 0)   # fitted now, not cargo
    ```

    Note the two different keys. The **item key is an inventory key too** &mdash; buying one
    writes `set_inventory_value(ship, "grav_tug_rig", n)` &mdash; so a "fitted" flag sharing
    that name is raised by merely *carrying* the crate, and selling the crate rips the
    upgrade back out of a fitted hull.

## If the effect is not a modifier, nothing will undo it

`modifier_add(..., duration=)` expires on its own, swept by the modifier handler. That is
the **only** self-expiring path. `upgrade_add` takes no duration, `Upgrade` has no expiry
or deactivate hook, and `duration:` on its own drives nothing but the re-use cooldown and
the "active" countdown on the tab.

So a `mode: consumable` body that writes a plain inventory value is **permanent by
accident**. Give the effect its own window and read that instead of a flag:

```
=== prefab_item_tug_rig_mk1
metadata: ``` yaml
type: item/upgrade/engineering
key: tug_rig_mk1
mode: consumable
duration: 600
desc: An early-pattern grav rig - hauls as if the ship were two and a half, for a time.
```
    set_timer(UPGRADE_AGENT_ID, "tug_rig_mk1", seconds=duration)
    ->END
```

```python
# and whatever consumes it asks the window, not a flag:
if not is_timer_finished(ship_id, "tug_rig_mk1"):
    ...
```

`is_timer_finished` answers `True` for a timer that was never set, so a ship that never
fitted one falls through &mdash; the guard fails closed. An `await delay_sim(duration)` in
the body would also work (the body is a real suspendable server task), but nothing binds
that task to the holder: a destroyed ship leaves it running, and a mission reload rebuilds
the scheduler with the flag still set. A timer has no task and dies with the agent.

!!! tip "Put `for a time` in the description"
    `item_describe` expands that exact phrase to the real window, so the tab reads
    *"for 10 min"*. Any other wording stays vague.

The **Heavy Tug Rig** and **Tug Rig Mk I** in Legendary Missions are the worked pair:
permanent-and-bought against found-and-expiring, one item key each, no code outside their
own metadata blocks.

## Where they live

Mission-wide item definitions go in a `.mast` file loaded by the mission (Legendary
Missions keeps them in its `items` add-on, e.g. `item_defs.mast`). Because they're
found by `type:`, dropping a new `prefab_item_*` label into a loaded file is all it
takes to add one.

See the [Items & Upgrades](items-upgrades.md) overview and the
[items](../api/procedural/items.md) / [upgrades](../api/procedural/upgrades.md) API.
