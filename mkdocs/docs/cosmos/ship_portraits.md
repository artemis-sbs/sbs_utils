# Ship portraits

`gui_ship` draws a hull as a **live 3D model**. That is the right thing for one ship you
want to look at, and the wrong thing for a list: every widget is its own 3D render, so a
roster with a ship on every row pays for every one of them, on every console.

A **portrait** is a picture of the hull taken once, ahead of time, and kept on a sheet.
Drawing one costs what an image costs. And because a sheet cell can be drawn as a
**face**, a ship can have a face of its own - which is what makes the
*unknown contact, then the ship, then its captain* sequence possible.

| You want | Use |
|---|---|
| a ship in a list row, a roster, a card | `gui_ship_portrait(hull)` |
| a ship in a text area or markdown | `![](ship://hull)` - a portrait already |
| the ship as a comms face | `ship_portrait_face(hull)` |
| a face that grows as the crew learns more | `ship_portrait_stage_face(hull, stage)` |
| one ship to turn and inspect | `gui_ship(hull)` - the live model |

A hull with no portrait **always falls back to the live 3D ship**, so nothing ever draws
blank - a missing or out-of-date sheet costs speed, never a picture.

## In a layout

```python
gui_ship_portrait("tsn_light_cruiser", style="col-width: 50px;")
gui_ship_portrait(ship_id)          # a ship id or object works too - its hull is used
```

In a text area, `ship://` embeds and ship leads are portraits by default. Add `live=1`
to keep the 3D model:

```markdown
![](ship://tsn_light_cruiser?height=100) Light cruiser
![](ship://torgoth_goliath?live=1) Torgoth goliath, live
```

Overlay cards (`overlay_hero(ship=...)`, `overlay_lower_third_portrait(ship=...)`) draw
their ship visual as a portrait too, and accept a ship id as well as a hull key.

## As a face

A portrait sheet is registered as a face sheet, so a hull is a face string like any other
and goes anywhere a face does - comms, a crew card, `face://` in a text area:

```python
face = ship_portrait_face("kralien_battleship")        # "shp_base0 #fff 10 0;"
```

### What the crew knows: stages

`ship_portrait_stage_face(ship, stage, captain=None)` builds the face for how much the
crew has learned. **The mission decides the stage** (has it been scanned? hailed?); the
library only builds the face.

| stage | shows | if that is missing |
|---|---|---|
| `"unknown"` | a generic contact - a radar ring and a question mark | the hull |
| `"contact"` | the hull's **silhouette** - a shape, not yet a ship | the unknown cell |
| `"hull"` | the hull's portrait | the unknown cell |
| `"captain"` | `captain` (any face string) | the hull |

```python
if not scanned:
    face = ship_portrait_stage_face(ship_id, "contact", silhouette_color="#6af")
elif not hailed:
    face = ship_portrait_stage_face(ship_id, "hull")
else:
    face = ship_portrait_stage_face(ship_id, "captain", captain=get_face(ship_id))
```

The silhouette is drawn **white**, because a face tint can only darken, never lighten - so
`silhouette_color` (default `#9ab`) is exactly the color it appears in.

## Where the sheets come from

The **base game's** sheet ships in the sbs_utils media pack and loads itself the first
time a portrait is asked for. Every mission on the library has it - there is nothing to
declare in `story.json`.

A **mod** builds its own sheet into its own media pack and loads it next to its ship data:

```python
add_extra("my_ships", mod="my_mod")
ship_portrait_load("ship_portraits/mymod")     # a logical path - found in any pack
```

Pass the **logical path**, not `media_shared(...)`: that probes for a `.png` or a folder,
so it cannot see the sheet's `.json`, and the folder form finds the wrong pack when two
mods both ship portraits. A mod's portrait wins over the base game's for a hull both have.

## Building a sheet: `sbs art portraits`

```
sbs art portraits                       the base game -> sbs_utils/media/ship_portraits
sbs art portraits MyMod --set mymod     a mod's own hulls -> MyMod/media/ship_portraits
sbs art portraits MyMod --check         what is stale or missing? (exit 1 if anything)
```

It renders every hull that has `hullpoints` (ships and stations; `--all` adds pickups and
asteroids) with the same three.js loader the browser mock draws ships with, in a headless
Edge or Chrome - nothing to install. Each hull gets a portrait cell and a silhouette cell,
256 px square, 16 across, on one 4096 px sheet for anything up to 128 hulls.

**It only redraws what changed.** Each cell records a hash of its hull's mesh and
textures, so a run after a texture edit redraws that one hull, and a run with nothing
changed touches nothing. Cells never move: a hull keeps its place across rebuilds, so a
face string handed out earlier still means the same ship. Rebuilding is a deliberate step
- `sbs art check` reports a stale sheet alongside half-baked art, and `--strict` fails on
it.

Once a mod folder has one sheet, later runs pick it up without repeating `--set`.

!!! note "Engine version"
    Portrait faces need the engine that takes a face sheet's cell size (1.3.15, exe of
    2026-10-17 or later). On an older exe the face path is refused and logged once;
    portraits still draw as images.
