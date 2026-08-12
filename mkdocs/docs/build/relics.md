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

## Checking it

`sbs lint` catches the faults that are otherwise silent — a `Passage to:` naming a chamber
that does not exist, a part naming a relic that does not exist, a radius of zero, a
`Chamber:` with too few numbers. All of them build *something*, just not what you wrote,
so they surface as a pathfinding bug rather than a typo.

## Looking at one

**Artemis AMD: Show Relic Plan** opens the relic, and nothing needs to be running:

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
