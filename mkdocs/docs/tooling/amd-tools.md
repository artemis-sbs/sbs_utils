# AMD authoring tools

Writing a mission's `.amd` file is writing a *graph* — scenes reveal quests, quests
signal each other, dialogue branches, landmarks anchor the map. Past a couple of dozen
headings that graph is hard to hold in your head. The **Artemis AMD** VS Code extension
gives you a set of tools that read the same `.amd` and show it back to you — so you can
navigate it, validate it, and edit it without scrolling the raw text.

They all read the **live** file (they refresh as you type), and every row links back to
its source line.

!!! note "For mission writers"
    These are *views over your `.amd`* — open one on the mission you're editing. Nothing
    here ships inside a mission; it's authoring help in the editor.

## Open a tool

With an `.amd` file focused, use the **editor title-bar icons** (top-right of the editor)
or the Command Palette (`Ctrl/Cmd-Shift-P` → "Artemis AMD: …"). The icons are ordered for
a document's life — **authoring first, live testing last**:

**Story Outline · Story Graph · AMD Resolver · Mission Map · Preview · Preview-in-session ·
Mission Inspector**

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
  headings** (unreachable — nothing reveals them and they have no `When:`/signal trigger),
  and structural / cross-file lint. Sorted worst-first, each jumps to source.

Single-click a row to browse (a reference selects the related entity; a red flag highlights
its node); **double-click** opens the source line. An empty "reached by" list is exactly
why a node shows as an **orphan**.

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
  filter by name, **Pause** to freeze the scroll while you read.
- **Widgets** — the widget tree a console is building this frame (tag, rect, parent).
- **Brains** — each NPC's behaviour tree with the active branch lit.

See also [Debugging your mission](mast-debugger.md) for stepping through MAST itself.
