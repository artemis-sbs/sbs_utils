# The signal system

Emit named events and register handlers that fire when those events occur.

## Overview

Signals are the primary decoupled communication mechanism in Cosmos missions. Any code can emit a named signal with `signal_emit`; any label can listen for it with the `//signal/<name>` route. Signals are processed synchronously within the same tick — all registered listeners are called immediately when `signal_emit` runs.

Data passed to `signal_emit` becomes task variables in the handler. By convention, variable names are `SCREAMING_SNAKE_CASE` (e.g. `SHIP_ID`, `TARGET_ID`).

`signal_emit` is safe to call even when no MAST runtime is active — it returns early with no side effects.

## Quick example

=== "MAST"
    ```
    == patrol ==
    ~~ signal_emit("enemy_spotted", {"ENEMY_ID": enemy_id, "SHIP_ID": SHIP_ID}) ~~

    //signal/enemy_spotted
    "Enemy spotted by {get_inventory_value(SHIP_ID, 'name')}!"
    ~~ target(SHIP_ID, ENEMY_ID) ~~
    ```

=== "Python"
    ```python
    from sbs_utils.procedural.signal import signal_emit, signal_connect, signal_disconnect

    signal_emit("enemy_spotted", {"ENEMY_ID": enemy_id, "SHIP_ID": SHIP_ID})
    ```

## Shared signals

A `//shared/signal/<name>` route fires for all clients and tasks, not just the one that emitted it:

```
//shared/signal/quest_completed
"Mission complete! Well done, crew."
```

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
