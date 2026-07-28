# AMD authoring tools

Writing a mission's `.amd` file is writing a *graph* — scenes reveal quests, quests
signal each other, dialogue branches, landmarks anchor the map. Past a couple of dozen
headings that graph is hard to hold in your head. The **Artemis AMD** VS Code extension
gives you a set of tools that read the same `.amd` and show it back to you — so you can
navigate it, validate it, and edit it without scrolling the raw text.

They all read the **live** file (they refresh as you type), and every row links back to
its source line. They also all read the **same record set**, so what one shows, the others
show: every heading in every `.amd` under the mission root, including per-section files
whose records are `#` headings, and including two records that happen to share a key
(a record is identified by its **path** — `job_ghost/scan` and `job_sweep/scan` are two
different steps, and where that matters a panel shows the path instead of the bare key).

!!! note "For mission writers"
    These are *views over your `.amd`* — open one on the mission you're editing. Nothing
    here ships inside a mission; it's authoring help in the editor.

## Open a tool

With an `.amd` file focused, use the **editor title-bar icons** (top-right of the editor)
or the Command Palette (`Ctrl/Cmd-Shift-P` → "Artemis AMD: …"). The icons are ordered for
a document's life — **authoring first, live testing last**:

**Story Outline · Story Timeline · Story Graph · AMD Resolver · Mission Map · Preview ·
Preview-in-session · Mission Inspector**

Once any tool is open, its **top bar has buttons for the others** — jump between Outline,
Graph, Resolver, Map, and Inspector without going back to the text editor. Tools open in
the **same editor group** (as tabs, not new splits), and opening one that's already showing
your mission just re-focuses it.

## Story Outline

A searchable list of every node, grouped by section, with a detail pane on the right. It's
"navigate the story like code": type a name to find a node, click it to see its **editable
fields inline**, a **1-hop mini-graph** of its immediate neighbours, and its **Leads to /
Reached from** connections (each a chip that re-focuses on click). This is the default view
for a large mission — it stays readable at any size because it never draws the whole graph.

## Story Timeline

The Outline is a list, the Graph is topology, the Map is space — the Timeline is **time**.
Lanes down the side, **beats** across the top, and the same editable inspector docked on
the right, so you can fix what you find without leaving the view.

**A beat is causal, not a clock.** AMD has no timestamps, so beat *N* means "at least *N*
things must happen first" — it's act structure, ranked from what reveals, parents, or
signals what. The one real duration in the language is `Fail after:` / `Complete after:`,
and that shows on the record itself (⏱ 6 minutes) rather than being faked as a bar width.

|   | What it shows |
|---|---|
| **Spine** | Everything chained, flagged `Required:`/`Critical:`/`Win:`/`Lose:`, or `State: active` — laid out in beat columns. Flagged records carry a marker down the left edge. |
| **Pool** | Content with no authored order (an idle job board). Sequencing it would invent an order you never wrote, so it gets an availability band instead. |
| **load** | The pacing curve under the spine: how much is in play at each beat. A thin column is a lull. |

**Lanes answer four different questions** — pick from the dropdown:

- **by section** — matches the Outline's grouping (the familiar default)
- **by arc** — the `Parent:`/nesting chain: *does act 3 have a middle, or does it jump
  from hook to payoff?* (a one-record arc collapses into its section, so a job board
  doesn't render as a dozen lanes of one)
- **by side** — *this faction is absent for the whole second act*
- **by console** — `Accept on:` / `Engage on:` / anything scan-shaped, i.e. **crew
  workload**: *is Science idle from beat 2 onward?*

A record can sit in several lanes at once (a job two consoles can accept) or in none
(nothing declared) — it still appears, in an explicit *(no console)* / *(no side)* lane,
rather than dropping out of the view.

**Scope: this file / whole mission.** Like every tool here, the Timeline *analyses* the
whole mission — it has to, because a signal's emit and its wait usually live in different
files, and ranking one file alone would flatten everything to beat 0. But opening one
`.amd` and being shown the whole repo isn't useful either, so the default **draws only the
open file** while still ranking against everything. Beat numbers are the true mission-wide
ranks in both modes, and only the beats holding something are drawn — so a scoped view
isn't a row of empty columns. The count reads `shown / in scope (mission: total)`.

Scoping could hide one thing that matters — that a chain **continues past this file** — so
it doesn't. A record whose causal neighbours live elsewhere is marked `↗n`, and its detail
pane lists them under **Continues outside this file**; clicking one widens the scope to the
whole mission and selects it. (LegendaryMissions' siege tree is the case in point: the
parent quest is in `siege_quests.amd` and every boss it parents is in its own file.)

Records in a **loop** (a dialogue hub you return to) are marked `loop`. A loop has no
beat order by definition; the ranking breaks it, ranks the rest, and tells you where.

### Drilling into a job

A job has no beat at *mission* level — that's the point of the pool — but a multi-step job
has a timeline of its own. Any record with sub-steps shows `⊞n`; click it to open **that
record's own timeline**, where **t=0 is acceptance, not mission start** (the frame in which
a job's clock actually means something — `Fail after:` anchors the same way). A breadcrumb
takes you back to the board, and the detail pane gains **⊞ steps** / **◀ parent** buttons.

Inside the drill:

- **Steps** are laid out in their own columns, ordered by declared references where the
  author wrote them (`Then: reveal case/two`).
- Where the AMD declares *no* order, the steps fall back to the order they're **written
  in** — because that's what the MAST sequencer replays. That's an inference, so it's
  labelled *"order assumed from file order — not declared in the AMD"* and the connectors
  are drawn dotted. The view never silently asserts an order the file didn't state.
- A container with *some* declared order leaves its unconstrained records at step 1 rather
  than pushing them to the end — Florbin's *Keep Florbin Alive* is a standing fail
  condition, not the fifth step.
- **Lifecycle** runs above the steps: offered → on accept → goal → fails/completes after →
  on complete. A single-step job has no sub-steps to draw, so this *is* its drill-down.

!!! note "Steps with the same name"
    A record's identity is its **path**, not its key — keys only have to be unique among
    siblings. `job_ghost/scan` and `job_sweep/scan` are two different records, and the
    Timeline keeps them apart (including when you edit one: it targets the record you
    clicked, not its namesake). Reference them by path — `Then: reveal job_sweep/scan` —
    since a bare `scan` that could mean either resolves to *neither*, on purpose.

## Story Graph

The whole story as a node-link diagram, laid out in **swimlanes by section**. Good for
seeing shape and flow. It has **search** (type to spotlight matching nodes; Enter cycles
them), **section filters**, **collapse**, hover-spotlight, and **right-click → Focus** to
zoom into one node's neighbourhood. Drag one node onto another to add a choice edge.

## AMD Resolver

AMD fails **silently** — a typo'd heading drops a whole quest; a `Then: reveal X` that
points at nothing just… goes nowhere. The Resolver makes that visible. Two panes:

- **Resolved model** (left) — every heading as the engine resolved it, grouped by kind
  (quest / scene / dialogue / lifeform / scan / landmark / …). Expand a node to see its
  references **both ways**: **→ leads to** (what it reveals/reaches) and **← reached by**
  (what reveals it). Each reference is marked **✓ resolved** or **✗ dangling**.
- **Red flags** (right) — everything that's broken: **dangling references**, **orphan
  headings** (unreachable — nothing reveals them and they have no `Starts when:`/signal trigger),
  and structural / cross-file lint. Sorted worst-first, each jumps to source.

Single-click a row to browse (a reference selects the related entity; a red flag highlights
its node); **double-click** opens the source line. An empty "reached by" list is exactly
why a node shows as an **orphan**.

**Live overlay.** With a mission running under `sbs debug`, the Resolver shows each quest's
**live state** — a badge reading *active / secret / complete / failed / idle*, or *not granted*
for a quest the running mission hasn't created yet. The header flips from **○ static** to
**● live** while state is streaming. (Dialogue/scene "fired" state isn't tracked by the engine,
so the overlay is quest-focused.)

### Add a new entity

Each section header (in the Outline, Graph, and Resolver) has a **"+ add"**. It inserts a
new record of that section's kind — with the fields that section conventionally uses —
creates the section if it doesn't exist yet, and opens it for editing (inline in the
Outline). No remembering which fields a lifeform vs. a landmark needs.

## Mission Map

Landmarks (`At: i,j`) and regions (`Center:`/`Radius:`) plotted on the sector grid. Drag a
landmark to move it; the `At:` value rewrites in the source. The spatial companion to the
list/graph views.

## Mission Inspector — live

The others are static analysis of the file. The **Mission Inspector** is the *live* view:
attach it to a running mission (it opens automatically on an `sbs debug` session) and watch
the mission's actual state in a 2×2 grid:

- **World** — every space object: side, kind, roles, and an **Enemy?** column (the
  diplomacy verdict — is this actually hostile to a player side, not just what side label it
  carries). Filter the table, tick **enemies** to show only foes, click a row to peek its
  inventory.
- **Signals** — a live, timestamped log of every signal fired and how many routes it hit;
  filter by name, **Pause** to freeze the scroll while you read, and click **↪ emit** / **↪
  route:line** to jump to where the signal was emitted or handled in source.
- **Widgets** — the widget tree a console is building this frame (tag, rect, parent).
- **Brains** — each NPC's behaviour tree with the active branch lit.

See also [Debugging your mission](mast-debugger.md) for stepping through MAST itself.
