# GUI patterns & gotchas (sbs_utils)

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

# 2. Enable it ON the console(s) you want. `//gui/normal_<console>` runs each time
#    that console is activated, and CAN HAVE MULTIPLE handlers - so a mission (or
#    addon) adds its own without touching the consoles addon. Console suffixes:
#    engi / sci / helm / weap / comm / main (see LM consoles/layout_widgets.mast).
//gui/normal_engi
    gui_tab_enable("fabrication")

//gui/normal_sci
    gui_tab_enable("fabrication")
```

This scopes the tab to exactly the consoles you name, is flexible (any console opts in
by adding a `//gui/normal_<console>` handler), and compiles cleanly. Reserve
`gui_tab_add_top` for tabs that genuinely belong on **every** console. The OU
`fabrication` addon is the reference implementation (engine-only; the mission enables +
authors content).

## Layout

- `gui_section(style="area: x, y, x2, y2;")` — a positioned region (percent coords).
- `gui_row("row-height: 2em;")`; `gui_blank()` spacer.
- `content = gui_sub_section()` then `with content:` to fill it later; reuse styles
  with `gui_style_def(...)`.

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

## Don't

- Don't add `gui_represent(...)` — deprecated (the dirty system handles re-render).
- Don't trust the mock for compile validity or exact layout — that's what the
  browser pass and `--test`/`--exercise` are for.
