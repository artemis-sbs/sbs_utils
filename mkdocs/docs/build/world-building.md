# World building

Populate a map with stations, ships, and terrain.

## Spawning objects

`npc_spawn` places a station or ship. The roles string is comma-separated; the
**first role is the side**:

```
station = npc_spawn(0, 0, 0, "Starbase Phoenix", "tsn, station", "starbase_civil", "behav_station")
raider  = npc_spawn(100, 0, -2000, "Raider", "raider", "kralien_cruiser", "behav_npcship")
```

Unpack a `Vec3` as positional args with `*`:

```
npc_spawn(*Vec3(1000, 0, 1000), "DS1", "tsn, station", "starbase_command", "behav_station")
```

See the [spawn](../api/procedural/spawn.md) and
[space_objects](../api/procedural/space_objects.md) API.

## Positioning

```
points = scatter_box(count, cx, cy, cz, dx, dy, dz, centered=True)   # box of points
pos    = Vec3.rand_in_sphere(min_r, max_r, include_y=False, flat=True)
```

See [Scatter](../api/utility/scatter.md) and [Vec3](../api/utility/vec.md).

## Terrain

Spawn one rock with `terrain_spawn`, or use the field helpers:

```
terrain_spawn_asteroid_box(cx, cy, cz, size_x=40000, size_z=15000, density=3, height=2000)
terrain_spawn_asteroid_sphere(cx, cy, cz, radius=7500, density=2)
terrain_spawn_nebula_sphere(cx, cy, cz, radius=12000, cluster_color="red")
```

See the [terrain](../api/procedural/terrain.md) API. For structured procedural
worlds, the tile-map system fills an ASCII map from weighted terrain decks &mdash;
see [maps](../api/procedural/maps.md).

## Sides

Create sides with the LegendaryMissions `prefab_side_generic`, then set relations:

```
tsn    = await prefab_spawn(prefab_side_generic, data={"key":"tsn", "name":"TSN", "color":"#07F"})
raider = await prefab_spawn(prefab_side_generic, data={"key":"raider", "name":"Raider", "color":"#F00"})
side_set_relations(tsn, raider, sbs.DIPLOMACY.HOSTILE)
```

See the [sides](../api/procedural/sides.md) API.
