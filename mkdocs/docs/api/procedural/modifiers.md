# Modifiers system

Apply temporary or persistent stat modifications to agents.

## Overview

Modifiers are named adjustments to an agent's engineering or inventory values. Each modifier has a key (the attribute being changed), a value (the amount of change), and a source tag (who applied it — used for selective removal). Multiple modifiers with different sources can stack on the same key.

`modifier_add` registers a modifier and applies it immediately. `modifier_remove` removes the modifier and reverts its contribution. `modifier_clear` removes all modifiers from an agent.

Modifiers are used internally by the upgrade system to track stat changes applied by upgrades — when `upgrade_remove_all` is called, the upgrade's modifiers are removed cleanly.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == apply_speed_boost ==
    modifier_add(SHIP_ID, "topSpeed", 5, "speed_upgrade")
    == remove_speed_boost ==
    modifier_remove(SHIP_ID, "topSpeed", "speed_upgrade")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.modifiers import modifier_add, modifier_remove, modifier_clear

    # Apply a +5 speed modifier tagged "speed_upgrade"
    modifier_add(SHIP_ID, "topSpeed", 5, "speed_upgrade")

    # Remove just the speed_upgrade contribution
    modifier_remove(SHIP_ID, "topSpeed", "speed_upgrade")

    # Remove all modifiers on this agent
    modifier_clear(SHIP_ID)
    ```

## API

::: sbs_utils.procedural.modifiers
