# The ASCII grid format

A public authoring format for ship interiors, requested as a **replacement for grid
data**. Built and exercised by the interiors work (done). Mechanics:
`GRID_REFERENCE.md`.

**Status: proposal.** New authoring syntax gets confirmed before it is built. s4 lists the
forks that need a decision.

---

## 1. Follow the tile map

`sbs_utils/cards/card.py` already has an ASCII map system (`Tilemap.map_deck` / `.fill`,
used by HereThereBeMonsters and theta_quadrant). Match it rather than invent:

| Convention | Tile map | Grid format |
|---|---|---|
| one char maps to one thing | `map_deck(char, deck)` | char -> room |
| duplicate key | warned | **error** |
| `.` reserved as no-op | yes | yes - open hallway cell |
| unknown chars | skipped | **error** |
| row-major, top line first, width from first line | yes | yes |

Two deliberate tightenings. In a tile map a skipped character loses one asteroid; in a
floor plan it silently deletes a room, and a silently deleted room is a system that
quietly has fewer hit points than the author intended.

The one genuine difference: a tile map draws a **deck** (weighted random); an interior is
deterministic. Chars map to rooms, not decks.

**Stdlib only.** If the format is parsed at runtime (s4 q3), that parser runs inside
Cosmos's embedded Python. No pip packages, no PIL, no exceptions.

---

## 2. What the format buys beyond less typing

- **Multi-cell rooms become the natural expression.** Today a 4-cell cargo hold is four
  JSON objects that happen to share a name and happen to be adjacent - the connected-
  component structure `GRID_REFERENCE.md` s5 had to recover *statistically*. In ASCII it is
  `cccc`. The author types the thing directly.

  This changes **authoring, not rendering**. Icons are center-anchored on a grid node, so
  `cccc` still draws four cargo icons, exactly as the four JSON objects do today - and
  `scale` could never have collapsed them into one, because scaling grows an icon about
  its own node rather than filling a block (`GRID_REFERENCE.md` s3). A one-icon-per-room
  look is a separate idea needing a different mechanism, not a property of this format.
- **Shape is legible.** The intent in the corpus - warp on the nacelles, `beam-aft` on the
  centerline, `sick-bay` in the protected core - is visible in an ASCII map and invisible
  in 3171 coordinate entries.
- **Off-hull placement becomes unrepresentable** rather than merely caught (s3).

---

## 3. Seed the file from the hull

The author never types the hull. The tool generates the file pre-filled, and the author
paints rooms over it:

```
  ' '  off-hull    - not a cell, cannot be painted
  '.'  open cell   - hallway, no object (the tile map's reserved no-op)
  else room per legend
```

So `pirate_brigantine` starts as:

```
      ..
    ....
    ....
   ......
   ......
  ........
  ........
 ..........
 ..........
..........
```

An author physically cannot place a room off-hull, because there is no cell there to type
on. That converts the most common defect in the shipped data - `science_ship` at 0.76,
rooms one cell outside the hull - from a validator complaint into an unrepresentable
state.

**Where the outline comes from depends on context** (`GRID_REFERENCE.md` s2, s8): the
engine's own `is_grid_point_open` when running in Cosmos, a PNG alpha decode in the mock
and in offline tooling. Regenerating the outline when a mask changes is the same code.

### 3.1 `damcons:` - how many teams, and where they stand

LegendaryMissions #381 asked for two things: a grid that needs no hallway, and damage
control teams as part of the grid data. The declaration is a **header key**, not a map
character:

```
damcons: <token> [<token> ...]      # a bare int is the COUNT; "x,y" is a POST

damcons: 3                          # three teams, engine-placed (today, written down)
damcons: 5                          # five teams, engine-placed
damcons: 3,2  1,4  5,4              # three posts -> count 3
damcons: 5  3,2  1,4                # five teams; DC1/DC2 posted, the rest engine-placed
```

**Why not a map character.** A post *coexists* with whatever occupies its cell, and the
map is one character per cell - so a post character would have to delete a room to make
space for it. On a hull with no hallway that is every cell, which is precisely the state
#381 exists to support. `' '` and `'.'` are reserved and rejected as legend keys, an
overlay map doubles the file, and the header already holds the other whole-ship facts
(`size:`, `theme:`).

Compatibility falls out of that choice: the parser collects unknown header keys and
ignores them, so an **older** parser reading a file with `damcons:` still loads every
room. An unknown *map* character, by contrast, is a hard `GridAsciiError`.

**Absent is not the same as `3`.** A plan with no `damcons:` line round-trips to an entry
with no `damcons` key, and `grid_get_damcons` returns `None` - the sentinel that keeps
every shipped floor plan and every third-party hull on exactly the old code path. Posts
above the stated count raise the count (four posts and `3` is a typo whose only sane
reading is four).

**A post is also the rally point.** `prefab_lifeform_damcons` spawns the team's rally
marker on the cell it is handed and seeds `blackboard:idle_pos` from it, so posting a team
by the nacelles keeps it there - no separate rally declaration, and no change to the brain.

**A bad coordinate is an authoring error, never a runtime one.** `grid_ascii_validate`
reports a post that is off the grid or off the hull as an *error*; at runtime
`grid_restore_damcons` logs a warning and lets the engine choose instead, because one typo
must never leave a ship with no damage control. An *occupied* post is accepted silently -
that is the whole point.

---

## 4. Open design questions

The forks. None is settled.

### q1. Where do roles live? RESOLVED - a room registry, not the theme

The original fork was "legend carries roles" vs "the theme supplies them". **The theme
option is wrong**, and not for the reason it looked close:

**The theme is a SKIN.** `grid_theme.json` holds `colors`, `damage_colors`, `icons`, and
`Retro` exists purely to re-skin the same ships. Roles are **mechanics** - they set
`system_max_damage` pools and the damage coefficients (`GRID_REFERENCE.md` s3). Roles
riding the theme would mean switching cosmos -> Retro changes what a ship can survive.
Category error.

**But repeating roles in every legend is redundancy that drifts.** Measured across the
corpus: **60 distinct room names, exactly one with more than one roleset** - `rec-room`,
53x `room,cabin,recreation` against 1x `...,gym` and 1x `...,brig`. Those two are
authoring mistakes that have gone unnoticed in shipped data. Name -> roles is effectively
a function, so retyping it per file buys nothing and risks a room that silently counts
toward no system pool.

**Three layers, not two:**

| Layer | Owns | Why it is separate |
|---|---|---|
| **Room registry** - `name -> roles` | mechanics | must survive a re-skin |
| **Theme** - `role -> icon/color` | appearance | exists to be swapped |
| **Legend** - `char -> room` | layout | per-file |

The legend names a room; roles come from the registry; an explicit roles clause overrides:

```
c: cargo                            # roles from the registry
c: plunder-hold / room,bay,cargo    # a new room type declares its own
```

The registry is **generated from the corpus during the migration** (phase 6), so it is not
new authoring work. A mod adding a room type declares roles inline and needs no theme
edit. And the validator gains a real check - *"`cargo` normally means `room,bay,cargo`;
did you mean to change it?"* - which is exactly what would have caught both `rec-room`
slips.

Fix those two rows during the migration.

### q2. Half-map with mirroring? RESOLVED - no. Full width.

The HULL is symmetric: all **63 of 63** captured hull maps are perfect left-right mirrors,
every one with `symmetrical_flag=1`. (That also answers probe 2.) So mirroring the
*outline* would be free - but the outline is generated for the author anyway (s3), so it
saves nothing.

**The CONTENTS are not symmetric, and mirroring them destroys rooms.** Measured over the
40 authored interiors: a half-map mirror gets **537 of 3171 cells wrong - 16.9%**, and up
to 39% on `starbase_industry`.

Mirroring `tsn_light_cruiser`'s port half:

| Room | before | after |
|---|---|---|
| `saloon` | 2 | **0** - it sits to starboard and vanishes entirely |
| `sick-bay` | 2 | 4 |
| `gymnasium` | 1 | 2 |
| `beam-starboard` | 1 | **0** |
| `beam-port` | 1 | **2** |
| `astro-lab`, `galley`, `conference-room`, `Workshop` | 1 | **0** |

The last two rows are not cosmetic: beam nodes set `system_max_damage` for weapons, so a
mirrored map silently changes what the ship can survive.

**So: full width, always.** It is also the format's whole selling point - a full-width map
is legible AS the ship (s2), and halving it throws that away to save typing on a file that
is generated pre-filled anyway.

**Mirroring stays as a TOOL operation, not a format feature** - paint one side, press
mirror, then fix the singletons. The author sees the result and owns it; nothing is
mirrored at load time, where a mistake would be invisible.

**Consequence for the validator:** port/starboard asymmetry is NORMAL at ~17%, so a
symmetry check must be a hint ("this room has no counterpart - deliberate?"), never an
error.

### q3. Runtime-parsed, or compiled to JSON?

Runtime parsing preserves tier 1's no-build-step property and makes the ASCII genuinely
*the* format rather than a source that compiles to the real one. A compile path is still
worth having for diffing and debugging.

**Recommendation: parse at runtime, compile on demand.** Note this puts the parser inside
the engine (s1).

Whichever way this goes, the format does NOT carry `scale`: it is per-icon emphasis owned
by the theme, and it cannot express extent (s2).

### q4. Replace or coexist?

JSON stays readable regardless. The question is only whether a *mod* may still ship JSON.

**Recommendation: both, with ASCII as the documented path.**

---

## 5. Where the generator fits

The `GRID_REFERENCE.md` s5 grammar - fore/aft and centre/edge distributions, blob-size
histograms, fill density, system counts derivable from shipData - is close to a generator
spec.

It should produce a **draft ASCII map**, not runtime output. Drafting into an editable
text file keeps the authored map as the artifact, so a bad placement is a one-character
fix rather than a tuning problem.

**Do not generate hand-authored-quality interiors at runtime.** What the grammar captured
is statistics, not design; a generator reproduces the averages and loses the reasons, and
every ship comes out looking like the same ship.

**The exception is systems-only**, which is genuinely
derivable rather than statistical - every node comes from shipData - and which *should*
run at spawn from the engine's own hull map. That is a different thing wearing similar
clothes: derivation, not imitation.

This is what makes the remaining stubs tractable. Torgoth, Skaraan, Kralien, Biomech and
cargo are several thousand more objects that nobody is going to hand-place.

---

## 6. Acceptance

The format is done when it **round-trips all 40 authored ships** - render to ASCII, read
back, get identical JSON semantics: same cells, same roles, same system counts. Not
spot-checked, and not one ship.

A ship that will not round-trip means the format is under-designed. Fix the format; do not
special-case the ship.
