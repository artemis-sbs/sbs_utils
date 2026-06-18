# The mission system

Structured mission lifecycle runner with `init`, `start`, `objective`, and `complete` phases.

## Overview

`mission_run` spawns a task that drives a MAST label through a defined lifecycle. The label should contain named `cmd_map` blocks (using the MAST `///` inline route syntax) for each phase:

| Block | When it runs |
|---|---|
| `///init` | Immediately, once |
| `///start` | After `__START__` is set to `True` in the task |
| `///objective` | Each tick while running; returns `OK_SUCCESS` when the objective is met |
| `///complete` | Each tick while running; returns `OK_SUCCESS` when the mission is complete |
| `///abort` | Each tick while running; returning `FAIL_END` aborts the mission |

The `mission_runner` generator drives these blocks in sequence. `init` runs first. The runner then waits until something sets `task.__START__ = True` before running `start`. After that, `abort`, `objective`, and `complete` are polled each tick.

This is the same pattern used by the built-in objective system — use `mission_run` for higher-level structured missions, and the `objective` module for lower-level task tracking.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        mission_run(escort_mission)
        ->END

    == escort_mission ==
        ///init
        spawn_escort_target()
        ///start
        log("Escort the freighter to the station.")
        ///objective
        if freighter_arrived(): OK_SUCCESS
        OK_RUN_AGAIN
        ///abort
        if freighter_destroyed(): FAIL_END
        OK_RUN_AGAIN
        ///complete
        log("Mission complete! The freighter has arrived safely.")
        OK_SUCCESS
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.mission import mission_run

    task = mission_run(escort_mission, data={"ship_id": ship_id})
    ```

## API

::: sbs_utils.procedural.mission
