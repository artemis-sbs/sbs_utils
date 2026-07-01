# Porting from Artemis 2.x

!!! danger "Work in progress — alpha quality"
    The `a2x` comfort layer and the `arme2cosmos` tool are **a work in progress at
    alpha-level quality**. Coverage is incomplete, names and behavior may change,
    and converted missions will need hand-tuning. Treat everything here as a
    starting point, not a finished path &mdash; and expect rough edges.

Coming from Artemis 2.8 (SBS) XML missions? The **`a2x` comfort layer** mirrors the
vocabulary of the old XML so hand-ports read like the original, and the
[`arme2cosmos`](https://github.com/artemis-sbs) migration tool uses it to translate
2.8 scripts into MAST automatically.

!!! note "Comfort layer, not the idiomatic API"
    `a2x` exists to make porting easy, not to be the best way to write new
    missions. For new work, prefer the native procedural functions
    ([spawn](../api/procedural/spawn.md), [comms](../cosmos/comms.md),
    [world building](../build/world-building.md), etc.).

## How it's exposed

Every `a2x` function is available in MAST with an **`a2x_` prefix** (e.g.
`a2x_pos`, `a2x_create_enemy`). No import is needed.

## Legacy semantics it assumes

- **Corner-origin coordinates** (0..100000), mirrored about the map centre the way
  Cosmos expects &mdash; use `a2x_pos(x, y, z)` to convert.
- **Headings in degrees** (0..360) &mdash; `a2x_angle(deg)`.
- **Count / radius / range** bulk placement, like the old spawn tags.

## What's in the layer

**Coordinates & geometry**

```
a2x_pos(x, y, z)         # 2.8 corner-origin position -> Cosmos position
a2x_angle(deg)           # degrees heading -> Cosmos
```

**Spawning** (2.8-style creators)

```
a2x_create_enemy(x, y, z, art, name=None, side="enemy",   behave="behav_npcship")
a2x_create_neutral(x, y, z, art, name=None, side="civilian", behave="behav_npcship")
a2x_create_station(x, y, z, art, name=None, side="friendly", behave="behav_station")
a2x_create_player(x, y, z, art, name=None, side="tsn")
a2x_create_monster(x, y, z, monster_type=0, ...)
a2x_create_anomaly(x, y, z, pickup_type, name=None)
a2x_create_generic(x, y, z, art, ...)
a2x_destroy(handle)
```

**AI**

```
a2x_add_ai(agent, ai_type, data=None)   # attach a 2.x-style AI behavior
```

**Comms & messages**

```
a2x_incoming_comms_text(message, from_name="", title=None, to=None, time=30)
a2x_big_message(title, subtitle1="", subtitle2="", to=None, time=30)
a2x_warning_popup(message, consoles=None, ship=None, title="Warning", time=30)
```

**Conditions**

```
a2x_is_docked(ship, station=None)
a2x_within(obj, x, y, z, radius)
a2x_in_box(obj, least_x, least_z, most_x, most_z, inside=True)
```

**Object properties**

```
a2x_set_ship_text(obj, name=None, race=None, ship_class=None, desc=None, ...)
a2x_set_special(obj, ability=None, on=True)    # elite/special abilities
a2x_set_side_value(obj, value)
a2x_set_fleet_coeff(which, value)
```

## The `arme2cosmos` tool

`arme2cosmos` is a standalone (stdlib-only) tool that converts Artemis 2.8 XML
missions into MAST, emitting `a2x_` calls so the output stays close to the source.
It depends on this comfort layer (plus the LegendaryMissions add-ons); the layer
itself never depends on LegendaryMissions.

After a conversion, treat the output as a starting point &mdash; it will run, but
you'll get cleaner, more maintainable missions by moving hot spots to the native
Cosmos API over time.
