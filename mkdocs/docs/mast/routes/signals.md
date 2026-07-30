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

## Running setup only once

`//shared/signal` decides **where** a route runs — the server, once per emit. It says
nothing about **how many times the signal is emitted**. Emit a setup signal twice and its
route body runs twice, `shared` or not, and that happens more easily than you'd think: two
addons emitting the same one, a copied emit in both the console start and a map body, an
emit inside a loop, a double-clicked Start button, or a route that failed halfway and got
re-emitted to fix it.

### Prefer a key: make the work idempotent

The best fix is for the work itself to be safe to repeat. Give what you create a stable
name and create it only if it's missing:

=== ":mast-icon: {{ab.m}}"
    ```
    for slot, data in enumerate(SETTINGS.get("PLAYER_LIST")):
        player_ensure(slot, 0,0,0, data["ship"], data["name"], data["side"])
    ```

Eight ships, however many times that runs. This is better than "did I already run?"
because it stays correct when you re-run **on purpose** — after a reset the ships are
gone and they get rebuilt, a destroyed ship can be remade, and a late-joining crew's slot
is filled without touching the others.

`player_ensure` / `player_slot_id` / `players_reset` work this way, as do `side_ensure`
and AMD landmarks and characters (they key off the record's own `(key)`).

### `once` when there is nothing to key on

For work with no natural name — award starting cash, play an intro — mark the route:

=== ":mast-icon: {{ab.m}}"
    ```
    //shared/signal/give_starting_cash once

    //signal/show_intro once if IS_HOST
    ```

It runs at most once per mission. The `if` is checked first, so a route whose condition is
false keeps its shot for later. `signal_once_reset("name")` re-arms it; starting a new
mission re-arms everything automatically.

!!! warning "Never put `once` on a route that repairs something"
    `create_sides` must stay re-runnable. Creating a new simulation leaves side
    relationships and colours needing to be written again, and re-declaring is the only
    cure — mark that route `once` and contacts quietly render grey. The same goes for any
    route that brings state back to how it should be rather than making something new.

### `sbs lint` catches the common shapes

| Code | Fires on |
|---|---|
| `signal-init-unkeyed-spawn` | a `//shared/signal/create_*` route that spawns without a key and isn't `once` |
| `signal-emit-in-loop` | a setup `signal_emit` inside a `for` / `while` |
| `signal-multi-emit` | such a signal emitted from more than one place |

