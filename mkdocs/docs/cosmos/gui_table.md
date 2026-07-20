# Tables — `gui_table`

`gui_table` builds a **declarative table**: pass your rows and a list of column
specs and it returns a real [`gui_list_box`](gui.md) — **selectable and
scrollable** — with the columns aligned, headed, and **auto-sized to their
content**. Cells can be plain text or interactive controls (checkbox, dropdown,
input, button).

It's a *helper*, not a new widget: it generates the row and header templates for
you. The thing it does that a hand-written `item_template` can't is **size columns
across all the rows at once** — a per-row template only ever sees one row, so it
can't know how wide the "Name" column needs to be for the whole list.

## Two ways to write one

**Declarative** (below) — describe the columns and it builds the rows. Best when
each cell is a field of the row.

**Block form** — author the row yourself with a `with` block, like the other
containers ([`gui_list`](gui_list.md), [`gui_grid`](gui_grid.md)):

```
with gui_table(fleet, headers=["Ship", "Hull"], select=True) as ship:
    gui_text("{ship.name}")
    gui_text("{ship.hull}%")
```

Each widget in the block is a column; the `headers` line up above them. Reach for
the block form when a cell needs more than a field value (a button, a face, mixed
widgets). Pass **no** `columns` — that's what selects the block form.

## A basic table

```
fleet = [
    {"name": "Artemis",  "hull": 100, "side": "tsn"},
    {"name": "Intrepid", "hull": 85,  "side": "tsn"},
    {"name": "Raptor",   "hull": 60,  "side": "raider"},
]

gui_table(fleet, [
    {"key": "name", "label": "Ship"},                        # auto width
    {"key": "hull", "label": "Hull", "align": "c", "width": 20},
    {"key": "side", "label": "Side", "align": "r", "width": 20},
], select=True)
```

| Ship (auto, left) | Hull (20%, center) | Side (20%, right) |
|:------------------|:------------------:|------------------:|
| Artemis           |         100        |               tsn |
| Intrepid          |          85        |               tsn |
| Raptor            |          60        |            raider |

Rows can be **dicts, `MastDataObject`s, or plain objects** — the column `key` is
read from whichever you pass.

## Column specs

Each column is a dict:

| Field | Meaning | Default |
|---|---|---|
| `key` | field read from each row | — |
| `label` | header text | the `key` |
| `align` | `"l"` \| `"c"` \| `"r"` | `"l"` |
| `width` | percent number, or `"auto"` | `"auto"` |
| `type` | `"text"` \| `"checkbox"` \| `"dropdown"` \| `"input"` \| `"button"` | `"text"` |
| `options` | choices for a `dropdown` | — |
| `button_label` | label for a `button` cell | the column `label` |

### Auto-sized columns

A column with `width: "auto"` (the default) is measured against **every** cell in
that column — header included — and the auto columns then split whatever percent
the fixed columns leave. In the example above, `name` is `auto` and the two fixed
columns take `20 + 20`, so `name` gets the remaining **~60%** — and it's wide
enough for the longest ship name in the list. Mix fixed and auto freely.

## Controls in cells

Give a column a `type` and its cells become **controls**. Interactive cells write
their new value straight back into the row, and — if you pass one —
call `on_cell_change(item, key, value)`:

```
def fleet_changed(item, key, value):
    log(f"{item['name']}: {key} -> {value}", "fleet")

gui_table(fleet, [
    {"key": "name",   "label": "Ship"},
    {"key": "active", "label": "Active", "type": "checkbox", "width": 14},
    {"key": "mode",   "label": "Mode",   "type": "dropdown",
        "options": ["patrol", "escort", "hold"], "width": 26},
    {"key": "go",     "label": "",       "type": "button",
        "button_label": "Launch", "width": 18},
], on_cell_change=fleet_changed)
```

| Ship | Active | Mode | Launch |
|---|:---:|---|:---:|
| Artemis  | ☑ | `patrol ▾` | `[Launch]` |
| Intrepid | ☐ | `escort ▾` | `[Launch]` |
| Raptor   | ☑ | `hold ▾`   | `[Launch]` |

- **checkbox** — reads/writes a boolean row field.
- **dropdown** — `options` are the choices; the cell shows the row's current value.
- **input** — a text field bound to the row field.
- **button** — fires `on_cell_change(item, key, None)` on press (`value` is `None`);
  `button_label` sets its text.

The write-back to the row happens automatically; `on_cell_change` is only for
*reacting* to a change. In Python you pass a function directly; from MAST, keep the
handler out of the call (an inline `~~lambda~~` doesn't parse as a keyword argument)
— the automatic write-back still works without one.

!!! note "Structure is declarative, behavior is Python"
    The column list describes **what** the table is — types, labels, widths. The
    **behavior** — what a changed cell *does* — stays in the Python `on_cell_change`
    callback. That split is deliberate: the spec never grows conditionals or event
    logic.

## Notes

- `select=True` makes rows selectable; read the choice with `get_value()` /
  `get_selected()`, same as any [`gui_list_box`](gui.md).
- `header=False` drops the column-label row.
- `font=` sets the cell/header font tag; `style=` sets the row style
  (row-height, padding).
- For a **static, formatted** table inside a text block (not an interactive grid),
  use a [`gui_text_area` pipe table](gui.md#rich-text-areas) instead.
