# Player ships & consoles

Two things every crewed mission needs: player ships to fly, and consoles for the
crew to fly them from.

## Player ships

The easy path uses the LegendaryMissions **fleets** add-on. With
`PLAYER_CREATE_DEFAULT: true` in [`settings.yaml`](../home/settings.md), it
pre-creates ships from `PLAYER_LIST` and shows the right number based on
`PLAYER_COUNT`. In your `@map/` body you just position them:

```
await task_schedule(spawn_players)                    # place player ships
await task_schedule(docking_standard_player_station)  # wire up docking

# then grab references
players = to_object_list(role("__player__"))
player  = players[0]
name    = player.name
```

Doing it yourself (no add-on): create each ship with `npc_spawn` and assign it with
`assign_client_to_ship(client_id, ship_id)`. See the [spawn API](../api/procedural/spawn.md).

## Consoles

The **consoles** add-on provides the standard helm / weapons / science /
engineering / comms / main-screen consoles. Loading it in `story.json` is enough
&mdash; clients are routed to the right console automatically:

```json
{ "mastlib": ["artemis-sbs.LegendaryMissions.consoles.v1.4.0.mastlib"] }
```

Add your own console with a `@console/` label:

```
@console/status !0 ^10 "Status"
    gui_console("status")
    await gui()
```

`@console/name !priority ^sort "Display" if condition` &mdash; see the
[GUI cookbook](../cosmos/gui.md) for building console layouts.

Without LegendaryMissions, route consoles yourself with `gui_reroute_server` /
`gui_reroute_clients`; MiningDays is an example that loads no add-ons.
