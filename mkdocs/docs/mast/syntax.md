# Syntax reference

The building blocks of MAST: variables, labels, flow control, tasks, and the rest.
MAST evaluates expressions with Python, so Python types and expressions work
inside MAST statements.

## Variables

Assign with `name = value`:

```
enemy_count = 20
name = "Artemis"
```

For values the MAST parser struggles with (nested lists, dict/set literals), wrap
the expression in **inline python** &mdash; two or more tildes (`~~`) on each side:

```
inventory = ~~ [[2, 3], [4, 5]] ~~
```

### Scope

Variables are scoped to the **task** by default. Two modifiers change that:

```
shared enemy_count = 20      # visible to every task in the story
default difficulty = 5       # set only if it isn't already defined
```

Reading is automatic &mdash; you only mark scope at assignment:

```
shared beer_count = 8
my_beer = beer_count         # read the shared value
shared beer_count = 0        # update the shared value
```

## Labels

A label starts at column 0 with two or more `=` signs. The trailing `=` is
optional, and the count doesn't matter:

=== ":mast-icon: {{ab.m}}"
    ```
    == goto_bar ==
        ...
    === show_helm
        ...
    ```

Two labels are implicit and don't need defining: **`main`** (where every script
starts) and **`END`** (ends the current task).

Labels are **not** functions &mdash; execution falls through from one into the
next:

=== ":mast-icon: {{ab.m}}"
    ```
    == one ==
        log("one")
    == two ==
        log("two")
    == three ==
        log("three")
    ```

=== "Output"
    ```
    one
    two
    three
    ```

## Jumps and ending

`jump label` (or the shortcut `-> label`) redirects flow. `->END` ends the task:

=== ":mast-icon: {{ab.m}}"
    ```
    == start ==
        log("first")
        -> here

    == skipped ==
        log("got here later")
        -> done

    == here ==
        log("second")
        -> skipped

    == done ==
        log("done")
        ->END
    ```

=== "Output"
    ```
    first
    second
    got here later
    done
    ```

Ending the last remaining task ends the story.

## Conditionals

MAST supports Python-style `if` / `elif` / `else` (and they can nest):

=== ":mast-icon: {{ab.m}}"
    ```
    if value < 300:
        log("less")
    elif value > 300:
        log("more")
    else:
        log("equal")
    ```

...and `match` / `case`:

=== ":mast-icon: {{ab.m}}"
    ```
    match value:
        case 200:
            log("200")
        case 300:
            log("300")
        case _:
            log("something else")
    ```

Conditions also work inline on many statements:

```
->END if obj is None
jump loop if not is_timer_finished(0, "warmup")
```

## Loops

Standard `for ... in`, plus a MAST-specific `for ... while` that loops until a
condition goes false. `break` and `continue` work as in Python:

=== ":mast-icon: {{ab.m}}"
    ```
    for x in range(3):
        log(f"{x}")

    y = 10
    for z while y < 30:
        log(f"{z} {y}")
        y += 10
    ```

=== "Output"
    ```
    0
    1
    2
    0 10
    1 20
    2 30
    ```

!!! tip "Interpolating variables in `log`"
    `log()` is a function call, so use an f-string to interpolate:
    `log(f"{x}")`. (Plain `log("{x}")` prints the literal text `{x}`.) GUI and
    comms text &mdash; `"""{x} ships"""` &mdash; interpolate without the `f`.

## Tasks

Start a background task with `task_schedule`; the current task keeps running:

=== ":mast-icon: {{ab.m}}"
    ```
    == start ==
        log("before")
        task_schedule(a_task)
        log("after")

    == a_task ==
        log("in task")
        ->END
    ```

=== "Output"
    ```
    before
    after
    in task
    ```

### Passing data

Data passed to a task becomes variables in it, separate from the caller's:

=== ":mast-icon: {{ab.m}}"
    ```
    == start ==
        message = "caller"
        task_schedule(a_task, {"message": "Hello"})
        log(f"{message}")
        ->END

    == a_task ==
        log(f"{message}")     # "Hello" - from the passed data
        ->END
    ```

### Waiting for tasks

Capture a task in a variable and `await` it, or race/join several with
`promise_any` / `promise_all`:

=== ":mast-icon: {{ab.m}}"
    ```
    t = task_schedule(a_task)
    await t                                   # wait for one task

    a = task_schedule(worker, {"say": "A"})
    b = task_schedule(worker, {"say": "B"})
    await promise_all(a, b)                    # wait for both
    # await promise_any(a, b)                  # wait for the first to finish
    ```

### Cancelling

```
t = task_schedule(a_task)
task_cancel(t)
```

## Comments

Line comments use `#`. MAST also supports C-style block comments:

=== ":mast-icon: {{ab.m}}"
    ```
    fred = 10   # set fred to 10

    /*
      A block comment.
      Handy for disabling several lines at once.
    */
    ```

!!! warning "`//` is not a comment"
    A line starting with `//` is a **route label**, not a comment. Use `#`.

## Importing

Split a mission across files and `import` them &mdash; including from a zip
(the basis of shareable add-ons):

=== ":mast-icon: {{ab.m}}"
    ```
    import story_two.mast
    from my_lib.zip import bar.mast
    ```

## Delays

Delays need a clock. `delay_app` uses the **real-time** clock (always running);
`delay_sim` uses **sim time** (paused when the game is). Both accept `minutes` and
`seconds`:

=== ":mast-icon: {{ab.m}}"
    ```
    await delay_app(seconds=10)
    await delay_app(minutes=1, seconds=5)
    await delay_sim(5)            # 5 sim-seconds

    for x in range(3):
        log(f"{x}")
        await delay_sim(1)
    ```

## Logging

`logger()` enables logging; `log()` writes to it. Logging can go to stdout, a
string variable, and/or a file, and you can have several named loggers.

=== ":mast-icon: {{ab.m}}"
    ```
    logger()                                    # enable stdout logging
    logger(file="{mission_dir}/my.log")         # also to a file
    logger(name="tonnage", var="tonnage")       # a second, named logger

    log("Hello, world")                         # default logger
    log(f"Tonnage: {tonnage}", name="tonnage")  # named logger
    log("Careful", level="warning")             # with a level
    ```

`log(message, name=None, level=None)` is preferred over `print()`. See the
[execution API](../api/procedural/execution.md).
