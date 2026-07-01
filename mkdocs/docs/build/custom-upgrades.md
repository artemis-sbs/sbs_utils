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
pickup_spawn(x, y, z, "carapaction_coil")   # by key
```

Collecting the pickup applies the effect through the upgrade system (which calls
`upgrade_add`, running the prefab body). Players see held upgrades in a generic
Upgrades GUI.

## Where they live

Mission-wide item definitions go in a `.mast` file loaded by the mission (Legendary
Missions keeps them in its `items` add-on, e.g. `item_defs.mast`). Because they're
found by `type:`, dropping a new `prefab_item_*` label into a loaded file is all it
takes to add one.

See the [Items & Upgrades](items-upgrades.md) overview and the
[items](../api/procedural/items.md) / [upgrades](../api/procedural/upgrades.md) API.
