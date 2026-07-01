# Common gotchas

MAST looks like Python and evaluates expressions with Python, but it is its own
language with its own flow. These are the things that most often trip people up.

## Don't write `== main ==`

`main` is **implicit** &mdash; all the top-level code (before the first label) *is*
`main`. Declaring `== main ==` yourself causes a "Duplicate label" error. Use
descriptive labels (`== setup ==`, `== patrol ==`) for everything else.

## Labels fall through

Execution runs **into the next label** unless you stop it. Forgetting `->END` is
the classic bug &mdash; your label quietly continues into the one below:

```
== greet ==
    log("hi")
    ->END          # without this, execution falls into 'cleanup'
== cleanup ==
    ...
```

**Route labels (`//...`) do *not* fall through** &mdash; they end at the next label.

## `//` is a route, not a comment

Comments are `#`. A line starting with `//` is a **route label**. `// old code`
doesn't disable a line &mdash; it declares a route.

## `log("{x}")` doesn't interpolate — but GUI text does

`log()` is a function call, so it needs an f-string:

```
log(f"{x}")        # correct
log("{x}")         # prints the literal text: {x}
```

But GUI and comms text interpolate **without** the `f`:

```
"""{count} ships"""          # GUI text - interpolates
+ "{dynamic_label}" handler  # comms button - interpolates
```

## `await` or it won't wait

A delay/promise on its own does nothing &mdash; you must `await` it:

```
await delay_sim(5)     # waits 5 sim-seconds
delay_sim(5)           # does nothing useful
```

And **don't `await` inside a comms or science button block** &mdash; it freezes the
menu while it waits. Schedule a task for the delayed part instead:

```
+ "Analyze":
    << [green] "Sci" % Working on it...
    task_schedule(analyze_results)     # not: await delay_sim(...) here
```

## Variables are per-task, not global

A variable set in one task isn't visible in another. Use `shared` to cross tasks:

```
shared score = 0
```

Two more surprises:

- **Top-level `shared` runs once.** After the first client, top-level `shared`
  assignments become no-ops &mdash; so they're effectively set by the server.
- **`default x = …` only assigns if `x` isn't already set** (unlike `=`). Perfect
  for values a task may be handed when scheduled.

## `@map/` bodies are server-only

The code under a `@map/...` label runs **only on the server**, never on client
consoles. Put per-console logic in `@console/` labels or client tasks.

## Not every Python builtin is available

MAST expressions run against an allow-list. Available include: `len`, `range`,
`min`, `max`, `abs`, `int`, `str`, `list`, `dict`, `set`, `tuple`, `zip`,
`enumerate`, `sorted`, `map`, `filter`, `isinstance`… but some common ones
are **not**: `bool`, `float`, `round`, `sum`, `any`, `all`.

If you hit a `NameError` for a builtin, either rewrite the expression, call a
`.py` helper, or drop into inline python:

```
total = ~~ sum(scores) ~~
ratio = ~~ float(hits) / shots ~~
```

## `~~ ... ~~` is only for what the parser can't handle

Inline python (two or more tildes each side) is for **complex literals and
expressions** the MAST parser chokes on &mdash; nested lists, dict/set literals,
unavailable builtins:

```
grid = ~~ {"x": px, "y": py} ~~
```

Do **not** wrap ordinary calls, assignments, `if`, or `for` in `~~` &mdash; those
are native MAST.

## `->END` is uppercase, and ends the task

It must be `->END` (not `->end`). It ends the current **task**; when the last task
ends, the story ends.

## You don't "open" comms or science

They're **route-based**. You don't call comms; the engine routes a selection to
your `//enable/comms` / `//comms` (or `//enable/science` / `//science`) routes, and
you react there. See [Comms](../cosmos/comms.md) and [Science](../cosmos/science.md).

## Signals are synchronous; `signal_next` is one-shot

`signal_emit` calls every listener **immediately, in the same tick**.
`await signal_next(name)` waits for the **next** emit only &mdash; loop it to react
repeatedly, or use a `//signal/<name>` route for a persistent reaction.

## `obj[key]` on a MastDataObject raises

Data objects (and PyMAST `MastDataObject`) store values as **attributes**. Read
with `obj.get(key, default)` or attribute access &mdash; `obj[key]` raises
`TypeError`. Likewise, prefer `data_set` over the legacy `blob` alias (they're the
same object).
