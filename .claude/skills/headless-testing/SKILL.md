---
name: headless-testing
description: Testing Cosmos missions and sbs_utils without the engine - the cosmos_dev mission runner (--test, --exercise, --runs, --fresh-process, --use-working-tree, --coverage-json, --strict-blob, --soak), unittest harnesses on the mock, driving a REAL MAST panel, console route, comms menu or picker in-process, soaks, and judging what a green result actually proves. Use when running cosmos_dev.mission_runner, writing or debugging a unit test for sbs_utils or a mission addon, building a harness that compiles MAST and clicks its buttons, chasing a run-2-only or order-dependent failure, reading a soak, or before claiming "fixed" or "the suite is green".
---

`cosmos_dev` is the dev-only mock of the `sbs` Pybind11 API plus a tick loop
(`cosmos_dev/mission_runner.py`). It lets a mission run headless in seconds, and it is
**kinder than the engine** in ways that hide real bugs. This file is about getting real
evidence out of it: which rung of the ladder proves what, the harness recipes that work,
and the traps that make a broken thing read green.

Already covered elsewhere - do not repeat, read them:

- `CLAUDE.md` "Testing" (unittest, `test_set_exe_dir()`, mock `sbs` setup) and
  "Development / Debugging" (flags, `--runs` / `--fresh-process` table, reset ledger,
  browser URLs, mock physics).
- `mkdocs/docs/tooling/testing.md` - the user-facing guide to conformance runs, the quest
  pilot and the soak ratchet.
- `python -m cosmos_dev.mission_runner --help` - the authoritative flag list.
- The `engine-debugging` skill - running the real exe and getting values out of it.

---

## The verification ladder

Each rung proves something the one below it cannot. Know which rung you are on before
you say what you proved.

| Rung | Command / tool | Proves | Does NOT prove |
|---|---|---|---|
| 0. Lint | `sbs lint` | Namespace collisions, `//signal` side effects, unguarded blob reads | That the story compiles (an unmet `requires` or a library-global collision lints clean and compiles to **0 labels**) |
| 1. Compile gate | `--test 5 --map 0` | Story + every mastlib compiled; top-level main ran | Anything past the first seconds; any console |
| 2. Conformance | `--test 30 --map 0 --seed 7` | No runtime error in what the mission's own flow reached | Any code the flow did not reach; behavior nothing asserts |
| 3. Exercise | `--test N --exercise [--exercise-console X --exercise-dwell D --exercise-click "A,B"]` | Selections, comms, the five core consoles, named buttons | Tab-strip pages; custom consoles unless named; watcher bodies at default dwell |
| 4. In-process harness | a `unittest` that compiles real MAST and clicks it (below) | A specific panel/route/menu does the specific thing, asserted | The engine's rendering, networking, timing |
| 5. Restart soak | `--test 15 --runs 3 [--fresh-process]` | No state leaks across a mission reload | Anything about a single run |
| 6. Browser mock | `--gui` | It looks and clicks right in the mock | Engine rendering (engine widgets are partly faked) |
| 7. Engine | Cosmos itself, or `sbs soak ... --engine` | **The only authoritative result** | - |

Pick the lowest rung that can **fail** on the bug you care about. A rung that cannot see
the bug proves nothing about it, however green.

---

## mission_runner recipes

All of these run from anywhere; pass the mission folder. The mission must live under a
folder that has `__lib__/` above it (the runner walks up for it and refuses otherwise).
`sbs debug` exposes none of `--test/--exercise/--soak`; use `python -m
cosmos_dev.mission_runner`.

### Compile gate and conformance

```
python -m cosmos_dev.mission_runner . --test 30 --map 0 --seed 7 --use-working-tree
```

- `--use-working-tree` runs the working-tree `sbs_utils` instead of the packaged
  `.sbslib`. Without it you are testing the last BUILT library, not your edit.
- Without it, LegendaryMissions run as its own mission uses addon SOURCE ("Using mission
  SOURCE for N declared addon(s)"); any other mission pulls built mastlibs from `__lib__`.
  Run both when a mastlib may be stale.
- The verdict (`cosmos_dev/verdict.py`) fails on MAST runtime errors, compile errors
  (shown as `(compile) [file.mast] ...`), `.amd` parse errors, and **any content in
  `mast.runtime.log`** (`sweep_runtime_log`) - which catches library code that swallows
  its own exception and only logs it, such as a listbox `item_template` error.
- `FAIL - mission executed 0 labels` means nothing ran: a mastlib failed to load, an
  addon `requires` is unmet, or a parse error desynced the compiler. The runner prints
  the compiler's own message; also read `mast.compile.log`.

**`mast.runtime.log` is opened with mode `"w"` in the mission folder on every compile.**
A headless run against the real mission destroys the log an engine session just wrote.
While someone is testing in the engine, run headless against a COPY placed under the
same missions root. A `--runs` reload archives each run's log as
`mast.runtime.run<N>.log` first.

**`log()` does not reach stdout** - a named log category goes to the log file, not the
console. Temporary proof markers are `print("PROOF ...")`; remove them before committing.

### `--map` is not the production entry path

`--map` has the runner schedule the `@map` label itself (`_try_auto_start_map`), so LM's
server console `start` label (roster hooks, music pick, time limit, saved setup) **never
runs**. To exercise the real console path, drop `--map` and pass AUTO_START through the
environment:

```
COSMOS_SETTINGS='{"AUTO_START": true, "WORLD_SELECT": "siege"}' \
  python -m cosmos_dev.mission_runner . --test 10 --seed 7 --use-working-tree
```

`show_server_menu` then takes its own `jump start if AUTO_START`. Anything written below
that jump is skipped on this path. `_merge_cosmos_settings` uses `setdefault`, so an
externally set key survives whatever the runner infers.

An sbs_utils-only mission (no LegendaryMissions) has no picker and no `--map` auto-start:
both come from LM's server console, and `maps_get_list()` returns `[]` when no page is
current. Such a mission must draw its own entry.

### Settings an addon registers

An addon's own `settings_add_defaults(...)` keys were measured NOT taking a `--profile`
value headless (library keys do; cause unconfirmed). Pass them via `COSMOS_SETTINGS`
(`'{"DIRECTOR": {"enable": true}}'`), and keep them in the profile for the engine.

### Exercise

| Flag | What it adds | Trap |
|---|---|---|
| `--exercise` | Drives selections, comms, and cycles helm/weapons/engineering/comms/science | Stages combat (zeroes shields, heat 1.5): kills a peacetime mission. `--pilot` suppresses it unless a quest wants a kill |
| `--exercise-console A,B` | Also cycles `@console/<name>` consoles | Extras come LAST (`_GAMEPLAY_CONSOLES + _extra_consoles`). Budget at least `dwell x (5 + extras) / 3` sim-seconds or the console is never opened |
| `--exercise-dwell N` | Steps per console (default 3, ~0.6 s) | At the default, an `on change` / watcher on a 1-second tick **never fires**. Use ~25-30 when watchers matter |
| `--exercise-click "A,B"` | Presses live buttons by DISPLAYED label, one press per pass, rotating | Comma-separated, so a label containing a comma cannot be driven. Tab-strip buttons are not in the tag map and cannot be pressed |

**A console tab page cannot be reached by `--exercise` at all.** `gui_queue_console_tabs`
builds its `TabControl`s into `page.pending_layouts`, not through `add_content`, so the
clicker never sees them. Every `//gui/tab/<x>` page is layer-4 territory (an in-process
harness).

### Coverage JSON: what actually ran

```
python -m cosmos_dev.mission_runner . --test 60 --map 0 --seed 7 --exercise \
  --coverage-json cov.json
```

Shape: `{"mission", "map", "summary", "labels": [...], "lines": {file: [line, ...]}}`.

- `labels` is the labels that RAN. A route absent from it is proof it never executed -
  the category counts in the text report are not.
- A file listed in `lines` compiled, even if none of its labels ran.
- Diff LINES, not labels, in an A/B. LM map 0's label count moves 1-3 between identical
  seeded runs (the quest/prefab picker is not seeded); lines are stable.
- **Check this before trusting `--exercise`.** It frequently never enters the console you
  care about; the report still says PASS.

### Strict blob reads

The engine returns `None` for a `data_set` field nothing has set; the mock returns a typed
default from `_DATA_SET_DEFAULTS` (~227 keys). `if energy < 30` runs clean headless for
years and raises `'NoneType' < int` on a bridge - and since a failing expression stops the
command, the watcher task just ends. `--strict-blob` makes the mock answer `None`:

```
python -m cosmos_dev.mission_runner . --test 60 --map 0 --exercise --strict-blob
```

It is a survey of what the run reached, not a coverage gate. The static twin is
`sbs lint`'s `blob-unguarded-none`. Fix with `get_data_set_value(id, key, default=0)` -
the third POSITIONAL argument is an index, not a default.

### Seeded A/B: RNG draws shift everything downstream

One extra `random_face()` on a per-build path took stock LM from 15 NPC hulls to 13 -
labels identical, verdict PASS. For changes on per-frame or per-build paths, diff the
LIST of `__npc__` hulls from `--test 30 --map 0 --seed 7` against a stock baseline.

### Deterministic scenario in the sandbox map

When the real map will not reproduce a behavior in-window (spawns far out, waves gated by
time or difficulty), temporarily `task_schedule` a label in LM's empty `@map/sandbox`
(`maps/sandbox.mast`) that spawns exactly the actors needed, run `--map sandbox
--use-working-tree`, grep `print("PROOF ...")` markers, then revert. This proves the
branch EXECUTED; a real map only proves the absence of a crash.

### Restart soak and the MOCK-vs-REAL classification

The commands and the three-row verdict table are in `CLAUDE.md`. Beyond that:

- **Column meanings.** `brains` = agents with a brain; `moving` = objects under way.
  `npcs` steady while `moving` collapses = frozen NPCs (brains stopped ticking). Rising
  `brains`/`moving` is state accumulating, the opposite shape.
- **Trailing bogus FAIL.** After the last run the runner reloads once more (so run N gets
  a leak measurement) and the closing report can read `labels 0/? FAIL - mission
  executed 0 labels`, exit 1. Trust the per-run table and the `STABLE` / divergence line;
  for a real verdict, run once without `--runs`. The difference from a real 0-label
  compile failure is whether the runs above it executed labels.
- **`--fresh-process` zero table.** If every leg reports `fresh run N produced no
  fingerprint` with all-zero counts and `errors 1`, it is a harness result, not a
  collapse: run the child command the parent printed, verbatim, on its own. Each leg is
  spawned with `cwd=` the sbs_utils project root and the parent's own argv, so **pass the
  mission as an absolute path** when using `--fresh-process` (a relative `.` resolves
  against the wrong folder in the child). Use plain `--runs N` for module-level leaks;
  that is the leg that exercises `run_next_mission`.
- **LM has pre-existing `--runs` divergences** (a run-3 `SETTINGS` collapse; npcs/terrain
  rising from run 2-3; AUTO_PLAY combat cascades that classify MOCK without a reset gap).
  Never gate a diff on an LM `--runs` soak - use it only for the frozen-brain shape and
  `errors > 0`. Confirm "pre-existing" by stashing, or with a detached-HEAD worktree placed
  UNDER `data/missions/`.
- New per-mission module state must be cleared in `reset_mission_state()` and declared
  with `register_reset_state(name, probe)` (`sbs_utils/handlerhooks.py`), or the soak
  cannot see it. Latches ("already scheduled" flags) count.
- `tests/test_restart_reset.py`, `test_restart_ai_ticks.py`, `test_restart_stream.py`
  are the sub-second unit forms.

---

## Unit-test harness patterns

### Boilerplate that works

```python
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()                                   # before anything touches a path

import sys, unittest
import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)              # before anything does `import sbs`

from sbs_utils.agent import Agent, clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  - ALWAYS import explicitly
from sbs_utils.spaceobject import SpaceObject

class Base(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        mock_sbs.resume_sim()          # delay_sim / timers need a running sim
        clear_shared()                 # BEFORE SpaceObject.clear(), see below
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "test"))
        Agent.SHARED.set_inventory_value("sim", mock_sbs.sim)
```

Details that each fail silently:

- **`sim` in MAST is a SHARED VARIABLE**, published by `cosmos_event_handler` every event.
  A harness that never sets it gets `'NoneType' has no attribute 'time_tick_counter'`
  from the addon's own main - reported against the addon, not the harness.
- **Order: `clear_shared()` then `SpaceObject.clear()`.** The other order wipes
  `Agent.SHARED` out of `Agent.all`, and anything resolving the shared agent
  (`quest_add(Agent.SHARED_ID, ...)`) is a silent no-op.
- `set_inventory_value(<id>, ...)` on an id with no Agent is a silent no-op. Client ids
  need `GuiClient(cid)` or `Gui.push` first.
- **An id is a typed thing.** `CID = 77` has no console bit, so code checking
  `is_client_id` takes the not-a-console branch. Use `0x8080000000000001` there.
- **The engine's event is READ-ONLY** (`cosmos_event_handler` calls `FakeEvent.freeze()`).
- `mockgui.create_new_sim()` enqueues `world_reset`; reset `gui_queue` after it.
- Capture MAST runtime errors by swapping `MastScheduler.on_runtime_error` (restore in
  `tearDown`). **`StoryScheduler` overrides `runtime_error`; the seam is
  `MastScheduler.on_runtime_error`** - asserting on anything else is vacuous.

### Isolation between tests that compile stories

Routes a compile registers (`//focus/comms`, `//drag/comms`, ...) live in
**dispatchers, not the story**, so the previous test's routes still answer. Every test
that compiles MAST:

```python
from sbs_utils.delete_queue import DeleteQueue

def setUp(self):
    from sbs_utils.handlerhooks import reset_mission_state
    reset_mission_state()          # drops story routes; the library's own handlers survive
    mock_sbs.create_new_sim(); mock_sbs.resume_sim()
    DeleteQueue.clear()
    ...
```

The library's import-time handlers (comms/science/popup selection, task purge on destroy,
mount/orbit cleanup, grid move-role) are registered with `<Dispatcher>.add_library(...)`,
and `clear()` replays them - so a reset keeps them (fixed 2026-09-18,
`tests/test_reset_keeps_library_handlers.py`). A NEW import-time registration must use
`add_library` too, or the dev runner's in-process reload loses it from run 2 on. On an
older sbslib a harness had to snapshot and re-add the ConsoleDispatcher defaults by hand.

Why `DeleteQueue.clear()`: it drains only at the end of `cosmos_event_handler`, which a
unit test rarely calls, and `create_new_sim()` recycles space-object ids - so a leftover
id makes `object_exists()` report a brand-new object as deleted.

Also reset in `tearDown`: `Gui.clients = {}`, `Gui.widget_list_sent = {}`,
`FrameContext.task/page/mast/context = None`, the page class's `story = None`, and any
`mock_sbs.send_*` you wrapped.

### Suite hygiene

- **Never import across test modules.** `unittest discover -s tests` imports files as
  top-level names, so `from tests.test_x import harness` creates a SECOND module object
  with its own state; its `MastGlobals.import_python_function(probe)` rebinds the probe to
  the copy's collector, and the original file's tests fail with `Lists differ: [] !=
  [...]`. Each file passes alone - that is the tell. Make every harness self-contained with
  uniquely named probes.
- **A piped run's exit code is the pipe's last command.** `... discover -s tests 2>&1 |
  tail` exits 0 on a failing suite. Read the verdict line:

  ```
  python -m unittest discover -s tests 2>&1 | grep -E "^(OK|FAILED|Ran |FAIL: |ERROR: )" | tail -8
  ```
- **Get the discriminator before attributing a failure**: stash the change and re-run
  (same count = not your change); for "did my new TESTS break it", check out the old test
  file against the current library.
- Mission addon tests run from the mission root:
  `PYTHONPATH=../sbs_utils python -m unittest comms.test_drag_orders`.

---

## Driving real MAST headless

`--test` proves a story compiles; `--exercise` drives selections. Neither opens a console
TAB or asserts what a panel shows. An in-process harness does, in under a second. Working
templates in LegendaryMissions:

| Template | Drives |
|---|---|
| `fabrication/test_fabricate_panel.py` | A `//gui/tab` route with a workflow behind it |
| `consoles/test_manual_beams_panel.py` | A bare builder; the `_Emitted` recorder; `Gui.on_message` clicks |
| `consoles/test_console_tab_widget_rects.py` | The real `layout_widgets.mast` consoles via `gui_console(...)`, tab round-trips, widget rects |
| `comms/test_drag_orders.py` | Comms buttons the engine would be sent; `comms_drag_event`; pressing them |
| `internal_comms/test_ultra_beam_on_ship.py` | Comms menus via `follow_route_select_comms`, Back navigation |
| `maps/test_pr_gunnery_surrender.py` | ONE `//shared/signal` route sliced out of a big map file |

### Compile the story the way the mission does

```python
story = MastStory()
story.basedir = ADDON_DIR                    # where `import x.mast` resolves
errors = story.compile("\n".join([
    "shared SETTINGS = {}",                  # if a file reads SETTINGS at top level
    "import helpers.py",                     # registers the addon's .py functions
    "import panel.mast",
    "gui_text('$text:harness;')",            # the PARK goes LAST
    "await gui()",
    ""]), "harness", story)
assert errors == []
Page.story = story; FrameContext.mast = story
```

- **Compile through MAST's own `import`, with `story.basedir` set.** The compiler injects
  `signal_register(...)` for every `//` route into THAT FILE'S main. Concatenating files
  into one source registers nothing (the click emits and nothing answers). Compiling files
  separately into one story wipes the label table.
- **The park goes last**, after the imports. Main must park (`await gui()`) or `present()`
  raises `EDGE CASE: Did you set END or Yield the last GUI Task?`.
- **Addon `.py` functions**: `import foo.py` in the harness source, or register them by
  hand, filtering to functions the module defines:

  ```python
  for n in dir(mod):
      f = getattr(mod, n)
      if callable(f) and not n.startswith("_") and getattr(f, "__module__", "") == mod.__name__:
          MastGlobals.import_python_function(f)
  ```
- `main` only falls through into a label **in its own file**; extra labels go after the
  park, and an imported label is never reached by fallthrough.
- `.amd` data is read at top level through `media_read_relative_file`, which has no mission
  dir here - load it yourself (`amd_document(open(path).read())`).
- Seed shared-agent data AFTER the first `present()`; starting the story resets it.

### Pages, presenting and clicking

```python
class HarnessPage(StoryPage):
    story = None

server = HarnessPage(); Gui.push(0, server)      # BOTH pages
page   = HarnessPage(); Gui.push(CID, page)

def present(n=2):
    for _ in range(n):
        mock_sbs.sim._time_tick_counter += 30
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "gui_present"))
        server.gui_state = "repaint"; server.present(FakeEvent(0, "gui_present"))
        page.gui_state   = "repaint"; page.present(FakeEvent(CID, "gui_present"))
```

- **Push a SERVER page as well.** `//shared/signal` routes are filtered by client 0 (the
  real filter is in `mast.signal_emit`); with only a client page they register and never
  run. Scheduled tasks tick on the page whose scheduler owns them, so present the server
  page too or a `//shared/signal` completion never fires.
- **Present twice** per step: a route entered on one present builds on the next.
- `present()` only re-emits the page's tree; to see a panel react, re-enter the route
  (`gui_reroute_client(CID, label)`) so the builder re-runs.
- **Click the way the engine does**, then present:

  ```python
  FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(CID, "gui_message"))
  Gui.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag=tag))
  present()
  ```

  Find the tag by wrapping `mock_sbs.send_gui_button` / `send_gui_clickregion` /
  `send_gui_text` in a recorder (`_Emitted` in `test_manual_beams_panel.py`) and reading
  back what the page emitted, or by walking `page.layouts` -> `.rows[].columns[]` and
  reading `props_display_text(item.value)`. Listbox row clicks are
  `"<lb_tag>:<row>:__click"`.
- **One press, then one tick.** The engine sends one `gui_message` per press and runs
  `tick_the_rest` right after. Several presses with no tick between, or a dispatch with
  `sim` unset, manufacture states the engine cannot reach - and have inverted an A/B.
- **Cannot see the console tab strip**: that is drawn by the console page these harness
  pages stand in for.

### A real console route (`//gui/normal_*`)

`gui_console("comms")` sets the page's widget list and console to `normal_comm`; the
page path becomes `gui/normal_comm`, so `await gui()` runs LM's `//gui/normal_comm` from
`consoles/layout_widgets.mast`:

```python
story.basedir = LM_CONSOLES
story.compile("\n".join([
    "shared SETTINGS = {}",
    "import manual_beams_helpers.py", "import tether_indicator.py",
    "import layout_widgets.mast",
    "jump harness_console", "",
    "== harness_console ==",
    '    gui_console("comms")',
    "    await gui()", ""]), "consoleharness", story)
```

Bake the console name into the source rather than a task variable: `Gui.push` presents
immediately, so main has reached the label before a test could set one. Record
`mock_sbs.send_client_widget_rects` to assert where engine widgets land.

### Comms menus and buttons

The comms console is not a GUI page - the engine is sent buttons. Wrap the two sends,
select, and press by text:

```python
mock_sbs.send_comms_button_info    = lambda ship, color, text, tag: buttons.append((text, tag))
mock_sbs.send_comms_selection_info = lambda ship, face, color, title: buttons.clear()

mock_sbs.assign_client_to_ship(CID, ship.id)
science_set_scan_data(ship, target, "identified")     # REQUIRED, see below
follow_route_select_comms(ship.id, target.id); present()

ev = FakeEvent(client_id=CID, tag="press_comms_button", sub_tag=tag,
               origin_id=ship.id, selected_id=target.id)
FrameContext.context = Context(mock_sbs.sim, mock_sbs, ev)
ConsoleDispatcher.dispatch_message(ev, "comms_target_UID"); present()
```

- **Comms sends no buttons for a contact the side has not scanned.** Without
  `science_set_scan_data(origin, target, ...)` the menu is empty and reads as a broken
  route.
- `selected_id` on the press IS the comms target (it can legitimately be 0 - "nothing
  selected").
- Drags: `DragDispatcher.dispatch_comms(FakeEvent(tag="comms_drag_event", origin_id=src,
  selected_id=dst, parent_id=ship))`; the mock has no drag gesture, so this is the only
  headless proof.
- Faking a 2D-view click: `select_space_object` with `sub_tag` = console NAME
  (`normal_comm`), `value_tag` = widget (`comms_2d_view`), `extra_tag` = console UID
  (`comms_target_UID`). A right-click is a different event, `hold_click`.

### Testing one route sliced out of a big file

The injected `signal_register` is appended to the END of main. A cut-down main that keeps
itself alive with an idle loop sits in front of it, so the route is never registered
(`story.signal_observers == {}`). Slice the real body with a regex up to the next column-0
label (`^//shared/signal/<name>.*?(?=^(?://|=|@))`, `re.S|re.M`) and register by hand:

```python
label = next(n for n in story.labels if n.startswith("__route__shared/signal/" + SIGNAL))
FrameContext.task = page.story_scheduler.tasks[0]    # main's task; emit skips done() tasks
signal_register(SIGNAL, label, True)                 # True = shared/server
```

### The LM console picker (lobby)

No runner flag reaches it: `--exercise`'s synthetic client connects after the map started.
Bootstrap in-process (`cosmos_dev/tools/drive_picker.py` is a partial harness - its
docstring banks what works and where it stops):

- `_load_libs(MISSION, MISSIONS_ROOT, use_working_tree=True)`, mock `sbs`,
  `sys.modules["script"] = sys.modules["__main__"]`.
- **`fs.exe_dir` is the Cosmos INSTALL ROOT** (parent of `data/missions`, as
  `mission_runner` sets it), and **`fs.script_dir` is the mission** - both, or every
  mastlib path and `settings.yaml` resolve wrong. The failure shows only in
  `page.compiler_errors`: `start_story` is a no-op while there are any, so
  `story_scheduler is None` is a bootstrap mistake, not a mission that did nothing.
- Per tick: bump `sbs.sim._time_tick_counter`, `cosmos_event_handler(sim,
  FakeEvent(0, "mission_tick"))`, then **`_drain_client_strings(...)`** - without it a
  client sits in `client_main` forever (its `gui_request_client_string` round trips never
  resolve).
- Connect: the runner's own path is `sbs.register_client(cid)` +
  `cosmos_event_handler(sim, FakeEvent(client_id=cid, tag="client_connect"))`. **Under
  the picker bootstrap that path gives no page at all** (measured 2026-09-18); call
  `Gui.add_client(FakeEvent(client_id=cid, tag="client_connect"))` directly, as
  `drive_picker.py` does. The harness is still BLOCKED: the page appears but never builds
  a layout, and the `exe_dir` fix did not change that.
- Count widgets ON the page, not the page: the page carries a tag of its own, and
  counting it turned an empty picker into "painted 1 widget".
- `Gui.clients` maps id -> **GuiClient**, not page; the live page is the top of its
  `page_stack`.
- Do not trust `active_label`: labels fall through, so a task can run the picker while
  still reporting `client_main`.

---

## Soaks

Check what exists before writing another - `mkdocs/docs/tooling/testing.md` is the guide:

- `sbs soak init|bless|run <mission> <scenario> [--engine] [--hours N|--runs N]`
  (`sbs_cli/src/soak_cmd.py`) over `cosmos_dev/quest_pilot.py`, `soak_manifest.py` and the
  supervisor `cosmos_dev/tools/mission_soak.py` (exit 0 pass / 1 regressed / 2 build
  changed / 3 nothing ran). In the runner: `--soak NAME` (`<mission>/soaks/NAME.yaml` -
  not LM's `soak/` ADDON), `--soak-init`, `--soak-bless`.
- **The ratchet is an INTERSECTION with per-item seen counts**: a baseline demands only
  what was seen in EVERY blessed run, so blessing more runs relaxes flaky items.
  `expect.routes_covered` is a contract; baseline route drift is allowed up to
  `expect.route_tolerance` (default 3). (The `--soak-bless` help text still says "unioned
  in"; `soak_manifest.py` is the truth.)
- Assert quests and labels (+/-2), never `nodes_entered` (+/-20).
- The pilot's `pilot_steps` must be non-zero: 0 means it never ran, whatever the coverage
  says - the mission's own execution accrues coverage too.
- Engine soaks (`cosmos_dev/tools/engine_soak.py`, `cosmos_dev/engine_soak.py`) exist
  because a mock soak can run clean all night while the exe dies - see `engine-debugging`.

### Harness code that must also run in the engine

`cosmos_dev` ships as its own sbslib, so harness code can run inside Cosmos, where
`sbs.sim`, `sim.space_objects` and `sim.nav_points_by_id` do NOT exist. Use
`FrameContext.context.sim`, `to_object` / `object_exists`, `broad_test_around`,
`closest` and `sim.get_navpoint_by_id`. A missing attribute there fails silently and
green if the caller swallows it - give every driver a step counter in the verdict.

---

## What a green run proves (and does not)

The engine is the only authoritative environment. Everything else is "not obviously
broken".

1. **A test must fail without the fix.** A test written after the change pins what was
   just built and cannot disconfirm it. Revert the fix and watch the test fail - every
   time.
2. **Fixtures must carry the shipped conditions.** Forty-odd green tests met six defects
   in minutes of play because every fixture dropped what mattered: unarmed content, one
   console present from the start, unrealistic spacing, a hull key that does not exist,
   PyYAML instead of the engine's HJSON, a client id without the console bit. Before
   "done", list what the real content has that the fixture lacks, and run at least one
   test on the shipped artifact.
3. **Conformance PASS cannot see behavior it does not assert.** Sides that were never
   enemies never fired; eight trials passed. For "nothing happens" symptoms assert STATE
   (`side_are_enemies`, the soak's `moving` column), not the absence of errors.
4. **The mock must MATCH the engine.** A kinder mock makes a fix and its absence
   indistinguishable. Fix the mock in the same change, with a test that fails without it;
   inventing behavior the engine lacks needs the owner's say. Known kindnesses: typed blob
   defaults (`--strict-blob`), no `Simulation::Tick`, engine-populated keys the mock never
   set (a player's `dock_state` `""` silently wiped every weapons selection).
5. **Say whether the engine can even reach it.** `--map` starts a map during server init;
   `--exercise` fakes `client_connect` outside the tick loop; several `/server` tabs can
   each press Start (the mock-only double `@map` launch, guarded by
   `install_map_launch_guard`). A fix for a harness-only path is "defensive hardening".
6. **A favorable result from an unfaithful driver is still wrong** (a click storm with no
   ticks once made a flag look like it GAINED coverage). And two tools disagreeing about
   the same page is itself the bug report.
7. **Check object counts before trusting a mock measurement** (`/debug` status). Task
   liveness is membership in `sched.tasks`, never `task.done` (a Promise METHOD until a
   jump overwrites it with a bool).
8. **Words.** Unless the symptom was SEEN to go away in the engine, write "should fix X -
   unverified in the engine". An engine report outranks any mock result.

---

## Known flaky and order-fragile tests

| Test | Symptom | Status / how to tell |
|---|---|---|
| `tests/test_volume.py` `TestTractorHold` (3) + `TestRemoveOneVolume.test_a_held_ship_is_let_go` | `len(sim.tractor_connections) == 0 != 1`, only in a full `discover` | Order/count fragility: removing ANY one of ~23 earlier modules makes it vanish (the mock id sequence moves). Passes alone. Not a grav_tether regression - `volume.py` does not call it. Unfixed |
| LM map 0 `--test` label count | Moves 1-3 between identical `--seed 7` runs | Quest/prefab picker is not seeded. Diff `--coverage-json` lines, not labels. OU maps 0/1 and LM map 1 reproduce |
| Any test importing a sibling test module | `Lists differ: [] != [...]` in the sibling | Module identity, not the library. Make it self-contained |
