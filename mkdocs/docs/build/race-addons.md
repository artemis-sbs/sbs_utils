# Race add-ons

!!! warning "List these in your `story.json`"
    A mission that loads LegendaryMissions' `ai` or `fleets` add-on **also needs the
    `race_*` add-ons**. Leave them out and your player ship has a **dead Engineering
    console**, and **nothing raids you** — with no error to tell you why.

    ```json title="story.json"
    "mastlib": [
        "artemis-sbs.LegendaryMissions.ai.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.fleets.v1.4.0.mastlib",

        "artemis-sbs.LegendaryMissions.race_tsn.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.race_ximni.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.race_usfp.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.race_arvonian.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.race_torgoth.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.race_skaraan.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.race_kralien.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.race_biomech.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.race_pirate.v1.4.0.mastlib"
    ]
    ```

    Missions created with `sbs create` from the v1.4.0 templates already have them.

## What a race add-on carries

One add-on per race, named for the race rather than for its contents, because a race is
more than any one of them.

| Content | What it does | Without it |
|---|---|---|
| **Ship interiors** | one ASCII floor plan per hull — the rooms and system nodes Engineering shows | the Engineering console is empty: no system nodes, no damcons, no internal damage |
| **Fleet ladders** | which ships make up a raiding fleet at each difficulty | `fleet_create` finds no ladder, so nothing spawns |

v1.4.0 ships nine: `race_tsn`, `race_ximni`, `race_usfp`, `race_arvonian`,
`race_torgoth`, `race_skaraan`, `race_kralien`, `race_biomech`, `race_pirate`.

## Why they are separate

Both bodies of content used to be **built in and unreachable**. Interiors lived in the
engine's `data/grid_data.json`, which is game-install data no mission or mod can edit.
Fleet ladders were six Python literals inside LegendaryMissions' `fleets` add-on, behind
an `if race == "..."` chain, with the roster of factions that can raid written as a
`random.choice([...])` beside it — so adding a race meant editing a mission library, and a
mod could not add one at all.

Now a race declares its own, and `"random"` picks from the races that actually registered
a ladder. **A new race joins the rotation by existing.**

## Turning races off

Two settings, because "which races can a player BE" and "which races raid them" are
different questions — most missions want few of the first and many of the second.

```yaml title="settings.yaml"
PLAYABLE_RACES: "TSN, USFP"                  # whose interiors load
NPC_RACES: "Kralien, Torgoth, Pirate"        # whose fleet ladders load
```

Each add-on skips itself when its race is not listed. An interior is only ever built for a
**player** ship, so floor plans for a race nobody can fly are parsed at load and never
used — with `PLAYABLE_RACES: "TSN"` that is 25 floor plans loaded instead of 63.

Both settings ignore case and spacing, and an **empty** setting means *no restriction*
rather than *nothing* — clearing it gives you every race.

## Adding a race

A race add-on is an ordinary add-on: a folder with `__init__.mast`, listed in
`__lib__.json`. See [Making add-ons](addons.md).

```mast title="race_myrace/__init__.mast"
provides race_myrace

if settings_race_is_playable("MyRace"):
    grid_merge_ascii(media_read_relative_file("myrace_cruiser.grid"), "race_myrace")

if settings_race_is_npc("MyRace"):
    fleet_table_load_yaml(media_read_relative_file("fleets.yaml"), "race_myrace")
```

Floor plans are ASCII grid files (`.grid`); fleet ladders are YAML:

```yaml title="fleets.yaml"
race: myrace
fleets:
  # difficulty 0
  -
    - [myrace_cruiser]
    - [myrace_cruiser, myrace_cruiser]
  # difficulty 1
  -
    - [myrace_battleship]
```

Eleven tiers of five variants is what the shipped races use; fewer is fine — the
difficulty index is clamped, so asking for a tier past the end gives you the top one
rather than an error mid-spawn.

Two add-ons supplying the same hull or the same race are reported by name in the log
rather than silently letting the last one win.

## Related

- [Making add-ons](addons.md)
- [Mission settings](../home/settings.md)
- [Damage](damage.md) — what the interior's system nodes actually do
