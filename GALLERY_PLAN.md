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

Grow the mission that was `missions/overlay_demo` in place. It already carries the LM stack, a map, players,
a station and a docking setup that the Overlays category needs, and it is already a
published repo (renamed to `artemis-sbs/control_gallery` once the fold landed;
the FOLDER was renamed to match afterwards, so it is now
`missions/control_gallery` and `sbs debug control_gallery`; GitHub redirects the old
repo URL).

- Folder name initially stayed `overlay_demo` to keep `sbs debug` and the launch
  config working; it was renamed to `control_gallery` once the fold had landed.
- `description.yaml` display name becomes **Control Gallery**.
- The two existing consoles survive unchanged as the **Overlays** category.
- The GitHub repo was renamed `control_gallery` after Phase 7, with the About text
  rewritten to match. The local folder was deliberately NOT renamed.

```
control_gallery/
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
| **2** | Controls complete (all widgets), `gallery.amd` prose, Copy button | **done** -- 19 controls, prose authored in AMD, index cross-checkable as text |
| **3** | Traps | each trap runs broken and fixed side by side -- **built**, 5 traps |
| **4** | Layout playground | row/column sizing modes driven live from dropdowns -- **built** |
| **5** | Recipes, incl. the `item_template` shelf | a new author can copy a working listbox + detail -- **built** |
| **6** | Guided tour narrated through the overlay lower third; README rewrite | **done** -- and the tour doubles as the test driver |

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

---

# Phase 7 — fold Overlays in, and morph the Viewer

**BUILT.** Two consoles and 31 buttons became 17 specimens in an **Overlays**
category, and the Gallery Viewer morphs into any of seven consoles. The mission
now offers exactly two consoles -- verified by calling
`gui_get_console_type_list()` (which applies each label's `if` gate) rather than
counting `@console` labels: `offered=['gallery', 'gallery_viewer']`.

Five things the build changed or found:

- **A role outlives the page that added it.** The Viewer adds
  `gallery_viewer` to itself, and nothing took it off -- so a client that visited
  the Viewer and came back to the gallery still answered to
  `role("gallery_viewer")`, and "Morph the viewer" would have morphed the gallery
  you clicked it on. `gallery_screen` now clears the role it is not. Engine-
  reachable by simply switching consoles; the plan did not have it.
- **`has_role(0, ...)` is ALWAYS False**, for the server client specifically:
  `to_object()` has an explicit `elif other==0: return None`, so it resolves no
  agent and `has_role` returns False without looking. The roles ARE set -- checked
  with `role()` set membership. This first showed up as a proof harness reporting
  `role_mainscreen=False` three times while the morph was working correctly, which
  is the shape of an assertion that passes while measuring nothing.
- **Turning a console off does not unregister it.** `HELM_CONSOLE_ENABLED = False`
  only removes it from the selection screen; `gui_console("helm")` still works.
  That is what lets the mission offer two consoles and still morph into seven.
  The flags are set with a PLAIN assignment, not `default` -- LM's addon declares
  them `default ... = True` and addon load order is not deterministic, so plain
  assignment is the only form that wins either way round.
- **`--exercise` clicks nothing on these screens** (`clicks 0`), so a green run
  proved only that the specimens DREW. The overlay handlers needed every button
  label passed to `--exercise-click` explicitly (724 clicks, empty
  `mast.runtime.log`). One button had to be renamed: that flag is comma-separated,
  so a label containing a comma cannot be driven.
- **The morph cannot be reached with one client**, because the button is on the
  gallery and the role is on the Viewer. Proved instead with a temporary harness
  that faked the role on client 0 and fired the label: reroute lands,
  `CONSOLE_TYPE=mainscreen`, and `mainscreen` / `console` / `gallery_viewer` are
  all on the client; the restore puts `CONSOLE_TYPE` back and drops `mainscreen`
  while keeping `gallery_viewer`.

Answers to the plan's open questions, now that it is built:

1. **The restore is clean**, but it does need `gui_widget_list_clear()` -- a
   console leaves an engine widget list behind and the gallery page would draw
   through it.
2. Not yet checked in the engine: the mock has no second browser client, so
   `assign_client_to_ship` on the Viewer while the server screen rides the same
   ship is an ENGINE-only observation.
4. **Page state partly survives.** The picked full-page example does (module-level
   Python), the listbox hint does not (a task variable, and the reroute starts a
   new task). Not worth carrying; the reveal puts the selection back on screen.

Still engine-only, unchanged from below: **which screen reacted**. No headless run
can tell a hero drawn on the Viewer from one drawn on the browser.


**Goal:** the Overlays consoles become a gallery CATEGORY, and the Gallery Viewer
becomes a second surface that can morph into any console. Then the Viewer is the
only console the mission needs, and all seven `*_CONSOLE_ENABLED` defaults go off.

## Why fold

The two overlay consoles are 31 buttons that **do not show the code that fired
them** — the exact complaint the gallery was built to answer. As specimens they
get a source panel and a notes panel for free, and `to=` stops being something
you infer from 12 near-identical buttons.

They are also the only reason the mission needs `MAINSCREEN` plus a crew console:
the audience checklist wants two or more surfaces, one of them a main screen.

## The morph

The pattern already exists — LM's **director** addon, `director/__init__.mast`:

```
=== cv_show
    default cv_ship_id = None
    default cv_console = "mainscreen"
    if cv_ship_id is not None:
        assign_client_to_ship(client_id, cv_ship_id)
    gui_console(cv_console)
    await gui()
```

driven by `gui_reroute_client(target, cv_show, {"cv_ship_id": .., "cv_console": ..})`.

**Do not copy it as-is.** LM's own `show_main_game_screen` does three things and
`cv_show` does one:

```python
gui_console("mainscreen")
set_inventory_value(client_id, "CONSOLE_TYPE", "mainscreen")
add_role(client_id, "console, mainscreen")
```

The comment on that third line explains why: anything narrowing an audience —
overlays, `announce()`, comms targeting — uses `any_role(...)`, so a screen with
`CONSOLE_TYPE` and no role is **invisible to all of them and the message is
dropped in silence.** Since the point of this phase is testing
`consoles="mainscreen"`, a morph that skips the role would make the specimen
report a false negative. Ours sets all three, and clears the previous console
role on the way (`common_console_select` removes every console role before adding
one — same reason, or a stale role leaves a phantom mainscreen behind).

`cv_show` therefore has a latent limitation for overlay-targeted use. Worth
raising with whoever owns the director addon; not fixing in passing.

## Addressing the Viewer

The gallery needs the Viewer's client id without knowing it. The Viewer adds a
role to itself on entry:

```
add_role(client_id, "gallery_viewer")
```

and the gallery targets `role("gallery_viewer")`. Same trick the GM/admiral
consoles use, and it survives the client id being whatever the engine assigned.

## What the category holds

- **One specimen per overlay KIND** (~13): hero, banner, toast, lower third,
  modal choice, HUD + watcher, letterbox, flash, credits, an AMD-declared
  overlay, a `//overlay` route, a signal-driven show, clear.
- **A target selector**, shared: this screen · Gallery Viewer · my ship (every
  console) · my side · all players · a station (expect nothing, plus one
  `resolved to no console` log line). The resolved audience is echoed next to it,
  because that is the thing being taught.
- **Four `announce()` specimens** (chapter / alert / hail / status), each pairing
  the overlay with its durable record — the point of that category.
- **A "morph the Viewer" specimen**: the dropdown that drives it, plus its
  source. A genuinely useful pattern in its own right; the director is the
  reference.

## What this does NOT solve

- **Draw-layer stacking over a live engine view** is the one thing the current
  console tests that a server screen cannot: the gallery browser has no 3dview.
  Covered by morphing the Viewer to `mainscreen` (or helm) and firing at it —
  which is a better test than today's, because the overlay and the engine view
  are then on a screen that is not the one you clicked.
- **Two consoles of the same ship** (button 1: "banner on EVERY console of your
  ship") still needs two, and the server screen is one of them only because LM
  assigns client 0 to the first player ship. Worth asserting rather than assuming.

## Verification

- headless: `--exercise-console gallery,gallery_viewer`, and the `--walk` tour
  covers every new specimen the moment it has an AMD record.
- engine only: **which screen reacted.** No headless run can tell a hero drawn on
  the Viewer from one drawn on the browser, so the audience specimens are checked
  by looking, with two surfaces up.
- the morph needs an engine pass per target console, because `gui_console()` sets
  an engine widget list and the mock approximates it.

## Open questions

1. **Does a morph back to the gallery page restore cleanly?** The Viewer would
   reroute to `gallery_viewer_screen`; a console widget list set by
   `gui_console()` may need clearing first (`gui_widget_list_clear`).
2. **Does `assign_client_to_ship` on the Viewer disturb the browser?** They are
   different clients, so it should not — but the server screen is assigned to the
   same ship, and the audience specimens depend on that.
3. **RESOLVED — overlay slots should NOT survive a morph, so do not rely on it.**
   A morph changes what the screen IS; a hero card left from the gallery page has
   no business on a mainscreen. So the morph CLEARS overlays for that client
   (`overlay_clear(to=...)`) before rerouting, while the region still belongs to
   the page that established it.

   That deletes the risk rather than testing it: the overlay layer's known
   failure mode is a stale sub-region after the page underneath changes, and this
   never asks a region to outlive its page. It also matches how the rest of the
   system treats a new GUI -- `gui_sub_task_schedule` tasks are tagged
   `end_on_new_gui` and cancel themselves for the same reason.

   Leaves a broader question for the overlay system, NOT for this phase: should a
   page reroute clear overlays generally? Today it does not, which is why the demo
   needs explicit "Clear All" buttons. Worth asking once the fold is done.
4. **Does the Viewer keep its own page state** (the hint, the picked full-page
   example) across a morph and back? Task variables, so probably — worth a look.
