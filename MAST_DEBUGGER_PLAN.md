# MAST Debugger — Design & Implementation Plan

Status: **Phases 0-5 done & attach VERIFIED LIVE.** Core, DAP adapter, `sbs dap`
(launch) command, VS Code contribution (launch + attach), attach mode over a
socket, and conditional/hit/logpoint breakpoints + setVariable — all working.
Attach was exercised end-to-end against a running LegendaryMissions: breakpoint
hit in a lazily-loaded `maps/siege.mast`, source shown, stack + variables
inspected. Docs at `mkdocs/docs/tooling/mast-debugger.md`. Remaining: phase 6
(long-poll stepping, PyMAST/real-engine) and polish.

Fixes that came out of live bring-up (all landed): bind the DAP socket **early**
(before GUI/story setup) and print `LISTENING` only once bound; **re-accept**
connections so disconnect/retry works; **basename-based** breakpoint matching +
index **all** live masts + periodic re-index (so lazily-compiled map files arm);
`--dap-wait` to hold map auto-start until the debugger attaches; VS Code attach
**retries** the port; **absolute** source paths + a `source` request so the
editor opens the real `.mast`.

Two entry paths now exist:
- **Launch** — `.mast` breakpoint in VS Code → `sbs dap` (DAP over stdio) →
  `MastDapAdapter` → `MastDebugCore` runs the `.mast` and parks the tick thread.
- **Attach** — `mission_runner --dap-port N` serves DAP over a localhost socket;
  VS Code attaches to a running mission, breakpoints park its tick loop while
  control is serviced on the socket thread. Detach leaves the mission running.

Both ride the inert-in-production `on_enter_node` seam. **No shipped-code change.**

- Phase 0 — `cosmos_dev/mast_debug.py` (`MastDebugCore` + `run_scheduler_in_thread`),
  `tests/test_mast_debug.py` (5 tests). Breakpoints, step over/in/out logic, call
  stack (single + multi-frame), separated variable scopes, blank-line breakpoint
  binding, and coverage co-existence, all against the mock.
- Phase 2 — `cosmos_dev/mast_dap.py` (`MastDapAdapter` + `run_stdio` +
  `build_file_runner`/`file_runner_factory`), `tests/test_mast_dap.py` (5 tests).
  Translates DAP (initialize/launch/setBreakpoints/configurationDone/threads/
  stackTrace/scopes/variables/next/stepIn/stepOut/continue/evaluate/disconnect)
  onto the core, with `stopped`/`initialized`/`terminated` events from a monitor
  thread; stdio Content-Length framing; and a launch-mode factory that compiles a
  `.mast` file.
- CLI — `sbs_cli/src/dap_cmd.py` adds `sbs dap <mission> [--mast <file>]`, reusing
  `debug_cmd`'s lib bootstrap and redirecting lib-prep output off the DAP stdout
  stream. Verified end-to-end over a real subprocess stdio pipe.
- VS Code — `editors/vscode/`: a `mast` language (`.mast`/`.mastlib`), a
  `breakpoints` contribution, a `debuggers` (`type: mast`) contribution, and a
  `DebugAdapterDescriptorFactory` in `extension.ts` that launches `sbs dap` via
  the detected Cosmos Python + `sbs.pyz` (mirrors the lint LSP launch). Compiles
  clean (`tsc`); F5 on a `.mast` needs no launch.json.

1122-test suite green (Python); extension type-checks clean. **No shipped-code change** — everything rides the existing
`on_enter_node` seam and lives in cosmos_dev / sbs_cli.

Goal: a source-level debugger for `.mast` (breakpoints, stepping, call stack,
variable inspection, watch/eval) surfaced in VS Code — built so that it has
**zero impact on non-debug (production) runs**.

---

## 0. TL;DR

The hard part is already built. `MastTicker.next()` — the single choke point
every MAST node passes through on entry — already fires an optional, class-level,
`None`-by-default hook (`MastTicker.on_enter_node`), and `cosmos_dev/coverage.py`
already uses it and already maps `node → (file, line)`. Coverage *is* a
breakpoint engine that can't block. A debugger is coverage that can block.

Consequences:

- **The shipped `.sbslib` needs no new code.** We reuse an existing inert seam.
- Everything else lives in `cosmos_dev/` (dev-only, never packaged) and `sbs_cli`
  — exactly where the linter/LSP tooling already lives.
- The MAST runtime model maps almost 1:1 onto the Debug Adapter Protocol (DAP).
- Design is **mock-first**: hard breakpoint/stepping is only safely possible
  against the `cosmos_dev` mock runner, not the live engine.

---

## 1. The "no impact on non-debug runs" guarantee

The only production-shipped touch point is a seam that **already exists**:

```python
# sbs_utils/mast/mastscheduler.py:436  (inside MastTicker.next())
if MastTicker.on_enter_node is not None:
    try:
        MastTicker.on_enter_node(self.active_label, cmd)
    except Exception:
        pass
```

- `MastTicker.on_enter_node` defaults to `None` (mastscheduler.py:106).
- Production cost = **one `is not None` branch per node entry**. Already present,
  already paid for by coverage. No new shipped code.
- Same "no-op when absent" pattern as `signal_emit()` returning early when
  `FrameContext.mast is None` (CLAUDE.md:113).
- All debugger logic (breakpoint index, blocking, stepping, scopes, transport,
  DAP translation) lives in `cosmos_dev/` and `sbs_cli` — **not** in the `.sbslib`.

**Invariant to protect:** the debugger must never require a change to the
shipped scheduler's hot path beyond the seam that is already there. If a future
need forces a shipped-code change, it must remain `None`/no-op-guarded.

---

## 2. Runtime → DAP mapping

The MAST runtime maps cleanly onto DAP, which is what makes this tractable.

| DAP concept          | MAST runtime reality                                   | Reference |
|----------------------|--------------------------------------------------------|-----------|
| Thread               | `MastAsyncTask` (each task + each sub-task)            | mastscheduler.py:684 |
| Stack frames         | `task.label_stack` (list of `PushData`) + active node | mastscheduler.py:50 / :707 |
| Frame source loc     | `cmd.file_num`, `cmd.line_num`, `cmd.loc`             | mast_node.py:14 |
| Scopes               | Frame / Task / Shared / Global (see §4)               | Scope enum, mast_node.py:136 |
| Variables            | `MastAsyncTask.get_symbols()`; classify via `get_value()` | mastscheduler.py:865 |
| Breakpoint hit       | `on_enter_node`, dedup by `(file_num, line_num)`      | mastscheduler.py:436 |
| Step in/over/out     | compare `len(label_stack)` at step vs. next entry     | — |
| Pause / Continue     | block/unblock the tick thread inside the hook          | mission_runner.py:682 |

Key accessors already present:
- `MastTicker.get_active_node()` (mastscheduler.py:383)
- `MastAsyncTask.get_active_node()` / `get_active_node_source_map()` (:850 / :853)
- `MastAsyncTask.get_symbols()` (:865) and `get_value()` → `(value, Scope)`

---

## 3. Architecture (layers)

```
VS Code (DAP client, breakpoints UI)
        │  Debug Adapter Protocol
        ▼
sbs_cli:  `sbs dap`  ── stdio DAP server (mirrors `sbs lint --lsp`)
        │
        │  in-process OR WebSocket /ws/debug (sessionPort 8765)
        ▼
cosmos_dev:  MastDebugCore  ←→  mission_runner tick loop
        │        ▲
        │        │ single-slot hook, multiplexed
        ▼        │
sbs_utils (shipped):  MastTicker.on_enter_node  (inert unless attached)
```

Responsibilities:

- **`sbs_utils` (shipped, unchanged):** exposes `on_enter_node`. Nothing else.
- **`cosmos_dev/MastDebugCore` (new, dev-only):** breakpoint index, the blocking
  hook, step-depth logic, scopes/variables provider, hook multiplexer (shares
  `on_enter_node` with coverage). Owns "pause the tick thread" mechanics.
- **`sbs_cli` (new `dap` subcommand):** DAP stdio server; reuses the existing
  lib-bootstrap helpers. Two front-ends: *launch* (spawn a mock run) and
  *attach* (connect to a running `sbs debug` session).
- **VS Code extension (extend):** add `debuggers` + `breakpoints` contribution
  points and a `DebugAdapterDescriptorFactory`. Reuse existing Cosmos-root
  detection + `sessionPort`.

---

## 4. Variable scopes (DAP `scopes`/`variables`)

Return separated scopes (do **not** just dump the merged `get_symbols()` dict):

| Scope   | Storage                                   | Reference |
|---------|-------------------------------------------|-----------|
| Frame   | `task.label_stack[-1].data` (PushData.data) | mastscheduler.py:928 |
| Task    | `task.inventory.collections`              | agent.py:142 |
| Shared  | `Agent.SHARED.inventory.collections`      | agent.py:136 |
| Global  | `MastGlobals.globals`                     | mast_globals.py |
| Client/Assigned | resolved via `StoryScheduler.get_value/set_value` | maststoryscheduler.py:80 |

- Merged view for a quick "locals" panel: `get_symbols()`.
- Per-name scope classification for display: `get_value(name)` → `(value, Scope)`.
- Values are arbitrary Python objects → present via `repr`; support expandable
  `variablesReference` for dicts / objects / `Agent`s.
- **Set variable / watch / eval:** reuse the interpreter's own path
  `eval(expr, globals, symbols)` (mastscheduler.py:1020/1042/1062). Powerful but
  side-effect-capable — gate behind an explicit "allow eval side effects" flag.

---

## 5. Breakpoints & stepping

### Breakpoint resolution
Build a post-compile index: `(filename → file_num → node)` by walking
`mast.labels[*].cmds` collecting `(file_num, line_num) → cmd`. Filename→file_num
via `Mast.source_map_files` / `Mast.get_source_file_name` (mast.py:237 / :371).

- Line with no node → bind to the next node on/after that line; report the
  adjusted line back to VS Code (DAP `breakpoint.line`).
- Rebuild the index on every (re)compile; rebind on file change.

### Hit test
In the hook: `if (cmd.file_num, cmd.line_num) in active_breakpoints:` → pause.
Dedup line granularity by the `(file_num, line_num)` tuple (a source line
compiles to several nodes; break only when the tuple changes) — coverage already
keys on exactly this tuple.

### Stepping (from `label_stack` depth)
Record `depth = len(task.label_stack)` and the current `(file,line)` when the
step is issued, then on each `on_enter_node`:
- **Step In:** break at the very next entry.
- **Step Over:** break at next entry with `depth' <= depth` **and** changed `(file,line)`.
- **Step Out:** break when `depth' < depth`.

### Conditional breakpoints / logpoints
Evaluate the condition/message in the hook via the interpreter `eval` path.
Nearly free; add in phase 5.

---

## 6. The pause model (why mock-first)

DAP is async request/response; the runner is a synchronous `while True` tick loop
(mission_runner.py:682). Standard in-process debugger pattern:

- When the hook hits a breakpoint, it **blocks the tick thread** on an
  event/queue and waits for `continue`/`step`.
- The transport thread keeps servicing `stackTrace`/`scopes`/`variables`.
  Reading `label_stack`/`get_symbols()` from the transport side is safe **because**
  the only mutator (the tick thread) is frozen at a clean node boundary.
- On resume, hand control back to the tick thread.

**Mock-first rationale:**
- The mock is dev-only and already spawns threads (physics daemon, asyncio
  WebSocket server in a child process) — blocking the MAST tick thread is fine.
- The real engine drives MAST from its event-handler thread; blocking it would
  freeze netcode/render. Real-engine debugging is therefore limited to *soft*
  pause (stop scheduling MAST advances) or trace/replay — never hard-block
  stepping.

**Physics coherence:** the mock's physics runs on its own ~30 Hz daemon thread.
At a hard breakpoint, also hold physics + call `sbs.pause_sim()` so the world
isn't drifting under a frozen MAST snapshot.

---

## 7. Transport — reuse the existing substrate

`cosmos_dev` already runs a stdlib WebSocket server with a `/ws/debug` channel
and an HTTP `POST /debug/command` side-door, dispatched per-tick through
`_handle_debug_command` (mission_runner.py:606) with `pause/resume/restart/
signal/status`, replying via `_debug_reply` / `_debug_status`. The VS Code
extension already POSTs to that endpoint (`postDebugCommand`, `sessionPort` 8765).

Two front-ends, one adapter:

- **Launch mode:** VS Code spawns `sbs dap` (stdio DAP), which starts an
  in-process mock run and drives `MastDebugCore`. Mirrors how `sbs lint --lsp`
  hands stdio to `amd_lsp.serve()`. Most idiomatic for
  `DebugAdapterDescriptorFactory`.
- **Attach mode:** connect to an already-flying `sbs debug` session on
  `sessionPort`; extend `_handle_debug_command` with DAP verbs over the existing
  `/ws/debug`. Killer feature: fly in the browser, set breakpoints in VS Code,
  hit them live. The extension's `postDebugCommand`/sessionPort is ~80% of the
  client already.

---

## 8. Complementary: record & replay (time-travel)

Because coverage already records execution, a **trace-and-scrub** mode is nearly
free and has **zero live-attach risk**:

- Dump a node-by-node trace + periodic variable snapshots to a file.
- Scrub it offline in VS Code (a read-only "replay" debug session).
- Ideal for `overnight`/soak failures you can't attach to live.

Reuses the coverage machinery verbatim; good low-risk first deliverable.

---

## 9. Reuse map (what already exists)

| Need | Existing asset | Reference |
|------|----------------|-----------|
| Per-node execution hook | `MastTicker.on_enter_node` | mastscheduler.py:106 / :436 |
| node → (file, line) mapping | `cosmos_dev/coverage.py` | coverage.py:49-64 |
| Call stack | `task.label_stack` of `PushData` | mastscheduler.py:50 / :707 |
| Variables | `get_symbols()` / `get_value()` | mastscheduler.py:865 |
| Eval/watch path | interpreter `eval(expr, globals, symbols)` | mastscheduler.py:1020 |
| Debug command dispatch | `_handle_debug_command` + `_debug_reply/_debug_status` | mission_runner.py:606 / :572 |
| WebSocket transport | stdlib WS server, `/ws/debug`, `POST /debug/command` | mockgui/server.py |
| stdio protocol server pattern | `amd_lsp.serve()` launched by `sbs lint --lsp` | amd_lsp.py / lint_cmd.py:175 |
| Diagnostic/emit model to mirror | `AmdFinding` (text/compact/json) | amd_lint.py:44 |
| Lib bootstrap under embedded Python | `_prefer_working_tree_sbs_utils`, `_BOOT`/`COSMOS_DEV_LIBS` | lint_cmd.py:12 / debug_cmd.py:44 |
| VS Code transport client scaffolding | `postDebugCommand`, `amd.sessionPort` | extension.ts:881 / package.json |

---

## 10. Known sharp edges

1. **Single-slot hook.** Coverage and the debugger both want `on_enter_node`.
   Introduce a small multiplexer (a callback list) in `cosmos_dev` — both
   consumers are already dev-only, so this never touches shipped code. Must
   chain/restore prior hook (coverage already saves `_prev`, coverage.py:50).
2. **PyTicker / PyMAST** generator labels (mastscheduler.py:449) never fire
   `on_enter_node` — that's really Python. Defer to `debugpy` or mark opaque in v1.
3. **Long-polling nodes** (await/delay spinning across ticks): `on_enter_node`
   only fires on *entry*. Breaking *inside* a stuck poll needs an extra tap at the
   `poll()` call site (mastscheduler.py:319). Phase 6.
4. **Real-engine debugging** only supports soft-pause / trace-replay (via the
   `webproxy` dev-queue bridge) — never hard-block stepping.
5. **Eval side effects.** The eval/watch path can mutate game state. Gate behind
   an explicit opt-in.
6. **Breakpoints set before compile / hot edits.** Rebuild + rebind index on
   (re)compile.
7. **Thread-safety on resume.** While paused, the tick thread is frozen (safe to
   read). Synchronize the handoff on resume so the transport thread stops touching
   task state before the tick thread runs again.

---

## 11. Phasing

| Phase | Deliverable | Risk | VS Code needed? |
|-------|-------------|------|-----------------|
| 0 | ✅ **DONE** — `MastDebugCore`: breakpoint index + blocking hook + coverage chaining, proven by 3 **unit tests against the mock** (`test_mast_debug.py`) | low | no |
| 1 | Trace / replay mode off coverage (time-travel scrub) | low | read-only replay |
| 2 | ✅ **DONE** — `MastDapAdapter` + `run_stdio` + file-runner launch mode (`test_mast_dap.py`), `sbs dap` CLI command (verified over real stdio), **and** the VS Code `mast` language + `breakpoints` + `debuggers` contribution + `DebugAdapterDescriptorFactory` (compiles clean). | med | ✅ done |
| 3 | ✅ **Logic done** — step in/over/out depth predicate implemented + unit-tested; step-over proven via integration | med | — |
| 4 | ✅ **DONE (headless)** — attach mode: `MastDapAdapter` attach path + `serve_dap_socket` (DAP over TCP) + `live_mission_provider`, wired to `mission_runner --dap-port` (inert by default). Tested over a real loopback socket against a live loop (`test_mast_dap.py`). **Needs live browser+VS Code verification.** | med | — |
| 5 | ✅ **DONE** — conditional breakpoints, hit conditions, logpoints, and setVariable, wired through the adapter (capabilities + `output`/`setVariable`); watch/evaluate already present. Tests in `test_mast_debug.py` + `test_mast_dap.py`. | low | — |
| 6 | Long-poll stepping (poll-site tap); any real-engine bridge | high | — |

---

## 12. First slice (Phase 0) — concrete spec

Prove the mechanics with **no VS Code and no DAP**, just Python + the mock.

`cosmos_dev/mast_debug.py` (new):

```python
class MastDebugCore:
    def __init__(self):
        self.breakpoints = {}        # filename -> set(line)
        self._index = {}             # (file_num, line_num) -> node(s)
        self._paused = threading.Event()
        self._resume = queue.Queue() # 'continue' | 'step_in' | 'step_over' | 'step_out'
        self._step = None            # active step request + recorded depth

    def install(self, mast):         # build index from mast.labels; chain on_enter_node
    def _on_enter(self, label, cmd): # hit test + step test -> block on self._resume.get()
    def stack(self, task):           # label_stack -> frames
    def scopes(self, task):          # frame/task/shared/global
    def variables(self, task, scope) # via get_value/get_symbols
```

Unit test (`tests/test_mast_debug.py`, `unittest`, calls `test_set_exe_dir()`):
1. Compile a small `.mast` with a few labels + a jump + a variable.
2. `install()` the debug core; set a breakpoint on a known line.
3. Drive the mock scheduler on a background thread; assert the tick thread blocks
   at the breakpoint line (via `get_active_node()`).
4. Assert `stack()` shows the expected label frames and `variables()` shows the
   expected value.
5. Issue `step_over` / `continue`; assert the next stop line and clean completion.

Success = pause/step/inspect works deterministically on a real `.mast` through
the existing `on_enter_node` seam, with coverage still functioning alongside
(multiplexer verified).

---

## 13. Open questions

- Should launch mode run the mock **in-process** inside `sbs dap`, or spawn
  `mission_runner` and attach over WS? (In-process is simpler for stepping;
  spawn matches the existing `sbs debug` lifecycle.)
- DAP "threads" granularity: one per `MastAsyncTask` including every sub-task, or
  collapse sub-tasks into nested frames? (Sub-tasks share scope via `root_task`.)
- Trace file format for replay — reuse coverage's tuple keying, or a richer
  per-step record with variable deltas?
- Do we want a `--dap`/`--debug-adapter` flag on the existing `debug` command
  instead of a separate `dap` subcommand?
