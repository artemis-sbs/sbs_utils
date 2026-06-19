# The ship_data module

Load and query the ship-definition JSON database.

## Overview

Cosmos ships are defined in a JSON database keyed by art ID (e.g. `"tsn_battle_cruiser"`). The `ship_data` module loads this database and provides helpers for looking up ship properties such as display name, base stats, and available systems.

`get_ship_data` returns the raw dict for a given art ID. `get_all_ship_data` returns the entire database. `get_ship_data_value` is a convenience wrapper that reads a single key from a ship's entry with a default fallback.

The database is loaded lazily and cached. Mission scripts do not normally need to interact with this module directly — higher-level spawn functions look up ship data automatically.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == pick_ship ==
        ship_db = get_ship_data("tsn_battle_cruiser")
        display_name = ship_db.get("name", "Unknown")
        log(f"Spawning a {display_name}")
        speed = get_ship_data_value("tsn_battle_cruiser", "topSpeed", 10)
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.ship_data import (
        get_ship_data, get_all_ship_data, get_ship_data_value,
    )

    # Single ship lookup
    data = get_ship_data("tsn_battle_cruiser")
    name = data.get("name", "Unknown")

    # Key with default
    speed = get_ship_data_value("tsn_battle_cruiser", "topSpeed", 10)

    # Iterate all ships
    for art_id, ship in get_all_ship_data().items():
        print(art_id, ship.get("name"))
    ```

## Common ship data keys

| Key | Description |
|---|---|
| `"name"` | Display name |
| `"side"` | Default faction side |
| `"race"` | Race/species string |
| `"topSpeed"` | Maximum speed |
| `"shieldStrengthFront"` / `"shieldStrengthBack"` | Shield strength |
| `"maxEnergy"` | Energy capacity |

## API

::: sbs_utils.procedural.ship_data
