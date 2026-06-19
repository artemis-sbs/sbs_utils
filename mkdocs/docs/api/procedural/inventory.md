# The inventory system

A per-agent key→value store for arbitrary mission data.

## Overview

Every `Agent` (space object, grid object, client, or story agent) has an inventory — a Python dict stored on the agent object itself. Use it to attach mission state to an object: HP values, flags, counters, task references, anything that should follow the object around and be readable by name.

Inventory values survive for the lifetime of the agent. They are not persisted across sessions.

Key functions:

- **`set_inventory_value` / `get_inventory_value`** — write and read a single key.
- **`has_inventory`** — find all agents that have a particular key set.
- **`get_shared_inventory_value`** — shorthand for `Agent.SHARED` (the global singleton).
- **`inventory_dict`** — return the whole inventory dict for inspection.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        set_inventory_value(ship_id, "hp", 100)
        set_inventory_value(ship_id, "shield_online", True)

    == check_hp ==
        hp = get_inventory_value(ship_id, "hp", 0)
        log(f"Ship HP: {hp}")
        if hp <= 0: jump destroyed
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.inventory import (
        set_inventory_value, get_inventory_value,
        get_shared_inventory_value, has_inventory,
    )

    set_inventory_value(ship_id, "hp", 100)
    hp = get_inventory_value(ship_id, "hp", default=0)

    # Global shared state
    get_shared_inventory_value("GAME_STARTED", False)

    # Find all agents with a given key
    damaged_ships = has_inventory("hp")
    ```

## Shared inventory

`Agent.SHARED` is a singleton agent used for global mission state. Use `get_shared_inventory_value` / `set_shared_inventory_value` as shorthands:

```
set_shared_inventory_value("GAME_STARTED", True)
if get_shared_inventory_value("GAME_ENDED"): jump end_screen
```

In MAST you can also use the `shared` keyword:

```
shared GAME_STARTED = True
```

## API

::: sbs_utils.procedural.inventory
