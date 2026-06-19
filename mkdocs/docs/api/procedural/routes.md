# The routes module

Register and manage MAST route handlers from Python.

## Overview

Routes are MAST labels prefixed with `//` that are invoked automatically by the engine when specific events occur (damage, console focus, object selection, etc.). The routes module provides the procedural API for registering route handlers dynamically from Python or MAST, without requiring them to be declared statically in a `.mast` file.

`route_schedule` registers a label as a handler for a given route path. `route_clear` removes it. These functions are used internally by the library to wire up system routes, but mission scripts can use them to dynamically enable or disable route handlers mid-mission.

See the [Routes overview](../../mast/routes/index.md) for the full list of route paths and their trigger conditions.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == enable_damage_handler ==
        route_schedule("//damage/internal", on_internal_damage)
        ->END

    == on_internal_damage ==
        grid_take_internal_damage_at(DAMAGE_TARGET_ID, EVENT.source_point)
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.routes import route_schedule, route_clear

    route_schedule("//damage/internal", on_internal_damage_label)
    route_clear("//damage/internal", on_internal_damage_label)
    ```

## API

::: sbs_utils.procedural.routes
