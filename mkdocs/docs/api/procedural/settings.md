# The settings system

Mission configuration defaults loaded from `settings.yaml` (or legacy `setup.json`).

## Overview

`settings_get_defaults()` returns a dict of built-in defaults merged with mission-specific overrides from `settings.yaml` in the mission directory. The result is cached after the first call, so all modules that read settings see a consistent snapshot.

Common use-cases:

- **Reading built-in settings** like `DIFFICULTY`, `PLAYER_COUNT`, `WORLD_SELECT`, or operator-mode config.
- **Adding module-specific defaults** with `settings_add_defaults` so that a module's settings are visible in `settings_get_defaults()` even when the author hasn't created a `settings.yaml`.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        settings = settings_get_defaults()
        difficulty = settings.get("DIFFICULTY", 5)
        log(f"Difficulty is {difficulty}")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.settings import settings_get_defaults, settings_add_defaults

    # Read built-in settings
    settings = settings_get_defaults()
    difficulty = settings.get("DIFFICULTY", 5)
    player_count = settings.get("PLAYER_COUNT", 1)

    # Register module-specific defaults (won't override settings.yaml values)
    settings_add_defaults({
        "ENEMY_COUNT": 10,
        "BOSS_ENABLED": False,
    })
    ```

## Built-in settings keys

| Key | Default | Notes |
|---|---|---|
| `DIFFICULTY` | 5 | Mission difficulty 1–10 |
| `PLAYER_COUNT` | 1 | Expected number of player ships |
| `WORLD_SELECT` | `"siege"` | World generation preset |
| `TERRAIN_SELECT` | `"some"` | Terrain density |
| `LETHAL_SELECT` | `"none"` | Lethal NPC density |
| `FRIENDLY_SELECT` | `"few"` | Friendly NPC density |
| `UPGRADE_SELECT` | `"max"` | Available upgrades |
| `AUTO_START` | `False` | Skip lobby and start immediately |
| `GAME_STARTED` | `False` | Set by the game engine at start |
| `GAME_ENDED` | `False` | Set by mission when over |
| `GRID_THEME` | 0 | Engineering grid color theme index |
| `PLAYER_LIST` | list of 8 ships | Player ship definitions |

## API

::: sbs_utils.procedural.settings
