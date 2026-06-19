# The torpedoes system

Define custom torpedo types and manage ship torpedo loadouts.

## Overview

Torpedo types are registered as shared strings on the server using a `"key:value;"` attribute format. Once registered, they can be added to a ship's loadout with `torpedo_make_available`. The weapons console reads these shared strings to populate the torpedo selector.

Use `torpedo_type` for strongly-typed Python registration or `torpedo_type_string` when building the definition dynamically (e.g. from a data file). `torp_update_value` lets you tweak individual attributes after registration.

The torpedo system is actively evolving — new `warhead` and `behavior` values will be added in future versions. Use the `other` parameter on `torpedo_type` to pass attributes not yet exposed as named params.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        torpedo_type("emp", gui_text="EMP Pulse", warhead="reduce_shields", damage=10, speed=15)
        torpedo_type("cluster", gui_text="Cluster Bomb", warhead="blast", blast_radius=1500, damage=50)
        torpedo_make_available(ship_id, "emp", count=4)
        torpedo_make_available(ship_id, "cluster", count=2)
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.torpedoes import (
        torpedo_type, torpedo_make_available, torpedo_make_unavailable,
        torpedo_get_count_for_ship, torp_update_value
    )

    torpedo_type("emp", gui_text="EMP Pulse", warhead="reduce_shields", damage=10)
    torpedo_make_available(ship_id, "emp", count=4)

    current, max_cap = torpedo_get_count_for_ship(ship_id, "emp")
    torp_update_value("emp", "damage", 20)

    torpedo_make_unavailable(ship_id, "emp")
    ```

## Torpedo attributes

| Attribute | Default | Notes |
|---|---|---|
| `speed` | 10 | Movement speed |
| `lifetime` | 25 | Seconds before expiry |
| `warhead` | `"standard"` | `"standard"`, `"blast"`, `"reduce_shields"` |
| `blast_radius` | 1000 | Used when warhead includes `"blast"` |
| `damage` | 35 | Base impact damage |
| `behavior` | `"homing"` | `"homing"` or `"mine"` |
| `energy_conversion_value` | 100 | Energy returned on disassembly |

## API

::: sbs_utils.procedural.torpedoes
