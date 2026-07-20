# Grids — `gui_grid`

`gui_grid` lays out items in **even rows of a fixed number of columns** — like a
palette of buttons or a board of tiles. You say how many columns, then add
items; every so-many items it drops to the next row automatically.

Unlike a [list](gui_list.md) or [table](gui_table.md), a grid is **static** — it
doesn't scroll or let you select a row. It's for arranging a set of things
neatly.

## The shape

```
with gui_grid(3):
    gui_button("Red")
    gui_button("Green")
    gui_button("Blue")
    gui_button("Cyan")
    gui_button("Magenta")
    gui_button("Yellow")
```

That's a 3-column grid: **Red / Green / Blue** on the first row, **Cyan /
Magenta / Yellow** on the second. You don't start new rows yourself — the grid
breaks every 3 items.

## Filling a grid from a list

It works nicely with a loop:

```
with gui_grid(4):
    for color in palette:
        gui_button(color):
            jump pick_color
```

If the last row comes up short, the grid pads it so the columns still line up.

## Sizing

You can suggest a column width or row height:

```
with gui_grid(3, col_width="20%", row_height="2em"):
    ...
```

Items that already set their own width keep it; the grid's sizes are just
defaults.

## `gui_grid` vs `gui_list` vs `gui_table`

- **`gui_grid`** — a **fixed grid** of items. No scrolling, no selection. Best for
  palettes, toolbars, boards.
- **[`gui_list`](gui_list.md)** — a **scrolling, selectable** list where you
  design the row.
- **[`gui_table`](gui_table.md)** — a **scrolling, selectable** table of aligned
  data columns with a header.

## How it works (the short version)

`gui_grid` just starts a fresh row after every N items — the same rows you'd
build by hand with `gui_row`, only counted for you. That's why it can't scroll or
select: it's a plain arrangement, not a listbox.
