# Objectives

The objectives system is a lightweight way to run mission goals over time.

An objective is a label-driven task attached to an agent. It is polled by the shared scheduler until it completes, then it is automatically cleaned up.


## What objectives are for

Use objectives when you want stateful goal logic such as:

- defend this station until reinforcements arrive
- escort a ship to a destination
- watch for mission fail/win conditions
- run per-agent progress checks that can complete independently

Compared to a one-off task, an objective gives you:

- a standard lifecycle (enter, test/main, leave)
- automatic registration and cleanup
- links/roles that make active objectives queryable


## Runtime model

The system schedules one shared tick task with objective_schedule().

That scheduler rotates work across ticks:

1. objectives_run_all + expired modifier cleanup
2. brains_run_all
3. extra scan sources + game end conditions

This spreads workload instead of running every subsystem every tick.


## Objective lifecycle

Each Objective instance stores:

- target agent id
- label to run
- optional data payload
- client id (for GUI-task scoped execution)
- current result and done state

Lifecycle flow:

1. Objective is added and linked to the owning agent.
2. Optional sub label enter runs once on first execution.
3. If sub label test exists, test is run each objective pass.
4. Otherwise, execution starts at label location 0.
5. Objective completes when result is no longer OK_IDLE.
6. Optional sub label leave runs on completion/stop.
7. Roles/links are removed automatically.


## Label contract

Objective labels should follow a simple contract:

- return OK_IDLE while still in progress
- return success/fail end when finished
- keep per-objective state in inventory or provided data

Runtime variables injected into objective label tasks:

- OBJECTIVE: objective object instance
- OBJECTIVE_ID: unique objective id
- OBJECTIVE_AGENT_ID: owning agent id
- OBJECTIVE_AGENT: owning agent object


## Using objectives

You can add objectives in several forms:

- label string
- label object
- dict with label and optional data
- list of labels/dicts (expanded per agent)

API:

```py
objective_add(agent_id_or_set, label, data=None, client_id=0)
```

Examples:

```py
    station = closest(player_ship, role("station"),10000)
    objective_add(ship_id, "objective_defend_station", data={"time_limit": 15, "station": station})
```



## Clearing and stopping

Clear objectives for one or many agents:

```py
objective_clear(agent_or_set)
```

Internally, clearing will:

- call stop_and_leave(...) on each active objective
- run leave sub label when present
- unlink and remove OBJECTIVE / OBJECTIVE_RUN roles


## Objective roles and links

When created, an objective is linked and marked so systems can find it:

- objective has role OBJECTIVE
- objective has role OBJECTIVE_RUN
- agent links to objective under OBJECTIVE and OBJECTIVE_RUN

These links are removed when objective ends or is force-cleared.



## Enter, test, leave pattern

A recommended objective label structure:

```mast
=== obj_example

+++ enter
	# one-time setup

+++ test
	# return idle until complete
	yield success if some_condition
	yield fail if some_failing_condition
    yield idle otherwise

+++ leave
	# cleanup / signals / reward payout
```

Use this pattern to keep setup, polling, and teardown easy to reason about.


## Building an Objective

You will typically build a custom objective with a few things in mind:
- To what agent does the objective apply
- What information could be added to metadata (for simpler customization)
- Under what conditions is the objective completed or failed
- What happens upon completion or failure


In this example, the objective applies to one or more player ships.
If the station is destroyed, the objective should fail.
If the station is not destroyed, the objective should succeed.

```mast
=== objective_defend_station
metadata: ```
time_limit: 10 # minutes
station: 
```
+++ enter

    # If station wasn't defined or included in data, then we'll find the closest one to the ship.
    default station = closest(OBJECTIVE_AGENT_ID, role("station"))

    # Check to make sure `station` is valid, otherwise we'll find the nearest station.
    if to_object(station) is None:
        yield fail
    set_timer(OBJECTIVE_AGENT, "defend_time_limit", minutes=time_limit)

+++ test

    # Check if station exists
    if to_object(station) is None:
        yield fail

    # Check the timer
    if is_timer_finished(OBJECTIVE_AGENT, "defend_time_limit"):
        yield success

    # Objective still in progress
    yield idle

+++ leave

    if OBJECTIVE.result == OK_SUCCESS:
        blob = to_blob(station)
        armor = blob.get("armor")
        max_armor = blob.get("armorMax")
        rep = armor/max_armor*5
        modifier_add(OBJECTIVE_AGENT_ID, "reputation", rep, "Station Defended")
        sbs.play_music_file(0, "music/default/victory")
    else:
        modifier_add(OBJECTIVE_AGENT_ID, "reputation", -10, "Station Destroyed")
        sbs.play_music_file(0, "music/default/failure")
```


## Game end integration

The objective module also contains end-game condition helpers:

- game_end_condition_add(promise, message, is_win, music=None, signal=None)
- game_end_condition_remove(id)

Registered promises are polled by the shared scheduler. When a promise completes, the system:

- sets shared game state flags (GAME_STARTED / GAME_ENDED)
- sets START_TEXT
- emits show_game_results (or custom signal)


## Best practices

1. Keep each objective focused on one mission goal.
2. Use data/metadata for tunable values, not hardcoded constants.
3. Return OK_IDLE only when truly waiting for future progress.
4. Use leave for cleanup, rewards, and signaling.
5. Prefer multiple small objectives over one monolithic label.


## Related systems

- AI brains for decision composition: [AI Brains](ai/brains.md)
- AI overview landing page: [AI Overview](ai/index.md)

Runtime implementation reference:

- sbs_utils/procedural/objective.py
