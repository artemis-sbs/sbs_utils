# Maps system

Manage ``@map`` labels that define discoverable map waypoints and regions.

## Overview

Map labels are declared in MAST with the `@map/path/name "Display"` syntax. They appear as markers on the navigation or sector map and can be discovered, hidden, or updated by the mission. The maps module provides the procedural API for interacting with registered map labels at runtime.

`map_get` retrieves a registered map label by path. `map_schedule` runs the label as a task (typically to update the map marker's state). Use the `//focus/grid` route to react when players click on map markers.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    @map/waypoints/alpha "Waypoint Alpha"
    @map/waypoints/beta "Waypoint Beta"

    == reveal_waypoints ==
    map_schedule("waypoints/alpha")
    map_schedule("waypoints/beta")
    == waypoints/alpha ==
    set_map_pos(5000, 0, 3000)
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.maps import map_get, map_schedule

    # Activate a map marker
    map_schedule("waypoints/alpha")

    # Get the label object
    label = map_get("waypoints/alpha")
    ```

## API

::: sbs_utils.procedural.maps
