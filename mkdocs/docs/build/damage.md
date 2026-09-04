# Damage

React to combat and hazards with `//damage/...` routes. They fire when an object
takes damage; the engine sets `DAMAGE_TARGET_ID`, `DAMAGE_ORIGIN_ID`,
`DAMAGE_SOURCE_ID`, and (for destroy) `DESTROYED_ID`.

| Route | Fires when |
|---|---|
| `//damage/object` | an object takes damage |
| `//damage/destroy` | an object is destroyed |
| `//damage/killed` | an object is killed |
| `//damage/internal` | internal (system) damage |
| `//damage/heat` | heat damage |

```
//damage/destroy
    log(f"Destroyed: {DESTROYED_ID}")
    ->END
```

## Wrecks

A destroyed ship can leave a wreck by using the `behav_wreck` behavior (the engine
recognizes it). LegendaryMissions' `damage` addon provides ready-made destroy
handlers that spawn wrecks.

## Internal damage & heat

Internal systems and heat are modeled through the
[internal_damage](../api/procedural/internal_damage.md) API and the
`//damage/internal` / `//damage/heat` routes. Heat builds from *overpowering* a
system; coolant is the only sink.

## Wear, condition and work orders

Damage is one axis; **condition** is the other. A grid node carries `__damaged__` or
`__undamaged__` as it always did, and wear rides on top as `__worn__` - so
`role("__undamaged__")`, `system_damage[]` and the explode check all mean exactly
what they meant before, and an all-worn ship cannot blow up.

Four tiers come out of it - damaged, worn, nominal, tuned - worth `0`, `0.75`, `1.0`
and `1.10` to the effectiveness coefficients. A node a damage-control team repaired
comes back **worn** and wants a maintenance order; a dockyard repair restores it
fully. **A healthy system can be tuned**, which is how the tuned tier is earned at
all, and nothing tunes itself: it takes an order.

An order is a link - `link(dc, "work-order", node)` - which is what it always was, so
a mission that files orders that way keeps working unchanged.

```
# What this node would accept: "repair", "maintain", or None if it is already tuned
kind = work_order_kind_wanted(node_id)
work_order_add(dc_id, node_id, kind)
work_order_set_priority(node_id, 100)      # the brain preempts its commit once
```

**Nothing happens until something writes wear.** An untouched node reads nominal and
weighs exactly `1.0`, so a mission that never opts in sees no change. LM's `damage`
addon wires up the usual sources (firing, being hit, and a per-minute beat for time
and travel); `grid_set_wear_tuning` moves every threshold and rate.

Full model, the tuning table and the gotchas:
[Work orders and maintenance](../api/procedural/work_orders.md).

See also the [DamageDispatcher](../api/dispatch/damage_dispatcher.md) and the
[Lifetime routes](../mast/routes/lifetime.md).
