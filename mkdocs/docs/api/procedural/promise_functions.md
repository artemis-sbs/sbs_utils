# Promise functions

Awaitable promise helpers for coordinating parallel async operations.

## Overview

Promises are objects returned by `await`-able functions. They represent a value that will be available in the future — when the associated task or condition completes. The promise functions module provides helpers for creating, combining, and querying promises in MAST.

`promise_all` resolves when every promise in a collection is done. `promise_any` resolves when the first promise completes. These are the lower-level primitives underlying `task_all` and `task_any` in the execution module — most scripts should use those instead.

`promise_is_done` and `promise_result` let you inspect a promise's state without blocking.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == run_parallel ==
        p1 = task_schedule(patrol_alpha)
        p2 = task_schedule(patrol_beta)
        await promise_all(p1, p2)
        log("Both patrols complete.")
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.promise_functions import promise_all, promise_any, promise_is_done

    p1 = task_schedule(patrol_alpha)
    p2 = task_schedule(patrol_beta)

    combined = promise_all(p1, p2)

    if promise_is_done(combined):
        result = promise_result(combined)
    ```

## API

::: sbs_utils.procedural.promise_functions
