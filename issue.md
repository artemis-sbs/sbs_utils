# LM #714 - GUI handler lifetime and `await gui()`

> **Status: PROBLEM STATEMENT (2026-08-19).** Part 1 below is a draft body for
> LegendaryMissions #714, replacing the rough notes that were here. Part 2
> records the design decisions taken. The phased implementation plan lives in
> `~/.claude/plans/in-sbs-utils-see-the-twinkling-floyd.md`; nothing has been
> posted and no code has changed.

---

## Part 1 - draft body for #714

### What this issue is

#714 groups #707 and #713. They are two faces of one problem: **a GUI handler
belongs to the MAST task that built the widget**, and that task is very often
not the task the handler needs to run on.

This is not one bad decision. It is an accumulation of changes that each made
sense on their own and together produced something both complicated and, in the
scheduled case, broken.

### The mechanism

`on gui_message(w):`, `on gui_click(w):` and `on change <expr>:` are all the
same compiler node - `OnChange` (`mast/core_nodes/on_change.py:7`), whose rule
makes the `change` keyword optional. At runtime (`on_change.py:72`) it records
`self.task` - the task executing the `on` statement - and
`(task.active_label, node.loc+1)`, the block's location inside *that task's*
label. Nothing else is ever recorded. It then splits two ways:

| | Registration | Fires by | Runs the block via |
|---|---|---|---|
| **Trigger** (`on gui_message` / `on gui_click`) | the value is a `Trigger`, which self-registers on the widget | click dispatch in `StoryPage.on_message` | `task.push_inline_block(...)` on the builder, or `start_sub_task` when a label arg was given |
| **Watcher** (`on change <expr>`) | `task.queue_on_change(self)` | polled every tick by `run_on_change()`, which recurses through `sub_tasks` | `task.push_inline_block(...)` on the builder |

A widget's `on_press=<label>` is the same story by a different route
(`procedural/gui/button.py:58-85`): a `Promise` gets its result set, a
`callable` is just called, and a **label** either jumps the builder task
(`is_sub_task=False`, the default) or starts a sub-task of it
(`is_sub_task=True`).

All of that is fine while the builder *is* the console's main GUI task. It falls
apart the moment the builder is a separate task that paints a panel and ends -
which is exactly what `task_schedule` / `sub_task_schedule` /
`gui_sub_task_schedule` are for. The widget survives; its handler's owner does
not.

### What the v1.4.0 fix covered, and what it did not

A partial fix for #707 shipped in **v1.4.0** and is on by default (`4c96bebc`
behind flags, `7ff587fd` flipped them on):

| Mechanism | What it does |
|---|---|
| `MastAsyncTask.revive_ended_handlers` (`mast/mastscheduler.py:1399`) | Wakes a builder that ended *normally*, in place, so the block it registered still runs with the scope, `active_label` and identity it was written against. The page's `gui_task` adopts it for **ticking only**. `StoryPage.on_new_gui` ends it with the GUI that owned the widget. |
| `OnChangeRuntimeNode.pop_inline_block_on_end` (`on_change.py:107`) | Lets an inline block that falls off its own end hand the task back. Not optional: without it a revived builder parks on the block's end node forever and accumulates in `Agent.all` on every click. |

A builder that **crashed** or was **canceled** is deliberately never revived; a
warning naming the source site goes to `mast.runtime.log` instead.

**The gap that leaves #713 open:** `revive_for_handler` is consulted at exactly
three sites - `gui/message.py:126`, `gui/message.py:44` and `gui/button.py:63`.
All three are the **click** path. The **watcher** path has no equivalent. An
`on change` watcher lives in its builder's `on_change_items` and is only reached
because `run_on_change()` recurses into `gui_task.sub_tasks`; when the builder
ends, `tick_subtasks` (`mastscheduler.py:1353`) removes it from that list and
`dispose()`s it, and the watcher goes with it. Nothing revives it.

Two smaller asymmetries in the same area, worth deciding about explicitly:

- `queue_on_change` double-buffers into `pending_on_change_items` **only when
  `is_gui_task`** (`mastscheduler.py:825`). A gui sub-task is not, so its
  watchers go live immediately and are never swapped or dequeued by
  `swap_on_change` - they are cleaned up only incidentally, by `end_on_new_gui`
  killing the whole sub-task.
- `is_sub_task=False` unpacks a `data={}` dict into variables on the builder
  task; the sub-task path passes the same dict as `inputs` instead. For a
  **dict** both end up as variables (`start_sub_task` walks `inputs`), differing
  only in scope. For a **non-dict** they diverge outright: the jump path binds
  it to a variable named `data`, while the sub-task path hands it to
  `for k in inputs`, which walks a string one character at a time.

So #707's symptom is largely gone. **The design problem it exposed is not**, and
#713 was never covered.

### Why this is hard: the runtime cannot predict the scripter

The library has no way to know what a scripter will put in a handler body. Any
single policy - "run it on the builder", "run it on a fresh sub-task", "jump the
GUI task" - is right for some bodies and wrong for others.

In practice there are exactly **two** shapes, and they want opposite things:

1. **Repaint.** The handler jumps to a label that builds a new screen and ends
   in `await gui()`. This *must* run on the console's main GUI task.
   Representative: `LegendaryMissions/casino/market.mast:46` -
   `on_press="market_action"`, whose body ends in `jump market_show`.
2. **Act.** The handler does a bit of work and returns, and may be pressed many
   times. This wants to be an independent task - which is what
   `is_sub_task=True` was added for. Representative:
   `LegendaryMissions/hangar/hangar.mast:517`.

`is_sub_task=True` is the better **default** for shape 2. The only reason it
cannot simply become the default is shape 1: nothing stops a scripter putting
repaint code behind it, and there is no way to detect that in advance.

### The sharp edge: `await gui()` off the main GUI task

This is the piece that has to be settled first, because every candidate design
runs into it.

`await gui()` only means anything on the console's main GUI task.
`procedural/gui/gui.py:670` currently reads:

```python
if task != gui_task:
    print("await gui() was not called in gui's main task. Consider using gui_task_jump.")
else:
    page.swap_gui_promise(ret)
return ret
```

So today, `await gui()` from any other task:

- emits a bare `print()` - not `log()`, so it never reaches `mast.runtime.log`,
  and in the engine it goes nowhere a scripter will look;
- returns a `GuiPromise` the page never adopted, so **nothing will ever resolve
  it**. The calling task hangs silently and permanently.

**What this looks like is not "nothing happened."** Measured rather than
assumed: the widgets the handler queued *do* draw, because `gui_*` calls queue
onto the PAGE whichever task makes them. What does not follow is **ownership**.

| | on screen | GUI task | the handler |
|---|---|---|---|
| today | the new screen | still parked on the OLD label and promise | stranded forever, leaking in `gui_task.sub_tasks` |

So the screen changes and then the flow dies, which is most of why this has been
so hard to place.

Naively "fixing" that by letting the child call `swap_gui_promise` is worse:
`swap_gui_promise` (`mast_sbs/maststorypage.py:230`) **cancels** the promise the
main GUI task is parked on, so the GUI task falls through past its own
`await gui()` into whatever follows - leaving a screen the scripter never asked
to leave.

**The required semantics:** when a handler reaches `await gui()`, the GUI task's
in-flight `await gui()` must **not resolve**. The new `await gui()` has to
behave as a **jump on the main GUI task**, with the handler's build becoming the
console's new screen. The machinery already exists - `gui_task_jump`
(`procedural/execution.py:708`) queues `page.gui_task.jump(label)`, and
`gui_reroute_client` (`procedural/gui/navigation.py:33`) does that plus a
same-frame `tick_in_context()`. The problem is that the scripter has to know to
reach for them, and nothing in the code or the docs tells them.

### Requirements for the fix

- **Simple for scripters.** No reasoning about which task a handler runs on, no
  classifying their own code as "repaint" vs "act". It should just work.
- **Backward compatible where it can be.** Deprecating a form, or changing a
  default with a deprecation path, is acceptable. Silently changing what
  existing scripts do is not.
- **Not more runtime complexity.** Collapsing mechanisms beats adding another
  special case.

Corpus exposure (LegendaryMissions + OpenUniverse, `.mast` and `.py`):

| Form | LM | OU |
|---|---|---|
| `on gui_message(...):` block | 122 | 10 |
| `on change ...:` block | 52 | 8 |
| `gui_sub_task_schedule` | 29 | 2 |
| `on_press=<label>` | 13 | 0 |
| `is_sub_task=` | 2 | 0 |

The block forms are what missions actually use. `on_press=<label>` and
`is_sub_task=` have a small enough footprint to change or deprecate.

### Also in scope: documentation

`on change`, `sub_task_schedule` and `gui_sub_task_schedule` have no mkdocs
coverage of **handler lifetime** - which task a handler runs on, how long it
lives, how it should end. #713's thread is two contributors saying plainly they
cannot find this written down and cannot infer it. They are right:

- The model is stated in **exactly one place in the doc set**, and it is a
  changelog entry: `whats-new.md:1540` - *"A widget's handler belongs to the
  task that built the widget."* Nothing links to it.
- `cosmos/gui.md:131`, the page an author actually reads, says only *"`on`
  handlers run while a GUI is on screen"* - the **wrong** model: it implies
  lifetime tracks the page when it tracks the builder task.
- **`is_sub_task=` has zero prose hits** in `mkdocs/docs`; it is reachable only
  by scrolling the mkdocstrings dump in `api/procedural/gui.md`.
- `on_press=` appears in no hand-written page. `gui_task_jump` has no positive
  documentation - it is named only inside a `!!! danger` about `map_start`.
- `gui_sub_task_schedule` appears only in `api/procedural/execution.md`, never
  connected to handlers, even though "cancelled when a new GUI page is shown"
  *is* handler lifetime.
- There is **no comparison table** of the handler forms, and the `on signal`
  **block** form is contrasted with neither `//signal/` routes nor `signal_next`
  anywhere.

### Not part of this issue

The "rapid click parks the task" defect pinned in `3d25a7a7` was later shown to
be a test-harness artifact and its `expectedFailure` tests were removed:
`handlerhooks` calls `tick_the_rest` immediately after `Gui.on_message`, so a
second click cannot land before the first block's return is taken. See the
`TestRepeatClicks` docstring in `tests/test_gui_message_dead_builder.py`.

---

## Part 2 - decisions taken (2026-08-19)

| Question | Decision |
|---|---|
| `await gui()` off the GUI task | **Auto-promote to a GUI-task jump.** The in-flight `GuiPromise` is superseded, never resolved. |
| `on_press=<label>` default | **A hosted sub-task becomes the default.** `is_sub_task=` is deprecated, still honored. |
| Baseline (keep vs revert the #707 fix) | **Decide after a spike**, comparing promotion mechanics against a fixture matrix. |
| Sequencing | **Code first, docs after.** |

### What promotion does to `gui_task_jump`

It does **not** make it obsolete; it demotes it from "the thing you must
remember" to "the explicit redirect", which is what it actually is. Three jobs
promotion cannot do:

1. **Redirect the GUI task without going there yourself.** The watch/repaint
   pattern - a `sub_task_schedule`d poll loop that kicks the panel to a repaint
   label and *keeps looping* - cannot be rewritten as `jump repaint`, because
   promotion would transplant the watcher and consume it.
2. **Fire-and-forget redirect with no build.** Promotion only triggers on an
   `await gui()`; code that just kicks a console to another screen has none.
3. **From a Python callable.** `on_press=<callable>` and `gui_message_callback`
   run with no task in the path and cannot `await`.

So promotion must be implemented *in terms of* the existing redirect rather than
beside it - one "jump this page's GUI task" helper behind `gui_task_jump`,
`gui_reroute_client` and promotion alike - and the collision must be defined:
if a handler calls `gui_task_jump("a")` and then reaches `await gui()`, the
explicit call wins and promotion no-ops.
