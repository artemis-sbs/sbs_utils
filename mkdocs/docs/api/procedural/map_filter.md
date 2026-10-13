# Map filters

Choose what a console's 2D map draws, and whether it draws nebulas and asteroids.

Each console family has its own filter on the player ship - a list of the ids its map
shows - and every console of that kind on the ship shares it. Needs engine 1.3.15 for
science, helm and weapons; the comms filter is older.

| Console | `console` argument | Engine view | Terrain flags |
|---|---|---|---|
| Comms | `"comms"` | `comms_2d_view` | none |
| Science | `"sci"` | `science_2d_view` (and its contact list) | yes |
| Helm | `"helm"` | `2dview` | yes |
| Weapons | `"weapon"` | `weapon_2d_view` | yes |

```
# Show only the hostiles on this ship's weapons radar
map_filter_set(ship_id, role("raider"), "weapon")

# Everything again
map_filter_clear(ship_id, "weapon")

# A helm radar with no asteroids on it
map_show_terrain(ship_id, "helm", asteroids=False)
```

- The ship is always kept in its own list, and only live space objects are written.
- A list that matches nothing shows the ship alone. An empty list would mean "no filter".
- The terrain flags default to shown and work with or without a filter. Terrain named in
  a filter is drawn only while its flag is on.
- An unchanged list is not re-sent.

## API

::: sbs_utils.procedural.map_filter
