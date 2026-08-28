# Viewscreen Plan - "On Screen" from the science console

> **Status: SUPERSEDED (2026-08-28) except for one engine check.** Phases 1-4 shipped and
> engine-verified on 1.3.5; phase 5 landed with the ownership work described below.
>
> **What this plan built is no longer the whole system.** It designed ONE viewer with a
> two-party arbitration - science versus helm - and the screen now has seven drivers. The
> replacement is `procedural/gui/viewscreen_claims.py`: a named owner, ONE baseline, and
> two tiers (`console` loses the screen to helm's control, `story` parks helm's press and
> applies it on release). Claims are FLAT - releasing goes back to what the CREW had,
> never to the previous claimant. Read `mkdocs/docs/cosmos/viewscreen.md` "Who owns the
> screen" for the current model; the API sketch further down this file is out of date.
>
> Phase 5's own list is done: `show_main_game_screen`'s `get_ship_of_client` re-link was
> audited and was indeed wrong in the `_server` variant, the LM wiring is in, and a
> two-run restart soak is stable.
>
> **Still open, and the reason this file is here rather than deleted:**
>
> * **The by-eye pass on a real LM bridge has never happened.** Everything below and
>   everything since rests on mock evidence for the camera work, which is exactly where
>   this system was wrong before. Two player ships, science puts a contact on screen,
>   weapons puts a different one up, helm presses FRONT - and the screen goes back to the
>   crew's own view.
> * **Nothing automated enters a console PAGE** (`gui 0/9`), so the console bodies are
>   covered by a static name guard and a call-sequence test, not by execution. Making
>   `--exercise` drive console pages is a `cosmos_dev` job of its own.

Science picks what the main screen shows. A drop-down beside the Follow checkbox
with four shots, and a data column that reads out what science knows about the
thing on screen, paging itself when there is more than one screenful.

The captain says "on screen"; science is the one who makes it happen.

---

## What already exists (and is therefore not being built)

Nearly all of the mechanism is in the tree already. This plan is mostly a
connector, and the parts that are genuinely new are called out as such.

| Need | Already there |
|---|---|
| Main-screen view state | `MAIN_SCREEN_VIEW` / `_FACING` / `_MODE`, inventory **on the ship**, read by `show_main_game_screen` (LM `consoles/server_console.mast:453`) and by `gui_console("mainscreen")` (`procedural/gui/console.py:104`) |
| Someone else changing the view | `handlerhooks.py:494` already writes those three keys on `main_screen_change`; `route_console_mainscreen_change` re-runs the mainscreen label |
| Slow dolly | `camera_move(to, subject, lens_from, lens_to, seconds, ease)` |
| Slow orbit | `camera_orbit(to, subject, distance, from_yaw, to_yaw, seconds, pitch)` |
| Engine auto-director | `gui_cinematic_auto(client_id)` |
| Re-aim without moving | `camera_rack(to, subject)` |
| Addressing "that ship's main screens" | `linked_to(ship, "consoles") & role("mainscreen")`, the narrowing `maststorypage.py:889` already uses |
| Tactical 2D on the main screen | `MAIN_SCREEN_VIEW == "tactical"` gives the widget list `2dview^ship_data` |
| Sizing an engine view | `gui_layout_widget("2dview")` -> `send_client_widget_rects` |
| Drawing over the screen | overlay slots, `draw_layer` 20000+, already used for hero cards addressed to `role("mainscreen")` |
| Timed paging of text too long to fit | `overlay._start_text_cycle` + `_auto_dwell` (generation-guarded) |
| Scan text for a target | `science_get_scan_data(origin, target, tab)`, `science_scan_tab`, `science_scan_def_for` |
| Rich text with headings/tables/`ship://` | `gui_text_area` mini-markdown |

**Genuinely new:** the mode state and its arbitration, the camera anchor
lifecycle, the data column and its page registry, and a comms history store
(see "The one missing store" below).

---

## The drop-down

`//gui/normal_sci` in `LegendaryMissions/consoles/layout_widgets.mast`, on the
same row as the Follow checkbox (that row is already `row-height: 35px` with the
checkbox at `col-width:90px`, so the drop-down takes the remainder).

```
Off
On Screen - Dolly
On Screen - Orbit
Tactical 2D
```

Selecting a shot calls `viewscreen_set(ship, mode, get_science_selection(ship))`.
`Off` hands the screen back to the engine.

The subject is **the science selection**, not a separate pick - so the console
already reads "select a thing, then say what to do with it", the same grammar as
Follow. Changing the selection while a shot is live re-points it (`camera_rack`
for 3D, focus change for 2D) without restarting the move.

---

## Where the data goes: a right-hand column, in BOTH modes

Decided (rather than a band above the view), for four reasons:

1. **The content is many short lines.** Scan tabs and comms traffic are lists.
   At equal area a tall narrow column holds roughly three times the lines of a
   bottom band, which means fewer slideshow pages and less churn on screen.
2. **The 2D mode can actually reflow.** `gui_layout_widget("2dview")` sizes the
   engine radar, so in Tactical the column sits *beside* the radar and occludes
   nothing. A band would have to eat the radar's vertical extent - the scarce
   axis for a view centered on the ship.
3. **The 3D mode cannot reflow** (the engine renders 3dview full-bleed), so
   there the column is an overlay on top. Using the *same rect* in both modes
   means one geometry to tune, and the crew's eye does not move when the mode
   changes.
4. **It stays clear of the surfaces already in use** - `top_banner` (0-8%),
   `lower_third` (74-94%), `center_hero`. Cutscenes and hero cards keep working
   over a live viewer.

```
+----------------------------------------------+
|  banner                                      |
+---------------------------------+------------+
|                                 |  SUBJECT   |
|                                 |  ---------- |
|        3D shot   /   2D radar   |  vitals    |
|                                 |  scan      |
|                                 |  comms     |
|                                 |            |
+---------------------------------+------------+
|            lower third (dialogue)            |
+----------------------------------------------+
```

Slot: `viewer_data`, rect `(72, 9, 99, 96)`, `draw_layer` 21000 - above the view,
below hero cards and cutscenes, so a story beat still takes the screen.

**One collision to settle:** the `objective` overlay slot is `(72, 4, 99, 40)` -
the same gutter. While the viewer is driven, the objective card is suppressed on
that console. Science is deliberately taking the screen; two cards fighting over
one gutter is worse than either choice.

---

## State model

Three keys, all inventory **on the player ship** - which is where Cosmos already
keeps main-screen state, so this is one more writer of an existing pattern, not a
parallel system.

| Key | Values |
|---|---|
| `MAIN_SCREEN_VIEW` | existing: `3d_view` \| `tactical` \| `lrs` \| `data` |
| `VIEWER_MODE` | new: `off` \| `dolly` \| `orbit` \| `tactical` |
| `VIEWER_SUBJECT` | new: subject id, `0` for none |

Scoped to the ship, so science on the Artemis cannot change what the Intrepid's
main screen shows. The audience for every camera and overlay call is
`linked_to(ship, "consoles") & role("mainscreen")`.

**Arbitration with helm is free.** Helm's engine `main_screen_control` widget
fires `main_screen_change`, which `handlerhooks` already turns into a write of
`MAIN_SCREEN_VIEW`. The viewscreen route notices `MAIN_SCREEN_VIEW` no longer
matches what `VIEWER_MODE` asked for and clears itself to `off`. Helm taking the
screen back needs no negotiation - it just takes it, and science's drop-down
falls back to Off on its next repaint.

---

## API - `sbs_utils/procedural/gui/viewscreen.py`

```python
viewscreen_set(ship, mode, subject=None)      # off | dolly | orbit | tactical
viewscreen_clear(ship)
viewscreen_mode(ship)                         # -> str
viewscreen_subject(ship)                      # -> int
viewscreen_consoles(ship)                     # -> set of mainscreen client ids

viewscreen_page_register(name, fn, order=50)  # fn(subject_id, ship_id) -> markdown | None
viewscreen_pages(subject, ship)               # built-ins + registered, empties dropped
```

Page functions return markdown or `None`; a `None` page is skipped, so the
slideshow never shows a blank. The built-ins go through the same registry as
mission pages - they are simply the first entries, which keeps one code path.

| Page | Source |
|---|---|
| `vitals` | name, class, side, hull/shields, range and bearing |
| `science` | EVERY scanned tab on ONE page, `##`-headed, via `science_get_scan_data` |
| `comms` | last N exchanges with the subject (see below) |
| `quest` | quest / objective / AMD facts bound to the subject |

Rendering is a **pure function of (subject, ship) -> markdown**, testable with no
engine and no browser - the same split `log_render` uses.

### Camera driving

No new engine calls. Per shot, against `viewscreen_consoles(ship)`:

- **dolly** - `camera_move` from a far lens to a near one, ~24s, `ease="in_out"`,
  looping; the two lens positions scale off the subject's size so a station and a
  fighter both fill the frame.
- **orbit** - `camera_orbit(..., 0, 360, seconds=~40, pitch=15)`, looping.
- **tactical** - write `MAIN_SCREEN_VIEW="tactical"`, re-run the mainscreen label,
  size the radar with `gui_layout_widget("2dview")` to leave the column, focus it
  on the subject.
- **off** - stop the move, `camera_auto`, re-assign the console to its player ship.

The four camera facts in `camera.py` all apply: the console must be **assigned**
to the object the lens rides, dolly and target must be the same object, and a lens
sitting on its own look-at point renders black. So each mainscreen console gets one
`camera_anchor` at setup and keeps it; shots move the lens, never the assignment.

---

## The slideshow

A server-side `TickDispatcher` interval advances a page index and swaps the text
area's value - one value change, not a rebuild, so the dirty system re-renders
just that widget.

- Dwell is computed from word count (`overlay._auto_dwell`, promoted to a shared
  helper - nothing about it is overlay-specific).
- Generation-guarded exactly like `_start_text_cycle`: a newer subject bumps the
  generation and the old cycle stops rather than fighting for the column.
- A subject change resets to page 0 and restarts the dwell.
- A single page does not cycle at all; it just sits there.
- The page indicator is a row of dots, not "3 / 7" - it is a viewscreen, not a
  form.

---

## The one missing store

`comms_message` is **emitted and not kept**. `comms.py:342` signals a
`COMMS_MESSAGE` carrying `other_id`, and LM's `mike_comms` prototype builds its
own `recent_list` from that signal - there is no store in the library. So the
comms page needs one:

```python
comms_history_add(player_id, other_id, entry)
comms_history_for(player_id, other_id, limit=None)
```

Capped per pair like `LOG_CAP`, fed from the `comms_message` signal, and
**registered with `register_reset_state`** so the restart soak can see it - an
unregistered module-level container is exactly the second-run bug the reset
ledger exists to catch. The `mike_comms` prototype can drop its private list onto
this afterwards.

---

## Wiring

| File | Change |
|---|---|
| `sbs_utils/procedural/gui/viewscreen.py` | new - state, camera driving, page registry, slideshow |
| `sbs_utils/procedural/gui/overlay.py` | `viewer_data` slot; `_auto_dwell` promoted to shared |
| `sbs_utils/procedural/comms.py` | comms history store + reset registration |
| `LM consoles/layout_widgets.mast` | the drop-down in `//gui/normal_sci`; re-point on `//focus/science` |
| `LM consoles/server_console.mast` | `show_main_game_screen` builds the column and reacts to the viewscreen signal |

Signal routing: the camera drive, the slideshow ticker and the state write are
**`//shared/signal/viewscreen`** - server, once. Only the per-console painting of
the column is a plain `//signal`. Five consoles must not start five orbits.

---

## Phases

1. ~~**State + arbitration.**~~ **DONE.** `procedural/gui/viewscreen.py` -
   `viewscreen_set/clear/mode/subject/is_live/consoles/helm_override`, exported from
   the gui package, hooked into the `main_screen_change` case in `handlerhooks`.
   25 tests in `tests/test_viewscreen.py`; full suite green (3075).

   Two things the build settled that the plan had left open:

   * **Facing and screen mode are left alone.** The viewer sets only
     `MAIN_SCREEN_VIEW`. It has an opinion about *what* is on screen, not about how
     the crew had it framed - and the value the engine wants in `MAIN_SCREEN_MODE`
     for a 2D view (`long` / `short`) is not ours to guess.
   * **Standing down restores what the crew had before the viewer took over**
     (`VIEWER_PRIOR`), recorded on the FIRST take only - so shot-to-shot changes do
     not overwrite it with a previous shot's framing. A helm takeover restores
     nothing: helm's choice *is* the new state.

   Arbitration compares the whole `(view, facing, mode)` triple against
   `VIEWER_EXPECT`, so a facing-only change still counts as helm taking the screen,
   while a console replaying the state it is already in does not.
2. ~~**The shots.**~~ **DONE, ENGINE-VERIFIED (engine 1.3.5).** `viewscreen_apply` drives
   dolly / orbit / tactical / off; `camera_dolly` added to `camera.py` (a push-in that
   FOLLOWS its subject - `camera_move` interpolates two fixed world points, so on a ship
   under way it turns into a fly-past). 16 more tests; suite green (3093).

   **The assignment is the thing to know.** `camera_track` assigns a console to the
   object the lens rides, because the engine only honors a camera change when the two
   match - so while a shot runs, the main screen is assigned to the SUBJECT, and
   `sbs.get_ship_of_client` on it answers with somebody else's ship. Hence
   `viewscreen_home_ship(client_id)`, which anything meaning "this console's own ship"
   must use. Standing down puts the assignment back. **Phase 5 must audit LM's
   mainscreen label for this** - `show_main_game_screen` reads
   `get_ship_of_client` and re-`link`s it as a console owner, which mid-shot would
   attach the console to the subject.

   Two bugs the tests caught, both in stand-down: a TACTICAL shot keeps no camera
   record, so routing its cleanup through the camera path leaked the 2D focus (hence
   `_release_consoles`, which runs whatever the shot was); and one shot replacing
   another handed the console back in between, clearing the home ship the new shot was
   about to need - stranding it on the subject (hence `_shots_stop(release=False)`).

   The loop is made of finite legs (a 22s dolly that ping-pongs in and out, a 48s orbit
   that carries its angle over), checked once a second. Finite legs recover by
   themselves: if one is cut short, the next tick starts another. A subject destroyed
   mid-shot stands the viewer down - the engine falls back to its own default view, so
   there is nothing to hold on to, and picking a different subject is a directing
   decision the library cannot make.
3. ~~**The column.**~~ + 4. ~~**Pages + slideshow.**~~ **BUILT; emission
   engine-confirmed, appearance NOT yet eyeballed.** Built together because they are
   one thing: `viewscreen_pages.py` (pure `(subject, ship) -> markdown`, registry +
   built-ins), the `viewer_data` overlay slot and its builder, and the paging clock. 28
   more tests; suite green (3121).

   * **One record, one ticker, for the camera AND the column.** A tactical shot has a
     column but no camera; two bookkeepers would have meant two chances to leave one
     running. `_VIEWERS` now holds every live mode.
   * **Re-show on CHANGE, advance on DWELL.** These are separate on purpose: paging
     needs the dwell, but a single-page column that never advances still has to keep a
     live value (range, shields) live. The guard is the rendered text itself, so an
     unchanged column costs one page render a second and no engine traffic.
   * **`comms_history_add/for`** in `comms.py`, filled where `comms_message` already
     builds its signal payload - one source of truth for "an exchange happened".
     Registered with `register_reset_state` and cleared on reset: the keys are object
     ids, which the next mission RECYCLES.
   * `overlay_auto_dwell` promoted out of overlay's privates, so every timed surface
     reads at one pace.

   **Corrected after the first engine session (user):** the scan tabs were one page
   EACH, so the column showed Scan and nothing else until the slideshow happened to
   come round - a contact scanned on three tabs read as a contact scanned on one. They
   are now one `science` page with a `##` section per scanned tab. The tabs are facets
   of one readout, not separate topics.

   Deliberately deferred to phase 5, where LM is touched: the **2D reflow**
   (`gui_layout_widget("2dview")` must be called from the page that builds the layout,
   which is LM's), and de-duplicating the hull-percent formula, which now exists both
   here and in LM's `results_helpers.py`.
5. **LM wiring, docs, `sbs lint` clean, restart soak** (`--runs 3 --fresh-process`).

---

## The engine check (`data/missions/viewscreen_probe`)

`Artemis3-x64-release.exe autostartserver defaultmission=viewscreen_probe` writes
`viewscreen_probe.txt` and needs no console clicks - the server console makes itself a
main screen with the same four lines LM uses, so it measures the library rather than
LegendaryMissions. **Engine 1.3.5, all six checks PASS:**

| check | result |
|---|---|
| assignment moves to the subject | PASS |
| `viewscreen_home_ship` still answers with the console's own ship | PASS |
| the shot survives 12s - no spurious `main_screen_change` takeover | PASS |
| standing down restores the assignment | PASS |
| the main-screen view really becomes `tactical` | PASS |
| a 2D shot leaves the console on its own ship | PASS |

**Seven checks pass** as of the column phase - the seventh being that the data column
is really BUILT on the console's page in the engine (an overlay needs a client page,
and the server console's is not the one the mock exercises).

### What the probe cannot do, and why the visual check needs LM

**A bare probe gives a client console nothing to display.** The engine starts a client
process (`autostartclient`) and it connects, but in this mission it never joins the
ship's console list - there is no console-selection layer, which is a thing LM provides
and the library does not. So across runs the ship has exactly ONE main screen, and
which one it is has varied. The measurements are taken against whichever console is
actually in the audience (`vsp_pick`), and both kinds have now been observed driven
correctly: assigned to the subject during the shot, back on their own ship after.

**Therefore the by-eye check belongs to phase 5, on LM**, where a real bridge has a
real main screen. A first attempt at eyeballing this probe showed nothing on screen,
and the preconditions are why - the 3D view needs the sim RUNNING, a PLAYER SHIP, the
console ASSIGNED to it, and the console's page actually PRESENTED (the task has to sit
in `await gui()`, not end). The probe now does all four and reports the first three.

### The one cancellation, explained

A single run ended with the viewer stood down and the console left on the subject. It
never reproduced - and the user then said they had CLOSED that session because nothing
was showing, which is almost certainly the cause: a console going away, not a viewer
cancelling itself. A disconnect plausibly reports a main-screen state that differs from
what the viewer asked for, and the arbitration reads any such difference as helm taking
the screen.

Left as-is deliberately. `viewscreen_helm_override` now DEBUG-logs every
`main_screen_change` with the triple that arrived and the one expected, so if it ever
happens with the session still up, the log says why.

Note the probe writes TWO reports, one per console that ran the story's top-level main
(server + client). Both agree; the doubling is the usual "top-level runs per client".

## Risks - things a green headless run will not tell us

- ~~**Assignment side effects.**~~ **SETTLED IN THE ENGINE** (above): the assignment
  moves to the subject and comes back on `off`, and `viewscreen_home_ship` covers the
  window in between. What is still open is the phase-5 audit of LM's mainscreen label,
  which reads `get_ship_of_client` and re-`link`s it as a console owner.
- **Does a script region draw over the engine 3dview on the mainscreen?** Hero
  cards addressed to `role("mainscreen")` already do, so the answer is very likely
  yes - confirm before building the 3D column path. Phase 3 does 2D first
  precisely so this is not on the critical path.
- **`gui_layout_widget("2dview")` on the mainscreen console.** Honored on comms
  and science; unverified there.
- **Two ships, two main screens.** Covered by the ship-scoped state, worth an
  explicit two-player check anyway.

Verification is `engine_cli` to a named map, not a mock PASS.


---

## Decisions taken at the end of the first engine session

| Question | Decision |
|---|---|
| The science page could overflow the column | **Fine as it is.** "They should just talk to science if that happens" - the column is a headline, the console is the source |
| The one-off cancellation | **Not a bug to chase** - it was the session being closed. Instrumented in case it returns |
| `objective` overlay shares the column's gutter | **Wait and see.** Suppression is designed but not built; do it if anyone actually hits it |

## Still open

* **Nothing automated enters a console PAGE.** Headless reports `gui 0/9` - the
  exerciser connects a synthetic client but the mission ends before it walks the
  consoles. Two guards stand in for it, and they cover the class of bug that actually
  reached a browser twice (a name MAST cannot see):
  `LegendaryMissions/consoles/test_console_library_names.py` (static: every library
  function a console .mast calls must resolve) and `TestTheConsolesCallSequence` in
  `tests/test_viewscreen.py` (the drop-down's four lines, executed in order). Making
  `--exercise` really drive console pages is a cosmos_dev job of its own.
* **Re-pointing restarts the shot** rather than racking to the new subject. Fine in
  practice; `camera_rack` is there if it ever reads badly.
