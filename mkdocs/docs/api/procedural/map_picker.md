# Map picker

Let a mission offer its `@map` labels and start the one chosen — **without
LegendaryMissions**.

## Overview

`@map` is how a mission offers several entry points, and until v1.4.0 it only worked if
you loaded LegendaryMissions. Both halves of the machinery lived there: LM's server
console drew the selection screen, so a mission loading only `sbs_utils` came up with an
**empty server page and no way in**, and the headless runner's `--map` had nothing to
start.

Two functions close that. `gui_map_picker()` builds the screen and returns something you
`await`; `map_start()` launches the map you were handed.

```
== main ==
    chosen = await gui_map_picker()
    map_start(chosen)
    ->END
```

That is a complete, playable mission front-end. It needs **only `sbs_utils`** — which is
the point: an add-on can now ship its own test mission that runs from a fresh clone with
nothing else installed.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    sim_create()
    sim_resume()

    === mission_start
    ---pick
        chosen = await gui_map_picker()
        map_start(chosen)
    ---running
        # Park - do NOT ->END. See "Keep the picker's task alive" below.
        await delay_sim(1)
        jump running

    @map/patrol "Border Patrol"
        " Fly the line and report contacts.
        ->END

    @map/siege "Siege"
        " Hold the station until relief arrives.
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.gui import gui_map_picker
    from sbs_utils.procedural.maps import map_start

    @label()
    def mission_start():
        chosen = yield AWAIT(gui_map_picker())
        map_start(chosen)
    ```

## What you get

A **carousel** of the story's maps — one card at a time with next/prev — showing each
map's display name and its description, plus that map's **`Properties:` panel** and a
Start button.

The properties panel is on by default, and that is deliberate: a map that declares

````
metadata: ``` yaml
Properties:
  Main:
    Player Ships: 'gui_int_slider("$text:int;low: 1.0;high:8.0;", var="PLAYER_COUNT")'
Defaults:
  JOBS_SELECT: some
```
````

expects `PLAYER_COUNT` to exist when it runs. Without the panel it would start with the
variable unset — a silent wrong-behaviour trap rather than a visibly missing feature.
Pass `properties=False` if you genuinely want just a carousel and a button.

| Argument | Default | Meaning |
|---|---|---|
| `maps` | `maps_get_list()` | Which maps to offer |
| `properties` | `True` | Render the selected map's `Properties:` panel |
| `title` | a count of the maps | Carousel title |
| `start_text` | `"Start"` | Label on the start button |
| `list_style` | `"item-gap: 7em;"` | Style string for the carousel |

Selection is handled in Python on the callback channel, so the panel repaints in place as
you move through the carousel — no page rebuild, and no MAST label needed for it.

## `map_start`

Applies the map's `Defaults:`, resumes the sim, schedules the map deferred, sets
`GAME_STARTED` and emits `game_started`.

This sequence used to exist **twice** — in LM's console and in the headless runner — and
the two had drifted on details that matter, including whether the sim resumes before or
after scheduling. `map_start` is now the single definition.

It does **not** do LegendaryMissions' own steps: the `reconcile_player_roster` signal,
beam damage, the game time limit, music selection, or the console reroutes. Those are LM's
contract and it still does them around its own call. `map_start(None)` is a no-op.

## Conditional maps

`@map/secret "Secret" if UNLOCKED` is now honoured — `maps_get_list()` evaluates the
condition and hides maps whose `if` is false. It never did before, so such a map was
offered regardless.

Two carve-outs, both deliberate:

- **No task in context means show.** The headless runner polls the map list from its own
  loop with no MAST task; hiding everything there would stop `--map` working entirely.
- **`maps_get_list(include_hidden=True)`** returns everything. That is for *resolving a
  known map* rather than offering a menu — a saved game code should not stop working
  because a condition happens to be false right now.

!!! warning "Index-based `--map 0` counts the filtered list"
    If your mission has conditional maps, the index a map sits at can move. Prefer
    `--map <name>`.

## Keep the picker's task alive

!!! danger "Do not `->END` after `map_start`"
    The task that ran the picker is usually `main`, and **`main` is the page's GUI task**.
    A started map's body runs on its own task and calls `gui_task_jump` to put its page on
    the GUI task — and `gui_task_jump` **silently discards** a jump when that task has
    already finished.

    Ending your task right after `map_start` therefore kills the GUI task a moment before
    the map tries to use it. There is no error: you get a blank screen. Park instead:

    ```
    ---running
        await delay_sim(1)
        jump running
    ```

## When to use LegendaryMissions' console instead

This is the **light tier** — a carousel, a properties panel, a Start button. LM's server
console additionally offers game codes and presets, music selection, the player roster,
operator mode and difficulty-scaled beam damage. If you want those, load LM and use its
console; this is for missions that must stand on `sbs_utils` alone.

## See also

- [maps](maps.md) — `maps_get_list`, `map_get_properties`, `map_apply_defaults`, game codes
- [gui](gui.md) — the widget layer the picker is built from
