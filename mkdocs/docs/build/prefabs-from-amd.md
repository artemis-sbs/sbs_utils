# Creating things from AMD: prefabs

Everything an `.amd` file puts into the world is made by a **prefab**: a landmark's
station or wreck, a side, a cast member's body, a crew member on the ground, a pickup
lying in space, a relic's set pieces and guards, a landmark's guards and the nebula around
it. A record says which prefab with `Prefab:`, and hands it arguments in a `Data:` block.
When a record says nothing, the library's **default** prefab for that kind of record is
used, and it does exactly what that record has always done.

That makes the content as extensible as the prefabs are. A mission that wants its stations
to be something more - docking rules, a brain, comms, a defense grid - writes one prefab
label, and every landmark that names it gets all of that.

## A landmark

```amd
## [Landmarks](landmarks)

### [Kessel Deep](kessel)
---
Prefab: npc/station/industry
Side: kralien
Roles: relay, mining
Loc: 12000, 0, -8000
Data:
  Race value: kralien
---
A Kralien ore refinery that pays in favors, not credits.

### [The Pale Ark](pale_ark)
---
Prefab: derelict
Art: wreck
Loc: -20000, 0, 5000
---

### [Picket Line](picket_lm)
---
Prefab: point
Loc: 4000, 0, 4000
Radius: 2500
---
```

`Prefab:` replaced `Kind:` on landmarks. A landmark that still says `Kind:` creates nothing,
and `sbs lint` tells you the line to write instead (`landmark-kind-retired`).

## Naming a prefab

`Prefab:` takes a prefab **type** - the label's `type: prefab/...` metadata without the
`prefab/` - or the label's exact **name**. Looked up in this order:

1. a label with exactly that name (`prefab_station_industry`);
2. a label whose type is exactly `prefab/<what you wrote>`;
3. a library default of exactly that name;
4. a label whose type is *under* it, when only one is - `npc/station/industry` written
   as `npc/station/ind` would not match, but `fleet` would find `fleet/raider` if it were
   the only fleet.

Exact always beats a prefix, so `npc` is the library's npc even in a mission with a dozen
`npc/...` prefabs. When the name could be several, nothing is created and the game says
which ones it could have been; it never picks one for you.

A mission's own label always wins over a library default of the same type. That is how you
change what `station` means for your whole mission without touching a single record.

## Library defaults

| Prefab | Used by | Makes |
|---|---|---|
| `station` | landmarks | `npc_spawn`, `behav_station` (needs `Art:`) |
| `npc`, `ship` | landmarks | `npc_spawn`, `behav_npcship` (needs `Art:`) |
| `terrain`, `asteroid` | landmarks | `terrain_spawn`, `behav_asteroid` (needs `Art:`) |
| `derelict`, `wreck` | landmarks | `terrain_spawn`, `behav_wreck` (needs `Art:`) |
| `nebula` | landmarks | one nebula object, `behav_nebula` (needs `Art:`) |
| `point` | landmarks | nothing - a named place, a zone, a speaker the document must know |
| `amd/side` | `## Sides` records | `side_create` with the record's fields |
| `amd/lifeform` | cast records | `lifeform_spawn` with the resolved face, roles, host, path |
| `amd/crew` | crew members on the ground | an unhosted lifeform |
| `boarding/host` | boarding zones | the hidden ship an interior is cut from |
| `grid/boarding_figure` | a person on an interior | one grid object |
| `pickup` | items (`item_spawn`, drops, relic contents) | a spinning `behav_pickup` object |
| `npc/ship` | relic `Spawn:` | one ship of a side, a random hull of that side if no `Art:` |
| `relic/setpiece`, `relic/barrier`, `relic/repair`, `relic/marker` | relic parts | the part's body, which the relic then fits to the part |
| `relic/wall` | every piece of a relic's walls | `terrain_spawn` with the style's art - the fast path; a ruin places hundreds |

Open Universe adds its own `derelict`, `station` and `worldlet`, which also bind a `Site:`.
Legendary Missions' catalog (`npc/station/...`, `fleet/raider`, `npc/ship`,
`terrain/nebula/sphere`, monsters, turrets) can be named from any mission that loads it.

!!! note "Sides default to `amd/side`, not `side`"
    Legendary Missions has a `prefab/side` of its own (`prefab_side_generic`), with TSN
    defaults. A side record uses the library's `amd/side` unless it says `Prefab: side`,
    so loading LM never changes what an AMD side record makes.

## Arguments: `Data:`

A prefab's metadata keys are its arguments, with their defaults; so is every
`default x = ...` in its body. Anything a record should hand the prefab goes under `Data:`,
one indented line each. Labels are matched loosely - `Race value:` arrives as
`race_value`, `Fleet difficulty:` as `fleet_difficulty`:

```amd
Data:
  Race value: kralien
  Fleet difficulty: 3
```

`Data:` wins over everything else the prefab is handed. The record's own fields arrive as
the variables prefabs conventionally read:

| Record | Prefab variable |
|---|---|
| heading | `NAME`, `name`, `display_text` |
| position (`Loc:`, `System:`, the cell) | `START_X`, `START_Y`, `START_Z`, plus `START_EXACT = True` |
| `Size:` | `SIZE_X`, `SIZE_Z` |
| `Side:` / `Roles:` / `Art:` / `Behavior:` | `side_value` / `roles_value` / `art` / `behavior` |
| the record, its key | `AMD_RECORD`, `AMD_KEY` |

A field that is not written is not passed, so the prefab's own default stands.
`START_EXACT` exists because a landmark is authored to a point: LM's station prefabs
scatter inside a box unless it is set.

`sbs lint` reports a `Data:` key the prefab does not take (`unknown-prefab-arg`), lists
what it does take, and refuses a key that would hide one of MAST's own names - `range`,
`random`, `list`, `sim` (`prefab-reserved-arg`).

## Fields that create on their own

`Guards:` and `Terrain:` on a landmark, `Spawn:` and `Atmosphere:` in a relic, and
`Fleet:` on an Open Universe side: each takes a prefab, on one line or nested.

```amd
Guards: fleet/raider x2

Guards:
  Prefab: fleet/raider
  Count: 2
  Data:
    Race: torgoth
    Fleet difficulty: 3
```

The older phrases still read: `Guards: torgoth 3` is `fleet/raider` with that race and
difficulty, `Terrain: nebula blue` is LM's nebula sphere sized for cover, and relic
`Spawn: raider x2` is two `npc/ship` on the `raider` side.

A relic's `Walls:` stays a style chain on one line (`Walls: torgoth, plates`). Nested,
it also names the prefab every wall piece is made by - the style still picks each
piece's art, handed to the prefab as `art`:

```amd
Walls:
  Style: torgoth, plates
  Prefab: relic/glowing_wall
  Data:
    Glow: amber
```

The prefab is looked up once for the whole ruin. Leave it out and the pieces are plain
terrain, which matters: a ruin is hundreds of pieces, and a MAST prefab runs once per
piece.

A theater can say which prefab builds each race's fleets, and `theater_fleet_prefab(race)`
answers for it:

```amd
# [The Dominion War](dominion_war)
---
Factions: dominion, cardassian
Fleets: dominion=fleet/dominion, *=fleet/raider
---
```

## Writing a prefab AMD can use

```
=== prefab_relay_station
metadata: ``` yaml
type: prefab/station/relay
display_text: Relay Station
art: starbase_civil
docking: friendly
```
    obj = npc_spawn(START_X, START_Y, START_Z, name, side_value + ", station, relay", art, "behav_station")
    yield result to_id(obj)
```

- **Yield what you made.** `yield result <id>` (or a set of ids) is how the record gets its
  object - a landmark is found again by its key through it. Never `yield result None`; it
  hangs anything waiting on the prefab.
- **Create before you wait.** A prefab that creates and finishes in one go hands back its
  object at once. One that `await`s first is still running when the record asks, so its
  result is collected when it finishes; a side prefab must not wait at all.
- **Metadata keys are the arguments.** Name them for what they mean, never after a MAST
  builtin (`range`, `random`, `list`, `sim`).

## Checking it

| Lint code | Means |
|---|---|
| `landmark-no-prefab` | the landmark names no `Prefab:`, so nothing is created |
| `landmark-kind-retired` | a landmark still says `Kind:`; the message gives the `Prefab:` line |
| `unknown-prefab` | no label, type or library default answers to that name |
| `ambiguous-prefab` | it could be several prefabs; name one |
| `unknown-prefab-arg` | a `Data:` key the prefab does not take |
| `prefab-reserved-arg` | a `Data:` key that would hide a MAST name |
| `data-without-prefab` | `Data:` with no `Prefab:` beside it |
| `prefab-wrong-record` | a landmark's prefab on a record read as something else - usually a landmark under the wrong `##` heading. A side keeps being declared as a side |

`unknown-prefab` is only reported when lint could read the mission's prefab catalog -
its own labels and those in the mastlibs it loads. With an unbuilt mastlib it stays quiet
rather than guessing.
