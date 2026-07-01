# Anatomy of a mission

Every `story.mast` has the same shape. Read Secret Meeting top to bottom and you
see it: **shared state → NPCs → sides → media → a `@map/` label that builds the
world and runs the game → helper labels**. Learn this shape once and the cookbook
pages slot into it.

## The order

Top-level code runs first (and once for `shared`), so define things before the
code that uses them:

1. **Shared state** &mdash; `shared` variables the whole story needs.
2. **Lifeforms** &mdash; NPCs (an Admiral, station crew) for comms and faces.
3. **Sides** &mdash; create sides and set their relations.
4. **Media** &mdash; `@media/music` / `@media/skybox`. *These labels execute, so put
   shared data above them.*
5. **`@map/` label** (server-only) &mdash; its `metadata` exposes setup options, then
   its body builds the world, spawns players, and runs the game.
6. **Helper labels** &mdash; reusable tasks (send a message, spawn a wave).

## Minimal skeleton

Copy this and fill in the blanks:

```
# 1. shared state
shared home_id = None

# 2. NPCs (for comms faces)
shared admiral = lifeform_spawn("Admiral Harkin", random_terran(), "admiral")

# 3. sides
tsn    = await prefab_spawn(prefab_side_generic, data={"key":"tsn", "name":"TSN", "color":"#07F"})
raider = await prefab_spawn(prefab_side_generic, data={"key":"raider", "name":"Raider", "color":"#F00"})
side_set_relations(tsn, raider, sbs.DIPLOMACY.HOSTILE)

# 4. media
@media/music/default "Cosmos Default Music"
@media/skybox/sky-bored-alice "borealis"

# 5. the map (server-only)
@map/my_mission "My Mission"
" Defend the station from raiders.
metadata: ``` yaml
Properties:
    Player Ships: 'gui_int_slider("$text:int;low: 1.0;high:8.0;", var="PLAYER_COUNT")'
    Difficulty:   'gui_int_slider("$text:int;low: 1.0;high:11.0;", var="DIFFICULTY")'
```
    # build the world
    home_id = to_id(npc_spawn(0,0,0, "Home Base", "tsn, station", "starbase_civil", "behav_station"))
    set_face(home_id, random_terran(civilian=True))

    # player ships + docking (from the LegendaryMissions add-ons)
    await task_schedule(spawn_players)
    await task_schedule(docking_standard_player_station)

    # game end conditions
    game_end_condition_add(destroyed_all(role("__player__")), "All ships lost.", False)
    game_end_condition_add(destroyed_any(home_id), "Base destroyed.", False)

    # kick off, then loop
    task_schedule(spawn_wave)
--- game_loop
    await delay_sim(120)
    task_schedule(spawn_wave)
    -> game_loop

# 6. helper labels
=== spawn_wave
    pos = Vec3.rand_in_sphere(3000, 6000, False, True)
    prefab_spawn(prefab_fleet_raider, {"race":"skaraan", "fleet_difficulty": int(DIFFICULTY-1),
                 "START_X": pos.x, "START_Y": pos.y, "START_Z": pos.z})
    ->END
```

## What each part does

- **`shared`** state is set once (by the server) and visible to every task &mdash;
  see [gotchas](../mast/gotchas.md).
- **Lifeforms, sides & faces** &mdash; [Sides, lifeforms & faces](sides-lifeforms.md).
- **`@media/`** labels *execute* to set music/skybox, so keep them below your shared
  data. See the [media API](../api/procedural/media.md).
- **`@map/` `metadata` Properties** become variables (`PLAYER_COUNT`, `DIFFICULTY`,
  `GAME_TIME_LIMIT`) driven by the setup-screen widgets. Defaults come from
  [`settings.yaml`](../home/settings.md).
- **Building the world** &mdash; [World building](world-building.md) and
  [Tile maps](tile-maps.md).
- **Player ships & consoles** &mdash; [Player ships & consoles](players-consoles.md).
- **The game loop** is usually an inline `---` label that waits, spawns, and jumps
  back until a timer or condition ends it. [Objectives](../mast/objectives.md)
  and [end conditions](../mast/tutorial.md#end-game-conditions).
- **Telling the story** &mdash; [Story & NPC messages](messages.md).

## Bigger missions: split into modules

Large missions keep `story.mast` almost empty and put maps in a module folder
(`maps/__init__.mast` importing the rest) &mdash; Drop_Off and MiningDays do this.
See [Making add-ons](addons.md) for the module mechanics.

Real references: [Secret Meeting](https://github.com/artemis-sbs/SecretMeeting),
[WalkTheLine](https://github.com/artemis-sbs/WalkTheLine),
[LegendaryMissions](https://github.com/artemis-sbs/LegendaryMissions).
