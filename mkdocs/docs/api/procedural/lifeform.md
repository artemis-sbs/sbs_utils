# Life form system

Spawn and manage grid-based crew members and lifeforms on the engineering console.

## Overview

Lifeforms are grid objects that move autonomously around the engineering grid. They are used for damcon crew members, marines, and other entities that exist inside a ship. Each lifeform has an HP value tracked via inventory, and the `life_form_died` / `life_form_hp_changed` signals fire as they take damage.

`lifeform_spawn` creates a new lifeform grid object on a ship at a given grid position. HP is set via `grid_set_hp` from the `internal_damage` module. Lifeforms can be given roles for targeting and filtering (`"damcons"`, `"crew"`, `"lifeform"`).

Damcon crew creation is handled automatically by `grid_restore_damcons` in the `internal_damage` module — you normally don't need to spawn damcons manually.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == spawn_marine ==
        marine = lifeform_spawn(ship_id, "Marine", "marine_01", 3, 4, 2, "white", "crew,marine")
        grid_set_hp(ship_id, marine, 6)
        ->END

    //signal/life_form_died
        log(f"Crew member {LIFE_FORM_NAME} has perished!")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.lifeform import lifeform_spawn
    from sbs_utils.procedural.internal_damage import grid_set_hp

    marine = lifeform_spawn(ship_id, "Marine", "marine_01", 3, 4, icon=2, color="white", roles="crew,marine")
    grid_set_hp(ship_id, marine, 6)
    ```

## API

::: sbs_utils.procedural.lifeform
