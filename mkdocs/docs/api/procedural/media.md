# The media system

Schedule skybox and music ``@media`` labels defined in MAST.

## Overview

Media labels are declared in MAST with the `@media/kind/path "Display"` syntax and discovered at runtime. `media_schedule` and `media_schedule_random` look up registered labels by kind (`"skybox"` or `"music"`) and apply them via the engine's `set_sky_box` / `set_music_folder` calls, then run the label as a sub-task.

The `ID` parameter targets a specific ship or client; `0` (the default) applies the change globally on the server.

Use `skybox_schedule` / `music_schedule` as convenient wrappers when you already know the media name; use the `_random` variants to pick from all registered labels of that kind automatically.

## A skybox no longer picks the music

It used to. Scheduling a media label runs its **body**, and nothing else ever chose a
track, so every `@media/skybox` label ended in `if client_id==0: music_schedule_random()`
— copied into thirty A28 labels, eight LegendaryMissions ones, and every mission that
inlined them. A skybox label with an empty body left a game silent.

The two are now independent. A skybox sets the sky; music is selected on its own, and a
skybox label body is free for things that are genuinely sky-specific.

## Choosing the music

`MUSIC_SELECT` names a bank — a bare folder name, an `@media/music` label's display name,
or `"random"`. It resolves strongest-first:

| Source | Beats |
|---|---|
| `var.MUSIC_SELECT=` on the engine command line | everything |
| `COSMOS_SETTINGS` environment JSON | the profile and below |
| `profiles/<name>.yaml` | the mission and below |
| the mission's `settings.yaml` | mods and the built-in |
| a mod's `settings_set_mod_default("MUSIC_SELECT", ...)` | the built-in |
| the library built-in, `"random"` | — |

At runtime the operator's console dropdown and a map's `Defaults: MUSIC_SELECT` outrank
the value above, in that order.

**A mission that pins music in its own `settings.yaml` locks every mod out of that key** —
that is what "explicit" means here. Leave it unset unless you mean it.

## Discovering what is available

`music_get_list()` / `skybox_get_list()` return the labels that are actually usable: a
missing folder or a false `if` condition drops the label, so a picker can never offer
something scheduling would refuse. This is what the LegendaryMissions server console builds
its Music dropdown from, which is why a mod's banks appear there without that console
knowing the mod exists.

`music_find(spec)` resolves an index, a path, a display name, or an unambiguous substring —
the same matcher `maps_find` uses, so a name means the same thing on a command line, in a
settings file and in a dropdown. An ambiguous spec returns `None` rather than guessing.

## Music must be a bare name, and that is the engine's rule

`set_sky_box` takes a path in any spelling. **`set_music_folder` does not**: it resolves a
bare name under `data/audio/music/`, and handing it a path does not fail — it **hangs the
engine**. The call never returns (measured in `missions/music_probe`, engine 1.3.6).

So a bank shipped in a mod's media pack is found by sbs_utils, and then deliberately *not*
handed over: the label logs a warning naming the folder it found and plays `default`. Copy
the folder into `data/audio/music/` to use it today. When an engine build is measured to
survive a path, set `MUSIC_ENGINE_ACCEPTS_PATHS: true` and packs work directly.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    @media/skybox/nebula "Nebula"
    @media/skybox/deep_space "Deep Space"
    @media/music/battle "Battle Music"

    == setup ==
    skybox_schedule_random()
    # "", None or "random" picks at random; anything else is resolved by name,
    # and a spec that matches nothing warns and falls back rather than going silent.
    music_schedule_select(MUSIC_SELECT)
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.media import (
        skybox_schedule, skybox_schedule_random,
        music_schedule, music_schedule_random, music_schedule_select,
        music_get_list, music_find, music_current,
    )

    # Pick a specific skybox
    skybox_schedule("nebula")

    # Pick a random skybox
    skybox_schedule_random()

    # Whatever MUSIC_SELECT asked for, including "random"
    music_schedule_select(settings_get_defaults().get("MUSIC_SELECT"))

    # Ship-specific music (pass ship ID)
    music_schedule("battle", ID=ship_id)

    # What a picker offers, and what is playing now
    [(m.path, m.display_name) for m in music_get_list()]
    music_current()          # -> the bank name, "default" until something schedules one
    ```

## API

::: sbs_utils.procedural.media
