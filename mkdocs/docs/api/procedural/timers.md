# Timers and counters

Wait for a duration, and measure how long something has been running.

## Overview

There are two separate things on this page.

**Delays** are awaitable promises: the task stops at the `await` and resumes when the
time is up. Two time bases:

- **Simulation time** (`delay_sim`) - scaled by the engine's simulation clock, so it
  stops while the sim is paused. This is the one a mission wants.
- **Real time** (`delay_app`) - wall-clock seconds, unaffected by simulation speed.

`timeout_sim` / `timeout` are the same two clocks in the form `promise_any` expects, for
racing a delay against something else.

**Timers and counters** are not awaitable. Each one is a single value in an agent's
inventory and nothing runs on its behalf, which is why a mission can hold hundreds of
them for free - a script *asks* about them, or arms one with a `signal` (see below).

- A **timer** counts DOWN to a deadline: `set_timer`, then `is_timer_finished`,
  `get_time_remaining`, `format_time_remaining`.
- A **counter** counts UP from a start: `start_counter`, then
  `get_counter_elapsed_seconds` or `format_counter_elapsed_seconds`.
  `clear_counter` stops it.

```
await delay_sim(seconds=5)

set_timer(SHIP_ID, "repair", seconds=30)
start_counter(SHIP_ID, "in_combat")
```

!!! note "`0` means the server"
    Every timer and counter takes an agent, and **id `0` is the server** - the usual
    place to hang a mission-wide clock. `set_timer(0, "mission_clock", minutes=20)` and
    `start_counter(0, "Mission_Elapsed_Time")` are ordinary usage.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == timed_event ==
        log("Reactor will detonate in 30 seconds!")
        await delay_sim(seconds=30)
        log("The reactor has detonated!")
        explode_player_ship(station_id)
        ->END

    == mission_clock ==
        # id 0 is the server, so this is the whole mission's clock.
        start_counter(0, "Mission_Elapsed_Time")
        ->END

    == show_elapsed ==
        elapsed = get_counter_elapsed_seconds(0, "Mission_Elapsed_Time")
        log(f"{int(elapsed)} seconds into the mission")
        # Or ready-formatted. Only the units you name are filled, and the
        # largest one present carries the overflow: "mm:ss" gives "90:00",
        # never "00:00", for an hour and a half.
        gui_text(format_counter_elapsed_seconds(0, "Mission_Elapsed_Time"))
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.timers import (delay_sim, delay_app, set_timer,
                                              is_timer_finished, start_counter,
                                              get_counter_elapsed_seconds, clear_counter)

    # Wait 10 simulation seconds before continuing
    await delay_sim(seconds=10)

    # Wait 5 real seconds
    await delay_app(seconds=5)

    # Count DOWN to a deadline
    set_timer(ship_id, "cooldown", seconds=30)
    if is_timer_finished(ship_id, "cooldown"):
        fire_again(ship_id)

    # Count UP from a start. 0 is the server.
    start_counter(0, "Mission_Elapsed_Time")
    elapsed = get_counter_elapsed_seconds(0, "Mission_Elapsed_Time")
    clear_counter(0, "Mission_Elapsed_Time")
    ```

## The mission clock

"How long have we been out here" is asked by the crew, not by one script, so the library
keeps that one counter itself. `map_start` stamps it - which every mission goes through -
so a mission has a clock without starting one:

| function | answers |
|---|---|
| `mission_elapsed_seconds()` | seconds since the mission started, as a float |
| `mission_elapsed_text(display="hh:mm:ss")` | the same, formatted and rounded |
| `mission_clock_start()` | restart it, when the real beginning is later |

```
== show_mission_time ==
    gui_text(f"$text:{gui_text_escape(mission_elapsed_text())};")
    log(f"{int(mission_elapsed_seconds())} seconds in")
    ->END
```

It is sim time, like everything else here, so a paused sim does not age the mission. A
mission whose real beginning is the end of a cutscene calls `mission_clock_start()` there
and the clock re-zeros. Nothing reads `None`: with no start stamped the clock answers with
the sim's own age.

The ePADD **home screen** draws it at the right end of its bar as `T+hh:mm:ss`, in the
wordmark's own size, and moves it on with `gui_app_home_tick()` from an `on change` - the
widget, never a page repaint.

## Signals instead of polling

A timer is one value in an agent's inventory and nothing runs on its behalf, which is
why a mission can hold hundreds of them for free — but it also means a script has to
**ask** whether one is finished. Pass `signal` to `set_timer` and the library emits that
signal once, when it expires, so a route can react instead:

```
== start_repairs ==
    set_timer(SHIP_ID, "repair", seconds=30, signal="repair_done")
    ->END

//shared/signal/repair_done
    repair_ship(TIMER_AGENT_ID)
    ->END
```

`set_interval` is the repeating sibling — it emits every so often until it is cleared:

```
== begin_patrol ==
    set_interval(SHIP_ID, "patrol", "patrol_beat", seconds=30)
    ->END

//shared/signal/patrol_beat
    pick_new_patrol_point(TIMER_AGENT_ID)
    ->END

== stand_down ==
    clear_interval(SHIP_ID, "patrol")
    ->END
```

Every emit carries three variables:

| Variable | Meaning |
|---|---|
| `TIMER_AGENT_ID` | The agent the timer or interval is on |
| `TIMER_NAME` | The timer or interval name |
| `TIMER_COUNT` | Which beat this is — always `1` for a `set_timer` completion |

!!! warning "Use `//shared/signal` for anything that acts"
    A plain `//signal/<name>` route runs **once per connected console**, so a five-console
    bridge repairs the ship five times — and an interval does it five times a beat. Only
    per-console *display* belongs in `//signal`. See [Signals](../../mast/routes/signals.md).

**Why it is worth using.** The alternative — a watcher task per timer — costs a task
resumption every tick, forever, for each one. An armed timer knows its deadline as a
number, so the library keeps only the earliest and a tick costs a single comparison. A
mission that arms none schedules nothing at all.

### What does and does not fire

- **Nothing fires early.** The signal lands on the same tick `is_timer_finished` starts
  answering `True`.
- **The timer is untouched.** `is_timer_set_and_finished`, `get_time_remaining` and
  `format_time_remaining` all behave exactly as they do without a signal, so a countdown
  widget and a route can share one timer.
- **Cleared, re-set without a signal, or its agent deleted → no signal.** Re-setting with
  `signal` again re-arms it.
- **`timer_add_time` moves the signal with the deadline** — extend a repair and the
  completion follows; shorten it past zero and it fires at once.
- **A paused sim does not expire timers**, and interval beats missed while paused are
  skipped rather than delivered in a burst on resume.
- **Beats do not drift.** Each one is scheduled from the interval's start, not from when
  the last one happened to be noticed.

## Real time vs simulation time

| Function | Time base | Pauses with sim? | Use for |
|---|---|---|---|
| `delay_sim(seconds)` | Simulation clock | Yes | Anything in the mission |
| `delay_app(seconds)` | Wall clock | No | UI pacing, outside the sim |
| `timeout_sim(seconds)` | Simulation clock | Yes | Racing with `promise_any` |
| `timeout(seconds)` | Wall clock | No | Racing with `promise_any` |

Timers and counters run on the simulation clock as well, so a paused sim neither expires
a timer nor advances a counter.

## API

::: sbs_utils.procedural.timers
