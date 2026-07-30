# The Control Gallery

A browsable, running catalog of the Cosmos GUI — every control shown live, and
**underneath it the source that built it**. Think of Material Design's component
gallery, except the snippet is not a copy of the example: it is sliced out of the
mission's own file at runtime, so it cannot drift from what you are looking at.

It is a mission you run, not a page you read. Start it and browse.

- Repo: [artemis-sbs/control_gallery](https://github.com/artemis-sbs/control_gallery)
- Folder: `data/missions/control_gallery`

## Running it

**In the engine** — launch Cosmos, pick **Control Gallery** in the mission browser,
and start the map. The gallery opens **on the server screen**: no console to pick and
no ship required, which is what a tool should be. "Main screen" in the header hands
the screen back to LegendaryMissions' own view.

**In the browser mock** — cheaper for a first look at layout:

```
sbs debug control_gallery --map 0
```

then open `http://localhost:8765/server`.

The same gallery is also available as a console, so a connected client can browse it
too.

## What is in it

54 entries in six categories:

| Category | Entries | What it holds |
|---|---|---|
| **Controls** | 20 | one entry per widget, live — text, buttons, checkbox, dropdown, sliders, list box, table, text area, icons, radio, input, grid, face, ship, image |
| **Layout** | 4 | `row-height` / `col-width` modes, size arithmetic, `overflow` — every box backgrounded, because the subject is where the edges land |
| **Recipes** | 4 | composed patterns: watch/repaint, a status line, a reusable style, and a shelf of four `item_template`s switched live |
| **Traps** | 5 | each runs **BROKEN and FIXED side by side**, with both snippets under the panel that drew them. Only the fix gets a Copy button |
| **Full page** | 4 | examples that are a whole screen: an embedded engine view, a self-redrawing region, a master/detail console, and a layout playground |
| **Overlays** | 17 | every overlay kind, `announce()`, and the audience rules — see [Overlays](overlays.md) |

## Why the source panel is the point

Every specimen's snippet is extracted at runtime from between `# >>gallery: <key>` and
`# <<gallery` markers in the mission's files. There is no second copy to fall out of
date. **Copy to clipboard** puts the real thing on your clipboard.

The slicer is language-agnostic — `.mast` and `.py` both comment with `#` — so one
entry can span both files. The `gui_list_box` entry shows the MAST call **and** the
Python `item_template` it points at, which is how real missions pair the two.

!!! note "Traps are the part worth browsing even if you know the widgets"
    A trap is a mistake that produces a *plausible* screen, so it survives review: a
    `1em` row under a bigger font, padding eaten out of the row height, a starved
    `content` row, `update()` dropping the rest of the style string, a handler built
    inside a `for` loop capturing the wrong item. Each one runs broken and fixed at the
    same time, next to each other.

## Take the tour

**"Take the tour"** in the header walks all 54 entries in order, narrating each one
through the overlay system's own lower third — the gallery introducing itself with the
feature the mission was originally built to demo. It stops at either end rather than
looping, so it tells you when you have seen everything.

## Full-page examples, and one console that becomes any console

Four examples are a whole screen rather than a control. Squeezed into the detail pane
they would teach the wrong thing about proportion, so they are listed in the index but
**drawn on the Gallery Viewer console** at full size.

That console also **morphs into any of seven consoles** on request, which is how the
mission demonstrates overlay fan-out and `consoles="mainscreen"` with only two consoles
enabled. The pattern is worth knowing on its own: reroute a client to a label that
assigns a ship and calls `gui_console(name)`.

!!! warning "A morph must set the console ROLE, not just `CONSOLE_TYPE`"
    Anything that narrows an audience — overlays, `announce()`, comms targeting —
    resolves it through `any_role()`. A screen carrying `CONSOLE_TYPE` with no console
    role is invisible to all of them, and the message is dropped **in silence** with
    nothing logged. Set both, and clear the previous console's role on the way.

## Adding an entry

Two things, joined by a key:

1. **A record in `gallery.amd`** — `## [Display](key)`, a `---` fence with `Category:`
   (and `Kind: trap` or `Kind: page`), then a body whose **first line is the blurb** and
   whose remainder becomes the notes panel. File order is nav order, and consecutive
   records sharing a `Category` collapse under one header — so the shape of that file is
   the shape of the menu.
2. **A marked span with the same key** in `gallery.mast`, `gallery_pages.mast` or
   `gallery_specimens.py`. A trap needs two: `<key>_broken` and `<key>_fixed`.

Nothing else — no code to touch for a new entry. A record naming a key with no span
reports that in the source panel rather than silently doing nothing.

## Related

- [GUI](gui.md) — the reference for the functions the gallery demonstrates
- [Custom lists (gui_list)](gui_list.md), [Tables (gui_table)](gui_table.md),
  [Grids (gui_grid)](gui_grid.md)
- [Sizing to content](gui_content_sizing.md) and
  [Text that does not fit](gui_overflow.md) — the two subjects the Layout category
  exists to make visible
- [Overlays (cards, HUDs, cutscenes)](overlays.md)
