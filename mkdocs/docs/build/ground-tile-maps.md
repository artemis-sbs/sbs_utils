# Ground tile maps

New in v1.4.0. The file formats and field names on this page are **settled for 1.4.0**:
what you write today keeps working. They are what the `away` starter
(`sbs create <Name> -t away`) and LandingParty (Dawnline) ship with, and what the linter
and the [Tile Map Editor](../tooling/tile-editor.md) read.

A **ground tile map** is walkable ground for an away team: a ridge, a colony street, a cave
system. Each place is an **area** drawn as ASCII in its own file, a party of crew figures
walks it one cell at a time, and a console draws it with `gui_tilemap`. Nothing on it is a
space object.

This is not the same thing as [Tile maps](tile-maps.md), which lay out a sector of
**space** from an ASCII string of terrain decks.

A mission's ground is made of three kinds of file:

| File | What it holds | Read by |
|---|---|---|
| `<area>.tiles` | One area: its map, legend, marks and exits | `tilemap_load` |
| `<name>.tileset` | The tile kinds: which can be walked or seen across, and how each one looks | `tilemap_tileset_load` |
| `media/tileart/<set>/manifest.json` | An **art set**: the pictures | `tilemap_art_use` |

Props, people and hostiles that stand on the ground are placed from an `.amd` file (see
[Placing things on the ground](#placing-things-on-the-ground)).

One line in `story.mast` loads all of it: [`boarding_ground_load(doc)`](#loading-it).

## An area file

```
area: ridge
title: Landing Ridge
tileset: mereth
entry: landing                  # a mark name, or "x, y"
legend:
  .: dust
  ,: scrub
  #: rock
  ~: brine
  L: dust @landing              # a tile kind, and a MARK on the cell
  c: path @to_colony            # a mark named to_<area> is an exit there
exits:
  to_colony: colony @to_ridge   # optional - where an exit leads, and to which mark
---
###########
#...,,..c.#
#..L......#
###########
```

Everything after `---` is the map, row 0 first, and `x` counts columns from the left. A
**space** is *nothing*: never walked, and drawn black.

**Header:**

| Key | Meaning |
|---|---|
| `area:` | The area's name. Required. |
| `title:` | What the players see. Defaults to the name. |
| `tileset:` | Which tileset its kinds come from. |
| `entry:` | Where somebody beamed down stands: a mark, or `x, y`. Without it, the walkable cell nearest the middle. |
| `known:` | `no` hides the area until a scan reveals it (`tilemap_reveal_area`). |
| `beam:` | `no` means the transporter cannot lock on here. |
| `size:` | `WxH`. Fixes the size instead of taking it from the longest row. The editor writes it when you resize. |

**Legend.** Each line is **one character**, a colon, and a tile kind. Because the key is
one character, `#` and `:` are fine as keys: a comment is only a `#` in column 0.
A legend line can also put a **mark** on every cell drawn with that character. For
example, `pppppp` drawn with `p: deck @pad` makes a six-cell mark called `pad`.

**Marks** name places: a prop or a person stands on one (`Mark:`), `entry:` names one,
and an exit is one. A scene does **not** belong to a mark. A scene belongs to the prop
that opens it (`Scene:`) or the person you talk to (`Talk scene:`), and nothing opens one
because somebody walked onto a cell. When an actor steps onto a mark the
`tilemap_entered` signal fires, which a mission's own route can use.

**Exits.** A mark called `to_<area>` is a way out to that area. The `exits:` block is only
needed to choose where the party arrives in the other area. Without it, they stand beside
that area's way back.

## A tileset file

```
tileset: mereth
title: Mereth surface
kinds:
  dust:    walk see   look=dirt
  salt:    walk see   look=salt
  brine:        see   look=water     # seen across, never walked
  cliff:        see   look=cliff
  rock:               look=rock      # neither
  wall:    tall       look=wall_metal
  door:    walk       color=#a86
```

Each word on a kind line is a **rule the kind has**. A kind that names neither `walk` nor
`see` blocks both. A misspelled word is an error, never a silent wall.

| Word | Meaning |
|---|---|
| `walk` | Can be walked on. |
| `see` | Can be seen across. Fog of war looks through it. A kind you can see across but not walk, such as water, is what makes a map readable. |
| `tall` | Stands up. The ground just south of it takes its art set's `shade` look. |
| `look=` | Which ground look an art set draws it with. The default is the kind's own name. |
| `cell=` | A sprite key to draw it with when no art set dresses it. |
| `color=` | A tint. The editor also uses it as the kind's color. |
| `over=` | When two kinds meet, the higher `over` has its fringe drawn on top. |

A `#` that starts a word ends the line, so `color=#a86` is a color and `  # note` is a
comment.

By convention, `tileset: mereth` in an area file names `mereth.tileset` **in the same
folder**. That is how the linter and the editor find it.

!!! note "A tileset declared in Python still works"
    `tilemap_tileset(name, {kind: {"walk": ..., "see": ..., "look": ...}})` is the same
    thing as a dict. The game treats both the same. Without a `.tileset` file, however,
    the linter and the editor cannot tell what can be walked. Their checks that need it are
    skipped, and the editor cannot hatch the cells nobody can walk.

## Loading it

One line, in the map body of `story.mast`, after the mission's `.amd` is read:

```
shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"), data_parser=amd_mission_data)
boarding_ground_load(MISSION_DOC)
```

`boarding_ground_load` does the whole sequence, in the order it has to happen:

1. Every `*.tileset` in the mission folder is declared and every `*.tiles` area is
   loaded. They can be in any subfolder. These are the same files `sbs lint` and the
   editor read.
2. The art is loaded: the mission's own `builtin` set if it has one, then the sets the
   `TILE_ART` setting names (see [Art sets](#art-sets)).
3. The document's `Props` section is put on the map, then `People` and `Hostiles`. Its
   `Scenes` section is what a prop's `Scene:` and a person's `Talk scene:` name, and
   `Skills:` on its crew are what a `check` rolls with.
4. Map clicks reach props and people, and the walk tick is started.

It returns what it did (`areas`, `props`, `people`, `scenes`, `art`, `art_missing`,
`unplaced`). Anything it could **not** place is named in `mast.runtime.log`, with the
reason: an `Area:` that is no area, a `Mark:` the area file does not have, a mark name
written in `At:`. A headless `--test` run fails on those.

A mission that keeps its world and its scenes in two files passes both:
`boarding_ground_load([world_doc, scene_doc])`. Calling it again is safe. Everything is
keyed, so an area already loaded and a prop already declared are left as they are.

Then open the party with [`boarding_visit`](boarding-parties.md#a-visit-on-a-tile-map),
naming the area to beam down into:

```
boarding_visit(ship, boarding_ground_scenes(), title="Kesh Relay", area="landing")
```

The pieces are still there for a mission that needs to do it by hand
(`tilemap_tileset_load`, `tilemap_load`, `tilemap_art_use`, `boarding_props_declare`,
`boarding_hostiles_declare`). If you do, load the tileset **before** the art, because an
art set dresses the kinds of a tileset that already exists. An area or tileset that
cannot be read is **logged and skipped**, not raised: one bad file should not take a
mission down. That is why the [checks](#checking-your-maps) matter.

## Art sets

A mission names logical keys only (`fig:crew_eva`, `prop:hatch`, ground looks like
`dirt`). An **art set** says what they look like: a folder
`media/tileart/<set>/` with PNG sheets and a `manifest.json`. `tilemap_art_use()` loads
the mission's own `builtin` set, then whatever the `TILE_ART` setting names. A set can
come from this mission or from a pinned media pack. A later set wins key by key, so a
pack that only redraws the people is a valid pack. The manifest format is documented in
`sbs_utils/procedural/tilemap_art.py`.

A mission does not have to ship any art. The `away` starter has none: it pins the
Cosmos-Tiles `frontier` and `station` packs under `shared_media` in `story.json` and
names them in `TILE_ART`. When a named set is **not installed**, `boarding_ground_load`
says so once, plainly, and carries on. The mission still runs, but a ground kind with no
art is not drawn, so with no art at all the map on the crew console is black. Fetch the
packs with `sbs fetch <mission> --update-libs`.

The engine draws a picture mirrored when its rect runs backwards, and art sets use that
in two ways:

- **A figure needs only one side.** When a set has a figure's east-facing looks but not
  its west-facing ones (or the reverse), the missing side is the other one mirrored. A
  side the set does draw is always kept.
- **A prop can have a mirrored twin.** A sprite marked `"mirror": true` in the manifest
  is also registered as `<key>_mirror`, and a prop that stands still is drawn as the twin
  on about half the cells, the same cells every time. It blocks the ground the twin
  covers. A field of rocks or a yard of hay bales then repeats half as often. Never mark
  anything with lettering or a handed shape.

A mirrored look is lit from the other side, so its baked shadow falls the other way. A
short shadow hides that and a long one does not: twinned trees in one orchard cast
shadows both ways. So the Cosmos-Tiles packs mark only small things (rocks, rubble,
bushes, hay, crystal seams, potted plants), and they keep their real west-facing
figures. `gui_image_mirror(key, as_key)` does the same for any image, for example one
arrow that points both ways.

## Placing things on the ground

Props, people and hostiles live in `.amd` sections (`## [Props](props)`,
`## [People](people)`, `## [Hostiles](hostiles)`) and name their spot in one of two ways:

```
### [Survey drone](drone)
---
Area: ridge
Mark: drone              # a mark in the area file
Sprite: prop:drone_wreck
---

### [Glassback](gb_1)
---
Area: caves
At: 18, 3                # or a cell, x then y
Patrol: 18 3; 25 4; 18 5
Sprite: fig:glassback
---
```

A mark name goes in `Mark:`, never in `At:`. `At:` reads coordinates only, so a word
there reads as nothing and the prop is never placed.

Fields the game acts on by itself, with no route in the story:

| Field | On | What happens |
|---|---|---|
| `Opens with: signal <name>` | a prop | The door opens when that signal is sent, for example by a scene's `; signal <name>`. |
| `Hidden until: <name>` | a prop, a person | It is not on the map until that signal is sent. |
| `Scan:` | a prop, a person | What the xESS **Scan** app says about it. Without one, its description. |
| `Blocks:`, `Once:`, `Calm:` | | `yes` or `no`. Anything else is reported by `sbs lint`. |

When a hostile is put down for good the game sends `hostile_down_<key>`, and a quest can
wait on it: `Done when: signal hostile_down_sentry`.

A person or hostile can also have a `Face:`, a face string or a keyword (`female`,
`male`, `terran`) that is resolved once, so they keep the same face all mission. The
xESS **Act** transcript shows it beside what they say. Someone without one appears there
as their `Sprite:` figure, facing you, and a prop appears as its sprite. See
[Faces and pictures in the transcript](boarding-parties.md#faces-and-pictures-in-the-transcript).

A prop with nothing to it (no `Scene:`, `Item:`, `Opens with:`, `Needs:` and no
description) is **scenery**: bunks, console banks, barrels, whatever furnishes a room.
It is drawn and `Blocks:` like any prop, but the Look list and the list of things further
off leave it out, it never gets a badge, and a click on it walks toward it instead of
using it. Give a prop one line of description and it becomes something to look at.

```
### [Bunk](gnaw_bunk)
---
Area: gnaw
At: 8, 5
Sprite: prop:bunk
Blocks: yes
---
```

### Big things cover more than one cell

A prop stands on one cell, but a parked car, a barn or a landed shuttle covers several.
The art set says how much ground each sprite stands on (its `base`), and a prop that
`Blocks:` blocks every cell it covers: nobody walks through a taxi. A cell counts as
covered when more than half of it is under the thing, each way, so a bunk one and a half
tiles long still takes one cell.

The prop is AT every cell it covers. A click on any of them is a click on it, and
"within reach" and the distances the device shows are measured to its nearest cell: you
use a car from its bumper, not by walking round to the middle. The `Mark:` or `At:` cell
is the middle of the thing, so leave room round it.

| Pack | Props over one cell |
|---|---|
| city | cars and taxis 1x3 (nose south), garbage truck 3x5 |
| countryside | barn 5x7, farmhouse 5x5, harvester 3x5, greenhouse and small barn 3x3, tractors 1x3, and a few more |
| frontier | hauler 3x1 |
| station | shuttle 3x3 |

A mission can give its own art a base with
`tilemap_sprite_base("prop:wagon", (-1.4, -0.5, 1.4, 0.5))`: left, top, right, bottom in
tiles from the center of its cell, x east and y south. `tilemap_sprite_cells(key)` says
which cells that covers.

## A ship's deck, drawn for you

Any hull with an interior plan (the one Engineering shows) can be boarded on a tile map
nobody has to draw. `boarding_deckplan` lays the plan out as a deck:

- each plan cell becomes 3 x 3 tiles;
- each room gets the floor and furniture of its kind. A galley gets tables and stools, a
  cargo hold gets crates, and a system room gets one piece of kit per node: a reactor per
  warp node, a turret per beam node, a power cell per impulse node;
- bulkheads separate the rooms, and every room gets a doorway, so the whole deck can be
  walked. A plan that comes in pieces, such as a starbase's modules, is joined by
  gangways;
- every room's tiles carry a mark named after the room (`room:impulse`,
  `room:crew-quarters`, `room:hallway`). Boarding arrives at `entry`, which is the
  airlock if the ship has one, otherwise the middle of the hallway.

```python
from sbs_utils.procedural.boarding_deckplan import (boarding_deck_plan,
                                                    boarding_deck_tileset,
                                                    boarding_deck_build)
boarding_deck_tileset()                       # the "deck" tileset: kinds named for looks
tilemap_art_use("station", tileset="deck")    # the Cosmos-Tiles station pack draws them
area = boarding_deck_build(boarding_deck_plan(ship), "boarded_deck", title="Enemy cruiser")
```

`boarding_deck_plan(ship)` reads a live ship's layout and hull map. For a `.grid` file, use
`boarding_deck_plan_ascii(text)`.

For a live ship, one call does all of it:

```python
deck = boarding_deck_for(enemy_id, title="Kralien cruiser")   # built once, then reused
boarding_invite(player_ship, [], title="Boarding", area=deck)
```

The deck then follows its ship. `boarding_deck_watch` checks it every second, and
`boarding_deck_sync` does one check on demand:

- a damaged node's kit goes dark, with rubble beside it that can be walked over. A system
  also throws sparks, and any other room catches fire;
- a repaired node comes back;
- each damage-control team stands where Engineering has it, walks when it moves, lies down
  at 0 HP, and leaves when it is gone. Teams are drawn as the ship's own race
  (`RACE_CREWS`, read from the hull key: `kralien_cruiser` has Kralien crews, a TSN ship
  has humans).

The ship's own crew can be put aboard as well, drawn as its race:

```python
boarding_deck_crew(deck, ship=enemy_id, boarders=player_ship, talk_scene="crew_talk")
```

If the ship is at war with the boarders, about three in five of the crew are guards. They
walk the hallways and fight whoever they notice. The rest are hands, calm in the cabins
and messes, who fight only when provoked. Aboard any other ship everyone is a hand. By
default there is one crew member per ten plan cells (2 to 12); `hostile=` and `count=`
override the stance and the number. `talk_scene` names a scene of the mission's own that
the hands can be talked to with.

Every doorway has a door, drawn front-on or side-on to match its wall. Doors never block:
`boarding_deck_animate` slides them open for anyone beside them and flips the frames of
the sparks and fire. `boarding_deck_watch` starts it; for a deck with no ship behind it,
call `boarding_deck_animate(area)` yourself.

The furniture is scenery, and the same plan always gives the same deck. A piece that
covers more than one cell is placed only where all of its cells are that room's floor,
clear of the doors, and where it cannot cut the room in two. To furnish a kind
of room your own way, use `boarding_deck_kit("cargo", furniture=["prop:barrel"])`. To start
from the generated deck and edit it by hand, `boarding_deck_text(layout, key)` gives it as
a `.tiles` file.

The deck's looks come from an art set. Without the `station` pack (or another set that
draws the same looks) the deck still works, but nothing is drawn. A mission that boards
ships therefore pins `artemis-sbs.Cosmos-Tiles.station.<tag>.zip`.

## A map built in code

Some maps are too big, or too procedural, to write down as a file. A galaxy with no edge
is one example. For those, build the area from a function and rebuild it as the view
moves. OpenUniverse's galaxy map works this way (`universe_core/universe_galaxy_map.py`):
each console gets its own window onto the galaxy, regenerated around the system it is
looking at.

| Call | What it does |
|---|---|
| `tilemap_generate(key, w, h, cell, tileset)` | Builds or rebuilds an area. `cell(x, y)` returns a kind, a `(kind, tint)` pair, or `None` for nothing. |
| `tilemap_tint(area, cells, color)` | Tints cells over their kind's own color, for things like owner, selection or warning. `color=None` clears the tint. |
| `tilemap_tint_at(area, x, y)` | A cell's own tint, or `None`. |
| `tilemap_unload(area)` | Drops an area and every actor in it. |

```python
def galaxy_window(client_id, ci, cj):
    def cell(x, y):
        i, j = ci + x - 10, cj - (y - 10)
        kind = system_kind(i, j)
        return ("sys_" + kind, owner_color(i, j))
    return tilemap_generate("galaxy:%s" % client_id, 21, 21, cell, "galaxy")
```

**A rebuild that comes out identical changes nothing**, and nothing is repainted. So you
can regenerate every second and pay only when the world actually moved. Actors stay where
they are through a rebuild, because moving them is your job. While the size is unchanged,
the area also keeps its explored cells, marks and blocked cells.

**Pan by rebuilding, not by moving the camera.** A view that follows nobody shows the
middle of its area. Rebuild the same-sized area around a new center and the view re-sends
only the tiles whose look changed, using the same widgets.

**Zoom is a page rebuild.** A view's column count is fixed when the page is built, because
the engine only updates widgets that were in the build. To show more or fewer cells, change
`cols` and rebuild the page.

**The area must exist before the page is built.** For the same reason, a view whose first
paint finds no area can never draw anything. It logs a warning once:
`tile view built before its area ... existed`.

A badge from `hints` can carry its own tint: return `(atlas key, color)` instead of a bare
key.

Actor ids do not have to be agent ids. A map token that stands for something else, such
as a fleet, can use a name like `"gm7:f:alpha"`. Named ids sort after numbered ones.

## Checking your maps

`sbs lint` checks area files, tileset files, and every placement in the mission's `.amd`.
The same findings appear as squiggles in VS Code while you type (Artemis AMD extension).

| Code | Level | What it catches |
|---|---|---|
| `tiles-unknown-char` | error | A map character the legend does not have. The whole area will not load, and every such character is named with its column. |
| `tiles-unknown-kind` | error | A legend kind the tileset does not declare. It draws nothing and cannot be walked. |
| `tiles-syntax` / `tileset-syntax` | error | A file the parser cannot read, such as one with no `---` or a misspelled rule. |
| `tiles-unknown-tileset` | warning | `tileset: X` with no `X.tileset` in the mission. |
| `tiles-legend-duplicate` | warning | The same character in the legend twice. The later line wins. |
| `tiles-mark-unplaced` | warning | A mark in the legend that is never drawn on the map. |
| `tiles-entry` | error/warning | `entry:` names nothing, or puts the party on ground it cannot move from. |
| `tiles-exit` | warning | An exit to an area that does not exist, an arrival mark that is not there, or an exit on ground nobody can walk onto. |
| `tiles-unknown-area` / `tiles-unknown-mark` | warning | A placement's `Area:` or `Mark:` names nothing. It is never placed. |
| `tiles-at-not-a-cell` | warning | A mark name written in `At:`. |
| `tiles-off-map` | warning | An `At:` or `Patrol:` cell outside the area. |
| `tiles-unwalkable` | warning | Someone who walks is placed on, or patrols through, ground that cannot be walked. A prop may stand anywhere. |

## Editing visually

The **Tile Map Editor** in VS Code paints `.tiles` files and shows them with the
mission's own art, as the game draws them. It also shows the props, people and hostiles
the `.amd` places on the area, and you can drag them (and patrol points) into place. A
`.tileset` file opens in the **Tileset Editor**, a table of its kinds with each look's
picture. See [Tile Map Editor](../tooling/tile-editor.md).

## Seeing a whole map

The game's tile view shows at most 40 tiles across, so a big map scrolls and follows a
walker. To see a whole map at once:

| For | Use |
|---|---|
| Working on it | The Tile Map Editor, zoomed out: the `-` button or key, or Ctrl+wheel, down to 8 pixels a tile. |
| Reading or sharing it | `sbs site <mission> --emit site`: a page per map, with the real art, linked to the records on it ([Maps](../tooling/site.md#maps)). |
| Paper or a PDF | Print a map page, or add `--maps-pdf` to write one PDF per map. `--profile player` leaves the secrets off. |
| A ship's boarding deck | The same `sbs site` build: every ship interior plan gets a deck page, listed under **Every ship deck** ([Ship decks](../tooling/site.md#ship-decks)). |
