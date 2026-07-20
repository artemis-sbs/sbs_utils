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
  rearrange); the **inspector** edits the selected piece's text, style, size, and so on.

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

## What it can't do (yet)

- The Preview is **approximate** — it shows where things sit, not a pixel-perfect render.
- **Data-driven screens** (a list built in a loop) — you design the *row template*, not
  the expanded result. That's the same limit every visual builder has.
