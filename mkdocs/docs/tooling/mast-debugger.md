# Debugging MAST

The **MAST source debugger** lets you set breakpoints, step, and inspect variables
**in your `.mast` files** — from inside VS Code — while a mission runs under the
`cosmos_dev` mock. It speaks the standard **Debug Adapter Protocol (DAP)**, so it
plugs into the normal VS Code debugger UI (breakpoint gutter, call stack, variables,
watch).

!!! note "Two different debuggers"
    This is a **MAST-level** debugger — breakpoints on `.mast` lines, MAST variables,
    the MAST call stack. It is **not** the Python/`debugpy` setup in
    [Contributing &rsaquo; Debugging](../home/contributing/debugging.md), which steps
    through the *Python* runner and library. Use this one to debug **mission logic**;
    use `debugpy` to debug **`sbs_utils` / the runner itself**.

## What you get

- **Breakpoints** on `.mast` lines (a breakpoint on a blank/comment line binds to the
  next real statement).
- **Conditional & hit-count breakpoints** — right-click a breakpoint → *Edit
  Breakpoint*. Condition is any MAST/Python expression (e.g. `hp < 20`); hit count
  accepts `N`, `==N`, `>N`, `>=N`, `%N` (every Nth).
- **Logpoints** — a breakpoint with a `{expr}` message that **logs and keeps running**
  instead of stopping (great for a busy route you don't want to pause).
- **Stepping** — step over / step in / step out, at source-line granularity.
- **Call stack** — the current label plus caller frames (from `call`/inline blocks).
- **Variables** grouped by scope: **Frame**, **Task**, **Shared**, **Global** — and you
  can **edit a value** in place while paused.
- **Watch / evaluate** — expressions run in the paused task's scope.
- **Step into Python** — *Step In* on a MAST line that calls Python (`~~ … ~~`, a
  function call, a condition) descends into that Python function: real `.py`
  source, a merged MAST+Python call stack, and the frame's **Locals**. See the
  setup below.

### Step into Python — setup

Two requirements, because `sys.settrace` is one-per-thread and debugpy owns it:

1. **Run the mission *plain* (not under debugpy).** The **"MAST: Debug mission
   (one click)"** config does this for you — the extension runs `sbs debug` (via
   `sbs.pyz`, which is plain), so Step-into-Python is on. (If you instead run the
   mission under a `debugpy` launch, the feature auto-disables — you'll see
   `[mast] step-into … disabled … under debugpy` — and you use debugpy for the
   Python half.)
2. Optionally **load `sbs_utils` from source** (`"useWorkingTree": true` on the
   config, or `sbs debug --use-working-tree`), so Python frames point at real
   *editable* files. Not required just to *see* the source: the debugger extracts
   source straight from a `.sbslib`/`.mastlib` zip and serves it (read-only) via
   the DAP `source` request — so Step In shows the library source either way. Use
   the working tree only when you want to **edit** the library live.

Step In on a line like `x = terrain_to_value(SEL)` then opens
`procedural/terrain.py` with the arrow on the line and Locals populated. The Debug
Console tells you which mode you're in: `[mast] step-into: tracing this eval …`
(working) vs `… skipped: a tracer is already active (…pydevd…)` (under debugpy).

!!! note "Stops just before a line runs"
    A breakpoint parks execution when a line is *entered* — its assignment/effect hasn't
    run yet, so you see the pre-line state (e.g. breaking on `x = 2` shows the old `x`).
    One subtlety: a function call evaluates its arguments on entry, so editing a variable
    changes **later** lines, not the already-entered call on the current line.

## Requirements

- The **Artemis AMD** VS Code extension — it contributes the `mast` debug type and
  connects `.mast` breakpoints to the adapter. **VS Code needs it to debug MAST.**
- A Cosmos install with `data/missions/sbs.pyz` (the extension auto-detects it by
  walking up from the open file, same as the language server).

!!! info "The adapter itself doesn't need the extension"
    `sbs dap` (stdio) and `--dap-port` (socket) are a plain **DAP server** — any
    DAP-speaking client can drive them. The extension is only what makes the
    **VS Code UI** (breakpoint gutter, `type: mast` configs, step buttons) speak to it.

---

## Launch mode — debug one `.mast`

Runs a `.mast` under the mock and stops at your breakpoints. Best for **library / logic
`.mast`** you can run start-to-finish.

### From VS Code

Open a `.mast`, set a breakpoint, press **F5**. With no `launch.json` the extension
debugs the open file. To save a config, add to `.vscode/launch.json`:

```json
{
  "type": "mast",
  "request": "launch",
  "name": "Debug MAST",
  "program": "${file}"
}
```

Under the hood VS Code launches `sbs dap <mission>` and drives it over stdio.

### From the CLI

```sh
sbs dap <mission_path> --mast logic.mast
```

`sbs dap` speaks DAP on **stdin/stdout** (diagnostics go to stderr). You normally let
VS Code start it, but it can be driven by any DAP client.

!!! warning "Launch mode targets logic `.mast`"
    Launch mode compiles and runs the file under a plain scheduler. Full
    **StoryScheduler missions** (comms/GUI/maps/story lifecycle) don't run to
    completion this way — debug those with **attach mode** below.

---

## Debug a live mission

Debug a mission **while it plays** (browser GUI and all): set breakpoints, hit them in
real time, step, inspect. This is the mode for full StoryScheduler missions.

### One click (recommended)

LegendaryMissions and LM_TestRange ship a **"MAST: Debug mission (one click)"** config
(`type: mast`, `request: launch`, with a `mission`). Pick it in the Run and Debug
dropdown and press play: the extension launches the mission (`sbs debug --dap-port
--dap-wait`), waits for it, attaches, and **stops the runner when you end the session** —
no task, no terminal, no process cleanup. `--dap-wait` holds the map's auto-start until
you're attached, so a breakpoint that runs at map start isn't missed.

### Manual (attach to a mission you started)

You can also start the mission yourself and attach:

```sh
sbs debug . --gui --dap-port 4711 --dap-wait
```

The runner prints `[runner] MAST debug adapter LISTENING on 127.0.0.1:4711`, then holds
for the debugger. Attach with a `mast` config:

```sh
sbs debug . --gui --dap-port 4711 --dap-wait
```

The runner prints `[runner] MAST debug adapter (attach) on 127.0.0.1:4711`, then holds
for the debugger. Attach with a `mast` config:

```json
{ "type": "mast", "request": "attach", "name": "Attach to MAST", "host": "127.0.0.1", "port": 4711 }
```

`--dap-port` is **opt-in** — without it the runner behaves exactly as before.
`--dap-wait` is optional but recommended when a breakpoint runs during map start.

### Play and break

Set a breakpoint in a `.mast` (e.g. a `//comms` route body), then trigger it in the
browser. Execution stops on that line; inspect the call stack and variables, step, then
**Continue**. **Disconnect** detaches without ending the mission.

!!! warning "Timing: a breakpoint only hits code that runs *while attached*"
    If auto-start (or `--map 0`) runs a map immediately and you attach a moment later,
    the map's start-up code has already executed — so a breakpoint there won't fire until
    that code runs again. **`--dap-wait` fixes this** by holding auto-start until you've
    attached. Map files (e.g. `maps/siege.mast`) compile lazily when the map starts; the
    adapter re-scans and arms them automatically — watch the Debug Console for
    `[mast] newly indexed: …` and the initial `[mast] N source file(s) indexed` list.

!!! note "Attach is verified against a live mission"
    Attach has been exercised end-to-end — attach to a running LegendaryMissions,
    break in a lazily-loaded map file (`maps/siege.mast`), view the source, and inspect
    the stack + variables. Still young, so report anything that misbehaves.

!!! note "The sim keeps moving while paused"
    A breakpoint parks the MAST tick loop, but the mock's **physics runs on its own
    thread** — ships keep drifting while you're stopped. MAST state is frozen and safe to
    inspect; the world is not.

---

## How it works

Every MAST node passes through one choke point on entry (`MastTicker.next()`), which
fires an optional, **`None`-by-default** hook (`MastTicker.on_enter_node`). The debugger
installs that hook to test breakpoints and **park the tick thread** when one matches;
control commands (continue/step) arrive on a **separate** thread (stdio or socket) and
release it.

Because the hook is inert unless a debugger attaches, there is **zero cost to normal
runs** and **no change to the shipped `.sbslib`** — all the debugger code lives in
`cosmos_dev` and the extension. It's the same seam
[MAST coverage](testing.md#headless-conformance-run) already uses.

## Status & limitations

| Area | State |
|---|---|
| Breakpoints (incl. conditional / hit-count / logpoints), step over/in/out, stack, variables, set-variable, watch | Working (launch + attach) |
| Launch mode | Logic `.mast` only (not full StoryScheduler missions) |
| Attach mode | Working — verified live against a running mission |
| Physics while paused | Not frozen (separate thread) |
| Step into Python MAST evals | Working (plain runner only; auto-off under debugpy) |
| PyMAST (`@label` Python generators) | Not debuggable (that's Python — use `debugpy`) |
| Breaking *inside* a long `await`/`delay` poll | Not yet (stops on node entry, not re-poll) |

See also: [Testing missions](testing.md) · [sbs CLI](cli.md) ·
[Contributing &rsaquo; Debugging](../home/contributing/debugging.md).
