# Signal routes
Signals are script defined event.

Signals are emitted. Signal name and the data to pass to the signal 

=== ":mast-icon: {{ab.m}}"   
    ```
    signal_emit("player_ship_destroyed", {"DESTROYED_ID": ship_id})
    ```


Only the server receives shared signals

=== ":mast-icon: {{ab.m}}"   
    ```
    //shared/signal/player_ship_destroyed
    ```

Each console will receive this signal

=== ":mast-icon: {{ab.m}}"   
    ```
    //signal/player_ship_destroyed
    ```

## Waiting for a signal: `signal_next`

A `//signal/<name>` route is a **persistent** handler — it fires every time the signal
is emitted, from anywhere. Sometimes you instead want to **pause a task at a point in
its flow** until the next emit. That's `await signal_next(name)`:

=== ":mast-icon: {{ab.m}}"
    ```
    data = await signal_next("wave_cleared")
    "The wave is down - move up."
    ```

- **One-shot.** It resolves on the **next** emit of `name` and returns that emit's
  **data** (which may be `None`). To react repeatedly, loop it; for an always-on
  handler, use a `//signal/<name>` route instead.
- **Resumes right where it waited**, so it reads like a step in the story — no separate
  route needed for a one-time beat.

### With a timeout

Pass `timeout` (application seconds — it advances even while the sim is paused) to give
up waiting; the await then resolves with `None`:

=== ":mast-icon: {{ab.m}}"
    ```
    data = await signal_next("reinforcements", timeout=30)
    if data is None:
        "No reinforcements came."
    ```

### Event or timeout with `promise_any`

`signal_next` composes with `promise_any`, which resolves with whichever finishes first
— handy for "the event, or a fallback":

=== ":mast-icon: {{ab.m}}"
    ```
    result = await promise_any(signal_next("docked"), delay_sim(30))
    ```

### Route vs `signal_next`

| Use | When |
|---|---|
| `//signal/<name>` route | A **persistent** reaction that should fire **every** time, from anywhere. |
| `await signal_next(name)` | A task needs to **wait inline** for the next emit and continue its own flow. |

