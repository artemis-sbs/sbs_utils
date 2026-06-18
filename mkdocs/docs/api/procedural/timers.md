# Timers and counters

Delay execution and count events with awaitable promises.

## Overview

Timers let MAST scripts wait for a real-time or simulation-time duration before continuing. Two time bases are available:

- **Real time** (`delay`) — wall-clock seconds; unaffected by simulation speed.
- **Simulation time** (`delay_sim`) — scaled by the engine's simulation clock.

Counters (`count_goal`) are awaitable promises that resolve once a named counter reaches a target value. Increment the counter with `increment_count`; reset it with `reset_count`.

All timer and counter functions are designed to be used with `await` in MAST:

```
await delay_sim(seconds=5)
await count_goal("enemies_killed", 10)
```

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == timed_event ==
        log("Reactor will detonate in 30 seconds!")
        await delay_sim(seconds=30)
        log("The reactor has detonated!")
        explode_player_ship(station_id)
        ->END

    == count_kills ==
        await count_goal("kills", 5)
        log("You have destroyed 5 enemies.")
        ->END

    //signal/enemy_destroyed
        increment_count("kills")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.timers import delay_sim, delay, count_goal, increment_count, reset_count

    # Wait 10 simulation seconds before continuing
    await delay_sim(seconds=10)

    # Wait 5 real seconds
    await delay(seconds=5)

    # Count-based gate
    await count_goal("patrols_complete", 3)

    # Increment from signal handlers or events
    increment_count("patrols_complete")
    reset_count("patrols_complete")
    ```

## Real time vs simulation time

| Function | Time base | Pauses with sim? |
|---|---|---|
| `delay(seconds)` | Wall clock | No |
| `delay_sim(seconds)` | Simulation clock | Yes |

## API

::: sbs_utils.procedural.timers
