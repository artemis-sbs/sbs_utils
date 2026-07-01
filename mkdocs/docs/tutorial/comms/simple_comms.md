# Tutorial: Simple Comms

Build comms menus for stations, enemies, and your own ship. Comms is
**route-based**: when a player selects an entity, the engine routes a comms event,
and the `//comms` route whose condition matches provides the menu. There's no
manual "router" to set up.

## Create the mission

Start from a starter mission:

=== ":mast-icon: {{ab.m}}"
    ```bash
    sbs fetch artemis-sbs mast_starter simple_comms
    ```

## Add some stations

Spawn two stations. The roles string's first entry is the side; add extra roles to
query them later:

=== ":mast-icon: {{ab.m}}"
    ```
    ds1 = npc_spawn(1000, 0,  1000, "DS1", "tsn, station", "starbase_command", "behav_station")
    ds2 = npc_spawn(1000, 0, -1000, "DS2", "tsn, station", "starbase_command", "behav_station")
    ```

## Station comms

A `//comms` route with a condition supplies the menu for matching targets. Inside,
`+` is a sticky button; `<<` is an incoming line (the NPC speaking) and `>>` is
outgoing (the player). Useful context: `COMMS_ORIGIN_ID` (the player) and
`COMMS_SELECTED_ID` (the target).

=== ":mast-icon: {{ab.m}}"
    ```
    //comms if has_roles(COMMS_SELECTED_ID, "station")
        + "Hail":
            >> "Hello, station."
            << [green] "DS1"
                % Good to hear from you, commander.
                % Standing by to assist.
    ```

`%` lines are alternatives &mdash; one is chosen at random each time, so repeated
hails don't feel canned.

## Enemy comms

Match a different role for a different menu:

=== ":mast-icon: {{ab.m}}"
    ```
    =$ raider red, white

    //comms if has_roles(COMMS_SELECTED_ID, "raider")
        + "Hail":
            << [$raider] "Raider"
                % We will destroy you, Terran scum!
                % You cannot win.
        + "Demand surrender" if side_are_enemies(COMMS_ORIGIN_ID, COMMS_SELECTED_ID):
            << [$raider] "Raider"
                % Never!
                % ...fine. We yield.
    ```

`=$` declares a named color/style you can reuse in dialogue titles.

## Your own ship: internal comms

Selecting your own ship (`COMMS_SELECTED_ID == COMMS_ORIGIN_ID`) is how crew
department comms work. Give each button its own colored reply:

=== ":mast-icon: {{ab.m}}"
    ```
    //comms if COMMS_SELECTED_ID == COMMS_ORIGIN_ID
        + "Sickbay":
            << [blue] "Sickbay" % Crew health is good, captain.
        + "Security":
            << [red] "Security" % All secure.
        + "Exobiology":
            << [green] "Exobiology"
                % Tests running - one moment.
    ```

For a reply that arrives *later*, schedule it instead of delaying in the button
(an `await delay_sim` inside the button would freeze the menu while it waits):

=== ":mast-icon: {{ab.m}}"
    ```
        + "Exobiology":
            << [green] "Exobiology" % Tests running - one moment.
            task_schedule(exobiology_results)

    === exobiology_results
        await delay_sim(3)
        comms_message("Results are in: indeterminate life signs.",
                      to_object_list(role("__player__")), COMMS_SELECTED_ID)
        ->END
    ```

## Submenus and navigation

Longer conversations branch into `//comms/<path>` submenus; a button navigates to
one, and `+ "Back" //comms` returns:

=== ":mast-icon: {{ab.m}}"
    ```
    //comms if has_roles(COMMS_SELECTED_ID, "station")
        + "Trade" //comms/trade

    //comms/trade
        + "Back" //comms
        + "Buy fuel":
            << [green] "DS1" % Topping you off now.
    ```

## Next steps

- Reference: [comms routes](../../mast/routes/comms.md) and the
  [Comms cookbook](../../cosmos/comms.md)
- Legendary Missions' `comms`, `internal_comms`, and `gamemaster_comms` add-ons
  provide ready-made comms trees you can load instead of writing your own.
