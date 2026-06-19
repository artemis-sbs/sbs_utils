# The execution system

Schedule and manage MAST tasks, jump between labels, and read task-scope variables.

## Overview

Execution functions are the backbone of MAST flow control. A **task** is a running instance of a label; multiple tasks can run concurrently within the same MAST scheduler. Tasks yield between ticks and resume from where they left off.

Key concepts:

- **`task_schedule`** — start a label as a new independent top-level task.
- **`sub_task_schedule`** — start a label as a child of the current task (cancelled when the parent ends).
- **`gui_sub_task_schedule`** — like `sub_task_schedule` but automatically cancelled when a new GUI page is shown.
- **`task_all` / `task_any`** — run multiple labels in parallel and `await` all or the first to finish.
- **`get_variable` / `get_shared_variable`** — read values from the current task scope or the shared `Agent.SHARED` scope.

`LABEL_ALWAYS_IDLE` is a sentinel label used internally to keep a task alive without advancing — you rarely call it directly.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == run_patrols ==
        await task_all(patrol_alpha, patrol_beta, patrol_gamma)
        log("All patrols complete.")

    == timeout_wrapper ==
        await task_any(do_objective, timeout_30s)
        jump next_phase

    == setup ==
        task_schedule(background_monitor)
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.execution import (
        task_schedule, task_all, task_any, task_cancel,
        get_variable, get_shared_variable,
    )

    # Fire-and-forget background task
    task_schedule(background_monitor)

    # Wait for all patrol tasks
    promise = task_all(patrol_alpha, patrol_beta)

    # Read a variable from current task scope
    ship_id = get_variable("ship_id")
    ```

## `task_all` vs `task_any`

| Function | Resolves when |
|---|---|
| `task_all` | Every spawned task completes |
| `task_any` | The first spawned task completes (others are cancelled) |

## API

::: sbs_utils.procedural.execution
