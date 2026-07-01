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

See also the [DamageDispatcher](../api/dispatch/damage_dispatcher.md) and the
[Lifetime routes](../mast/routes/lifetime.md).
