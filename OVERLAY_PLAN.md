# Overlay System — Plan

A GUI **overlay** subsystem for the StoryPage framework: screen-anchored surfaces
that draw *on top of* a console's page and its embedded engine views, updated
independently of the page's build/present pass, and driven by signals.

Covers three families under one framework:

- **Cinematic** — lower thirds, hero/chapter cards, letterbox cutscenes, credits.
- **Interactive (modal)** — full-screen choice cards, codex/lore panels, prompts
  that own input and return a result. The "better than story dialog, with controls"
  goal.
- **HUD** — sticky readouts and control clusters floating over the live view
  (fighter controls, status strips, objective trackers), replacing `comms_broadcast`
  abuse and the tile-only layout.

---

## Why this is buildable cheaply

The **info panel is already a proto-overlay** — we generalize its mechanism rather
than invent one:

| Existing mechanism | File | What we reuse |
|---|---|---|
| `TabbedPanel` draws into its **own** named sub-region (`tag+"$$"`) | `pages/widgets/tabbed_panel.py:197` | a slot = an independent absolute region, not a section in the page tree |
| Panel is **retained on the page** and re-presented every `swap_layout` | `mast_sbs/maststorypage.py:216` | overlays survive page/tab/console rebuilds without the mission re-sending |
| Fed by a **message-queue API** (`gui_info_panel_send_message`) | `procedural/gui/tabbed_panel.py:208` | `overlay_show(...)` pushes content out-of-band, no page repaint |
| Attaching a button returns an **`InfoButtonPromise`** you `await` | `pages/widgets/tabbed_panel.py:285` | modal overlays reuse an existing awaitable — no new input machinery |
| `draw_layer` style key on every `send_gui_*` (default `1001`; buttons use `10000`) | `cosmos_dev/mockgui/widget_stylestring_documentation.txt` | "draw on top" is a style value, not an emission-order trick |

So an overlay is: **the info-panel's retained-region + queue + promise pattern,
freed from the upper-left corner, multiplied into N slots, stacked by `draw_layer`.**

---

## Architecture

**An overlay = a page-retained absolute sub-region ("slot") + a content-builder +
signal-driven push + `draw_layer` stacking.**

- `page.overlays`: `slot_name → retained Layout/PageRegion`, re-presented in
  `swap_layout` alongside `info_panel` (`maststorypage.py:216`), so overlays persist
  across page rebuilds.
- Each slot has a default **rect** and default **`draw_layer`**.
- Content builders reuse existing widgets (`gui_text`, `gui_image`, `gui_face`,
  `gui_text_area`, `gui_button`). A custom overlay is `overlay_register(kind, builder_fn)`.
- `OverlayManager` on the page owns the slot dict, retain-on-swap, and stacking.

### How full page repaints are avoided

The page's full repaint is the `gui_state == "repaint"` path (`send_gui_clear` →
present *every* layout → `send_gui_complete`, `maststorypage.py:660`). Overlays stay
off it:

1. **Each slot is its own named sub-region**, not a section in the page's layout
   tree. `region_begin` emits `send_gui_sub_region` + clears/redraws only its own tag
   (`layout.py:1224`) — independent of the main content stream.
2. **Updates ride the dirty/represent path, not `swap_layout`.** `overlay_show`
   rebuilds one slot and calls `gui_represent(slot_region)` → `calc()` + `present()`
   on that sub-tree only (`update.py:4`, `layout.py:393`). No `swap_layout`, so no
   `Gui.dirty(client_id)` full-page trigger.
3. **Overlays survive legitimate page repaints** because they're retained and
   re-presented on `swap_layout`.

Cost model: a hero card or toast = one region clear + one region present. A full page
repaint only happens when the page changes for its own reasons — the overlay just
re-attaches.

---

## Slots & layers

| Slot | Default rect (%) | `draw_layer` | Default kinds |
|---|---|---|---|
| `objective` | top-right stack | 20000 | tracker, status pill (sticky) |
| `hud` | anchored to view | 21000 | fighter controls, status strip (sticky + live) |
| `corner_toast` | lower-right stack | 22000 | toast (transient) |
| `top_banner` | full-width top strip | 24000 | banner, countdown |
| `lower_third` | bottom, ~60% wide | 26000 | name-plate + line + portrait |
| `center_hero` | centered card | 28000 | hero/chapter, choice-card (modal), codex |
| `fullscreen` | full bleed | 30000 | letterbox bars, flash/vignette, credits |

Higher slots sit above lower ones (and above the page's `10000` button layer) by
`draw_layer`. Within a slot, same-slot pushes **replace or queue** (per-slot policy).

---

## Lifecycle → existing mechanisms

| Lifecycle | Behavior | Rides on |
|---|---|---|
| **Transient** (`seconds=N`) | auto-clears after a timer | info-panel `time` arg (`tabbed_panel.py:208`) |
| **Sticky** | stays until `overlay_clear`; re-presented across rebuilds | `info_panel` retain path |
| **Modal** | builder attaches buttons, returns an awaitable | `InfoButtonPromise` (`tabbed_panel.py:285`) |
| **Live** (HUD) | per-widget value updates from a watcher | `gui_update` / `.value` (`update.py:138`) |

---

## Value update vs. rebuild (the HUD rule)

- **Value change** (speed, shields, ammo, alert lamp) → `gui_update(tag, props)` /
  `.value` on that one widget. Cheapest path; because it's a value change not a
  structural one, it **does not ghost**.
- **Structural change** (toggle a control cluster in/out, swap modes, any cinematic
  card show) → **rebuild the whole slot region**, never mutate a child in place —
  the [gui_region ghosting caveat](sbs_utils/pages/layout/section.py#L151). A per-slot
  rebuild is still tiny vs. a page repaint.

A small watcher sub-task (`gui_sub_task_schedule`) polls state and pokes values for
live HUD readouts (watch/repaint pattern, at the value level).

---

## Signal contract (the trigger) — ✅ Phase 2

**`to` targeting is the core, fully library-side capability** — server story logic can
push straight to a set of consoles with no signal at all:

```
overlay_hero("CHAPTER TWO", subtitle="The Long Dark", to=role("mainscreen"))
overlay_clear("center_hero", to=role("mainscreen"))
```

`to` is `None` (caller's console) | an int client id | a role set / query. Resolution:
`to_set(to)` → `gui_page_for_client(id)` (non-console ids resolve to no page and are
skipped), then each target page's `OverlayManager` runs under a `FrameContextOverride`
so the builder targets that client. First show requests that page's repaint to
**establish**; thereafter updates are out-of-band.

**Signals are a thin bridge, NOT auto-wired.** There is no Python signal-callback
registry (a `//signal` handler must be a MAST label), so a mission authors a **one-line
`//shared/signal` forwarder** — `//shared/signal` so the dispatch runs **once on the
server** and fans out to the `to` targets (a per-console `//signal` would run N times,
each pushing to all targets). Content travels as a nested `fields` dict so the route
needs no `**kwargs`:

```
# emit from anywhere:
signal_emit("overlay", {"to": role("mainscreen"), "slot": "center_hero",
                        "kind": "hero", "fields": {"title": "CHAPTER TWO"}})
signal_emit("overlay_clear", {"to": role("mainscreen"), "slot": "center_hero"})

# forward once, on the server (mission-authored, copy-paste):
//shared/signal/overlay
    overlay_signal_show(to, slot, kind, fields)
//shared/signal/overlay_clear
    overlay_signal_clear(to, slot)
```

`overlay_signal_show`/`overlay_signal_clear` are shipped helpers. (A future mastlib
could ship the two routes so missions skip even that; deferred.)

---

## Ergonomic API — one shape, three front doors

Every overlay `kind` exposes the **same field set** whether it's called from Python,
declared in AMD, or fired by a quest hook. AMD loading is then a dict→kwargs pass and
a quest field is `<kind> <inline text | amd-key>`. One builder underneath all three.

### 1. Scripter wrappers (procedural / MAST)

Thin wrappers over `overlay_show`; `to=None` means "all consoles", every timing/style
arg defaulted:

```
overlay_hero(title, subtitle=None, image=None, to=None, seconds=None)
overlay_toast(text, icon=None, to=None, seconds=3)
overlay_banner(text, style=None, to=None, seconds=None)
overlay_lower_third(name, line, face=None, to=None, seconds=None)
overlay_credits(entries, to=None, scroll=True)
overlay_codex(title, body, to=None)              # -> await dismiss
overlay_choice(title, buttons, to=None)          # -> await result
overlay_clear(slot=None, to=None)
overlay_show(slot, kind, to=None, **content)     # low-level escape hatch
```

### 2. AMD — declare overlays as content

An `amd_overlays(section)` loader is a **projection of `amd_records`** (like every
other domain loader): `display` → title, body → the big text, fenced fields → wrapper
kwargs. Author once, fire by key:

```
# overlays.amd
# [Chapter Two](ch2)
Kind: hero
Subtitle: The Long Dark
Image: ch2
Seconds: 4
---
CHAPTER TWO
```

```
overlay_amd("ch2", to=role("mainscreen"))        # fires the declared record
```

`amd_mission_data` chains the overlay vocabulary so overlays live in the same
`.amd` file as quests/scans/landmarks.

### 3. QUEST — lifecycle fields fire overlays automatically

The quest driver's hooks (`on_accept`, `on_complete`, `on_fail`, `on_reach`,
`on_scan`, `on_dock`, `on_kill`) each accept an optional overlay directive. `to` is
**auto-scoped to the quest's participants** (per-player grant → that player's
console; server quest → mainscreens), so authors never wire targeting:

```
# [Rescue the Convoy](rescue)
On accept:   toast New job: Rescue the Convoy
On complete: hero CONVOY SAVED
On fail:     banner Convoy lost
On complete: overlay ch2        # or reference a declared AMD overlay by key
```

A directive is `<kind> <rest>` where `<rest>` is inline text for the primary field,
or `overlay <key>` to fire a declared `amd_overlays` record. Same builder, zero
targeting code in the mission.

---

## Input routing (`input:` flag) — and the deferred engine dependency

Every slot/overlay carries an **`input: passthrough | capture`** flag from day one.

- **`passthrough`** (today's default): the overlay draws; input falls through to
  whatever is underneath.
- **`capture`**: the overlay's own controls take the input.

**What works now:** overlays over **non-interactive** surfaces — the page itself,
`3dview`, cutscenes, text/status readouts — plus all cinematic + modal cards and HUD
*displays*. `on_press=` callbacks route to the page task by tag, so persistent HUD
toggles need **no** dedicated `await gui()`.

**Deferred to the engine (do not gate on it):** a button/clickregion drawn over an
**interactive** engine widget (`2dview` selection) actually *capturing* the click.
`draw_layer` controls drawing order; input routing over embedded engine widgets is
the engine's job. HUD **controls** that must sit over the interactive tactical view
are built anyway and marked "pending engine input-routing" — they light up as a
one-line `input: capture` switch once the engine honors overlay-layer input, no
redesign. Until then they run over non-interactive surfaces or beside the view.

---

## Build phases

### Engine-verified rendering rules (learned the hard way, Phase 1)

- **A sub-region is only ESTABLISHED during a full page repaint** (root
  `send_gui_clear("")`). Send `send_gui_sub_region` out-of-band and the engine
  ignores it — child widgets then dangle up to **root** (visible, but not in the
  slot, so clear can't reach them). So overlays **establish in `present_all`** (the
  repaint hook); the first `show` requests a repaint, and only *after* establishment
  do `show`/`clear` update out-of-band (`clear` → fill → `complete`, no `sub_region`).
- **Region tag must be `"<prefix>$$"`** (suffix `$$`, no leading `$$`, no colon) —
  the info-panel / listbox / `Layout.drawing_region_tag` convention. A malformed tag
  also drops children to root.
- **`complete` only swaps the back buffer forward when it holds something** — an
  empty back buffer isn't swapped (stale content stays). So clearing a slot still
  emits one invisible placeholder (a space).
- Diagnose with `overlay_debug_log(path)` (command stream to a file) — the engine's
  `get_debug_gui_tree` is painted, not copyable.

1. **Core** — ✅ **DONE + engine-verified** (show + clear). `OverlayManager` + `OverlayRegion`
   ([procedural/gui/overlay.py](sbs_utils/procedural/gui/overlay.py)): slot registry,
   `draw_layer` stacking, `input:` flag (all `passthrough`), SubPage-built sub-regions,
   `overlay_show` / `overlay_clear` / `overlay_register` / `overlay_slot_define` +
   `overlay_hero` wrapper. Wired into `StoryPage` (`__init__` + `present_all` in the
   repaint/refresh loops, [maststorypage.py](sbs_utils/mast_sbs/maststorypage.py)).
   Covered by [tests/test_overlay.py](tests/test_overlay.py) (6 tests: bracketing,
   draw_layer, retain-on-repaint, off-the-full-repaint-path, clear, end-to-end hero
   build); full suite 1478 green. **Remaining:** browser-verify render + stacking in a
   mock session (user checkpoint).
2. **Signal layer + `to` targeting** — ✅ **DONE (headless; engine pending).**
   `overlay_show`/`overlay_clear`/`overlay_hero` take `to` (None | client id | role
   set), resolved via `to_set` → `gui_page_for_client` and driven under a
   `FrameContextOverride` per target page. `overlay_signal_show`/`overlay_signal_clear`
   forwarders + the mission-authored `//shared/signal/overlay(_clear)` pattern (no
   Python signal registry exists). 7 new tests (`to` resolution, fan-out, clear
   targeting); full suite 1487 green. Demo wires the signal path end-to-end.
3. **Three proofs (one per family)** — ✅ **DONE (headless; engine pending).**
   `overlay_toast` (transient, auto-dismiss via `TickDispatcher.do_once`),
   `overlay_banner` / `overlay_lower_third` / `overlay_credits` + `overlay_hero`
   (cinematic; all support a `seconds` auto-dismiss), and `overlay_choice` (modal:
   `gui_button(on_press=Promise)` → returns an awaitable resolving to the pressed
   label; button clicks route via the merged `page.tag_map`, the proven info-panel
   path). 7 new tests incl. the full click→promise resolve; suite 1494 green. Demo
   drives each, with a background-task modal (`await overlay_choice(...)`).
4. **HUD** — ✅ **DONE (headless; engine pending).** `overlay_hud(rows, controls,
   title)` sticky slot + `overlay_hud_update(rows=…)` via `OverlayManager.patch`
   (merge fields → out-of-band re-fill, no page repaint). Rows are `label: value`
   text (one per row); controls are `is_sub_task` buttons so a toggle doesn't hijack
   the console gui. Live update is **watcher-throttled** (update only when a shown
   value changes) — cheaper than per-widget `gui_update` and correct given overlays
   rebuild on repaint anyway (per-widget gui_update by stable tag noted as a future
   optimization). 5 new tests; suite 1499 green. Demo: live HUD over `3dview` with a
   watcher sub-task + a Toggle Alert control. `2dview` controls still pending engine
   input-routing.
5. **Declarative bindings** —
   - **5A (sbs_utils) ✅ DONE (headless).** `amd_overlay.py`: `amd_overlays(section)`
     (a projection of `amd_records` — registered via `MastGlobals.import_python_module`)
     + `overlay_amd(key, to, **overrides)`. Fence fields → content; body → the kind's
     primary field (title/text/line); `Seconds` coerced + auto-dismiss; per-kind default
     slot. 6 new tests; suite 1509 green. Demo loads `overlays.amd` and fires `ch1`.
   - **5B (LegendaryMissions) ✅ DONE (headless).** `quest_driver` fires overlays at
     accept / complete / fail to the quest's **participant consoles**
     (`_quest_audience` ships → `linked_to(ship,"consoles")`). BOTH directive forms:
     a declared reference (`complete_overlay: key` → `overlay_amd`) and inline
     (`on_complete: <kind> <text>`, or `on_complete: overlay <key>`); underscore or
     space authoring both work. 8 LM tests (`quests/test_quest_overlay.py`); existing
     45 quest tests still green. Demo grants a quest with both forms + a Complete Quest
     button. (sbs_utils `overlay_amd` took a `fields=` dict instead of `**overrides`
     to dodge the IDE-linter `**kwargs` false positive.)
6. **Polish** — transient timers, same-slot queue policy, letterbox/flash on
   `fullscreen`, browser-verify actual stacking + render (mock only approximates
   layout; `--test` can't confirm z-order or input).

---

## Gotchas (already on the radar)

- **Full-rebuild-per-show** for structural/cinematic overlays to avoid region
  ghosting; value updates go per-tag.
- **ASCII-only** engine text — no emoji / smart quotes / em-dashes.
- **`draw_layer` must exceed 10000** (the page's button layer) to sit on top.
- **Verify in the browser, not `--test`** — stacking and input routing are real only
  in a session; the mock approximates layout.
- **`--test` can silently PASS** on a broken multiline literal / global tab add;
  confirm overlays actually render.
