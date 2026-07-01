# The MAST language

MAST reads like a screenplay more than a program. Execution moves **forward**
through a file, jumping between **labels**, pausing when it needs to wait, and
ending when the story is done. If you've seen BASIC, Ink, or ChoiceScript, this
will feel familiar.

This page covers the mechanics of the language. For *why* MAST exists and how it
fits {{ab.ac}}, see [What is MAST](index.md).

## Labels and flow

A **label** starts at column 0 with two or more `=` signs. Code under a label is
indented. Execution runs forward and, by default, **falls through** into the next
label unless you jump or end.

- `jump label_name` (or the shortcut `-> label_name`) jumps to a label.
- `->END` ends the current task.

=== ":mast-icon: {{ab.m}}"
    ```
    == start ==
        log("Hello, world")
        -> goodbye

    == skipped ==
        log("I get jumped over")

    == goodbye ==
        log("Goodbye")
        ->END
    ```

=== "Output"
    ```
    Hello, world
    Goodbye
    ```

!!! note "The implicit `main`"
    Top-level code (before the first label) is automatically combined into one
    `main` label that every mission starts at. Don't write `== main ==` yourself
    &mdash; use descriptive labels like `== setup ==` instead.

## Pausing the flow with `await`

MAST runs inside the game engine, which gives it only a sliver of time each tick.
If MAST ran without stopping it would freeze the game. So when a story can't
continue &mdash; it's waiting for a timer, a button, a scan &mdash; MAST **yields**
control back to the engine and resumes later.

`await` is how you wait. It suspends the task until the condition is met, then
continues on the next line:

=== ":mast-icon: {{ab.m}}"
    ```
    == start ==
        log("Hello, world")
        await delay_sim(5)      # wait 5 sim-seconds; the engine keeps running
        log("Goodbye")
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    @label()
    def start():
        log("Hello, world")
        yield AWAIT(delay_sim(5))
        log("Goodbye")
    ```

You'll `await` many things:

- `await delay_sim(5)` / `await delay_app(5)` &mdash; sim-time / real-time delays
- `await gui()` &mdash; a GUI interaction
- `await signal_next("docked")` &mdash; the next time a signal fires
- `await task_schedule(other_label)` &mdash; another task to finish

To force a single yield without waiting for anything, use a bare `yield`.

## Tasks: storylines in parallel

MAST is *Multiple Agent Story Telling* &mdash; many storylines run at once. Each is
a **task**: an independent thread of the story that runs until it ends. They're not
truly parallel (the engine is single-threaded), but the scheduler advances all of
them each tick, so they run "at the same time."

A player ship might run one task for its comms, another for science, and another
for a side quest.

- `task_schedule(label, data)` &mdash; start a task and keep going (fire and forget)
- `await task_schedule(label, data)` &mdash; start a task and wait for it to finish
- `sub_task_schedule(label)` &mdash; start a child task tied to the current one

=== ":mast-icon: {{ab.m}}"
    ```
    == start ==
        await task_schedule(count_to_three)
        log("done")

    == count_to_three ==
        for x in range(3):
            log(f"{x}")
            await delay_sim(1)
        ->END
    ```

=== "Output"
    ```
    0
    1
    2
    done
    ```

## Variables and data

Variables are scoped to the **task** by default. A few modifiers change that:

- `shared x = 5` &mdash; visible to every task in the story
- `default x = 5` &mdash; set only if `x` doesn't already exist (great for values a
  task may be given when scheduled)

Passing a data dict to `task_schedule` makes those values variables in the new
task &mdash; so the same label can be scheduled many times with different data:

=== ":mast-icon: {{ab.m}}"
    ```
    == start ==
        shared greeting = "Hello"
        task_schedule(greet, {"name": "World"})
        task_schedule(greet, {"name": "Cosmos"})
        ->END

    == greet ==
        log(f"{greeting}, {name}")     # greeting is shared; name came from the data
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    @label()
    def start():
        set_shared_variable("greeting", "Hello")
        task_schedule(greet, {"name": "World"})
        task_schedule(greet, {"name": "Cosmos"})

    @label()
    def greet():
        log(f"{get_shared_variable('greeting')}, {name}")
    ```

## Route labels

**Route labels** run automatically when an engine event matches their condition
&mdash; the system schedules a task to run the label. They start with `//`:

=== ":mast-icon: {{ab.m}}"
    ```
    //spawn if has_roles(SPAWNED_ID, "tsn, player")
        log("A new TSN player spawned")
        ->END
    ```

Routes cover comms, science, damage, spawning, signals, and more. See
[Routes](routes/index.md).

## Sub-labels

A **sub-label** starts with three or more dashes (`---`) at column 0. It's a jump
target *local to the enclosing `==` label*, so names can't collide across labels
&mdash; ideal for loops and re-entry points:

=== ":mast-icon: {{ab.m}}"
    ```
    == patrol ==
        set_up_patrol()
    --- loop
        await delay_sim(2)
        if still_patrolling():
            -> loop
        ->END
    ```

## Delays and timers

`delay_sim` / `delay_app` handle one-off waits. For named countdowns, use timers:

=== ":mast-icon: {{ab.m}}"
    ```
    set_timer(0, "meeting", minutes=20)
    ...
    jump meeting_over if is_timer_finished(0, "meeting")
    ```

A common pattern &mdash; show pages of text a few seconds apart &mdash; is just a
sequence of awaits:

=== ":mast-icon: {{ab.m}}"
    ```
    == show_credits ==
        """The first page of credits"""
        await gui(timeout=delay_sim(10))
        """The second page of credits"""
        await gui(timeout=delay_sim(10))
        ->END
    ```

!!! info "Coming from Artemis 2.x (XML)?"
    XML `<event>` tags always ran, every tick, forever. MAST **tasks** are the
    modern equivalent but better: they only run when scheduled, they can end, and
    they can be cancelled. **Route labels** are tasks that schedule themselves when
    their condition is met. And unlike XML variables (all global), task variables
    are scoped &mdash; so a label can be reused with different data instead of being
    copy-pasted. (XML is not supported in {{ab.ac}}.)
