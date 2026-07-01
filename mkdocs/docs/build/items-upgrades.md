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
