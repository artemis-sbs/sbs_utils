# Tutorial: Simple AI

Add basic NPC targeting behavior to an Artemis Cosmos mission.

## Create mission

Start from a starter template.

=== ":mast-icon: {{ab.m}}"
    ```bash
    .\fetch artemis-sbs mast_starter simple_ai
    ```

## Add stations

Spawn two friendly stations at known positions.

=== ":mast-icon: {{ab.m}}"
    ```
    ds1 = npc_spawn(1000, 0, 1000, "DS1", "tsn", "starbase_command", "behav_station")
    ds2 = npc_spawn(1000, 0, -1000, "DS2", "tsn", "starbase_command", "behav_station")
    ```

## Add a spawn route

A `//spawn` route fires whenever any object is spawned. `SPAWNED_ID` is automatically set to the ID of the spawned object. Use it to start an AI task for each enemy ship.

=== ":mast-icon: {{ab.m}}"
    ```
    //spawn
        ->END if not has_role(SPAWNED_ID, "raider")
        task_schedule(npc_targeting_ai, {"ship_id": SPAWNED_ID})
        ->END
    ```

## Add the AI targeting task

The targeting loop runs every 5 seconds. The `->END` guard stops the task if the ship was destroyed between ticks.

=== ":mast-icon: {{ab.m}}"
    ```
    == npc_targeting_ai ==
    --- loop
        ->END if not object_exists(ship_id)
        players = to_object_list(role("__player__"))
        if players:
            target(ship_id, to_id(players[0]), True, 1.0)
        await delay_sim(5)
        jump loop
    ```

## Spawn some enemies

Now spawn enemy ships so the `//spawn` route has something to give AI to.

=== ":mast-icon: {{ab.m}}"
    ```
    fleet_pos = Vec3.rand_in_sphere(5000, 10000, False, True)
    prefab_spawn(prefab_fleet_raider, {
        "race": "skaraan",
        "fleet_difficulty": 3,
        "START_X": fleet_pos.x,
        "START_Y": fleet_pos.y,
        "START_Z": fleet_pos.z
    })
    ```

When these ships spawn, the `//spawn` route will fire for each one, and each raider will get its own targeting task.
