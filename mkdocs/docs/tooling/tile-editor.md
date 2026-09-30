# The Tile Map Editor (experimental)

!!! warning "Experimental"
    New in v1.4.0 and not yet tried on many maps. It edits the text file directly and
    VS Code's undo covers every change, so it cannot lose work. Keep an eye on what it
    writes, and report anything odd.

A [ground tile map](../build/ground-tile-maps.md) is an ASCII grid, and typing one is
easy. The hard parts are seeing it and checking it. Edges, fringes and shade depend on the
neighboring cells, so a map only really shows in the game. The **Tile Map Editor** paints
the grid and draws it with the mission's own art, the way the game does.

It is part of the **Artemis AMD** VS Code extension.

## Open it

Open any `.tiles` file and it opens in the editor. **Text** on the toolbar switches to the
plain text editor. To come back, use **Open in Tile Map Editor** on a `.tiles` text
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

## What it writes

The text file is the map. A stroke rewrites **only the rows it changed**, so comments,
the header and the legend's spacing are left alone, and each stroke is one step of undo.
A row's trailing blanks are dropped, because they mean *nothing* anyway.

## Not yet

- Props, people and hostiles from the `.amd` are not drawn on the map, and cannot be
  dragged into place. `sbs lint` already checks where they stand.
- A sprite's `color` tint is not applied in Art mode.
- `.tileset` files get syntax highlighting and checks, but no visual editor.
