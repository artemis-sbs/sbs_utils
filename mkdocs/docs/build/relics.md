# Relic interiors

A relic is a structure a ship flies **inside** — a hollow ruin, a canyon, a docking
throat. This is how you author one.

## Model the space, not the walls

The instinct is to build the walls out of solid objects. The engine cannot do that: its
only collision primitive is a **keep-out sphere**, and a hollow shell is the opposite of a
sphere. Approximating one with hundreds of them is not merely expensive — the boundary
never lines up with the art, so the ship either clips through corners or stops in what
looks like open space.

So you describe the **navigable space**:

| you write | it is | it means |
|---|---|---|
| `Chamber:` | a sphere | a room |
| `Passage to:` | a capsule | a corridor between two rooms |
| `Box:` | a rectangle | a *built* space, with flat walls and real corners |
| `Solid:` | a subtraction | a pillar, a spire, a solid hub |

Everything else is wall. A dozen branching chambers is about thirty primitives.

## Writing one

Relics and their parts are **flat siblings** in one `Relics` section. A record carrying
`Relic:` is a part of that relic; a record carrying none is the relic itself.

```amd
## [Relics](relics)

### [The Ossuary](ossuary)
---
Loc: 12000, 0, -8000
Atmosphere: purple
Containment: tractor
Margin: 60
Forbid jump: yes
---
An ancient thing, hollow, and not built by anyone still alive.

### [hub](hub)
---
Relic: ossuary
Chamber: 0, 0, 0, 900
---

### [gallery](gallery)
---
Relic: ossuary
Chamber: 3000, 0, 0, 700
Passage to: hub 300
---

### [the vault](vault)
---
Relic: ossuary
Box: 3600, 0, 2900, 900, 260, 380
---

### [the core](core)
---
Relic: ossuary
Solid: sphere, 0, 0, 0, 320
---
```

Chamber coordinates are **relative to the relic's `Loc:`**, so the same layout can be
dropped at two places in a system without editing a single number.

A box takes **half**-extents — `900, 260, 380` is a room 1800 by 520 by 760.

## The walls are scenery

Every prop dressing a relic is terrain with `exclusion_radius` **0** — visible, not solid.
Delete them all and containment behaves identically. Their entire job is making an
invisible boundary *legible*: without them you are hauled back by nothing you can see,
which reads as a bug rather than a wall.

Two consequences worth knowing:

- **A subtracted solid must be dressed too.** An undressed pillar is an invisible
  obstacle.
- **Props sit on or just outside the boundary.** That alignment is why hitting the visible
  rock and hitting the invisible wall happen at the same moment.

!!! warning "Never give a fly-through prop an AI behavior"
    An AI behavior carrying `exclusion_radius: 0` NaNs the engine and asserts. Props must
    be terrain — passive, with no steering or rotation to go wrong.

## A chamber is a shell of props, not one big rock

Scaling a single mesh up to room size does not work: measured by eye in the engine, an
asteroid at 80x reads as "more of a tunnel than a room", and one blown-up mesh has poor
texel density and one obviously repeated silhouette. Scatter ordinary-scale props over the
chamber's boundary instead.

## Two size rules

| rule | limit | why |
|---|---|---|
| neighbouring chambers apart | ~3500u | `render-distance-objects` is 5000; space them wider and the relic stops drawing its own far side |
| the whole relic across | ~11200u | so its atmosphere fits in **one** nebula |

## Atmosphere does the speed limiting

`Atmosphere:` fills the relic with nebula, and **the engine caps warp inside a nebula by
itself**. That is better than any script governor: no per-tick throttle writes, nothing for
the helm to fight, and no disagreement with the client.

One nebula can be about 12000 across, so a relic that obeys the size rule above needs
exactly one — which matters, because nebula costs roughly five times an asteroid per
object and count is the only real lever.

## Being caught by a wall

Containment is graded, on how far past the boundary you are:

| how far out | what happens |
|---|---|
| inside | nothing |
| in the wall | a scrape — signalled, and you can still fly out |
| past the scrape band | throttle drops to impulse, and you are held inside |

The hold is an engine-side **tractor**, which matters more than it sounds. The obvious
implementation — teleport the ship back each tick — is correct on the server and looks
wrong from the seat, because the client predicts its own position and you visibly leave
the volume before snapping back.

What a scrape *means* is yours. The library emits `volume_scrape`, `volume_breach` and
`volume_recovered` when a ship changes tier; route them with `//shared/signal` so they run
once on the server rather than once per console.

```
//shared/signal/volume_scrape
    log(f"hull scrape at depth {depth}", "relic")
```

## Filling it in

A volume says where space **is**. What you see is ordinary props scattered over that
boundary - and the library does the sampling, so a mission only chooses art:

```
# the shell: props on the walls, with an outward normal each
for (x, y, z, nx, ny, nz) in volume_surface_points("ossuary", 600, seed=7):
    p = terrain_spawn(x, y, z, "", "#,relic_wall", art, "behav_asteroid")
    p.engine_object.exclusion_radius = 0

# the pillars, which MUST be dressed or they are invisible obstacles
volume_solid_points("ossuary", 50, seed=7)

# and anything floating in the rooms
volume_inside_points("ossuary", 40, seed=7, margin=200)
```

Three things it does that are easy to get wrong by hand:

- **Even, not random.** A sphere is sampled on a golden-angle spiral. Uniform sampling
  clumps, and a clumped shell has holes you can see straight out through.
- **A box is sampled on its FACES**, not as a shell - a box dressed like a sphere reads as
  a cave again and hides the corners that are the whole reason it is a box.
- **The shell is clipped to the outside of the union.** Each shape is sampled on its own
  surface, so where two overlap one wall runs through the other's open space. On the demo
  layout that was 54 of 403 points, several more than 280 units deep: rock in the middle
  of a corridor.

Budgets split by area, so a chamber twice the size gets about twice the props. Everything
is deterministic in `(seed, n)`, so a relic looks the same every run and a rebuild after an
edit changes only what the edit changed. `Seed:` and `Art:` on the relic are what the file
uses to say so.

**Verify any art key against shipData.** An unknown key does not fail - it silently renders
the `unknown` mesh, so a typo shows up as a relic built out of question marks.

## Places inside it

`Point:` names a spot - somewhere an item is found, where NPCs arrive, the way in:

```
### [the reliquary](cache)
---
Relic: ossuary
Point: 4651, 0, 3188
Roles: item, quest
---
```

A point adds no navigable space and subtracts none. It is authored **relative to the
relic's `Loc:`**, like every other part, so it travels with the relic - which is why it is
a relic part rather than a landmark, whose `Loc:` is absolute and would stay behind.

**In the editor:** press **Add point** (or right-click where you want it), then type
its roles in the properties panel - `item`, `spawn`, `entrance`, or whatever your
mission looks for. The roles are yours; nothing in the library interprets them.

What goes there is the mission's call:

```
item_spawn("relic_core", *relic_point("ossuary", "cache"), qty=2)
npc_spawn(*relic_point("ossuary", "picket"), "Sentry", "raider", ...)
marker_point(*relic_point("ossuary", "mouth"), "The Ossuary")
```

`relic_points("ossuary", "spawn")` gives every point with a role, for when there are
several.

## What is in it

A relic can hold things, and say when they turn up. That is the half of a ruin the plan
view cannot show you: the Red Beacon in the vault, the power cells on the shaft floor, the
raiders that wake when you reach the core.

Contents hang off the **part they are at**. A point names a spot; a chamber means
"somewhere in this room".

```
### [the reliquary](cache)
---
Relic: ossuary
Point: 4651, 0, 3188
Item: red_beacon
Qty: 1
Starts when: reach vault_door 900
---
Something worth the trip. Nothing here until the crew reaches the vault door.
```

| field | means |
|---|---|
| `Item:` | an authored item is found here - a key from the `Items` section |
| `Qty:` | how many of it |
| `Spawn:` | what wakes up here - `raider x2`, `skaraan 4` |
| `Starts when:` | when any of it appears. Leave it out and it is simply there |

`Item:` is a **reference**, not free text, so a typo is a lint error with a line number
rather than a beacon that never appears:

```
  relic-unknown-item  `cache` holds `red_becon`, which is not a defined item
```

### When it appears

`Starts when:` is the **same trigger grammar quests use** - not a second way to say the
same thing. A relic watches three of its phrases:

| phrase | fires when |
|---|---|
| `reach <role> [radius]` | a player comes within `radius` of anything holding that role (default 900) |
| `signal <name>` | `signal_emit("<name>")` runs, whoever emits it |
| `<n> minutes` / `<n> seconds` | that long after the relic was armed |
| *(nothing)* | placed immediately - the common case |

Anything else parses, but a relic cannot evaluate it, so `sbs lint` refuses it rather than
letting you wait for a beacon that is never coming:

```
  relic-when-unwatchable  a relic cannot watch for 'accepted' - it understands reach,
                          signal and a delay; contents with this phrase would never appear
```

### Giving `reach` something to measure

`reach` measures against **objects holding a role**, and a point is only a place until
something is standing on it. Arming does that for you: every point carrying `Roles:` gets
an invisible, selectable marker with those roles.

So the trigger above needs one more part, and nothing else:

```
### [the vault door](vault_door)
---
Relic: ossuary
Point: 2682, 0, 2482
Roles: vault_door
---
```

### Arming it

The mission writes one line:

```
relic_items()                      # if the items live in the same .amd - see below
relic_contents_arm("ossuary")
```

Contents with no trigger are placed now; the rest wait on their phrase. Each record is
placed **once**, keyed by its part, so re-arming - or a live preview reload - does not
litter the ruin with a second beacon. The return value is how many are still waiting.

It stays an explicit call rather than something `relics_build` does by itself: a mission
may want the relic standing with nothing in it yet, and loot that spawns as a side effect
of loading geometry is the kind of thing nobody can find later.

**Items are declared separately.** `Items` is its own section with its own reader, so the
mission joins the two:

```python
from sbs_utils.procedural.amd_items import items_declare_amd
from sbs_utils.procedural.amd_doc import amd_section
items_declare_amd(amd_section(doc, "items"))
```

### Asking what is where

```
relic_contents("ossuary")                    # every record, with its world position
relic_contents_state("ossuary", "cache")     # "placed" | "waiting" | "unarmed"
```

`waiting` and `unarmed` both look like "the loot is not there", and only one of them is a
bug - which is why they are different words.

**In the editor:** select a part and fill in **item**, **qty**, **spawn** and **when** at
the bottom of the properties panel. The item box completes from the file's own `Items`
section. A part that holds something is marked in the view, so "which rooms are furnished"
is answerable at a glance instead of by clicking through every part.

## The way in, and who gets held

**Containment only applies to a ship that has been inside**, and lets go once it is a whole
relic clear. A ship that never entered is never touched.

That is what makes an entrance possible: the tier is a pure depth test, so before this a
ship 80,000 units away read as a breach and was tractored toward the relic. Fly in through
a mouth - a chamber or passage reaching out past the hull - and you are inside the volume
before you are deep in it, so containment engages without a breach ever happening.

`volume_engaged("ossuary")` is who is in there now, which is also the answer to a question
missions ask for their own reasons: a quest that starts on arrival, a door that closes
behind you. Pass `engage="always"` for a volume that IS the playfield rather than a place
inside one.

## Checking it

`sbs lint` catches the faults that are otherwise silent — a `Passage to:` naming a chamber
that does not exist, a part naming a relic that does not exist, a radius of zero, a
`Chamber:` with too few numbers, an `Item:` naming nothing, a `Starts when:` a relic
cannot watch. All of them build *something*, just not what you wrote, so they surface as a
pathfinding bug - or an empty room - rather than a typo.

## Looking at one

**Artemis AMD: Show Relic Plan** opens the relic, and nothing needs to be running:

- **Add chamber / Add box / Add solid / Add point** build the four parts, and the
  right-click menu places one exactly where you clicked; the properties panel's
  **subtracted** tick flips a chamber or box into a solid and back, which is lossless
  because the numbers are the same. A point is drawn small with a ring - cyan for an
  entrance - and moves like anything else, but has no size to drag. Its **roles** box
  in the properties panel is what makes it an item, a spawn, or the way in.
- **click** a part to select it; **drag a handle** to move it along one axis or to change
  its radius; **SHIFT-drag** between two parts to connect them; **right-click** for a menu
  that can add a chamber exactly where you clicked.
- **MIDDLE-drag** orbits, **SHIFT-middle** pans, the **wheel** zooms - Blender's
  convention, which is what leaves the left button free for all of the above.
- the corner **navigation gizmo** points the view down an axis; clicking the axis you are
  already looking down flips to the far side. **Top**, **Front** and **Right** do the
  same from the toolbar.
- the **properties** panel, bottom right, types exact numbers when a drag will not do -
  and renames a part. Its **key** is shown but not editable: passages name their ends
  by key, so renaming one would silently orphan every corridor reaching it.
- **Undo** is a button, because CTRL-Z pressed over a webview never reaches the
  document your edits landed on. Every edit here - typed, dragged or renamed - is one
  line of the `.amd` and one undo step.

**The axes are not Blender's.** Blender is Z-up; Cosmos is Y-up, because a chamber's
second number is its altitude. So the ball meaning *look down from above* is **Y** here
and Z there:

| ball | view | you see |
|---|---|---|
| Y | Top | X across, Z into the screen |
| Z | Front | X across, Y up |
| X | Right | Z across, Y up |

Top is the old plan view exactly - same axes, same +Z up the screen. It is a camera angle,
not a separate editor.

**Why the editor draws it rather than the game.** A relic can sit 80,000 units from the
spawn, or not exist until a quest spawns it, so starting the mission and flying over is
not a way to check a chamber radius. The views above work on the file alone. Use the live
preview below when the question is how it *feels* - whether the wall catches you - which
is the one thing a drawing cannot answer.

## Live preview

Open the file with **Artemis AMD: Show Relic Plan** and press **Preview** - the running
session re-reads the `.amd` and rebuilds the relic where it stands. No restart, and **no
code in your mission**: the rebuild is a debug action the library answers, the same way
previewing a dialogue node is. Turn on **Live** and every drag previews by itself.

**You do not have to start the session first.** With nothing listening, Preview starts
`sbs debug` for the file's own mission. It opens at the map picker, so the first Preview
after a cold start will tell you to pick the map that builds the relic - a session cannot
guess which one that is. After that every Preview lands. (The **Live** toggle never starts
a session: spawning a mission process in the middle of a drag would be a surprise.)

What comes back for free:

- the volume is **replaced in place**, under the same name, so anything addressing the
  relic goes on addressing it;
- **containment follows the rebuild by itself.** A watch is keyed by the volume's name
  and re-resolves every tick, so it keeps its margin and its hold. Do not unwatch and
  re-arm around a rebuild - that drops the tractor and fires a spurious `volume_recovered`
  at every ship inside;
- if you started containment with `relic_contain`, editing `Margin:`, `Scrape band:`,
  `Containment:` or `Forbid jump:` takes effect on the **same** Preview as moving a
  chamber. If you called `volume_watch` by hand instead, your numbers are left alone.

### Your half: the art

The props scattered over the walls are yours, and nothing in the library knows what they
are. After a rebuild it emits `relic_rebuilt`, carrying `key`, `volume` and `file`:

```
//shared/signal/relic_rebuilt
    relic_undress()          # delete your props FIRST
    relic_dress()
    relic_atmosphere()
```

Order matters. Delete before you build, so an identity guard (*if the walls are already
here, do nothing*) sees an empty role and rebuilds instead of no-opping. `delete_object`
clears role membership as it goes, so the two are safe back to back.

A mission with no such route is not broken - its geometry rebuilds and its old walls stay
standing. That is the deal: **geometry is free, art is opt-in.**

### Only a relic read from a file can be reloaded

`relics_build` / `relics_load` remember the path they read and the volume they built. A
relic assembled in code has nothing to re-read, and Preview will say so rather than
pretend. The same goes for the other two failures worth naming: no session on the port,
and a key that no longer exists in the file.

From MAST or Python, the same thing without the editor:

```
relic_reload("ossuary")     # one relic, by key
relics_reload_all()         # every relic that came from a file
```

## See also

- [Volume API](../api/procedural/volume.md) — the functions behind all of this.
- [The AMD file format](amd-format.md) — headings, fences and value shapes.
