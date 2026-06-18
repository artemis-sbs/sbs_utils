# The routes module

Register and manage MAST route handlers from Python.

## Overview

Routes are MAST labels prefixed with `//` that are invoked automatically by the engine when specific events occur (damage, console focus, object selection, etc.). The routes module provides the procedural API for registering route handlers dynamically from Python or MAST, without requiring them to be declared statically in a `.mast` file.

`route_schedule` registers a label as a handler for a given route path. `route_clear` removes it. These functions are used internally by the library to wire up system routes, but mission scripts can use them to dynamically enable or disable route handlers mid-mission.

See the [Routes overview](../../../mast/routes/index.md) for the full list of route paths and their trigger conditions.

## Quick example

=== "MAST"
    ```
    == enable_damage_handler ==
    ~~ route_schedule("//damage/object /internal", on_internal_damage) ~~

    == on_internal_damage ==
    ~~ grid_take_internal_damage_at(PLAYER_ID, EVENT.source_point) ~~
    ```

=== "Python"
    ```python
    from sbs_utils.procedural.routes import route_schedule, route_clear

    # Dynamically register a damage handler
    route_schedule("//damage/object /internal", on_internal_damage_label)

    # Remove handler when no longer needed
    route_clear("//damage/object /internal", on_internal_damage_label)
    ```

## API

::: sbs_utils.procedural.routes
