# The media system

Schedule skybox and music ``@media`` labels defined in MAST.

## Overview

Media labels are declared in MAST with the `@media/kind/path "Display"` syntax and discovered at runtime. `media_schedule` and `media_schedule_random` look up registered labels by kind (`"skybox"` or `"music"`) and apply them via the engine's `set_sky_box` / `set_music_folder` calls, then run the label as a sub-task.

The `ID` parameter targets a specific ship or client; `0` (the default) applies the change globally on the server.

Use `skybox_schedule` / `music_schedule` as convenient wrappers when you already know the media name; use the `_random` variants to pick from all registered labels of that kind automatically.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    @media/skybox/nebula "Nebula"
    @media/skybox/deep_space "Deep Space"
    @media/music/battle "Battle Music"

    == setup ==
    skybox_schedule_random()
    music_schedule("battle")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.media import (
        skybox_schedule, skybox_schedule_random,
        music_schedule, music_schedule_random,
    )

    # Pick a specific skybox
    skybox_schedule("nebula")

    # Pick a random skybox
    skybox_schedule_random()

    # Ship-specific music (pass ship ID)
    music_schedule("battle", ID=ship_id)

    # Random music for server
    music_schedule_random()
    ```

## API

::: sbs_utils.procedural.media
