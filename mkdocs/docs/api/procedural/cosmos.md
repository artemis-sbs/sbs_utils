# The cosmos functions

Low-level simulation control: create, pause, and resume the game simulation.

## Overview

These three functions wrap the engine's simulation lifecycle commands. They are typically called from lobby or game-flow scripts rather than from regular mission logic.

- **`sim_create`** — initialises a new simulation instance. Called once at the start of a mission after all setup is complete.
- **`sim_pause`** — freezes the simulation clock. Objects stop moving; timers stop counting.
- **`sim_resume`** — resumes a paused simulation.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == mission_start ==
        sim_create()
        jump setup

    == cutscene ==
        sim_pause()
        await delay(seconds=5)
        sim_resume()
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.cosmos import sim_create, sim_pause, sim_resume

    sim_create()
    # ... later ...
    sim_pause()
    sim_resume()
    ```

## API

::: sbs_utils.procedural.cosmos
