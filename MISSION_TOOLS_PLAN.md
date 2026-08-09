# Mission Authoring Tools — VS Code Plan

> **Status: ACTIVE (2026-08-09).** Mostly built. What remains is the **GUI Editor**
> (G0 pixel canvas, G2 live preview over the socket, G3 capture-and-tweak, G4 undo/redo)
> and the Mission Inspector's live click-test. Section 4.4 is the live queue; sections 0-3
> are now a status log rather than a proposal.
>
> Shipped since this was written: `cosmos_dev/mast_inspect.py` carries the InspectionBus and
> the Signal / World / Gui / Brain / Quest taps, and the VS Code extension registers
> `showMissionInspector`, `showResolver`, `showStoryOutline`, `showTimeline`, `showGraph`,
> `showMissing`, `guiEditor`, `showMap` and `showPreview`. The layout containers of section
> 3.7 all exist (`pages/layout/grid.py`, `group.py`, `repeater.py`).

Follows the pattern that worked for the MAST debugger (`MAST_DEBUGGER_PLAN.md`): tap an
existing seam, stream to a VS Code panel, keep zero cost on non-debug runs.

---

## 0. The platform you already have

Building the debugger produced a reusable substrate. Every tool below leans on it:

- **A live socket into a running mission** — `serve_dap_socket` (dev-only), plus the
  attach flow (`live_mission_provider`) and the self-cleaning runner.
- **Inert, `None`-guarded seams** every mission already passes through: `on_enter_node`
  (every MAST line). Add a few more in the same style (all inert in production):
  `signal_emit`, the brain tick, `send_gui_*`, an agent snapshot.
- **A webview host in the extension** (map preview / graph / inspector already exist).
- **Source mapping**, incl. reading source out of `.sbslib`/`.mastlib` zips.

So the marginal cost of each new tool is small: **tap a seam → push typed events →
render a panel.**

## 1. Two families of tool

- **Live inspectors** — *read* a running mission and show it. Signal Tracer, World
  Inspector, GUI DevTools, Brain Watcher, AMD Live Resolver.
- **Authoring tools** — *generate/edit* MAST. The GUI Editor.

They share the transport but differ in one key way: **inspectors must stream while the
mission runs, without pausing it.** So they ride an *inspection channel* that is
independent of breakpoints (attaching an inspector must never park the tick loop).

---

## 2. Shared building blocks (build these once)

### 2.1 The Inspection channel
A continuous, typed event stream from runner → editor, independent of the debugger's
pause. Two viable shapes:

- **Custom events on the existing debug socket** (DAP allows custom events). The runner
  taps seams and pushes `mast/signal`, `mast/agents`, `mast/widgets`, `mast/brains`;
  the extension routes them to panels. One connection, many lenses.
- **A dedicated inspection WebSocket** (like `mockgui/server.py`) if we want inspectors
  to work with **no debugger attached at all**.

Recommendation: start with **custom events on the debug socket** (reuse everything), and
split out a dedicated channel only if "inspect without debugging" becomes a real need.

Define a tiny **inspection protocol**: `{kind, seq, t, payload}` where `kind` is
`signal|agents|widgets|brains|amd`. Each seam emits one kind. The extension has one
subscriber per panel.

### 2.2 The seam taps (all inert unless a tool is listening)
Taps are installed by **monkeypatching a reference-stable method** from cosmos_dev
(the python-step technique), so there's **no shipped-library change**. Prefer a
*method* over a module function — module functions get cached into MAST globals and
won't see a patch; class methods resolve via the class at call time. Each tap only
publishes when a sink is subscribed (inert otherwise).

| Tap | Reference-stable point | Feeds |
|---|---|---|
| signal | `Mast.signal_emit(self, name, sender_task, data)` (mast.py — knows matched routes) | Signal Tracer |
| gui | the `send_gui_*` path (already flows to mockgui) | GUI DevTools |
| brain | brain tick / `on_enter_node` for brain tasks | Brain Watcher |
| agents | poll `Agent.all` on a timer | World Inspector |

### 2.3 The widget-render module (for GUI DevTools + GUI Editor)
`mockgui/client.html` already draws every widget (`button`, `checkbox`, `dropdown`,
`icon`, `image`, `face`, `3dship`, `radar`, `text`, `list`, …). Factor its per-widget
drawing into a **reusable module** both the mock browser and the two GUI tools import, so
a widget looks identical whether it's live, inspected, or being designed.

---

## 3. Live inspectors

Each: **Problem → Panel → Seam → Effort.**

### 3.1 Signal Tracer  ·  effort: **low** (do first)
- **Problem:** signals are the mission's nervous system and completely invisible.
- **Panel:** a scrolling log — `t · signal_emit(name, data) → routes fired [file:line…]`.
  Filter by name; click a row → jump to emitter or route. Later: an emitter→signal→route
  graph (living event-flow docs).
- **Seam:** `signal_emit` — one function, one tap. Pairs with the existing `signal_lint`.

### 3.2 World Inspector  ·  effort: **low-med**
- **Problem:** "why isn't this ship targeted / hailable / counted as an enemy?" Object
  state (side, roles, links, HP) is opaque — and **diplomacy** made "is this an enemy?" a
  relationship, not a label.
- **Panel:** live table/tree of agents (ship/station/monster) — side, roles, HP, position,
  links, and the **diplomacy verdict** ("enemy of players? via side X at war with Y").
  Filter by side/role; click for full inventory; the live twin of the static map preview.
- **Seam:** poll `Agent.all` on a timer → snapshot → stream.

### 3.3 GUI DevTools  ·  effort: **med**
- **Problem:** layout is trial-and-error (overflow, overlap, the "60% width" class of bug).
- **Panel:** browser-devtools for a live console — the **widget tree** (tag, rect, style,
  parent); hover a node → highlight in the mock browser and vice-versa; overflow/overlap
  flagged inline (reuse `cosmos_dev/layout_audit`).
- **Seam:** the `send_gui_*` stream already goes to the mock; fan it to the editor too.
- **Note:** shares the widget-render module (§2.3) with the GUI Editor.

### 3.4 Brain Watcher  ·  effort: **med**
- **Problem:** NPC AI is a black box.
- **Panel:** a **Brains** view (sibling to Call Stack). Pick an NPC → active behavior,
  target link, blackboard (throttle/steer/weapon); for behavior-tree brains, the **tree
  with the active branch lit** (which `bt_seq`/`bt_sel` child is running / succeeded /
  failed).
- **Seam:** brains are MAST tasks → already hit `on_enter_node`; tap the brain tick to
  snapshot `{npc → active node, blackboard}`.
- **Honest unknown:** cleanly identifying the *active BT node* at runtime. Fallback:
  behavior + blackboard without the tree highlight — still a big win.

### 3.5 AMD Live Resolver ("AMD debugger")  ·  effort: **med-high**
- **Problem:** AMD fails **silently** — a typo'd heading drops a whole quest; a dangling
  `Then: reveal`/`reach`/`signal` goes nowhere with no error.
- **Panel:** two panes. Left: `.amd` source. Right: the **resolved model** (quest tree,
  lifeform badges, dialogue graph, scans) as the engine built it, each entity linking to
  its source line. **Red-flags** headings that resolved to nothing and references that
  point at nothing. Attached, it also shows **live state** (which quests are active, which
  dialogue fired) and a **"why didn't this show?"** trace.
- **Seam:** `amd_core.parse` (static, already exists, with source spans) cross-referenced
  against live mission state over the socket. The static half is lint-you-already-have;
  the live half is a new tap.
- **STATUS — static half DONE.** New LSP request **`amd/resolve`** (`amd_lsp.py`
  `_mission_resolve`): serializes the whole `amd_core` model — every heading as an
  **entity** (key/display/section/**archetype**/span/summary/fields + inbound/outbound
  reference counts + an **`orphan`** flag) and every **reference** with a `resolved`
  bool and any dangling lint code, plus the mission-wide **`issues`** list (structural
  + cross-file lint). It's a serialization pass over the existing model + `amd_lint`
  output — no new resolution logic. Command **`amd.showResolver`** ("AMD Resolver"):
  two panes — left, the **resolved entity tree** grouped by archetype with error/warn/
  **orphan** badges, each row jumping to source and expandable to show its refs marked
  **✓ resolved / ✗ dangling**; right, the **red-flags** list (dangling refs + orphan
  headings + structural/cross-file issues), severity-sorted, each jumping to source.
  Auto-refreshes on `.amd` edits. Tested (`test_amd_lsp.py::test_mission_resolve`; 38
  LSP tests green). **The live half** (attach → active quests / fired dialogue / "why
  didn't this show?" trace) remains — needs the socket tap.

### 3.5.1 Improved Story Graph  ·  effort: **med**
- **Problem:** the current `amd.showGraph` is a free node-link diagram. It reads fine at
  ~20 elements and becomes a **hairball** past that — edges cross, nodes overlap, and you
  can't find anything. The force layout fights the author instead of helping.
- **Root cause:** we made *"see the whole graph at once"* the primary interaction. That
  doesn't scale — no auto-layout keeps a large story readable, and a writer rarely needs
  the whole thing; they need *"what connects to the node I'm looking at."*
- **Strategy — navigate, don't render-it-all (their instinct is right):** make a
  **master list/tree + focus view** the default, and demote the full diagram to an
  optional overview. This is code-navigation applied to the story (outline +
  go-to-definition / find-references), and it stays readable at any element count because
  we never draw the whole graph.
  - **Left — outline tree**, grouped `file → label/scene/quest`, **searchable** and
    **filterable by kind** (scenes / quests / signals / labels). This replaces "scan the
    hairball" with "type a name."
  - **Right — focus view** for the selected element: its **direct connections only**,
    split **incoming** vs **outgoing** — what it reveals / jumps-to / signals, and what
    reveals / jumps-to / signals *it*. Each connection is a chip that **re-focuses** on
    click (walk the graph one hop at a time) and has a **↪ open source** link (we already
    have source spans). A tiny **local mini-graph** (selected node + 1 hop) gives shape
    without the spaghetti.
  - **Overview (optional)** — keep the full diagram, but add **filter-by-kind**,
    **search-to-highlight**, and **click-to-focus** (selecting in the diagram drives the
    same focus view). Consider a **hierarchical (layered) layout** and **collapse-by-group**
    so the overview degrades gracefully instead of into a hairball.
- **Why this over "just a better layout":** Sugiyama/edge-bundling reduces crossings but is
  still one big picture that overwhelms at scale. The list/tree+focus scales to *any* count
  because the visible element budget is bounded by the selection, not the story size.
- **Reuses what exists:** same resolved model as **3.5 AMD Live Resolver** (this is the
  navigable *view* of that model) and the source-span links from lint. Build the model
  extraction once; the Resolver and the Story Graph are two panels over it.
- **Phasing:** (a) list/tree + focus view with in/out connection chips + open-source
  (ships the scalability win alone); (b) local mini-graph; (c) retrofit the existing full
  diagram with filter/search/click-to-focus.
- **STATUS — phase (a) DONE.** Command **`amd.showStoryOutline`** ("Show Story Outline
  (scalable)"): a searchable, section-filterable outline (left) + focus detail (right)
  showing the selected node's **Leads to** / **Reached from** connections as clickable
  chips (re-focus in place) with **↪ src** and **Open source / Edit** buttons. Reuses the
  existing `amd/graph` model + `openLocation`/`showInspector` — pure client-side view, the
  diagram (`amd.showGraph`) is untouched, no live tap needed. Auto-refreshes on `.amd`
  edits.
- **STATUS — phases (b) + (c) DONE.** (b) The Story Outline detail pane draws a
  **1-hop mini-graph** (selected node centered, incoming left / outgoing right,
  edge kinds labelled, neighbours click-to-refocus). (c) The full diagram
  (`amd.showGraph`) gained a **toolbar search box** — filter/spotlight nodes by
  name or key (dims the rest + their edges), match count, Enter/Shift+Enter to
  cycle+center matches, Esc to clear — alongside its existing hover-spotlight,
  section filters, and right-click Focus. **§3.5.1 is now fully shipped.**

### 3.5.2 AMD Story Timeline  ·  effort: **med** (static) / **med-high** (recorded)
- **Problem:** the suite has three lenses on a mission — **list** (Outline), **topology**
  (Graph), **space** (Map) — and none on **time**. A writer can see *what connects to
  what* but not *when it happens, in what order, or whether anything is happening at all
  during minute 14*. Pacing bugs (dead air, reveal-cascade pileups, a console with nothing
  to do for half the mission, authored content a real run never reaches) are invisible in
  every existing view.
- **The honest constraint — AMD has no clock.** Nothing in the vocabulary is a timestamp,
  so the view must be explicit about **three different time axes** and never silently blend
  them:

  | Axis | Source | Drawn as |
  |---|---|---|
  | **Beat time** (planned) | causal order: `Parent:` / `Then: reveal` / `Scene:` / choice edges, plus signal edges (below) | uniform-width bars, ranked in beats — act structure, *not* seconds |
  | **Declared time** | `Fail after:` (the only real duration in the language) | a deadline gutter *over* the beat, not the bar itself |
  | **Actual time** (recorded) | a real playthrough streamed from a session | a true Gantt — the only axis where bar width means seconds |

  Drawing a Gantt off the static file alone would be a lie: most nodes have no knowable
  duration (a fetch quest lasts however long the player takes). Beat time is the default
  and is always available; real widths appear only where declared or recorded.
- **Panel:** the **Outline's** shape, third lens. Left rail = lanes/node list (searchable,
  section-filterable); centre = the time canvas; right = the **same `amd/schema`-driven
  inline inspector form** the Outline already uses. Shared selection, the standard tool
  top-bar, live refresh on edit.
  - **Lanes are where the insight is** — one selector, four questions: **by section**
    (matches the Graph's swimlanes; the familiar default) · **by arc** (`Parent:` chain —
    "does act 3 have a middle, or does it jump from hook to payoff?") · **by side** ("the
    Ashfang are absent for the whole second act") · **by console** (`Accept on:` /
    `Engage on:` / scan `Tab:`) = **crew workload over time**, which nothing else in the
    toolchain can show and which on its own probably justifies the view.
  - **Spine vs. pool.** An idle-until-accepted job board (18 jobs, all available at t=0)
    plots as 18 bars stacked at zero — correct and useless. Split the canvas: **spine**
    (top) = the `Required:`/`Critical:` chain laid out in beats, critical path highlighted;
    **pool** (bottom) = unordered optional content as an *availability band* (when it
    becomes offerable, when it expires), not a sequence.
  - A histogram strip under the canvas (active-content count per beat) reads as the
    **pacing curve**.
- **Direct manipulation, ranked by how defensible the write-back is:**
  - **Safe:** drag a bar's right edge → rewrite `Fail after:`. A real edit of a real number.
  - **Reasonable:** drag a bar onto another lane row → rewrite `Parent:` (the Graph already
    does drag-to-add-edge for choices).
  - **Don't:** free horizontal drag — there is no field it could write. Inventing a `Beat:`
    ordering field to make the gesture work would push AMD toward a scheduling DSL; that's
    the tail wagging the dog (see the "AMD dialogue is not a language" principle).
- **Seam / plumbing:** a new LSP request **`amd/timeline`** in `amd_lsp.py`, layering done
  **server-side** (stdlib-only, ships in `sbs.pyz`, unit-testable offline exactly like
  `_mission_resolve`) so the webview stays dumb. Returns roughly
  `{lanes, beats, items:[{key, beat, lane, kind, declaredDuration, required, sources}],
  gaps, cycles}`. The recorded overlay rides the **existing** DAP `mast/inspect` channel —
  the Resolver's `QuestTap` already streams `{quest key -> state}`; recording it with
  timestamps is the whole of the live half.
- **The one real prerequisite — signal edges.** `_mission_graph` only treats
  `choice|scene|reveal|parent` as edges. Signal-mediated causality (`Then: signal X` → a
  `//signal/X` MAST route → another node's `When: signal X`) is **not an edge today**, so a
  signal-driven mission would render as disconnected confetti with everything at beat 0.
  `amd_lint` already computes half that join (`signal-no-route`, `unfired-signal`); the
  work is promoting it to a first-class edge kind — **worth doing regardless**, since it
  also improves the Graph and the Resolver's orphan detection.
- **Second-order problems** (decide, not blockers): **cycles** (A reveals B reveals A) need
  a feedback-arc pass or an explicit "cycle" badge; a node reachable by two branches has two
  beat ranks — take the earliest and label it *earliest possible*.
- **The payoff is the recorded axis.** Record the `QuestTap` stream instead of only badging
  it and every quest gets `granted → active → complete/failed` timestamps. Laid under the
  planned beats, that answers what no static view can: **dead air** (a 90-second window with
  nothing active — the most useful pacing bug there is), **pileup** (eleven jobs going active
  in ten seconds off one reveal cascade), **never fired** (reachable but not reached — a
  different failure from the Resolver's statically-unreachable *orphan*), and **drift**
  (planned beat 7 actually happened before beat 4). It composes with the headless harness:
  `--test 300` emits `timeline.json`, the extension opens it, and two runs can be
  **diffed** — story-pacing regression testing in CI, which nothing else here provides.
- **Phasing:** (a) signal edges promoted to first-class (prerequisite, standalone value);
  (b) `amd/timeline` + beat lanes by section + spine/pool split + the existing inspector
  form docked right — useful day one, pure static analysis, no tap; (c) lane-by-console /
  side / arc + the pacing histogram; (d) recorded runs (timestamped `QuestTap`), gap/pileup
  analysis, `timeline.json` from `--test`, run diff; (e) edge-drag → `Fail after:` /
  `Parent:` write-back.
- **STATUS — phases (a) + (b)/(c) DONE, server side.** The whole model lives in a new
  **`procedural/amd_timeline.py`** (stdlib-only, ships in `sbs.pyz`, unit-tests offline
  like `amd_lint`), served as **`amd/timeline`** by `amd_lsp` (`_mission_timeline`).
  - **(a) Signal edges.** `signal_edges()` joins every `Then: signal X` / choice
    `… signal X` emit to every `When:` / `Goal:` / `Fail on signal: X` wait across the
    whole document set, anchored at the emit site. `amd/graph` now returns them as
    `kind: "signal"` edges and `amd/resolve` counts them toward inbound/outbound — so a
    node a signal turns on stops reporting as an **orphan** (it was a false positive).
    Self-edges (emit + wait on one name = a deliberate repeatable loop) are dropped.
  - **`Goal: signal [N] NAME` is now a reference** (`amd_core`, kind `wait_signal`) —
    it wasn't one at all before, which is why every idle-until-accepted job on the
    Peacetime board read as an orphan. The count is stripped exactly as
    `amd_quest.amd_trigger` strips it. The linter checks it like `When: signal`, so an
    unfinishable job (goal signal nothing emits) is now a warning.
  - **Linter emit-scanner gap found + fixed.** `quest_credit_signal(ship, "x")` /
    `quest_on_signal("x")` advance a quest DIRECTLY without ever calling `signal_emit`,
    so the cross-file check read peacetime's owner-scoped jobs as "nothing emits this".
    Both are now recognized emitters. Verified against LegendaryMissions / StormsBeacon /
    OpenUniverse / LM_TestRange / overlay_demo: **no new findings vs. the baseline.**
  - **(b)/(c) The model.** `timeline()` returns `{items, beats, lanes, edges, cycles}`:
    longest-path **beat** rank over the causal graph (`Parent:` reversed into causal
    order), DFS **cycle** detection so a dialogue hub can't hang the ranking (reported
    per-item as a badge), the **spine/pool** split, `declared` durations parsed exactly
    as the engine parses `Fail after:`/`Complete after:`, and all four **lane** modes
    (section / arc / side / console) precomputed. Single-record arcs collapse to their
    section so a job board isn't a dozen lanes of one; scan `Tab:` values are
    deliberately *not* consoles.
  - **Also found: flat `.amd` files were invisible.** A per-section file handed straight
    to a loader (`jobs.amd`, `bridge_stories.amd`) has no `#` root or `##` group — its
    records are the `#` headings, which the shared `level <= 2` filter drops. The
    timeline detects the file shape and reads them (OU's 12 jobs went from 0 items to
    12). **`amd/graph` and `amd/resolve` still have this blind spot** — a contained
    follow-up, deliberately not folded in here so three shipped panels don't change
    behaviour in the same pass.
  - Tests: `tests/test_amd_timeline.py` (23 cases) + `amd/timeline`, graph signal-edge
    and orphan cases in `test_amd_lsp.py`, goal/credit cases in `test_amd_lint.py`.
    Full suite green (1709 tests; the 3 `test_a2x_props` failures are pre-existing and
    unrelated).
- **STATUS — the PANEL (phases b/c client side) DONE.** Command **`amd.showTimeline`**
  ("Show Story Timeline") in `sbs_cli/editors/vscode` — title-bar icon at navigation@2
  (between Outline and Graph) and in the shared cross-tool switcher. Lanes down / beats
  across, a **lane-mode dropdown** (section · arc · side · console) whose choice survives
  the live refresh, search, the **spine/pool** split, the per-beat **load** bar, and
  `Fail after:` / `loop` / lint badges on each record. Selecting a record loads the
  **same `inspectorForm.js`** the Outline uses into the docked detail pane, so the
  timeline edits the file rather than only reporting on it. Auto-refreshes on `.amd`
  edits, reuses `reuseToolPanel`/`registerToolPanel`, `tsc --noEmit` clean. Writer docs:
  `tooling/amd-tools.md`.
  - **Scope selector (this file | whole mission), defaulting to THIS FILE.** Every panel
    here indexes the whole mission root (`_index_for` → `_mission_root` → glob
    `**/*.amd`), which is right for the Graph but reads as *"I opened one file and it
    gathered the others"* on a timeline. The analysis stays mission-wide — it has to be,
    or the cross-file signal join collapses and everything ranks at beat 0 — so the fix
    is **rank globally, draw locally**: a display filter on the item's `uri`, with the
    true mission-wide beat numbers kept on the columns so both modes read the same. Only
    beats that hold something are drawn (a scoped or searched view isn't a row of empty
    columns), and the count reads `shown / in scope (mission: total)`. URI matching
    normalizes VS Code's `file:///f%3A/…` against Python's `pathlib.as_uri()`
    `file:///F:/…`, plus backslashes and percent-escaped spaces.
  - **Cross-boundary marker.** The one thing scoping could hide is that a chain
    *continues* past the file, so it doesn't: a record with causal neighbours elsewhere
    shows `↗n`, and the detail pane lists them under "Continues outside this file" as
    chips that widen the scope and select. Not a hypothetical — LM has 4 cross-file
    edges (the `siege_quests.amd` mission tree parents each boss in its own file) and OU
    has 6 (a lifeform's `Scene:` pointing into `officers.amd`).
  - **NOTE:** the panel talks to the LSP inside the **packaged `sbs.pyz`**, so
    `amd/timeline` only answers once `sbs.pyz` is rebuilt from this working tree.
  - **Drill-down into a record's own steps — DONE.** A job has no *mission* beat (that's
    the pool), but a multi-step job has its own timeline. Any container shows `⊞n`; the
    drill opens its steps in their own columns with **t=0 = acceptance**, a breadcrumb
    back, ⊞/◀ buttons in the detail pane, and a **lifecycle strip** (offered → on accept
    → goal → fails/completes after → on complete) which *is* the drill for a single-step
    job. Step order: declared references where they exist; otherwise **document order**,
    because that is what the MAST sequencer replays (`pr_ghost_seq`, "Work the steps in
    order") — labelled *"order assumed from file order"* with dotted connectors, never
    silently asserted. A container with SOME declared order leaves its unconstrained
    children at step 0 rather than appending them (Florbin's `alive` is a standing fail
    condition, not the fifth step).
  - **BUG FOUND + FIXED: records were being silently dropped.** Identity was the bare
    key, but a key is only unique among SIBLINGS — nested records are addressed by path.
    De-duplicating on the bare key lost **7 records in LegendaryMissions and 10 in Open
    Universe**, including three of the very job steps the drill-down exists to show
    (`job_sweep/scan`, `job_sweep/recover`, `job_cache/recover`, each shadowed by a
    namesake under a different job). The timeline now keys on a **uid** (`<uri>#<path>`);
    edges carry both bare keys (`from`/`to`, what the Graph indexes by) and uids
    (`fromUid`/`toUid`, what the ranking uses); references resolve by **path suffix**, so
    `Then: reveal job_sweep/scan` reaches that one, and an ambiguous bare key resolves to
    **nothing** rather than a coin-flip (a wrong edge moves a beat, and a silently wrong
    timeline is worse than a missing line). LM went 175 → 182 records, OU 124 → 134.
  - **`amd/node` gained optional `uri` + `line`** so the inspector edits the record that
    was clicked, not whichever namesake `by_key` happened to keep — the panels all have
    the line already. Without it, drilling into `job_sweep/scan` and typing would have
    edited `job_ghost/scan`.
  - **ROLLED OUT to the Graph, Outline and Resolver — and the hole was much bigger than
    the duplicate keys.** `amd_timeline.records()` is now the single definition of *what
    a record is*, read by `_mission_graph` and `_mission_resolve` too, so all four views
    agree. Measured against HEAD: **LegendaryMissions 118 → 182 records, OpenUniverse
    70 → 134** — over a third of both missions was invisible to the Outline/Graph/
    Resolver, mostly whole **flat single-section files** (`bridge_stories.amd`,
    `jobs.amd`, the dialogue and lore files) that the `level <= 2` filter read as empty.
    - **Orphans went DOWN, 44 → 32**, despite 64 more records: a record nested inside
      another is reached *through its parent* (often by a MAST sequencer rather than an
      AMD edge), so a step is no longer flagged unreachable on its own account. That
      cleared a class of standing false positives (Florbin's steps, `beacon_arc`'s).
    - The three panels index by key internally (layout maps, adjacency, selection), so
      rather than rewrite that machinery, `disambiguateKeys()` makes the keys themselves
      unique: a key used once is untouched, a key used twice becomes its **path**. The
      Resolver keeps a separate key map for REFERENCE resolution (refs are written as
      keys in the file; re-keying them would make every ref into a duplicated key read
      as dangling) and selects by uid. Every panel now passes `line` when inspecting.
  - **REMAINING:** phase (d) recorded runs (timestamped `QuestTap`, gap/pileup analysis,
    `timeline.json` from `--test`, run diff) and (e) edge-drag write-back.

---

## 3.6 Status
- **Platform + Signal Tracer + World Inspector + GUI DevTools taps** — **DONE
  (cores).** `cosmos_dev/mast_inspect.py`: an `InspectionBus` (pub/sub, inert with
  no sink) + `SignalTap` (`Mast.signal_emit`), `WorldTap` (poll `Agent.all`),
  `GuiTap` (wrap the live `sbs.send_gui_*` — assemble the per-frame widget list
  with parent/tag/rect). All stream as DAP custom `mast/inspect` events.
- **Brain Watcher tap** — **DONE (core).** `BrainTap` polls the `__BRAIN__`
  inventory and publishes each agent's behaviour tree (select/sequence/simple,
  per-node label + last result, active child marked, paused flag). No library
  change.
- **Mission Inspector panel** (extension) — **DONE (v1, 2×2 grid).** World table,
  Signals log, **Widgets tree** (GuiTap), **Brains tree** (BrainTap, active node
  highlighted); auto-opens on a `mast` session. **Polish DONE:** World + Signals
  filter boxes (match/total counts) and a Signals **Pause** (freeze auto-scroll,
  keep collecting). Still wants a live click-test against a running session.
- **Improved Story Graph (§3.5.1) — DONE** (outline + mini-graph + diagram
  search).
- **AMD Live Resolver (§3.5) — static + live half DONE.** Static: `amd/resolve` +
  `amd.showResolver` (resolved entity tree + red-flags, resolved/dangling refs,
  orphan headings). Live: a **`QuestTap`** (`mast_inspect.py`) polls the
  `__quests__` inventory and streams `{quest key -> state}` (idle/active/secret/
  complete/failed) over the DAP; the Resolver overlays a live state badge per
  quest (and "not granted" for quests absent from the running mission), with a
  ● live / ○ static indicator. Note: dialogue/scene "fired" state doesn't exist
  at runtime, so the overlay is quest-state focused (not dialogue).

---

## 3.7 Layout containers to add (before / alongside the editor)

The current model is **rows of columns** (`Row`→`Column`→widget), with
`bounds`/`padding`/`border` and a `row_template` for Listbox/table data rows.
`Tabs` already exist (`procedural/gui/tabbed_panel.py`). Additive new containers —
so existing scripts are untouched — tiered by value:

- **Tier 1:** **Grid** (positional N×M with col/row span), **weight/grow** (a
  per-child sizing share — the single biggest editor win: "drag a divider" = set
  weights), **Group/Panel** (titled/bordered frame over a Column — cheap, maps to
  section/sub_section).
  - **Grid — DONE (additive core).** `pages/layout/grid.py`: `Grid(columns,
    col_width, row_height)` composes **standard Rows of Columns** (short final row
    padded with `Hole` spacers), so it adds no render path and can't regress
    existing layouts. `.add`/`.add_all`/`.rows()`/`.build(layout)`. Size defaults
    apply only where a cell hasn't set its own. Tested structurally
    (`tests/test_layout_grid.py`, 8 cases) — no renderer needed.
  - **Grid — MAST-native `gui_grid()` DONE.** So writers get grids in *pure MAST*
    (not just Python): `with gui_grid(N):` (context manager, like
    `gui_sub_section`) + `procedural/gui/grid.py`, auto-registered into MAST
    globals. `StoryPage` gained a `_grid_stack` + `grid_begin`/`grid_end`, and
    `add_content` auto-breaks to a new row every N and Hole-pads the final row.
    Inert unless a grid is open — no behaviour change to existing pages. Nestable.
    Tested (`tests/test_gui_grid.py`, 8 cases); 107-test GUI/MAST regression green.
    Usage: `with gui_grid(3): gui_text(...); for s in ships: gui_button(s.name)`.
  - **Group/Panel — DONE (additive).** `pages/layout/group.py`: `Group(tag,
    title, …)` is a standard `Layout` configured with `border_style`/
    `border_color` + an optional title `Row` holding a `Text`. `.add`/`.add_all`/
    `.build()`. No border/title ⇒ an ordinary Layout, so no new failure mode.
    Tested (`tests/test_layout_group_repeater.py`).
  - **weight/grow** deferred: it modifies the **core** flex math in `layout.py`
    (`calc`), which runs in every shipped layout — needs visual QA, so it wants a
    checkpoint rather than a blind edit.
- **Tier 2:** **Wrap** (a Row that flows onto the next line — variable badge/chip
  lists), **Overlay/Stack** (z-layering: badges, HUD over a view).
- **Repeater — DONE (additive).** `pages/layout/repeater.py`: `Repeater(columns,
  factory, …)` maps a list through `factory(item, index) -> cell` and lays the
  cells out in rows via **Grid** (so only standard Rows/Columns are emitted).
  `.cells_for`/`.rows_for`/`.build(items, layout)`. Tested. (The runtime
  live-expand/binding — re-run on data change — is the remaining editor piece.)
- **Tier 3:** **Repeater/ItemsView** (bind a container to a list, render a child
  *template* per item — the fix for data-driven GUIs; the editor authors the
  template, live-expanded at runtime).

**PARKED: `Scroll`** — being worked on elsewhere. Keep the contract below in mind
for it and for any overflow-prone container.

### The no-clip contract
The engine has **no clipping**, so "hidden" must mean **not drawn** and "overflow"
must mean **not laid there** — everything is *realize/cull*, never *clip*. The house
already does this in `text_area`: **measure real glyphs → size to fit width (no
horizontal overflow) → scroll by a line index that snaps at whole-line boundaries**
(only complete lines drawn). Per container: **Tabs** realize only the active panel;
**Grid** cells size-to-fit (wrap / ellipsis / nested scroll, never spill); **Wrap**
fits width; **Overlay** children fit the bounds. The editor turns this into a
**design-time guardrail**: reuse `cosmos_dev/layout_audit` to flag would-overflow
widgets live on the canvas using the engine's real text measurements — you can't
author an out-of-bounds screen unknowingly.

---

## 4. The MAST GUI Editor (authoring)

**Feasibility verdict: strong — more so than expected**, because the two things that
usually sink a WYSIWYG editor are already solved here:

1. **The renderer exists.** `mockgui/client.html` already draws every widget. Reuse it
   (§2.3) → pixel-faithful canvas for free.
2. **The layout is a flow model, not absolute pixels.** `pages/layout/` is
   `Layout`/`LayoutPage`/`Row`/`Column`/`Bounds`/`RegionType` — rows stack, columns nest,
   widgets carry Bounds. That's **flexbox**, which maps cleanly onto a web canvas and onto
   drag-and-drop. (Absolute-rect editors are the painful kind; this isn't one.)

### 4.1 What it looks like
A webview with three parts: a **palette** (the `gui_*` widgets), a **canvas** (rows/
columns you drop widgets into, rendered by the shared module), and a **properties panel**
(text, style string, tag, size/bounds, the widget's callback). A **Generate** button (or
live two-way) emits the MAST. A **live preview** can render the design in the real mock.

### 4.2 Architecture
- **Model:** a tree of regions (Row/Column) and widgets with props — mirrors
  `pages/layout`.
- **Render:** the shared widget module (§2.3).
- **Code-gen:** model → MAST `gui_*` calls (+ the layout row/column scaffolding). This
  direction is straightforward.
- **Round-trip (the hard direction):** parsing arbitrary MAST GUI code back into the model
  is *not* generally possible (loops, conditionals, dynamic values). Three strategies,
  best-first:
  1. **Marked designer region** — the editor owns a delimited block
     (`# <gui-designer> … # </gui-designer>`); it regenerates only that block, leaving
     hand-written code around it. Safe, predictable, ships first.
  2. **Live capture & tweak** — attach to a running mission, capture the widgets a page
     actually produced (the `send_gui_*` stream — the GUI DevTools data), and open *that*
     in the editor to adjust styles/positions, emitting overrides. Ties the editor to the
     inspection platform; great for "fix this screen I'm looking at".
  3. **Declarative sub-format** — a small data description of a panel (YAML/AMD-ish) that
     the editor round-trips losslessly and MAST renders at runtime. Cleanest long-term,
     biggest new surface.

### 4.3 What it can't do (set expectations)
- **Data-driven GUIs** (a list built in a loop) — you design the *template/row*, not the
  expanded result. That's the same limit every form builder has.
- **Full round-trip of arbitrary existing screens** — hence the marked-region / capture
  approaches above.

### 4.4 Phases
| Phase | Deliverable |
|---|---|
| G0 | Shared widget-render module (§2.3), used by a read-only **preview** of a selected `.mast` GUI region |
| G1 | Palette + canvas + properties → **code-gen into a marked region** (one-way author) |

**G1 — STARTED (v0).** Command **`amd.guiEditor`**: a structural composer (palette →
design tree → properties → live **Generated MAST**), not yet a pixel canvas. Palette
covers all the containers (`section`/`sub_section`/`row`/`grid`/`list`) + widgets
(`text`/`button`/`checkbox`/`slider`/`input`/`face`/`icon`/`image`/`blank`/`table`).
Code-gen handles `with`-block indentation (grid/list/sub_section) and procedural flow
(section/row), button jump-blocks, and `gui_table`'s declarative form. Output → clipboard
or **Insert into file** (replaces a `# <gui-designer> … # </gui-designer>` block, else
inserts at the cursor). A representative generated snippet compiles as valid MAST.

**G1 shipped further:** classic 3-pane layout (palette · Preview/Code tabs · tree +
inspector), a root **Screen** node with **sections-only-off-root**, **drag** nodes in the
tree, **move/resize sections** in the preview, and **round-trip** — a parser reads the
editor's own dialect back into the model (comments/unknowns kept as `raw`; `parse→gen`
byte-stable). **`*.gui.mast` opens as the editor** (CustomTextEditorProvider, two-way
synced, loop-guarded) with a one-click toggle to/from the full text editor. Writer docs:
`tooling/gui-editor.md`. Next: the pixel-faithful canvas/preview (G0/G2) and undo/redo.
| G2 | **Live preview** in the mock (render the design via the socket) |
| G3 | **Live capture & tweak** (strategy 2) — reuses GUI DevTools |
| G4 | (optional) declarative sub-format for lossless round-trip |

---

## 5. Suggested sequence across the suite

1. **Inspection channel + Signal Tracer** (§2.1 + §3.1). Smallest, proves the platform,
   immediately illuminating.
2. **World Inspector** (§3.2). Cheap; makes diplomacy legible.
3. **Widget-render module + GUI DevTools** (§2.3 + §3.3). Unlocks the GUI Editor's renderer.
4. **GUI Editor G0→G1** (§4). Preview, then author-into-a-marked-region.
5. **Brain Watcher** (§3.4) and **AMD Live Resolver** (§3.5) — the two "dream" tools for
   the AI and data-authoring crowds.
6. **GUI Editor G2→G3** — live preview + capture-and-tweak.

Each is independently shippable. The through-line: you now have a **running mission you
can interrogate from the editor**; each tool is a new lens on that live state, and the GUI
Editor closes the loop by letting you *author* the thing you're inspecting.

## 6. Cross-cutting principles (from the debugger)
- **Zero cost off:** every seam is `None`-guarded and dev-only-installed; nothing ships in
  the `.sbslib` behavior.
- **One connection:** prefer custom events on the existing socket before adding channels.
- **Source-map everything:** every panel row links back to a `.mast`/`.amd` line (incl.
  zip-hosted source).
- **Write for mission writers:** panels speak in mission terms (signals, quests, ships),
  not runtime internals.
