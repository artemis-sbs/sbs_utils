# Fleets & raiding

A **fleet** is a group of NPC ships spawned together, given a shared brain, and pointed at
your players. What ships it contains comes from a **fleet ladder** — a per-race table of
what a raiding force looks like at each difficulty.

You need this page if you are placing enemies in a map, or if you are adding a race and
want it to show up in the rotation.

## Spawning one

Fleets are a **prefab**, so a map spawns one the same way it spawns anything else:

```mast
prefab_spawn(prefab_fleet_raider, {"race": "kralien", "fleet_difficulty": DIFFICULTY,
                                   "START_X": pos.x, "START_Y": pos.y, "START_Z": pos.z})
```

!!! warning "Keep the dict on one line"
    MAST parses line by line, so a `{` broken across lines is an unclosed brace — and the
    error cascades through the rest of the file. Bind it to a variable first if it gets
    long. See [Common gotchas](../mast/gotchas.md).

| Key | Default | What it does |
|---|---|---|
| `race` | `kralien` | Whose ladder to draw from. `"random"` picks among registered races |
| `fleet_difficulty` | `5` | Which tier — see [Difficulty](#difficulty) below |
| `ship_roles` | `raider` | Roles added to every ship in the fleet |
| `fleet_roles` | `raider_fleet` | Roles added to the fleet agent itself |
| `faction_side` | `false` | Put the fleet on its own side — see [Sides](#sides-shared-raider-or-per-faction) |
| `START_X/Y/Z` | — | Where it appears |
| `brain` | a chase-and-scatter tree | The fleet's behavior |

The prefab returns the fleet agent's id. The default brain picks a target (angriest first,
then stations, then players), computes a forward vector and scatters into formation; supply
your own `brain` to change that. See [Brain Trees](../mast/ai/brains.md).

## Difficulty

`fleet_difficulty` is **1-based** in the prefab, and the encoding has two special forms
that are easy to miss.

| You pass | You get |
|---|---|
| `1` … `11` | that tier, counting from 1 |
| `0` | **the mission's `DIFFICULTY` setting** |
| `200` | `DIFFICULTY + 2` — a *relative* offset |
| `-200` | `DIFFICULTY - 2` |

Anything with a magnitude over 99 is read as a relative offset of `value // 100`, which is
floor division — so `-150` is `DIFFICULTY - 2`, not `- 1`. The result is then clamped to the
ladder, so you cannot fall off either end even if a race ships fewer tiers than you assumed.

The relative form is the useful one for a map that wants a fight *harder than the mission
is set to* without hard-coding a number:

```mast
# Two tiers above whatever the players chose
prefab_spawn(prefab_fleet_raider, {"race": "torgoth", "fleet_difficulty": 200, ...})
```

## The ladder file

One YAML file per race, loaded by that race's add-on. Eleven tiers, and each tier holds
several **variants** — one variant is one fleet, and the spawner picks among them at random,
so difficulty 4 does not produce the same three ships every game.

```yaml title="myrace_fleets.yaml"
race: myrace
fleets:
  # difficulty 0 — five variants, all the same here
  -
    - [myrace_scout]
    - [myrace_scout]
    - [myrace_scout]
    - [myrace_scout, myrace_scout]
    - [myrace_scout, myrace_scout]
  # difficulty 1
  -
    - [myrace_scout, myrace_scout]
    - [myrace_cruiser]
    - [myrace_cruiser]
    - [myrace_cruiser, myrace_scout]
    - [myrace_cruiser, myrace_scout]
```

Registered from the add-on, gated so a race nobody enabled is not parsed:

```mast title="__init__.mast"
if settings_race_is_npc("MyRace"):
    fleet_table_load_yaml(media_read_relative_file("myrace_fleets.yaml"), "my_addon")
```

Fewer than eleven tiers is fine — the index is clamped, so asking for a tier past the end
gives the top one rather than an error mid-spawn. Two add-ons registering the same race are
reported by name in the log instead of the last one silently winning.

### Designing one

The shipped ladders are built on three combat hulls plus a flagship, and escalate roughly
like this: tier 0 is a single light hull, the medium appears around 2, the heavy around 6,
and tier 10 is a six-ship wall led by the flagship. Copying that curve is a reasonable
starting point — it is the one players have actually played against.

Fighters are usually **left out**: they are carrier craft rather than fleet units, which is
why the shipped pirate ladder has no `pirate_fighter` in it.

## Sides: shared `raider`, or per-faction

By default every raiding fleet goes on the shared **`raider`** side, whatever race it is.
That is simple and it is what most missions want.

`faction_side: true` instead puts the fleet on **its own side**, registered hostile to every
current player side:

```mast
prefab_spawn(prefab_fleet_raider, {"race": "torgoth", "faction_side": True, ...})
```

Each ship still carries the `raider` role, so anything scoping on that role keeps working —
but the ship's **side** is now the faction. That is what makes a multi-faction scenario
possible: hostility is expressed as diplomacy, so a mission can call a ceasefire with one
faction while another keeps firing. See [Sides, lifeforms & faces](sides-lifeforms.md).

## Which races can raid

A race raids if it has a **registered ladder**, which means the race is in `NPC_RACES` *and*
some add-on loaded a ladder for it. **A new race joins the rotation by existing** — nothing
holds a list of factions to keep in sync.

```mast
fleet_table_races()          # every race with a ladder, sorted
fleet_table_has("myrace")    # does this one have a ladder?
fleet_table_pick_race()      # one at random, honoring the mission seed
fleet_table_get(race, difficulty, variant=None)   # the ship keys for one fleet
```

`"random"` as the race picks among the registered ones, so a map does not have to know who
is installed.

## When nothing spawns

Almost always one of two things, and the first one tells you so:

- **No ladder for that race.** `fleet_create` prints the race it was asked for and the list
  of races that *are* registered. Usually the race is missing from `NPC_RACES`, or it is a
  typo.
- **The `races` add-on is not in `story.json`.** Then no race has a ladder at all. See
  [The races add-on](race-addons.md).

Both fail quietly in the game itself — you simply are not attacked — so check the log rather
than the screen.

## Related

- [The races add-on](race-addons.md) — where the shipped ladders live
- [Making a mod](making-a-mod.md) — shipping a race, its ships and its ladder together
- [Brain Trees](../mast/ai/brains.md) — what the fleet does once it exists
- [Sides, lifeforms & faces](sides-lifeforms.md) — diplomacy between factions
- [Mission settings](../home/settings.md) — `DIFFICULTY`, `NPC_RACES`
