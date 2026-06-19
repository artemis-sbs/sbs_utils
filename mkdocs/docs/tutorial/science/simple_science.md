# Tutorial: Simple Science

Add science scan content to objects in an Artemis Cosmos mission.

## Create mission

Start from a starter template.

=== ":mast-icon: {{ab.m}}"
    ```bash
    .\fetch artemis-sbs mast_starter simple_science
    ```

=== ":simple-python: {{ab.pm}}"
    ```bash
    .\fetch artemis-sbs pymast_starter simple_science
    ```

## Spawn an object to scan

Spawn an NPC ship or object that the science officer can target, and tag it with a role.

=== ":mast-icon: {{ab.m}}"
    ```
    wreck = npc_spawn(5000, 0, 5000, "Derelict Alpha", "neutral", "tsn_light_cruiser", "behav_npcship")
    add_role(to_id(wreck), "derelict")
    ```

## Enable science for the object

The `//enable/science` route controls whether the scan button appears when an object is selected. It must run without `->END` to enable scanning.

=== ":mast-icon: {{ab.m}}"
    ```
    //enable/science if has_role(SCIENCE_SELECTED_ID, "derelict")
    ```

## Add scan content

The `//science` route fires when the science officer selects the object. Use `+` buttons and `<scan>` blocks with `%` lines for random scan text — one `%` line is chosen at random each time.

=== ":mast-icon: {{ab.m}}"
    ```
    //science if has_role(SCIENCE_SELECTED_ID, "derelict")
        + "Scan"
            <scan>
                % No life signs detected.
                % Hull integrity at 12 percent.
                % Drive core is offline.
        + "Status"
            <scan>
                % The ship is drifting. It has been here a long time.
    ```
