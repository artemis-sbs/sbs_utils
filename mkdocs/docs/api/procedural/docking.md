# Docking system

Manage proximity-based docking between player ships and NPCs.

## Overview

The docking system runs a background tick task that monitors registered (player, NPC) pairs for proximity. When a player ship comes within the docking distance defined on the label, the system drives the pair through a state machine:

```
undocked → docking → dock_start → docked → undocking → undocked
```

Each state transition runs an inline sub-label (defined with `///`) on the docking label:

| Inline label | Runs when |
|---|---|
| `///enable` | Player comes within range — return `FAIL_END` to prevent docking |
| `///docking` | Approach phase — NPC closes in on player |
| `///docked` | Pair has physically connected — run refit logic here |
| `///refit` | Called each tick while docked |
| `///throttle` | Called when player throttle exceeds 0.6 — return `OK_SUCCESS` to undock |
| `///undocking` | Pair is separating |

The `DOCKING_PLAYER`, `DOCKING_PLAYER_ID`, `DOCKING_NPC`, and `DOCKING_NPC_ID` variables are set in every inline label. The `docked` signal is emitted when the pair reaches the `docked` state.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        docking_set_docking_logic(player_set, station_set, docking_logic)
        ->END

    == docking_logic ==
        ///enable
        OK_SUCCESS   # always allow docking

        ///docked
        set_engineering_value(DOCKING_PLAYER_ID, "energy", 1000)
        OK_SUCCESS

        ///refit
        hp = get_engineering_value(DOCKING_PLAYER_ID, "hullLevel")
        if hp >= 1.0: OK_SUCCESS
        set_engineering_value(DOCKING_PLAYER_ID, "hullLevel", hp + 0.01)
        OK_RUN_AGAIN

    //signal/docked
        log(f"Ship {DOCKING_PLAYER.name} has docked.")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.docking import docking_set_docking_logic

    docking_set_docking_logic(player_set, station_set, docking_logic_label)
    ```

## API

::: sbs_utils.procedural.docking
