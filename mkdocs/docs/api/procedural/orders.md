# Orders

Who can be given which order - decided by what the object can actually **do**. The comms
"Can order" chip, the right-click popup and drag all ask this one module, so they cannot
disagree about a unit.

An order is a MAST **objective label** whose `type` starts with `objective/orders/`. The
label says what it needs and what it may be aimed at:

~~~
=== objective_escort
metadata: ```
display_name: Escort
type: objective/orders/move/escort
valid_for: allies
requires: move
```
~~~

## Capabilities

| Capability | An object has it when |
|---|---|
| `move` | it was not spawned `behav_station` or `behav_selection` |
| `weapons` | it is a turret, carries turret mounts, or is a **mobile** hull with beams or torpedo tubes (a stock-hull `behav_station` never fires - engine-measured) |
| anything else | an addon supplies it through `orders_caps_provider(fn)` - LegendaryMissions' hangar adds `launch`, `wing_out`, `wing_delegable`, `wing_delegated` |

A mission overrides per object with `orders_caps_set(obj, add=..., remove=...)`. The
`no_orders` role blocks everything - use it for a story ship.

## `valid_for`

| Value | Accepts |
|---|---|
| `self` | no target, or the unit itself |
| `allies` | the unit's own side or an allied one |
| `hostile` | any other ship |
| `marker` | a marker object (the `marker` role - see [markers](markers.md)) |
| `point` | an empty spot in space |
| `any` | any target but itself |

Several may be listed: `valid_for: allies, marker`.

## One menu entry per instance

`orders_items(origin, selected, target)` returns `(label, instance, text)` entries. An order
whose label names `instances: <function>` appears once per instance the function returns -
LegendaryMissions uses it so one "Launch @" label becomes "Launch Red wing (4/4)" and
"Launch Gold wing (4/4)". The chosen key reaches the objective as `order_instance`.

## Stance

`orders_stance_set(obj, "hold" | "free")` - hold fire or weapons free. A host passes it on to
its turret mounts. `turret_acquire` honors it, and an explicit designation (a "Fire on"
order) still stands during hold fire.

## API

::: sbs_utils.procedural.orders
