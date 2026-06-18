# The upgrades system

Apply MAST-driven ability labels to ships or other agents as activatable upgrades.

## Overview

An upgrade is a MAST label that runs as a server task when activated. Upgrades are linked to their agent via the `__UPGRADE__` link, so multiple upgrades can be active on the same agent simultaneously. When an upgrade activates, the `upgrade_activated` signal is emitted with `UPGRADE_AGENT`, `UPGRADE_AGENT_ID`, and `UPGRADE` variables.

Use `upgrade_add` with `activate=False` to pre-register upgrades (e.g. at ship setup) and `upgrade_add` with `activate=True` to apply them immediately. `upgrade_remove_all` stops all running upgrade tasks and cleans up their links.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        upgrade_add(ship_id, shield_boost_label, activate=True)
        ->END

    == shield_boost_label ==
        set_engineering_value(UPGRADE_AGENT_ID, "shieldStrengthFront", 200)
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.upgrades import upgrade_add, upgrade_remove_all

    upgrade_add(ship_id, shield_boost_label, activate=True)
    upgrade_add(ship_id, {"label": power_label, "multiplier": 2})
    upgrade_remove_all(ship_id)
    ```

## Reacting to upgrade activation

```
//signal/upgrade_activated
    log(f"Ship {UPGRADE_AGENT.name} received an upgrade!")
```

## API

::: sbs_utils.procedural.upgrades
