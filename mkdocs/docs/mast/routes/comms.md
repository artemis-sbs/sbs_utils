# Communication related
The communication system is a powerful system for communicating with npc ships and stations. As well as internally and with engineering rooms and damcons.


The comms task provides these variables

- COMMS_ORIGIN_ID - The engine ID of the player ship for the comms console
- COMMS_ORIGIN - The python Agent of the player ship for the comms console
- COMMS_SELECTED_ID - The engine ID of the Agent being communicated with
- COMMS_SELECTED - The python Agent of being communicated with



# Enabling comms
Agents are not immediately available to the communication system. Comms must be enabled.

??? warning "It is possible to enable comms too much"
    Enabling comms runs a task to handle the comms. It is vary possible that an agent meets the conditions of one or more //enable/comms.
    roles an conditions should be created to make the agent unique enough so that it is only enabled once.
    If comms is enabled more than once, you may not see all the comms buttons expected.
    This issue may be fixed in a future version.

Enabling comms is a label, and can have addition task related data associated with it.

=== ":mast-icon: {{ab.m}}"
    ```
    //enable/comms if has_roles(COMMS_SELECTED_ID, "raider")
        # Example of data being defined with enable comms
        hail_count = 0
    ```

The same communication system is used by the engineering grid system. It uses a different route label: //enable/grid/comms

=== ":mast-icon: {{ab.m}}"
    ```
    //enable/grid/comms if has_roles(COMMS_SELECTED_ID, "damcon")
        # Example of data being defined with enable comms
        injured_count = 0
    ```

## Comms Buttons and tree navigation
Comms routes can be very rich and deep. A comms route specifies the navigation path that the buttons are added to.

Comms buttons are specified with a plus + followed by a Quoted string for the button text. Then followed by either a route to navigate to, or a block of code to execute. 

These button types can be mixed together. e.g. the code button example has a back button that is a route navigation


??? info "Button order"
    Button order is currently can sometimes result in unexpected order. This will be addressed in a future version.

=== ":mast-icon: {{ab.m}}"
    ```
    #
    # Comms buttons with route navigation
    #
    //comms if has_roles(COMMS_ORIGIN_ID, 'admiral')
        + "Spawn" //comms/admiral/spawn
        + "Selected" //comms/admiral/selected
        + "Area" //comms/admiral/area
        + "Commands" //comms/admiral/commands
    ```

=== ":mast-icon: {{ab.m}}"
    ```
    #
    # Comms buttons with code
    #
    //comms/admiral/spawn/terrain if has_roles(COMMS_ORIGIN_ID, 'admiral')
        + "Back" //comms
        + "Asteroids":
            pos = Vec3(COMMS_ORIGIN.pos)
            size = get_inventory_value(COMMS_ORIGIN_ID, f"ADMIRAL_lmb_SIZE", 5000)
            # This should be a property setting
            map_asteroid_scatter(9, 21, *pos, size, 1000, size)
        + "Nebulas":
            pos = Vec3(COMMS_ORIGIN.pos)
            size = get_inventory_value(COMMS_ORIGIN_ID, f"ADMIRAL_lmb_SIZE", 5000)
            # This should be a property setting
            map_nebula_scatter(4, 12, *pos, size, 1000, size)
        + "Black hole":
            pos = Vec3(COMMS_ORIGIN.pos)
            pos.x = pos.x + 100
            terrain_spawn_black_hole(*pos.xyz)
        + "Monster":
            pos = Vec3(COMMS_ORIGIN.pos)
            pos.x = pos.x + 100
            typhon_classic_spawn(*pos.xyz)
        + "Minefield":
            pos = Vec3(COMMS_ORIGIN.pos)
            size = get_inventory_value(COMMS_ORIGIN_ID, f"ADMIRAL_lmb_SIZE", 5000)
            map_mine_scatter(4, 10, *pos, size, 1000, size)
    ```

## More
The Admiral comms demonstrate many different whay that comms buttons and navigation can work.

This documentation may grow over time, but for now refer to that file for examples that include:

- Complex comms tree
- Dynamic buttons from the simulation data
- etc.

[Admiral comms](https://github.com/artemis-sbs/LegendaryMissions/blob/main/zadmiral/admiral_comms.mast)



