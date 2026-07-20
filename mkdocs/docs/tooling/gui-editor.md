# The GUI Editor

Building a console screen by hand — sections, rows, buttons, a list — means typing a lot
of `gui_*` calls and guessing where things land. The **GUI Editor** lets you **compose a
screen visually** and it writes the MAST for you: drag pieces in, see roughly where they
sit, and copy the code into your mission — or edit a `.gui.mast` file straight in the
editor.

It runs inside VS Code, part of the **Artemis AMD** extension.

!!! note "For mission writers"
    You place widgets and set their text; the editor generates the `gui_text` /
    `gui_button` / `gui_list` … calls. No need to remember the exact syntax.

## Open it

Two ways:

- **Any `.mast` file:** Command Palette (`Ctrl/Cmd-Shift-P`) → **"GUI Editor (compose a
  layout → MAST)"**. Compose, then **Copy** or **Insert into file**.
- **A `*.gui.mast` file:** just open it — it opens *as* the GUI Editor automatically. The
  whole file is the screen, edited visually.

## The panels

- **Left — palette.** Click a piece to add it. **Containers** hold other pieces (Section,
  Row, Grid, List); **Widgets** are the pieces themselves (Text, Button, Checkbox, Face,
  Table…).
- **Middle — Preview / Code tabs.** *Preview* shows roughly where things land on the
  screen; *Code* shows the generated MAST (in a `.gui.mast` file, the **Code** tab opens
  the full text editor).
- **Right — the tree and the inspector.** The **tree** is your layout's structure (drag to
  rearrange); the **inspector** edits the selected piece's text, style, size, and so on, and has
  **↑ ↓ Duplicate Delete** actions (all undoable). A line the editor doesn't recognise is kept as
  an editable **Raw line** rather than lost.

## Compose a screen

1. Add a **Section** and set its **Area** (`left,top,right,bottom` as percents of the
   screen) — or drag its corner in the Preview to size it, and its top-left grip to move
   it. Sections are the boxes you place content in; they live at the top level.
2. Select the section and add pieces into it — a **Text** for a heading, a **List** or
   **Grid**, some **Buttons**.
3. Put several widgets on one row and they become that row's **cells**.
4. **Drag** pieces in the tree to move them between sections or reorder them.

## Get the MAST out

- **Copy** puts the generated code on your clipboard.
- **Insert into file** drops it into the active `.mast`. If that file has a
  `# <gui-designer>` … `# </gui-designer>` block, it updates just that block (so your
  hand-written code around it is left alone); otherwise it inserts at your cursor.

## `*.gui.mast` files — edit visually or as text

Name a file `something.gui.mast` and it becomes an **editor-owned screen**: opening it
shows the GUI Editor, and your visual changes are saved back to the file as MAST.

- Switch to the raw text with the **Code** tab (or **"Reopen With…"**).
- Switch back from text with **"Open in GUI Editor"** on the editor's title bar.
- You can edit it either way — the editor reads your text back in when you return, so
  comments and anything it doesn't recognise are kept as-is.

## Console screens — engine widgets

Beyond layout widgets, the palette has the real **engine console views** so you can lay out a
helm/weapons/science/cockpit-style screen the way the shipped consoles do:

- **Console views** — drop a **3D View**, **2D Radar** (and the Science / Weapons / Comms 2D
  variants), **Ship Data**, **Text Waterfall**, **Radar Zoom**, **Ship Internal**, the **Comms**
  cluster, or **Red Alert** into a section. Each emits `gui_layout_widget("<name>")` — the engine
  owns the content, so you place and size it (via the section's **Area**) and the preview shows a
  recognizable placeholder (a radar scope, a 3D-view starfield, stat bars, …). One widget fills
  its section, matching the engine.
- **Console setup** — a **Console preset** (`gui_console("helm"|"weapons"|…)` — a whole prebuilt
  console), **Activate console** (`gui_activate_console`), and a **Cinematic camera**
  (`gui_cinematic_auto` / `gui_cinematic_full_control`).
- **Template…** (top bar) — start from a ready-made skeleton: *Cinematic* (full-screen 3D view),
  *Cockpit* (background image + placed views), *Science* / *Weapons* / *Comms* (a 2D view beside a
  controls/data column).

The real pattern is a full-screen background section plus absolutely-positioned `area:` sections,
each holding one engine widget — exactly what the templates produce.

## Control events — `on gui_message`

Interactive controls can carry a handler that runs when the player uses them. A **Button** has an
**On click** (matched by its label). A **Checkbox / Slider / Dropdown / Radio / Input** has an
**On message** handler plus an optional **Ref var** — the editor emits `<ref> = gui_checkbox(...)`
and an `on gui_message(<ref>):` block (leave Ref var blank and it auto-names one). Existing files
using either form round-trip unchanged.

## What it can't do (yet)

- The Preview is **approximate** — it shows where things sit, not a pixel-perfect render.
- **Data-driven screens** (a list built in a loop) — you design the *row template*, not
  the expanded result. That's the same limit every visual builder has.
