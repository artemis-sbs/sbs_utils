# The signal system

Emit named events and register handlers that fire when those events occur.

## Overview

Signals are the primary decoupled communication mechanism in Cosmos missions. Any code can emit a named signal with `signal_emit`; any label can listen for it with the `//signal/<name>` route. Signals are processed synchronously within the same tick — all registered listeners are called immediately when `signal_emit` runs.

Data passed to `signal_emit` becomes task variables in the handler. Use snake_case for script-defined signal data keys (e.g. `ship_id`, `target_id`). System-emitted signals use CAPS keys (e.g. `DESTROYED_ID`, `LIFE_FORM_NAME`).

`signal_emit` is safe to call even when no MAST runtime is active — it returns early with no side effects.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == patrol ==
        signal_emit("enemy_spotted", {"enemy_id": enemy_id, "ship_id": ship_id})
        ->END

    //signal/enemy_spotted
        log(f"Enemy spotted!")
        target(ship_id, enemy_id)
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.signal import signal_emit, signal_connect, signal_disconnect

    signal_emit("enemy_spotted", {"enemy_id": enemy_id, "ship_id": ship_id})
    ```

## Shared signals

A `//shared/signal/<name>` route fires for all clients and tasks, not just the one that emitted it:

```
//shared/signal/quest_completed
    log("Mission complete! Well done, crew.")
```

## Awaiting a signal

A `//signal/<name>` route reacts *every* time a signal fires. Sometimes instead a
task just needs to **pause until the next one**. `signal_next(name)` is a one-shot
await of the next `signal_emit(name)`; it resolves with the emitted data.

=== ":mast-icon: {{ab.m}}"
    ```
    == wait_for_dock ==
        result = await signal_next("docked")
        log("Docked - continuing the mission.")
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.signal import signal_next

    result = yield AWAIT(signal_next("docked"))
    ```

Loop it to react repeatedly, or use a `//signal/<name>` route for persistent
reaction. It composes with `promise_any` (signal-or-timeout, button-or-signal)
and accepts a `timeout`:

```
# whichever happens first
await promise_any(signal_next("docked"), delay_sim(30))

# give up after 10 seconds
result = await signal_next("scan_done", timeout=timeout(10))
```

| Use | When |
|---|---|
| `await signal_next(name)` | a task should pause *here* until the next emit (one-shot) |
| `//signal/<name>` route | react *every* time the signal fires, from anywhere |

`signal_next` is safe to call when no MAST runtime is active.

## Built-in signals

Many modules emit signals automatically. Common ones:

| Signal | Data keys | Emitted by |
|---|---|---|
| `quest_activated` | `AGENT_ID`, `QUEST_ID`, `QUEST` | `quest_set_state` |
| `quest_completed` | `AGENT_ID`, `QUEST_ID`, `QUEST` | `quest_set_state` |
| `upgrade_activated` | `UPGRADE_AGENT`, `UPGRADE_AGENT_ID`, `UPGRADE` | `upgrade_add` |
| `player_ship_destroyed` | `DESTROYED_ID` | `explode_player_ship` |
| `life_form_died` | `SHIP_ID`, `LIFE_FORM_NAME` | internal damage |
| `docked` | `ORIGIN_ID`, `SELECTED_ID` | docking system |

## API

::: sbs_utils.procedural.signal
