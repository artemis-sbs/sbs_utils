# Mission Authoring Tools — VS Code Plan

Status: **proposal / roadmap**. No code written yet. Follows the pattern that worked
for the MAST debugger (`MAST_DEBUGGER_PLAN.md`): tap an existing seam, stream to a
VS Code panel, keep zero cost on non-debug runs.

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
  edits. Phases (b) mini-graph and (c) diagram retrofit remain.

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
  highlighted); auto-opens on a `mast` session.
- Next tap: **AMD Live Resolver** (§3.5) — then the **Improved Story Graph**
  (§3.5.1) as the navigable view over that same resolved model.

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
