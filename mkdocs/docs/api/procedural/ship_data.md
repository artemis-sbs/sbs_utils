# The ship_data module

Load and query the ship-definition database, and let an add-on declare ships of its own.

## Overview

Cosmos ships are defined in `data/shipData.yaml`, keyed by art ID (e.g.
`"tsn_battle_cruiser"`). This module loads that database, merges anything a mission
or add-on has contributed, and answers queries against the result.

`get_ship_data()` returns the whole merged database (a dict with a `#ship-list`).
`get_ship_data_for(key)` returns one ship's entry. `get_ship_name(key)` is the display
name, and `filter_ship_data_by_side` is how a prefab finds "a Kralien warship".

The database is loaded lazily and cached. Mission scripts do not normally need this
module directly - spawn functions look ship data up for you.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == pick_ship ==
        entry = ship_data_get_ship_data_for("tsn_battle_cruiser")
        display_name = entry.get("name", "Unknown")
        log(f"Spawning a {display_name}")
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.ship_data import (
        get_ship_data, get_ship_data_for, get_ship_name,
    )

    entry = get_ship_data_for("tsn_battle_cruiser")
    name = entry.get("name", "Unknown")

    # every ship the database knows
    for ship in get_ship_data().get("#ship-list", []):
        print(ship.get("key"), ship.get("name"))
    ```

!!! note "The MAST names carry a `ship_data_` prefix"
    The prelude registers this module with a prefix, so Python's `get_ship_data_for`
    is `ship_data_get_ship_data_for` in MAST, and `add_extra` is
    `ship_data_add_extra`.

## Adding ships from an add-on

An add-on ships a ship-data file and names it. Nothing is written:

=== ":mast-icon: {{ab.m}}"
    ```
    ship_data_add_extra("turrets/extraShipData_turrets", mod="MyMod")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.ship_data import add_extra

    add_extra("turrets/extraShipData_turrets", mod="MyMod")
    ```

`add_extra` points **both** readers at the one file: sbs_utils' own table (which is
what `filter_ship_data_by_side` and `get_ship_name` read) and the **engine** (which
is what resolves `artfileroot`, and what makes a `behav_station` fire at all).

The name takes **no extension** - the engine tries `.yaml` then `.json` itself - and
may include a logical folder. With no path it is looked for where the media system
already looks: this mission, then each media pack it pinned.

!!! tip "Put the file in a media pack, not a mastlib"
    A mastlib is a **zip**, and the engine cannot read inside one. A media pack is
    unpacked to disk once, so the engine can be handed a real folder. That is the
    whole reason this used to involve writing a file.

!!! warning "The older generating route is broken"
    `ship_data_merge_mod` reaches the engine by generating `extraShipData.json` in the
    mission folder. `get_ship_data()` then prepends that file whole on the next run -
    `#mod` entries and all - while the add-on declares the same entries again. Measured
    at **51 hulls becoming 102** from run 2 onward. Use `add_extra`.

`extra_enable(False)` turns off only the engine half, leaving the library merge in
place - useful while the engine side is in flux, since headless and the mock keep
behaving identically.

## API



::: sbs_utils.procedural.ship_data
