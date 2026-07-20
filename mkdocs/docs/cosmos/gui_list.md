# Custom lists — `gui_list`

`gui_list` gives you a **scrolling, selectable list where you design the row
yourself**. You write the row once, right where the list is, and it runs for
every item — so the same layout is repeated down the list, filled in with each
item's data.

Use it when a plain [table](gui_table.md) of columns isn't enough — when a row
needs a picture, a button, two lines of text, whatever you like.

## The shape

```
with gui_list(ships) as ship:
    gui_text("{ship.name}")
    gui_text("Hull: {ship.hull}%")
```

Read that as: *"for each `ship` in `ships`, lay out this little block."* The word
after `as` (`ship` here) is **one item at a time** — use it inside the block to
fill in that row.

Everything you put in the block becomes that row. Several widgets on one row sit
side by side, like cells:

```
with gui_list(ships) as ship:
    gui_text("{ship.name}")          # left cell
    gui_text("{ship.side}")          # middle cell
    gui_button("Hail"):              # right cell — a real button
        jump hail_ship
```

## Letting the player pick a row

Add `select=True` and the player can click a row to select it:

```
with gui_list(ships, select=True) as ship:
    gui_text("{ship.name}")
```

The list scrolls on its own when there are more rows than fit.

## Where the data comes from

`ships` is just a list you make in MAST — of anything:

```
ships = ["Artemis", "Intrepid", "Raptor"]        # a list of names
```
```
ships = [
    {"name": "Artemis",  "hull": 100},
    {"name": "Intrepid", "hull": 85},
]
with gui_list(ships) as ship:
    gui_text("{ship['name']}  —  {ship['hull']}%")
```
```
ships = all_ships()                               # or a list you already have
```

Whatever each item is, the `as` name becomes that item while its row is drawn.

## Options

| Option | What it does |
|---|---|
| `select=True` | let the player click to select a row |
| `multi=True` | allow more than one selected row (with `select`) |
| `title="…"` | show a heading row above the list |
| `style="…"` | style the list container |

## `gui_list` vs `gui_table` vs `gui_grid`

Pick by what the row needs:

- **[`gui_table`](gui_table.md)** — rows are **columns of data** that line up
  neatly (Name / Hull / Side), with a header. You describe the columns; it builds
  the rows. Best for record-like data.
- **`gui_list`** — you **design the row** (mixed text, buttons, faces…). Best
  when a row is more than aligned columns.
- **[`gui_grid`](gui_grid.md)** — a **fixed, non-scrolling grid** of items (like a
  palette of buttons). No selection or scrolling.

All three can be written entirely in MAST.

## How it works (the short version)

A normal `with` block runs once. `gui_list` is special: it runs its block **once
per item**, top to bottom, so each item gets its own row — and the list keeps
those rows scrollable and selectable for you. You don't have to do anything for
that; just write the row and let it repeat.
