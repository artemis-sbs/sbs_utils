# The races add-on

!!! warning "List this in your `story.json`"
    A mission that loads LegendaryMissions' `ai` or `fleets` add-on **also needs the
    `races` add-on**. Leave them out and your player ship has a **dead Engineering
    console**, and **nothing raids you** — with no error to tell you why.

    ```json title="story.json"
    "mastlib": [
        "artemis-sbs.LegendaryMissions.ai.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.fleets.v1.4.0.mastlib",
        "artemis-sbs.LegendaryMissions.races.v1.4.0.mastlib"
    ]
    ```

    Missions created with `sbs create` from the v1.4.0 templates already have them.

## What it carries

One add-on covering every race, holding two kinds of per-race content.

| Content | What it does | Without it |
|---|---|---|
| **Ship interiors** | one ASCII floor plan per hull — the rooms and system nodes Engineering shows | the Engineering console is empty: no system nodes, no damcons, no internal damage |
| **Fleet ladders** | which ships make up a raiding fleet at each difficulty | `fleet_create` finds no ladder, so nothing spawns |

Nine races in v1.4.0 — TSN, Ximni, USFP, Arvonian, Torgoth, Skaraan, Kralien, Biomech and
Pirate — covering **63 ship interiors** and **six fleet ladders**.

**Why one add-on and not one per race:** the per-race control is in the settings below.
Splitting the *package* too would only have made every mission list nine mastlibs instead
of one, without granting anything the settings did not already give.

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

Each race's content is skipped when it is not listed. An interior is only ever built for a
**player** ship, so floor plans for a race nobody can fly are parsed at load and never
used — with `PLAYABLE_RACES: "TSN"` that is 25 floor plans loaded instead of 63.

Both settings ignore case and spacing, and an **empty** setting means *no restriction*
rather than *nothing* — clearing it gives you every race.

## Adding a race

A race is a block in `races/__init__.mast`, or a whole add-on of your own — the calls are
the same either way. See [Making add-ons](addons.md).

```mast title="__init__.mast"
provides races_myrace

if settings_race_is_playable("MyRace"):
    grid_merge_ascii(media_read_relative_file("myrace_cruiser.grid"), "races_myrace")

if settings_race_is_npc("MyRace"):
    fleet_table_load_yaml(media_read_relative_file("myrace_fleets.yaml"), "races_myrace")
```

Files are named **race first** (`myrace_cruiser.grid`, `myrace_fleets.yaml`) so everything
for one race sorts together — a mastlib zip is flat, so names must be unique across the
whole add-on.

Floor plans are ASCII grid files (`.grid`). Fleet ladders are YAML, and have a page of
their own — the file format, the difficulty encoding and per-faction sides are all in
**[Fleets & raiding](fleets.md)**.

Adding a whole race of your own, with its ships and art as well as its interiors and
ladder, is **[Making a mod](making-a-mod.md)**.

Two add-ons supplying the same hull or the same race are reported by name in the log
rather than silently letting the last one win.

## Related

- [Fleets & raiding](fleets.md) — ladders, difficulty, spawning
- [Making a mod](making-a-mod.md) — a race with its own ships and art
- [Making add-ons](addons.md)
- [Mission settings](../home/settings.md)
- [Damage](damage.md) — what the interior's system nodes actually do
