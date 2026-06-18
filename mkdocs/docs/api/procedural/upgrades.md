# The upgrades system

Apply MAST-driven ability labels to ships or other agents as activatable upgrades.

## Overview

An upgrade is a MAST label that runs as a server task when activated. Upgrades are linked to their agent via the `__UPGRADE__` link, so multiple upgrades can be active on the same agent simultaneously. When an upgrade activates, the `upgrade_activated` signal is emitted with `UPGRADE_AGENT`, `UPGRADE_AGENT_ID`, and `UPGRADE` variables.

Use `upgrade_add` with `activate=False` to pre-register upgrades (e.g. at ship setup) and `upgrade_add` with `activate=True` to apply them immediately. `upgrade_remove_all` stops all running upgrade tasks and cleans up their links.

## Quick example

=== "MAST"
    ```
    == setup ==
    ~~ upgrade_add(SHIP_ID, shield_boost_label, activate=True) ~~

    == shield_boost_label ==
    ~~ set_engineering_value(SHIP_ID, "shieldStrengthFront", 200) ~~
    ```

=== "Python"
    ```python
    from sbs_utils.procedural.upgrades import upgrade_add, upgrade_remove_all

    # Add and activate immediately
    upgrade_add(SHIP_ID, shield_boost_label, activate=True)

    # Add with extra data
    upgrade_add(SHIP_ID, {"label": power_label, "multiplier": 2})

    # Remove all upgrades at end of mission
    upgrade_remove_all(SHIP_ID)
    ```

## Reacting to upgrade activation

```
//signal/upgrade_activated
"Ship {UPGRADE_AGENT.name} received an upgrade!"
```

## API

::: sbs_utils.procedural.upgrades
