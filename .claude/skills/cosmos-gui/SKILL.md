---
name: cosmos-gui
description: Building GUIs and consoles in Cosmos: the dirty system, style strings, gui_text_area markdown, listboxes, the for-loop handler trap, engine widgets, console tabs, and layout/content sizing. Use when writing or debugging any gui_* code, console or panel.
---

The GUI is the `procedural/gui/` wrappers (`gui_text`, `gui_button`, `gui_list_box`,
…) over the engine's `sbs.send_gui_*` commands. This file collects the patterns and
gotchas that **bite repeatedly** — read it before building a console or panel.

- Full widget API: the `typings/**/*.pyi` stubs + `MAST_CLAUDE.md` ("GUI System").
- Every valid style-string key per engine command:
  `f:/a/Cosmos-1-3-0/data/widget_stylestring_documentation.txt`.

---

## Best practices (do this)

- **Build the layout once, update the data.** Lean on the dirty system (below):
  set `.value` / `.update()` or drive an `on change`, rather than tearing down and
  rebuilding the whole page every time one number moves.
- **One main GUI task per client.** Each console client sits in a single
  `await gui()`. Run live watchers as **sub-tasks** (`gui_sub_task_schedule`) that
  auto-cancel when a new page is presented — don't spin your own loops on the main
  GUI task.
- **Watch/repaint for live panels.** The standard live-panel shape: a watcher
  sub-task polls state and calls `gui_task_jump("repaint")` when it changes; the
  `repaint` label rebuilds that section. (Lighter alternative: update a widget
  handle from an `on change` — see the dirty system.)
- **Every repeating list is a `gui_list_box` + a detail panel** (see Listboxes),
  titled with `title_template` — not a stack of buttons, not a text-label row.
- **Feedback must land on a surface that's actually shown.** A console with no info
  panel will silently drop `comms_info_card` / info-panel messages — put
  confirmations in a **visible status line**, or add the panel. Route
  chatter/notifications to the **info panel** (`comms_info_card`), not the text
  waterfall; keep the waterfall for pure mechanical status.
- **Legible over pretty.** Generous `row-height`, real contrast, `$text:` first.
  Ugly-but-readable beats clever-but-cramped (the first Admiral-console review note).
- **Prefer `on_press=` / `data=` on buttons** over loop-registered `on gui_message`
  (see the for-loop trap) — it's the reliable path for per-item handlers.
- **Size sections deliberately.** `gui_section(area: …)` in percent; give panels the
  space their content needs (a build-status panel wants real height, not a strip).
- **Verify tiers in order:** `--test` (compiles / doesn't crash) → `--exercise`
  (drives the GUI, catches MAST-layer errors the suite can't) → **browser** (the
  only place layout and render are real). Never call a GUI done off `--test` alone.

---

## The dirty system (live updates)

Widgets mark themselves **dirty** when their value changes; the engine re-renders
them each tick — no full `clear`/`complete` cycle. **`gui_represent(widget)` is
deprecated** (safe but redundant — don't add it).

Update a live widget by setting `.value` or calling `.update("<style>")`:

- **`.update()` REPLACES the whole style string.** Passing only `text:X` drops the
  other props (`justify`/`font`/`color`) and the widget reverts to unstyled/left.
  Carry them all:

  ```
  w.update("text:" + line + ";justify:center;font:gui-4")   # not "text:" + line
  ```

- A plain `gui_text(...)` label is built **once and goes stale.** For live text,
  keep a **handle + repaint on change**:

  ```
  t = gui_text("$text:" + status() + ";justify:center;font:gui-4")
  on change status():
      t.update("text:" + status() + ";justify:center;font:gui-4")
  ```

## Style strings

- **`$text:` comes FIRST** in a text style string.
- **`justify:left` is the default — never write it.**
  `"""$text:{line};font:gui-2"""`, not `"""justify:left; font:gui-2; $text:{line}"""`.
- Give text rows enough **`row-height` (~2.2em+)** — cramped vertical text is a
  common first review note.

## gui_text_area = rich multi-line text (mini-markdown)

`gui_text_area(props, style=None)` is **not** just a bigger `gui_text` — it parses a
**mini markdown-like language** and **auto-scrolls** (adds a vertical slider) when
content overflows its bounds. Reach for it for multi-line / formatted blocks (help,
briefings, logs, comms transcripts); keep plain `gui_text` for a single styled line.
Authoritative parser + built-in styles: `pages/layout/text_area.py`.

- **Line syntax (leading token):** `#`/`##`/`###` → h1/h2/h3 headings (auto-numbered);
  `-` → bullet; `1.`/digit-led → ordered list (auto-numbered); **blank line** resets
  style + restarts list numbering; `^` → newline (the setter maps `^`→`\n`), a line of
  `<br>`/`<br/>` also breaks; `{var}` interpolation works.
- **Inline objects** via namespaced markdown link-refs (with a `?query`):
  `![](image://KEY?scale=0.5&color=#f00&fill=fit|center)`,
  `[](ship://HULL_TAG?height=50&align=center|right)`,
  `[](face://FACESTRING?height=50&align=..)`,
  `[](style://font:gui-4;color:#8cf;background:#123)` (inline style switch).
  Define once / reference later: `[name]: image://KEY` … then `[name]`.
- **Custom / per-line styles:** built-in keys `t h1 h2 h3 p1 ul ol _`(default), each
  with font/color/prepend/indent/height. New styles via `=$name font:..;color:..` or
  `[name]: style://font:..;`; per-line override `$stylekey text…` or `$$font:..; text…`.
  Auto-number `prepend`: `1`(numeric) `a`/`A`(alpha) `i`/`I`(roman) `*`/`-`(bullet).
- **Headings: use `#`/`##`/`###`, not `$h1`/`$h2`/`$h3`.** The `$h1..$h3` per-line
  style prefix is a **deprecated** way to reach the h1–h3 styles — it still works
  (back-compat), but `#`-style markdown headings are canonical now that AMD headings
  are the link form (`# [x](key)`), so `#` in a body is always content. Prefer `#`.
- **Fast path / failure mode:** a single line with no `=`/`$`/`$text:` prefix renders
  as plain `send_gui_text` (no parsing). On **any** parse error the whole area drops to
  simple text reading `Document syntax issue line number N` — a blank/garbled area
  usually means a syntax slip on that line. (Engine is ASCII-only — no smart quotes.)

```
gui_text_area("## Status\nAll systems nominal.\n- shields up\n- 1 contact")
gui_text_area("![](image://logo?scale=0.5) Mission active")
```

## Listboxes = the repeating-list pattern

**Every repeating list is a `gui_list_box` + a context/detail panel** acting on the
selection (the settled UI pattern: Map/Research/Fleets/Requisition, the hangar
board, the quest log).

- **Label it with `title_template`** (a small fn with `gui_row` + `gui_text`), NOT a
  separate text-label row above it — so the list uses the whole section.
- `item_template=` renders each row; `select=True`; read with `get_value()` /
  `get_selected_index()` / `get_selected()` (multi).

```
lb = gui_list_box(items, "row-height: 2.2em;", item_template=row_fn,
                  title_template=title_fn, select=True)
on change lb.value:
    sel = lb.get_value()
```

## Handlers: gui_message / gui_click / change

- `on gui_message(widget):` — fires when the widget's **value changes** (button,
  checkbox, dropdown, slider, typein).
- `on gui_click(widget):` — fires when **clicked** (icons / elements with a
  `click_tag`).
- `on change <expr>:` — fires when an arbitrary expression changes each tick (a var,
  `lb.value`, `get_data_set_value(...)`, a function call). This is the repaint/watch
  hook.
- Inject locals into a handler with `data={}`; the firing widget is `__ITEM__`.

## The for-loop handler trap (bites every time)

**`on gui_message(widget):` registered inside a `for` loop is flaky** — and an
inline block captures the loop var at its **last** value (closure trap). Proven
fixes:

- **`on_press=` / `data=` on `gui_button`** (a MessageHandler) works fine in a plain
  `for` loop — the proven path.
- Or read **`__ITEM__`** in the block instead of the loop var; or **unroll** fixed
  counts (e.g. a 5-card hand).
- Comms `+` buttons in a loop: use a **handler label + data dict**
  (`+ "{lbl}" handler {"key": val}`), never an inline block.

## Engine widgets via gui_layout_widget

`gui_layout_widget("<name>")` embeds an **engine console widget** into a story-page
layout: `2dview`, `comms_2d_view`, `science_2d_view`, `weapon_2d_view`,
`radar_zoom_ctrl`, `comms_face`, `comms_control`, `ship_data`, `red_alert`,
`text_waterfall`, `comms_waterfall`, … `gui_console("helm"|"weapons"|"science"|
"comms"|…)` sets a whole standard console's widget list at once.

Detached command consoles (Game Master, the OU Admiral overseer) embed the 2D
views this way — see `MAST_CLAUDE.md` **"Detached command consoles"** for the full
pattern (cambot spawn, console-name selection routing, `comms_navigate_override` to
refresh an open menu, side-wide scan so comms enables).

## Adding a console tab (the clean, per-console way)

To add your own tab to a console (e.g. a Fabrication tab on Engineering), do **not**
use `gui_tab_add_top("x")` at a mission top level — it adds the tab **globally** and,
dropped in a mission's `story.mast`, it **silently collapses the compile** (`labels
0/N, nodes 0`, yet `--test` prints "PASS"). It works only inside a packaged addon.

Instead, register the tab **content** and **enable** it from each console's activation
route:

```
# 1. The tab's content (a //gui/tab route + a screen label).
//gui/tab/fabrication
    jump fabrication_screen

=== fabrication_screen
    gui_tab_back(CONSOLE_SELECT)
    # ... build the panel ...
    await gui()

# 2. Enable it ON the console(s) you want. The hook is `//gui/<console name>`, where
#    <console name> is the EXACT string that console passes to `gui_console(...)` /
#    `gui_activate_console(...)` - it fires each time that console is activated, and
#    CAN HAVE MULTIPLE handlers, so a mission (or addon) adds its own without touching
#    the console's own code. Names: the standard consoles are `normal_engi`,
#    `normal_sci`, `normal_helm`, `normal_weap`, `normal_comm`, `normal_main` (LM
#    consoles/layout_widgets.mast); the hangar is `hangar`; a custom console is whatever
#    you named it. Enable is what scopes the tab - so drop any `CONSOLE_SELECT ==` gate.
//gui/normal_engi
    gui_tab_enable("fabrication")

//gui/normal_sci
    gui_tab_enable("fabrication")
```

This scopes the tab to exactly the consoles you name, is flexible (any console opts in
by adding a `//gui/<name>` handler), and compiles cleanly. Reserve `gui_tab_add_top` for
tabs that genuinely belong on **every** console. The OU `fabrication` addon is the
reference (engine-only; the mission enables per console + authors content); the LM casino
tab (enabled from `//gui/hangar` in the maps folder) and the OU admiral galaxy tab follow
the same pattern.

## Layout

- `gui_section(style="area: x, y, x2, y2;")` — a positioned region (percent coords).
- `gui_row("row-height: 2em;")`; `gui_blank()` spacer.
- `content = gui_sub_section()` then `with content:` to fill it later; reuse styles
  with `gui_style_def(...)`.
- **`col-width` / `row-height` are in the SAME units as the enclosing `area:`** —
  screen percent, not a fraction of the panel. In a section spanning `51..99`,
  `col-width: 26` is about half of it; `col-width: 55` runs off the right edge.

## Sizing to content (v1.4.0)

Rows and columns FILL by default — the section's height is split across rows, the
row's width across columns. Add a keyword to size to the content instead:

```
gui_text("$text:`Shields:`;", "col-width: content;")   # hugs its own text
gui_text("$text:`{value}`;")                           # takes the rest
gui_row("row-height: content;")                        # as tall as its tallest cell
```

| keyword | on a **column** | on a **row** |
|---|---|---|
| `content` | natural width, clamped to what's available | tallest cell at its final width, wrapping included |
| `min-content` | widest unbreakable word | **alias of `content`** |
| `max-content` | the whole line, unbroken | tallest cell as one unwrapped line |

**These are requests, not reservations.** When a row can't hold everything, flex
columns shrink to 0 first, then content columns shrink toward `min-content`, then
it clamps. Over-tall content rows scale down proportionally so flex rows aren't
left negative. Fixed rows are never scaled.

Things that bite:

- **Content can't invent space.** Fill a section with fixed `em` rows and the
  content rows are correctly squeezed to nothing. If a content row renders
  zero-height, the section is oversubscribed — that's the layout, not a bug.
- **Not everything is measurable.** `Dropdown`, `Slider`, `Ship` and console
  widgets deliberately decline (their size includes engine-drawn chrome nobody
  can measure), so they **fall back to flex, never to zero**. That's what makes a
  section-level `col-width: content` safe — it cascades to every column in it.
- **Squares ignore content width** and never drive a content row's height — a
  square is sized *from* the row height, so that would be circular. A row of only
  squares has no natural height and falls back to flex.
- **`TextArea` declines too** — it already scrolls to handle its own overflow.
- Row heights over **wrapping text in a narrow column** are the least certain
  case: mock wrap matches the engine at ≥600px column width and 94% at ≥300px,
  but diverges below that. The engine does not clip, so a row short by one line
  spills into whatever is under it. Check narrow wrapping cases in a real
  session — `missions/content_demo` exists for exactly this.

**`1fr` is the DEFAULT** (`layout.AUTO_DEFAULT`): a row/column that declares
nothing still shares the leftover space but is never squeezed below its
`min-content`. The other three take it out of the flex pool entirely.
Names follow CSS: this mode is CSS's `1fr`/`flex: 1`, NOT CSS's `auto` (which
means content-driven). `auto` still works as an alias; prefer `1fr` in new work.
`fit-content` aliases `content`; `visible` aliases `overflow: spill`. `hidden`
is deliberately NOT an alias of `hide` -- CSS `hidden` clips, ours does not draw.

**No row is squeezed below its content to pay for another** (min-constrained
water-filling), and a nested section measures its rows WRAPPED when the width
is known, so it asks its parent for the height it really needs.

**`em` is one line of the ROW's font, and an unfonted row is `gui-2` (24px).**
A `row-height: 1em` row holding `font:gui-3` text is 4px short and overdraws.
Declare the font on the row, or use `content`. One line: smallest 18, gui-1 22,
gui-2 24, gui-3 28, gui-4 32, gui-5 36, gui-6 52.

**Padding is `left, top, right, bottom`; top/bottom come out of the row height.**
A single value (`padding:13px`) is horizontal only and costs no height. A row
needing one gui-3 line plus 10px top padding is `row-height: 1em+10px`.

**Arithmetic works** in row-height/col-width (`1em+10px`, `62-25px`) — before
v1.4.0 a `+`/`-` term was silently dropped.

**In a listbox item template, size the ROWS — never return a height.** The
listbox only calls `resize_to_content()` when the template returns `None`, and
each item section starts at zero height; returning a size leaves it degenerate,
which kills selection and the click region. Content keywords inside a listbox
template still fall back to flex.

**A `carousel=True` listbox is the exception: its item IS the panel**, so the
item section is handed the box's remaining height (minus the prev/next nav
band), and a **flex row in the template works normally**. Prefer that over a
fixed height — a fixed `em`/`px` row does not shrink with the window, so a
template tuned at 768 tall runs off the bottom of a 600-tall one. Stacked
(non-carousel) items still start at zero and must use fixed rows.

**`overflow:` — `spill` (default) | `shrink` | `ellipsis` | `hide`** on any
text-bearing widget, applied at present time against the final rect. For text
that cannot fit at any size; not a substitute for sizing the row properly.

Cost: a layout using none of these keywords pays one identity comparison per
column and nothing else. Sizing to content does make a *value* change a *layout*
change, but only when the measured size actually moves — same-width text stays on
the cheap visual-only path.

## The engine compiler is stricter than the mock — VERIFY IN BROWSER

The headless mock (`--test`) is **permissive**; the engine MAST compiler is
stricter, so a GUI can pass `--test` and still fail to compile (or mis-render) in
Cosmos. Confirmed gotchas:

- **Colons inside a quoted string** in an `on ...:` / `await ...:` header now
  compile fine (fixed v1.4.0) — e.g. `on gui_message(gui_button("Test Upgrades:")):`.
  On an **older sbslib** the `:` was mistaken for the block colon; the workaround
  there is to assign the button to a **var** first, then `on gui_message(btn):`.
- **Don't start an identifier with `jump`** (`jump_btn`) — it parses as a `jump`
  statement. Use `go_btn`.
- **IDE-linter false positive:** *"Missing required argument(s): 'fields'"* on a
  `+ "label" handler` comms button (no data dict) — the real compiler accepts it.
  Verify with `--test`, not the editor.
- **Comms button conditions run OUT of task** in the engine — `+ "x" if cond:`
  re-evaluates outside the route's task, where loop/task vars are undefined
  (NameError spam). Make `+` buttons **condition-free**; gate them with plain `if`
  statements in the route body.
- Engine-rendered text is **ASCII-only** — no emoji / smart quotes / em-dashes.

The user verifies the **actual render in the browser** at each checkpoint — the
mock approximates layout, it doesn't guarantee it.

## The Options button

`gui_options_button(transparent=True, client_id=None)` — makes the engine Options
button transparent **and keeps it that way**.

Do NOT call `sbs.transparent_options_button()` directly from a story page: it is a
one-shot, and `StoryPage.on_new_gui()` restores the button on **every** new GUI —
which fires from `add_tag`, on the first tagged widget of a build. So anything set
at the top of a screen label is taken back a moment later, on every rebuild. The
same raw call works fine in a **cinematic**, because no story page is being built,
which makes this look like a wrong flag value when it is an ordering problem.

`1` is transparent (the library's own restore is `0`). `gui_options_button` records
the intent per client and the page restores to *that*, so where you call it stops
mattering. Absent intent defaults to `0` — a mission that never calls it is
unaffected.

Pair with `sbs.suppress_client_connect_dialog(0)` (the flag is the DIALOG's state:
`0` hides the connect nag, `1` brings it back) when a mission owns the server
screen. That one is a genuine one-shot and is fine from the `@map` body.

## Don't

- Don't add `gui_represent(...)` — deprecated (the dirty system handles re-render).
- Don't trust the mock for compile validity or exact layout — that's what the
  browser pass and `--test`/`--exercise` are for.
