# Tile maps

For large, structured worlds, build the map from an **ASCII string**: map each
character to a **deck** of terrain prefabs, then fill a tile grid from the art.
It's a compact way to lay out sectors of space (used by HereThereBeMonsters and
theta_quadrant).

## Create a tile map

```
tile_map = maps_tile_map_create(0, 100_000, 1_000, 2_000)
#                                min_x  min_z  cell_x  cell_z
```

## Define decks

A deck is a weighted set of terrain prefabs; each mapped character draws from one:

```
nebula_deck = maps_deck_create()
nebula_deck.add_card(prefab_terrain_nebula_sphere, {"density": 0.5, "cluster_color": "red"})

black_hole_deck = maps_deck_create()
black_hole_deck.add_card(prefab_black_hole, {"gravity_radius": 10_000})
```

`add_card(card, data=None, count=1, cost=0)` adds a prefab to the deck; `count`
weights how often it's chosen.

## Map characters to decks

```
tile_map.map_deck("n", nebula_deck)
tile_map.map_deck("b", black_hole_deck)
```

## Fill from an ASCII string

`map_art` is a string (often imported from its own `.mast` file). Each character
maps to a deck; spaces and unknown characters are skipped.

```
res = await tile_map.fill(map_art, x_count=100)
res &= role("black_hole")     # the result is a role set of everything spawned
```

Missions can use several tile maps with different cell sizes for different regions
(theta_quadrant uses 16). For simpler asteroid/nebula fields without a grid, see
the field helpers in [World building](world-building.md).
