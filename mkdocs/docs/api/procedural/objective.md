# The objective module

The tick scheduler that drives brains, docking, and other background systems.

## Overview

The objective module manages a recurring tick task that runs registered background systems once per second. Most library systems that need periodic evaluation (brains, docking, extra scan sources) piggyback on this tick rather than creating their own `TickDispatcher` intervals.

Mission scripts rarely call objective functions directly — `brain_schedule`, `docking_schedule`, and similar functions call `objective_schedule` automatically. The one exception is `objective_add` / `objective_remove`, which let you register your own callback to be called every objective tick.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
    objective_add(check_mission_state)
    == teardown ==
    objective_remove(check_mission_state)
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.objective import objective_add, objective_remove, objective_schedule

    def my_tick(tick_task):
        # Called every ~1 second
        check_mission_state()

    # Register your tick callback
    objective_add(my_tick)

    # Remove when done
    objective_remove(my_tick)
    ```

## API

::: sbs_utils.procedural.objective
