# Handler lifetime

Which task runs a GUI handler, how long it lives, and how it should end.

!!! info "The one rule"
    A GUI handler belongs to the task that **built the widget** &mdash; not to
    the screen it appears on. Everything on this page follows from that.

That rule is invisible while you are writing a normal console, because there the
builder *is* the console's main GUI task. It starts to matter the moment part of
a screen is painted by a different task &mdash; `task_schedule`,
`sub_task_schedule` or `gui_sub_task_schedule` &mdash; which is exactly what you
reach for when a panel gets big enough to split up.

---

## The forms

| Form | Which task runs it | When it dies | Takes over the GUI task? | How it should end |
|---|---|---|---|---|
| `on gui_message(w):` / `on gui_click(w):` block | the builder, as an inline block | with the build that registered it | no | falls off its end, or `jump` |
| `on change <expr>:` block | the builder, as an inline block | with the build that registered it | no | falls off its end, or `jump` |
| `on signal <name>:` block | the builder, as an inline block | with the build that registered it | no | falls off its end, or `jump` |
| `on_press=<label>` | a sub-task hosted by the GUI task | when it ends, or with the build | only if it reaches `await gui()` | `->END` |
| `on_press=<callable>` | no task &mdash; plain Python | n/a | no | `return` |
| `gui_message_callback(w, fn)` | no task &mdash; plain Python | n/a | no | `return` |
| `gui_message(w, label)` | a sub-task hosted by the GUI task | when it ends, or with the build | only if it reaches `await gui()` | `->END` |
| `*` / `+` inside `await gui()` | the GUI task itself | when the `await gui()` resolves | it *is* the GUI task | `jump`, or fall through |

The two Python forms are the only ones with no task in the path at all. When you
want a handler that cannot be affected by any of this, use one of those.

---

## Handlers are owned by the BUILD, not by the builder

An `on ...:` block lives as long as the GUI build that registered it, and dies
when the next build replaces it. Its position in the label does not matter
&mdash; a handler written above the first widget lives exactly as long as one
written below it.

The same is true of a handler registered by a *scheduled* task that has since
finished. The builder is woken to run its own block, and ends again afterwards:

=== ":mast-icon: {{ab.m}}"

    ```
    == console_body ==
        gui_section("area: 5,5,95,95;")
        await task_schedule(build_panel)     # paints, then ends
        await gui()

    == build_panel ==
        gui_row()
        b = gui_button("Fire")
        on gui_message(b):                   # still runs, after the builder ended
            fire_torpedo(SHIP_ID)
        ->END
    ```

!!! warning "A builder that CRASHED is not woken"
    Reviving a task that failed part-way would re-run it from a state it never
    reached, so a crashed or cancelled builder stays dead. When a click cannot
    be delivered for that reason, a warning naming the source site goes to
    `mast.runtime.log`. Check that file &mdash; the verdict of a headless run
    will still say `PASS`.

`signal_register(name, label)` &mdash; and the `//signal/<name>` routes that
compile to it &mdash; is a different thing, and is **not** GUI-transient. It
lives as long as its task does. Register one on every visit to a screen and you
have registered it several times.

---

## How a handler label should end

A handler that **does something and returns** ends with `->END`:

=== ":mast-icon: {{ab.m}}"

    ```
    b = gui_button("Launch", on_press=launch_fighter)

    == launch_fighter ==
        hangar_launch_craft(SHIP_ID)
        ->END
    ```

A handler that **paints a new screen** needs nothing special. Build the widgets
and `await gui()`; the console follows you there:

=== ":mast-icon: {{ab.m}}"

    ```
    b = gui_button("Buy", data={"item": key}, on_press=market_buy)

    == market_buy ==
        market_purchase(client_id, item)
        jump market_screen          # paints, then `await gui()` -- that is all
    ```

!!! danger "`->END` and the deprecated `is_sub_task=False`"
    With `is_sub_task=False` an `on_press` label is a **jump on the GUI task**,
    so the handler *is* that task &mdash; and `->END` ends the console, not the
    handler. The screen goes dead. That is the historical behavior, and the
    reason `is_sub_task` is deprecated: it made the correct ending depend on a
    flag most scripters never knew was there.

---

## Steering the GUI task from somewhere else

Reaching `await gui()` sends the console to whatever you just built, so a
handler that paints does not need to do anything else. Three cases still want an
explicit redirect:

| You want to | Use |
|---|---|
| send the console somewhere **without going there yourself** (a watcher loop that keeps looping) | `gui_task_jump(label)` |
| redirect one client's console from outside it | `gui_reroute_client(client_id, label)` |
| redirect every client, or the server | `gui_reroute_clients(label)` / `gui_reroute_server(label)` |

=== ":mast-icon: {{ab.m}}"

    ```
    --- watch
        await delay_sim(1)
        ->END if not object_exists(ship_id)
        state = get_data_set_value(ship_id, "red_alert", 0)
        if state != prev_state:
            gui_task_jump("repaint")     # the panel repaints; this loop carries on
        jump watch
    ```

!!! note "A finished GUI task cannot be jumped"
    `gui_task_jump` silently discards the jump if the target task has already
    ended. That is the trap behind the `->END`-after-`map_start` warning in
    [map_picker](../api/procedural/map_picker.md).

---

## Splitting a screen across tasks

`gui_sub_task_schedule(label)` paints part of a screen from another task, and
tags it so it is cancelled when a new GUI is presented. Its handlers &mdash;
buttons and `on change` watchers alike &mdash; belong to the build, so they keep
working after the sub-task itself has finished.

=== ":mast-icon: {{ab.m}}"

    ```
    == console_body ==
        gui_section("area: 0,0,100,100;")
        gui_sub_task_schedule(status_panel)
        gui_sub_task_schedule(target_panel)
        await gui()

    == status_panel ==
        gui_row()
        t = gui_text(f"Hull {hull_pct(SHIP_ID)}%")
        on change hull_pct(SHIP_ID):
            t.update(f"$text:Hull {hull_pct(SHIP_ID)}%;")
        ->END
    ```

!!! warning "Watchers need time to fire"
    `on change` is polled once per tick. In a headless `--test` run the
    exerciser sits on each console for well under a sim-second by default, so a
    watcher keyed to a one-second change never fires and everything inside it
    goes unverified. Pass `--exercise-dwell 30`.

---

## Reacting to a signal: three ways

| | Runs on | Lives for | Use when |
|---|---|---|---|
| `//signal/<name>` route | one task per connected console, plus the server | the mission | reacting anywhere, per console |
| `//shared/signal/<name>` route | the server only, once | the mission | anything that spawns, saves, rewards or counts |
| `on signal <name>:` block | the builder | the GUI build | updating the screen you are building |

The block form is the GUI-scoped one. If your handler does anything other than
paint, it belongs in a route &mdash; see [Signals](routes/signals.md).

---

## Every handler on a widget runs

A widget can carry as many handlers as you attach, in any mix of forms, and they
all fire in registration order (which is source order):

=== ":mast-icon: {{ab.m}}"

    ```
    b = gui_button("Go", on_press=fire)
    on gui_message(b):          # BOTH run
        log("also me")
    ```

The `gui_message_callback` / `gui_message_label` family always runs first,
because the page walks the layout tree before it looks the tag up in its tag
map. A handler that raises is logged to `mast.runtime` and the remaining ones
still run. To **replace** rather than add, call `gui_message_clear(widget)`
first.

---

## See also

- [Runtime &amp; Tasks](runtime.md) &mdash; schedulers, tasks and the tick loop
- [GUI](../cosmos/gui.md) &mdash; building the layout itself
- [Signals](routes/signals.md) &mdash; routes vs `signal_next`
- [execution API](../api/procedural/execution.md) &mdash; `task_schedule`,
  `sub_task_schedule`, `gui_sub_task_schedule`, `gui_task_jump`
