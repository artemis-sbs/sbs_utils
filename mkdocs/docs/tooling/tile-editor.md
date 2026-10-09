# The Tile Map Editor

New in v1.4.0. It edits the text file directly and VS Code's undo covers every change, so
it cannot lose work. The file formats it reads and writes are settled for 1.4.0.

A [ground tile map](../build/ground-tile-maps.md) is an ASCII grid, and typing one is
easy. The hard parts are seeing it and checking it. Edges, fringes and shade depend on the
neighboring cells, so a map only really shows in the game. The **Tile Map Editor** paints
the grid and draws it with the mission's own art, the way the game does.

It is part of the **Artemis AMD** VS Code extension.

## Open it

Open any `.tiles` file and it opens in the editor. **Text** on the toolbar switches to the
plain text editor. To come back, use **Open in Tile Map / Tileset Editor** on a `.tiles` text
editor's title bar.

The editor needs the **AMD language server**, the same one that checks `.amd` files, for
art, the tileset's rules and problems. Without it you can still paint, and cells are
colored by kind.

## Painting

| Tool | Key | What it does |
|---|---|---|
| **Paint** | `B` | Paints the selected legend entry. Drag to paint a line with no gaps. The **right** mouse button erases to *nothing*. |
| **Rect** | `R` | Drag a rectangle. Hold **Shift** as you release for an outline. |
| **Fill** | `F` | Fills the region the clicked cell belongs to. |
| **Pick** | `I` | Picks the clicked cell's legend entry. **Alt+click** does it with any tool. |
| **Entry** | `E` | Sets `entry:`, where a party beamed down stands. |
| **Move** | `M` | Drags a prop, person or hostile (or the mark it stands on), or one point of a patrol, to a new cell (see [Things](#things-props-people-and-hostiles)). A click without a drag opens it in the AMD Inspector. |

**The legend is the palette.** Click an entry to paint with it. Double-click it to change
its kind or mark. **+ Entry** adds one: pick a kind (the tileset's kinds are offered), an
optional mark (`to_<area>` makes an exit) and a character. By default the character is the
kind's first letter, if it is free. A mark is just a legend entry, so painting with it
places the mark.

**Resize** sets the map's width and height. It writes a `size:` header so that blank
columns at the edge are kept.

## What you see

- **Kinds** colors each kind. A cell that cannot be walked is hatched. A character that is
  not in the legend is magenta, and the whole area will not load until it is fixed.
- **Art** draws the mission's art sets: its own `builtin` set, then the `TILE_ART`
  setting. They are found in the mission, then in a repo checked out beside it, then in
  `__lib__`. The footer names the sets it found and any it did not. The art comes from the
  game's own code (`tilemap_cell_look` and `tilemap_cell_fringes`), so edges, fringes,
  grids and shade match the game. A freshly painted cell shows its kind's color for a
  moment, until the new look arrives.
- **Marks** outlines every mark and labels it. Exits are drawn in blue with the area they
  lead to. The **star** is the entry.
- **Problems** lists what `sbs lint` would say about this area. A red corner marks the
  cell each problem is on. Click a problem to open the text at that line.

**Zoom** with `+` / `-` or Ctrl+wheel. **A** toggles Kinds and Art.

## Things: props, people and hostiles

**Things** (on by default) draws every prop, person and hostile that the mission's
`.amd` files place in this area, read from your unsaved text too. In **Art** they are
drawn with their sprites, standing on their cell and tinted the way the game tints them.
In **Kinds** they are icons:

- an amber square for a prop
- a green circle for a person who never attacks (`Calm: yes`)
- a red circle for a hostile

A hostile's `Patrol:` is drawn as a dashed loop through its points. Anything with
`Hidden until:` is drawn faded. Anything with a problem is ringed in red. The sidebar
lists everything placed in this area, including anything that cannot be drawn because it
is off the map or on a mark that is not there. Click an entry to open it in the AMD
Inspector.

With the **Move** tool:

- **Drag** a thing placed by `At:` to rewrite its `At: x, y` in the `.amd`.
- **Drag** a patrol point to rewrite that one point of `Patrol:`.
- **Drag** a thing placed by `Mark:` to move **the mark**. The mark keeps its whole shape
  and each cell keeps its own character. Everything else standing on that mark, and any
  scene that belongs to it, moves with it. The cells it leaves become plain ground of
  the same kind, or the ground around them if the legend has no plain character for
  that kind.
- **Click** without dragging to open the thing in the Inspector.

Moving a mark edits **this file**, so the editor's own undo covers it. Moving an `At:` or
a patrol point edits the **`.amd`**, which the editor's undo cannot reach. For those, use
**Undo move** on the toolbar, which puts back the last move while the text is still what
the move left. If the `.amd` had no unsaved changes, a move saves it again, so a drag
does not leave a file dirty in the background. If you have unsaved edits there, they are
left for you to save.

**Face S** cycles the figures through S, W, N and E, to preview a set's art each way
round. It only changes the preview. The game places everyone facing south and turns
them as they walk.

## What it writes

The text file is the map. A stroke rewrites **only the rows it changed**, so comments,
the header and the legend's spacing are left alone, and each stroke is one step of undo.
A row's trailing blanks are dropped, because they mean *nothing* anyway.

## The Tileset Editor

Open a `.tileset` file and it opens as the **Tileset Editor**. Each row is one kind, with:

- a picture of the look it wears, from the mission's art sets, tinted by its `color=`
- **Walk**, **See** and **Tall** checkboxes
- its **Look**, with the art sets' looks offered as you type; a look no art set draws is
  outlined in red
- its **Tint** and **Over**
- **Cells**: how many cells of the mission's areas are drawn with it

Below the table is every look the art sets offer. Select a kind, then click a look to put
it on. **+ Kind** adds a kind that can be walked and seen across. **x** removes a kind,
and one that is still drawn somewhere takes a second click. **Renaming** a kind renames
it in every area that uses this tileset too: each legend line that draws it has just that
word changed. The whole rename is one edit across the files, so one undo takes it back.
The areas are left unsaved, so use **Save All** to keep them. Mission code that names the
kind in a string is not changed.

Each edit rewrites one line. It is lined up with the file's own columns, so a file
laid out in columns stays that way.
