# Terrain system

Spawn and manage terrain objects: nebulae, asteroids, black holes, and anomalies.

## Overview

Terrain objects are passive space objects that affect gameplay through their physical presence (collision, visual obstruction) or special engine behaviours (gravity wells, nebula interference). They are spawned with art IDs from the terrain catalogue and are otherwise treated like any other space object for targeting and role-based querying.

Use `terrain_spawn` as the general-purpose call. Convenience wrappers exist for common terrain types. All terrain spawners return an `Agent` object whose ID can be stored for later deletion with `delete_object`.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == place_terrain ==
    nebula = terrain_spawn("nebula2", 1000, 0, 2000)
    asteroid = terrain_spawn("asteroid", 3000, 0, 1000)
    add_role(nebula, "safe_zone")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.terrain import terrain_spawn
    from sbs_utils.procedural.space_objects import delete_object

    nebula = terrain_spawn("nebula2", 1000, 0, 2000)
    asteroid = terrain_spawn("asteroid", 3000, 0, 1000)

    # Remove when no longer needed
    delete_object(nebula)
    ```

## API

::: sbs_utils.procedural.terrain
