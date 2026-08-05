# The ASCII grid format

A public authoring format for ship interiors, requested as a **replacement for grid
data**. Built in `GRID_INTERIORS_PLAN.md` phase 5, exercised by phase 6. Mechanics:
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

**Where the outline comes from depends on context**, per `GRID_INTERIORS_PLAN.md` s1a: the
engine's own `is_grid_point_open` when running in Cosmos, a PNG alpha decode in the mock
and in offline tooling. Regenerating the outline when a mask changes is the same code.

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

### q2. Half-map with mirroring, or full width?

Hulls are symmetric and the corpus authors both halves explicitly, so a `mirror` directive
halves the typing. But real layouts have asymmetric singletons - `sick-bay` off-centre,
`beam-port` vs `beam-starboard` - so it needs an escape hatch.

Depends partly on probe 2 (what `symmetrical_flag` actually does).

### q3. Runtime-parsed, or compiled to JSON?

Runtime parsing preserves tier 1's no-build-step property and makes the ASCII genuinely
*the* format rather than a source that compiles to the real one. A compile path is still
worth having for diffing and debugging.

**Recommendation: parse at runtime, compile on demand.** Note this puts the parser inside
the engine (s1).

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

**The exception is systems-only** (`GRID_INTERIORS_PLAN.md` s3.2), which is genuinely
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
