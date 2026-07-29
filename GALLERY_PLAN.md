# Control Gallery

Grow the Overlay Demo into a **Control Gallery**: a browsable, runnable catalog of the
Cosmos GUI, in the shape of Material Design's component gallery or Storybook, but built
for a system whose docs are a skill file and whose widgets are `send_gui_*` commands.

- Overlay system it grows out of: `OVERLAY_PLAN.md`, `OVERLAY_ADOPTION_PLAN.md`
- The knowledge it makes runnable: `.claude/skills/cosmos-gui/SKILL.md`
- API docs it should replace the "what exists?" half of: `mkdocs/docs/cosmos/gui*.md`

---

## The problem

Today a mission author learning the GUI has three bad options: grep `procedural/gui/`
for `def gui_`, read a skill file written for an agent, or copy a fragment out of
LegendaryMissions and hope the surrounding context isn't load-bearing. There is no place
to *see* a `gui_property_list_box` before deciding to use one.

The existing `overlay_demo` is a **verification harness**, not a teacher: twenty buttons
that each fire one effect. The button says "Hero + Letterbox" and the code that produced
it is in a file you are not looking at.

## The one idea

> **The gallery renders the exact lines of its own source that built the specimen you are
> looking at.**

Every specimen is wrapped in markers in the `.mast` file:

```
# >>gallery: list_box_basic
    lb = gui_list_box(items, "row-height: 2.2em;", item_template=row_fn, select=True)
# <<gallery
```

At runtime the mission reads its own source, slices between the markers, dedents, and
renders it beside the live control. The snippet cannot drift from the demo, because it
**is** the demo. `gui_clipboard_put` exists, so "Copy" is a real button: see a control,
copy working MAST, paste it into your mission.

Doc-rot is the failure mode every gallery-shaped thing eventually dies of. This design
makes it unrepresentable.

---

## Where it lives

Grow `missions/overlay_demo` in place. It already carries the LM stack, a map, players,
a station and a docking setup that the Overlays category needs, and it is already a
published repo (`artemis-sbs/overlay_demo`).

- Folder name stays `overlay_demo` (so `sbs debug overlay_demo` keeps working, and the
  git remote is untouched).
- `description.yaml` display name becomes **Control Gallery**.
- The two existing consoles survive unchanged as the **Overlays** category.
- Renaming the GitHub repo later is a one-click redirect; not a blocker, and the user's
  call.

```
overlay_demo/
  story.mast              map + the existing overlay consoles; imports the gallery
  gallery.mast            the shell: @console/gallery, nav, detail pane, dispatch
  gallery_controls.mast   Controls specimens          (marked spans)
  gallery_layout.mast     Layout playground           (marked spans)
  gallery_recipes.mast    Recipes                     (marked spans)
  gallery_traps.mast      Traps: BROKEN / FIXED pairs (marked spans)
  gallery_code.py         source slicer + the code-view renderer
  gallery.amd             prose per entry: blurb, when to use, do/don't, see-also
```

## Where it is shown (three surfaces)

The gallery is a **tool**, so it should not require a ship, a console assignment, or a
running crew to read.

1. **The server screen** is the browser's home. The map IS the gallery
   (`@map/control_gallery`): starting it reroutes the server to `gallery_screen`, so the
   browser is there the moment the mission starts.
   The cost is honest: it replaces LM's server main-screen and the pause/resume region
   that lives on it, so the header carries a **"Main screen"** button that hands it
   back. (The LM server console has no tab or extension hook, so a reroute is the only
   way in.)
2. **A console** (`@console/gallery`) carries the same browser, for anyone who wants it
   on a crew station or on a second screen.
3. **The Gallery Viewer console** (`gallery_pages.mast`) draws the **full-page**
   examples -- an embedded engine view, an absolutely-positioned region, a master/detail
   console. A whole screen squeezed into the browser's detail pane teaches the wrong
   thing about proportion. Picking a "Full page" entry in the browser records it for
   that client; the viewer shows whatever you last picked.

Demos that need a real crew station say so and let the reader open that console, rather
than trying to reproduce one inside the gallery.

### Does the gallery need LegendaryMissions?

Traced, not guessed. The teaching material needs **none** of LM's content -- Controls
and Traps are pure `gui_*` from sbs_utils. But two things do:

| Needs LM | Why |
|---|---|
| the console picker (`show_console_selected`) | it is how you reach `@console/gallery` and the Viewer at all |
| the Overlays category | `spawn_players`, `docking_standard_player_station`, `prefab_side_generic` -- ships, sides, docking, mainscreen fan-out |

So LM stays. The real cost of keeping it is not runtime, it is **iteration**: ~70s per
headless specimen check, nearly all of it mastlib compile. That is fixed by running
checks in parallel against disposable copies of the mission
(`scratchpad/verify_gallery.py`) rather than by trimming the mission -- copies must sit
under the missions root, since the runner refuses to start anywhere it cannot find
`__lib__/`.

Trimming to a tool mission (no LM, `content_demo`-style) and splitting into two missions
were both considered and rejected: the first loses the Overlays harness and forces a
hand-rolled console switcher, the second buys the same thing at the price of a second
repo.

## Architecture

**Shell** (`gallery.mast`). One `@console/gallery`, laid out as the pattern the skill
mandates so that reading the gallery's own source is the second lesson:

```
+----------------+--------------------------------------------+
| category +     |  SPECIMEN      (live, on a labeled surface) |
| entry listbox  +--------------------------------------------+
| (collapsible   |  KNOBS         (rewrite the style string)   |
|  headers)      +--------------------------------------------+
|                |  SOURCE        (sliced from this file)      |
|                |  [Copy]                                     |
|                +--------------------------------------------+
|                |  NOTES         (from gallery.amd)           |
+----------------+--------------------------------------------+
```

`gui_list_box(..., collapsible=True)` with `gui_list_box_header` gives the two-level nav
in one widget, titled with `title_template` (not a label row above it).

**Entry registry.** `gallery.amd` is the index and the prose; the `.mast` marker key is
the join. One entry = one AMD record + one marked span. `sbs lint` can then catch a
record whose marker does not exist, and the nav is data, not a hand-maintained list.

**Dispatch.** The detail pane is a `match SPEC:` in a per-category label, one `case` per
specimen, the marked span inside it. Selection sets `SPEC` and repaints. This keeps the
specimen code inline and copyable rather than hidden behind a Python builder.

**Source slicer** (`gallery_code.py`):

```python
gallery_source(key)   -> list[str]   # dedented lines between the markers, cached
gui_code_block(lines) -> None        # renders them as GUI rows
```

## Resolved technical risks

| Risk | Finding | Decision |
|---|---|---|
| Rendering source in `gui_text_area` | Its mini-markdown eats code: `#` (a MAST comment!) becomes an h1, `-` a bullet, `$`/`=$` style directives | **Do not use `gui_text_area` for code.** A listbox of per-line `gui_text` |
| `{` in **any** dynamic text | `compile_and_format_string` f-string-formats any props containing `{`, so a blurb reading "use `data={}`" is an empty format field and raises at present time | Brace-double (`{` -> `{{`). Applies to prose as much as to code -- one `gallery_label()` for both |
| `:` / `;` in a snippet | Would inject style properties | `gui_text_escape()` per line (backtick quoting) |
| Line indentation | Backtick-quoted leading spaces may be trimmed by the engine | Render indent as a per-row `padding`, not as spaces. Verify in browser |
| No monospace font | Fonts are `gui-1..gui-6` + `smallest` | Accept. Color-code instead: comments dim, strings amber, keywords light |
| Specimen code cost | Every specimen is layout built each repaint | Build one specimen at a time (the selected one), not all |

## The five categories

| Category | Contents | Why it earns a place |
|---|---|---|
| **Controls** | one entry per widget: text, text_area, button, icon_button, checkbox, radio/vradio, drop_down, slider, int_slider, icon (+ atlas, named), image, face, ship, grid, table, list_box, property_list_box, input, region, hole, blank | the catalog. "What exists at all" is currently only discoverable by grepping |
| **Layout** | four inline specimens (row-height modes, col-width modes, size arithmetic, `overflow:`) plus a full-page **playground** on the Viewer: dropdowns set row-height, col-width and font, and the boxes move under you | the hardest part of the system and unteachable in prose. Absorbs what `content_demo` demonstrates by hand |
| **Recipes** | watch/repaint (state changed by another task), a status line, a reusable `gui_style_def`, and a **shelf of four `item_template`s** switched live by a dropdown | this is what `HelloWorld/simple_gui.py` already is -- a scrappy row template someone learned from. Ship a curated shelf. (Listbox + detail and engine-widget embedding live in **Full page**, where they have room.) |
| **Traps** | each trap is **two buttons side by side, BROKEN and FIXED**, with the diff between the two snippets underneath | teaching by contrast. Nothing in a doc page beats watching the broken one misbehave |
| **Overlays** | the two existing consoles, unchanged | screen-anchored surfaces are part of the control surface, and multi-console fan-out is an axis no web gallery has |

Traps, from the skill's gotcha list, each runnable:

- `.update("text:X")` dropping the rest of the style vs. carrying it whole
- `on gui_message` registered in a `for` loop vs. `on_press=` / `data=`
- `row-height: 1em` under `font:gui-3` overdrawing by 4px
- `padding` top/bottom eating row height
- a content row starved by fixed `em` siblings
Built: `update()` dropping the style, the for-loop handler, `1em` under a bigger font,
padding eating row height, the starved content row. Each opens a BROKEN and a FIXED
frame of identical size, captions outside the marked spans, and both snippets below the
panel that drew them. Only the fix gets a Copy button.

Two candidates deliberately left out, because a gallery entry has to *run*:

- **the multi-line dict literal.** Its whole point is that it does not compile, so it
  cannot live in a file the mission loads. It would have to be quoted text, which is a
  doc page, not a specimen.
- **`gui_represent()`** (deprecated). Correct code and dead code look identical on
  screen; there is nothing to watch.

## Second and third jobs

- **`--exercise` walks every specimen**, making the gallery a broad GUI smoke corpus:
  MAST-layer errors across the whole widget surface in one headless run.
- **The Layout category is a regression corpus** for the sizing-accuracy work:
  `--audit-layout` over the gallery gives mock-vs-engine deltas across the full widget
  set instead of hand-picked cases.
- **`gui_screenshot`** can generate the images for `mkdocs/docs/cosmos/gui*.md`, so doc
  images stop drifting too.

## Phases

| # | Deliverable | Done when |
|---|---|---|
| **1** | Shell + code view + 7 Controls specimens | selecting an entry shows a live control and the real source that built it; browser-verified |
| **2** | Controls complete (all widgets), `gallery.amd` prose, Copy button | every `gui_*` layout widget has an entry |
| **3** | Traps | each trap runs broken and fixed side by side -- **built**, 5 traps |
| **4** | Layout playground | row/column sizing modes driven live from dropdowns -- **built** |
| **5** | Recipes, incl. the `item_template` shelf | a new author can copy a working listbox + detail -- **built** |
| **6** | Guided tour narrated through the overlay lower third; README rewrite | the gallery introduces itself |

Later, not now: folding in `content_demo`, `layout_probe` and `font_measure`. They are
measurement rigs with their own output formats and would distort the shell before it has
settled. Promote `gui_code_block` into `sbs_utils` only once it has proven out here.

## Phase 1 status (built)

`gallery.mast` (shell + 7 Controls specimens), `gallery_code.py` (slicer, code view,
index), `gallery_specimens.py` (the Python row templates one specimen references),
imported from `story.mast`.

Confirmed working: span slicing, dedent, and **cross-file concatenation** -- the
`list_box_basic` snippet shows the `.mast` listbox line *and* the Python
`item_template` / `title_template` it points at, under one key. All 7 specimens build
without a runtime error (one headless run each, `--exercise-console gallery`).
Outstanding: the browser pass.

Two things found while building it, both worth keeping:

- **`--exercise` never entered a mission-defined console.** The cycle was hardcoded to
  the five core gameplay consoles, so the gallery -- and the existing overlay consoles,
  and every custom console in every mission -- had zero headless coverage. Added
  `--exercise-console NAME[,NAME]` (opt-in; unchanged by default) in
  `cosmos_dev/exerciser.py` + `mission_runner.py`. It found a real bug on first run.
- **A hook-level error inside a listbox `item_template` still reports `PASS`.** The
  template raised a `TypeError` on every repaint, printed a full traceback, and the
  verdict said "PASS - no runtime errors". Same family as the compile-error gap that
  `--test` already closed; `MastVerdict` should count these. Not fixed here.

## Verification

Per the standing tiers: `--test` (compiles) -> `--exercise` (drives the GUI) -> **browser**
(the only place layout and render are real) -> engine session for anything overlay- or
draw-order-shaped. A gallery is never done off `--test` alone.

## Costs, honestly

Engine-only verification grows with every specimen. Source slicing needs the `.mast`
readable at runtime, which is fine for a loose mission file and awkward if this ever
becomes a packaged addon. And a gallery is a maintenance surface: a widget added without
an entry is now a visible gap. That is good discipline, but it is discipline.
