# Cinematic Plan — camera, cutscenes, rundowns, and the widgets they need

Where this is heading, captured because it spans sessions:

1. **Scriptable camera animation**, within what the engine actually allows.
2. **Paired with overlays** to make real cutscenes — framing, furniture and text moving together.
3. **Rundowns**: prepared shots a director can *punch* to live, for the streaming case.
4. **Richer lower thirds**, including the two-face conversation layout.
5. A **flat click-region button**, because overlay furniture needs a control that is text on a
   background rather than engine button chrome.

Related plans: [OVERLAY_PLAN.md](OVERLAY_PLAN.md) (the surface all of this draws on),
[OVERLAY_ADOPTION_PLAN.md](OVERLAY_ADOPTION_PLAN.md), [GALLERY_PLAN.md](GALLERY_PLAN.md)
(where every new widget earns a specimen).
Proving ground: **`missions/VisualTestRange`** — every phase below lands a specimen there.

---

## 0. Scripted camera: what actually renders (2026-08-01)

Established with `missions/CameraRepro` - a raw `script.py`, no sbs_utils, no MAST, no
framework, every line a direct engine call. **An earlier version of this section claimed only
`dollyID` 0 works. That was wrong** - a faithful Game Master replica renders with a real id.
Left here as written because the sequence matters:

| rung | call | result |
|---|---|---|
| 1-3 | view modes `chase` / `first_person` / `tracking`, no cinematic | **draw** |
| 5 | `cinematic` mode, script control RELEASED (engine director) | **draws** |
| 4 | scripted, ids **0/0**, zero offsets (Manual Beams' call) | **draws** |
| 7 | scripted, `dolly=target=`NPC id, **zero** offsets | **black** |
| 8 | scripted, `dolly=target=`player-family cambot, **zero** offsets | **black** |
| 9 | scripted, GM replica: `dolly=target=`a real id, offset **500** | **draws** |
| bottom row | scripted, **different** ids for dolly and target, offset 900 | **black** |

So the id alone is not it. Two candidate rules survive, and rungs 10/11 separate them:

* **Do not put the camera where it is looking.** 7 and 8 place the lens at the target's exact
  position - a zero-length view vector. 9 does not.
* **Dolly and target must be the same object.** 9, 4 and GM all pass one id twice; the black
  bottom row is the only shape passing two different ids.

Both would be worth knowing. The second is the one that costs: a cutscene that rides one object
while looking at another - the ordinary "camera here, subject there" shot - would be impossible,
and every shot would have to be composed by moving a camera object rather than by aiming.

## 1. The floor: what the engine gives us

From `data/script_documentation.txt`, the **entire** camera API:

```
cinematic_control(clientID, scriptControlsCamera, dollyID, dollyPos: vec3, targetID, targetPos: vec3)
  "for a specific client (0=server machine), this sets the values to be used with the
   'cinematic' console, which requires a 3d_view widget, and 'cinematic' == camModeTag"
```

Wrapped twice in `procedural/gui/cinematic.py`: `gui_cinematic_auto`,
`gui_cinematic_full_control`. That is the whole surface today.

Four consequences that drive every design decision below:

- **A camera is an object.** The only positional inputs are two object ids plus two offsets.
  So "animate the camera" is always "animate an invisible object", and the interesting
  engineering is a *mover*, not a camera.
- **Every change is a cut.** Swap dolly or target and the view jumps. No engine-side
  interpolation, no blend, no dissolve.
- **No lens.** No FOV, roll, depth of field, shake. Anything lens-like must be faked with
  motion or with an overlay drawn on top.
- **Per-client only.** The odd one out in a procedural layer that otherwise addresses
  `role("a") & role("b")` sets.

**Docs lag the engine.** `set_main_view_modes` documents `cam_mode = (first_person, chase,
tracking)` — "cinematic" is not in that list, yet it is what `cinematic_control` requires. It
also calls the widget `3d_view` while our code passes `"3dview"`. Trust `cinematic_control`'s
own docstring and engine runs, not that enum.

### Open questions that block design (Phase 0 answers them)

| # | Question | Why it matters |
|---|---|---|
| Q1 | Are `dollyPos` / `targetPos` **world-space or dolly-local**? | The mock adds them raw (world). If the engine does too, "over the shoulder" is inexpressible and every chase/orbit shot must recompute an anchor each tick. If local, chase and orbit are free. **This one changes the shape of everything.** |
| Q2 | Does a change of dolly/target **snap or blend**? | Assume snap. If it blends, cuts need a hold-off and the rundown's punch feel changes. |
| Q3 | How smoothly can a **server-driven anchor** move? MAST runs at 5 Hz; physics at 30. | If teleporting an anchor 5×/s stutters in the engine, motion must ride a *physics-driven object* (velocity, not position writes), which changes the mover's implementation entirely. |
| Q4 | What happens when the **dolly object is deleted** mid-shot? | Cutscenes tear down scenes; if the engine holds a dangling id the view may freeze or fall to origin. Determines whether shots must release before cleanup. |
| Q5 | Does the camera respect **`assign_client_to_ship`** or is it fully independent? | Decides whether a director's program feed needs a ship at all. |

---

## 2. Phases

### Phase 0 — Spikes ✅ BUILT, awaiting engine answers

The three specimens exist in VisualTestRange (`visual_camera_offsets`, `visual_camera_cut`,
`visual_camera_rate`) and run clean headless. **They are experiments, not regression tests** —
their value is entirely in being run in the *engine* and having Q1–Q4 written down below.
Q5 (does the camera need `assign_client_to_ship`?) is answered incidentally: none of them
assigns a ship, so if the view works at all in the engine, the camera is independent.

Each answering a question above by being *looked at* in both renderers:

- `visual_camera_offsets` — a ship rotating slowly, one camera pinned at `+X`, another at
  `+Z`. View orbits with the ship → local. Ship spins while the view holds → world. **(Q1)**
- `visual_camera_cut` — two anchors, alternating every 2s; watch for snap vs slide. Then
  delete the live dolly and watch what the view does. **(Q2, Q4)**
- `visual_camera_rate` — the same move driven three ways: MAST tick writes, a
  `TickDispatcher` interval, and an NPC under its own throttle. Whichever is smooth in the
  **engine** is how the mover gets built. **(Q3)**

Deliverable: this table filled in with engine answers, dated. Nothing in Phase 2+ gets
designed before then.

| Question | Mock says | **Engine says** | Source |
|---|---|---|---|
| Q1 offsets world or local | world (adds raw) | **WORLD** | GM orbits by rotating the offset ITSELF |
| Q2 cut or blend | cut | **SNAPS** - no blend, the mock was right | Doug, engine, 2026-08-01 |
| Q3 what drives a move smoothly | — | **per-tick re-apply is fine** | GM re-applies every camera change this way |
| Q4 dolly deleted mid-shot | — | **the view FALLS to the engine default** (a top-down on a station) - it does not freeze and does not crash | Doug, engine, 2026-08-01 |
| Q5 camera needs a ship assigned | no | **YES — assigned to a space object** | Doug, and GM assigns its cambot before setting the view up |

### The Game Master already does this — read it before building anything

`LegendaryMissions/gamemaster/gamemaster.mast` ships a working orbit-and-dolly rig around an
arbitrary selected object. It is the reference implementation, and it settles most of Phase 0
by construction:

```mast
    source = Vec3(0, 0, dolly * 10)                          # distance straight back
    source = source.rotate_around(Vec3(0,0,0), 0, orbit, 0)  # ORBIT: script rotates it itself
    gui_cinematic_full_control(client_id, sel, source, sel, Vec3())
```

What that proves, without an engine session:

- **Offsets are WORLD-space (Q1).** If the engine rotated the offset into the dolly's frame,
  the GM would not need `rotate_around` to orbit. The orbit angle is applied on the CPU.
  So Phase 2's `camera_orbit` is exactly this: rotate a vector, re-apply. `Vec3.rotate_around`
  ([vec.py:410](sbs_utils/vec.py#L410)) is the primitive, already there.
- **Both ids are the same object for a single-subject shot** — `(sel, source, sel, Vec3())`,
  matching the rule Doug gave: one object involved means both ids are that object and the
  offsets are relative to it.
- **Per-tick re-application is shipped practice (Q3).** The GM's sync loop re-applies on every
  selection change and unconditionally every ~15s. So a written move is acceptable; the mover
  does not have to ride a physics object.
- **Assignment and dolly are DIFFERENT things (Q5).** The GM assigns its client once to an
  invisible cambot (`player_spawn(..., "invisible")` + `remove_role("__player__")`), and then
  freely points the cinematic camera at *other* objects. Assignment is the console's identity;
  the dolly is where the lens sits. `camera_track` must not conflate them.
- **Dolly and orbit are just two numbers** on sliders. The whole rig is two scalars plus a
  vector rotate — which is the shape the rundown's shot definitions should take.

### Phase 1 — Camera primitives ✅ BUILT (`procedural/gui/camera.py`, 13 tests)

Shipped as `camera_anchor`, `camera_assign`, `camera_track`, `camera_auto`, plus
`camera_orbit_eye` — the GM's orbit formula as a pure function, so placing a shot by angle is
one call instead of a rediscovery. `camera_track` and `camera_auto` are set-addressed through
the same `consoles_of` resolver the overlay system uses, which was the whole point: the engine
call takes one client id.

Deliberately **not** conflated: `camera_track` does not assign. Assignment is the console's
identity and changes what it can SEE (culling follows the assigned object, not the lens); the
GM assigns one cambot for a console's whole life and then moves the lens freely.

Two things the tests pinned down along the way:

- A console id must carry the client bit (`0x8000…`). A small int resolves to no console at
  all — correctly, but silently, so a test that passes `1` asserts nothing.
- **The mock keeps per-client cinematic state across `create_new_sim()`.** Beyond test
  isolation, that means a mission restart leaves each client pointed at a dolly id from the
  *previous* sim — the Q4 dangling-dolly case, arriving by a route nobody chose.

### Phase 1 — original sketch (kept for the reasoning)

Pure ergonomics over a verified call. Keep the surface tiny — MAST back-compat means these
signatures freeze.

```
camera_track(set_or_client, dolly, eye=Vec3(...), look=None, look_offset=None)
camera_auto(set_or_client)                  # release to the engine's director
camera_anchor(x, y, z, name=None) -> id     # the invisible dolly post
camera_is_scripted(client) -> bool          # sbs_utils-side bookkeeping (no engine getter)
```

**Set-addressed** is the entire point: today a mission that does not know client ids has to
invent an indirection (VisualTestRange declares a pin into harness state and each console
applies it for itself). `camera_track(role("mainscreen"), anchor, eye=...)` deletes that
dance. `camera_anchor` is the admiral-cambot pattern — invisible art, `behav_selection`,
dropped from the radar stream — already written and exercised in the range's harness.

Explicitly **not** in Phase 1: easing, framing helpers, anything time-based.

### Phase 2 — The mover (not the camera) ✅ BUILT

```
camera_move(to, subject, eye_from, eye_to, seconds, ease="in_out")  -> Promise
camera_orbit(to, subject, distance, from_yaw, to_yaw, seconds, pitch) -> Promise
camera_rack(to, subject)          # look elsewhere, hold the lens where it is
camera_move_stop(to)              # stop, leaving the lens put
camera_eye(to)                    # where the lens is (the engine cannot be asked)
```

Built on the two answered questions: offsets are **WORLD** (Q1), so an orbit recomputes the
offset and re-aims rather than rotating a local frame; and **per-tick re-apply is fine** (Q3),
so the driver IS the animation. Every move returns a Promise, so MAST can `await` it or race it.

Three things the tests forced out, each of which would have shown up in-engine as something
other than what it was:

- **Aim on the call, not on the first tick.** Waiting a frame leaves the lens wherever the
  previous shot put it for one frame - a visible pop at the top of every move, which reads as
  a bad cut rather than a late driver.
- **Never resolve a Promise with `None`.** `Promise.done()` tests `_result is not None`, so a
  None result is indistinguishable from never having resolved - a story awaiting a shot that
  nobody could see would hang forever. Resolve with the position.
- **A driver must check it still owns the console.** The dispatcher holds tasks in a SET, so
  two drivers on one console fight in whatever order iteration gives, the last to run winning
  each frame. That tears the camera between two paths and looks like an engine fault. Each
  driver carries a token and stops itself the moment it is no longer the owner.

`_MOVES` is in the **reset ledger** ("camera moves"), registered from `handlerhooks` rather
than from `camera.py` - whose own import of that module is circular, and a swallowed
ImportError would have left the container invisible to the audit, which is the exact leak the
ledger exists to catch.

Not built: `camera_handheld` (low-amplitude noise to sell "live"). It is ten lines on top of
`_drive`, but it is the one move whose value can only be judged by eye, so it waits for a
specimen rather than being guessed at.

### Phase 3 — Shots and cutscenes (declarative) ✅ BUILT

**Teardown order is now a rule, not a preference.** A deleted dolly drops the view on the
engine's default (a top-down on a station), so a cutscene must **release or re-point the
camera BEFORE it deletes its scene**. Deleting first and releasing after guarantees at least
one garbage frame. `camera_move` already recovers on its own side - a subject that vanishes
mid-move stops the driver and resolves its promise, so an `await`-driven cutscene advances to
its next shot instead of holding on a dead id.

**Cuts SNAP.** No blend, no hold-off needed - a cut is a cut, which is what the rundown punch
wants anyway.


A **shot** is a camera pin plus its furniture and duration. A **cutscene** is an ordered list
of shots plus a bed (letterbox, music, skippability). Authored as **data**, matching where the
project has gone with AMD — the movie-script stays a movie script and the timeline *consumes*
it rather than growing control flow into it.

```
Shot:    dolly / target / eye / look / move / seconds / ease
         overlay: kind + fields (lower third, hero card, caption)
Cutscene: shots[] + letterbox + skippable + on_skip + music
```

Runtime: `cutscene_play(name, to=role("mainscreen"))` returns a Promise resolving with
`{"skipped", "shots", "name"}`. The furniture is **existing overlay kinds**; this phase added
no drawing, only sequencing.

Built, and the decisions worth keeping:

- **Skip is a parameter, not a race the caller writes.** `cutscene_skip` honours the scene's
  `skippable`, so one global skip button can be wired once and left alone; `cutscene_stop` is
  the teardown path that overrides it, because a mission ending must not be blocked by a scene
  that declared itself unskippable to the crew.
- **The first shot starts on the CALL.** A cutscene that begins a tick later begins on the
  previous shot, which reads as a late cut rather than a late driver - the same bug as the
  mover's, and it would have been invisible until an engine session.
- **A dead subject ends that shot, not the cutscene.** The move resolves early, the sequencer
  treats that as "this shot is over" and advances. Holding out the remaining seconds would sit
  on a frame the engine has already replaced with its default.
- **Teardown clears only the slots the cutscene used**, so it cannot wipe furniture a console
  had of its own - and it releases the camera at the end, BEFORE the caller deletes its scene.
- Both containers are in the **reset ledger** AND cleared by `reset_mission_state`. The probe
  alone would only have reported the leak; the clear is what stops a stale owner making the
  next mission's first move think it is being superseded.

### Phase 4 — Rundowns and the director punch ✅ BUILT

A **rundown** is not a cutscene. It is a named, ordered set of *available* cameras the
director chooses between live:

```
rundown_add("wide",        dolly=station, eye=Vec3(0, 4000, -9000))
rundown_add("hero",        dolly=artemis, eye=Vec3(0, 120, -420))
rundown_add("two-shot",    dolly=anchor,  target=raider)
rundown_add("approach",    dolly=cam3,    move=...)
```

The broadcast idiom, and it maps cleanly onto what we have:

- **PROGRAM** — the feed the stream sees (one client, or a role).
- **PREVIEW** — what the director is lining up next (a second client / second console).
- **Punch** = `camera_track(program, shot)`. A cut is free; anything fancier is faked with a
  one-frame `flash` overlay, since the engine cannot dissolve.
- **Auto-suggest**: the engine already has an "excitement" notion (`gui_cinematic_auto` tracks
  the most exciting object). If that value is readable per object, the rundown can *rank*
  candidate shots and highlight the one worth punching to — director assist, not autopilot.
- **Tally**: mark the live shot in the director's list, so the punch is unambiguous.

**Built.** `rundown_add` / `rundown_program` / `rundown_preview` / `rundown_stage` /
`rundown_take` / `rundown_punch` / `rundown_release` / `rundown_suggest` / `rundown_tiles`.

- **A shot means ONE thing everywhere.** `shot_apply` / `shot_furniture` moved out of the
  cutscene sequencer and are shared, so a rundown shot and a cutscene shot are the same dict.
- **Auto-suggest turned out to be implementable**, not aspirational: the engine's excitement
  notion lives on the object as the data_set key **`exciting`**, so a suggestion agrees with
  what the engine's own cinematic camera would have picked rather than being a second opinion
  invented here. *(Engine-confirm that key before trusting it in a session - it is modelled in
  the mock, and `cinematic.py` describes it, but it has not been read off a real object.)*
- **Suggest never punches.** A test pins it. The whole point of a rundown is that a person
  chooses; the moment it takes the feed on its own it is autopilot, which is a different
  product.
- **Preview shows framing, not furniture.** A director already knows what the tile says;
  duplicating the lower third onto their screen hides the framing they are judging.
- **Removing a shot clears the tally but not the feed** - pulling a shot out of a list is not
  a directing decision.
- `rundown_tiles()` returns `{name, label, live, staged, suggested, excitement}` as DATA. The
  director's console is a mission's to design; this layer has no opinion about tiles. The flat
  look that wants is `gui_button(background_color=…)`, which already exists (Phase 6).

`gui_screenshot(image_path)` already exists (full-desktop BMP via GDI) — worth revisiting for
capturing a punch or a specimen, though it grabs the desktop rather than the view.

### Phase 5 — Lower thirds and conversation furniture

**Why the stock lower third has no face**, and why that was the right call: the `lower_third`
slot is a single bottom strip whose line **cycles in timed parts** when it is too long
(`overlay_lower_third(cycle, dwell, loop)`). A portrait fights that on both axes — it eats the
width the cycling needs, and a name-plate strip is the wrong aspect for a face. The fix is not
a parameter on the strip; it is **distinct kinds in their own slots**, registered via
`overlay_register` / `//overlay`, each with its own rect and rules.

Proposed kinds — each is a builder plus a slot, all reusing the machinery that ships today:

| Kind | Layout | Use |
|---|---|---|
| `lower_third` *(today)* | name plate + cycling line | keep exactly as-is; the workhorse |
| **`lower_third_portrait`** ✅ | **ONE face, on the LEFT or the RIGHT** (`align`), name + line beside it | BUILT - `overlay_lower_third_portrait()` |
| `interview` | one face, name plate, wide text column | longer reads where cycling would annoy |
| `caption` | centered line, no plate | narration / VO subtitles |
| `speaker_badge` | tiny corner chip: face + name, no line | pairs with audio that carries the words |
| `chyron_stack` | stacked lines that push upward | objectives / mission log for a stream sidebar |
| `ticker` | plate + one scrolling line | telemetry or status for a stream |

**A conversation is one face that changes sides**, not two faces on screen at once. Each beat
shows a single speaker with `align="left"` or `align="right"`; alternating that across beats
is what reads as a back-and-forth, and it keeps the strip's width for the line rather than
spending it on a second portrait that is not talking. It also degrades correctly for a
three-hander or a monologue, which a fixed two-face layout does not.

Shared modifiers all kinds should take: `align` (left/right), `scrim` (translucent backing so
text survives a bright 3D view — `overlay_hero` already has `background`), `accent` (per-speaker
colour, so left and right read as different people), and an explicit `enter`/`exit` of **cut
only** until we know the engine can animate alpha.

Conversation API, one call per beat:

```
overlay_lower_third_portrait(name, line, face=..., align="left"|"right", to=...)
```

with a helper that walks an AMD dialogue block so a movie-script drives the face, the side and
the line together. **The AMD stays declarative** — no control flow creeping into dialogue.

**Settled**: its own kind, and the parameter is **`align`**, never `side` — a *side* in Cosmos
is a FACTION, and this is layout. The separate kind earns itself: the strip is taller (a
portrait needs more than a name plate), and the line cycles in timed parts when it is too long,
so it must be measured against the strip MINUS the square or the segments still do not fit.

Built with it: an empty visual still **reserves** the column, so a run of beats does not slide
sideways when a speaker has no portrait; the name and line **justify toward** the visual;
`tests/test_overlay_portrait.py` and the `visual_lower_third_portrait` specimen.

**Two layout traps this turned up**, both of which draw OUTSIDE the box because the engine does
not clip:

- the layout lexer has **no `%` token at all** — `col-width: 22%` raises at *render* time, and
  the overlay try/except swallows it into a silently empty slot. Widths take `em`/`px`/weights,
  heights take `em`/`content`.
- a bare `col-width` number is an **absolute percent of the region**, not a weight. `22 + 78`
  oversubscribes a strip that is only 60% of the screen.

The fix for both was to stop sizing the visual at all: a face is a **square** column, so it
takes its size from the row height. LM's `bar_helpers.py` templates already did exactly this.

### Phase 5b — the square slot takes an icon, a ship or an image ✅ BUILT

Same strip, same geometry, four things that can sit in the square. **Square is REQUIRED**, and
that requirement is the design: it makes the bite out of the strip, the gutter, the empty
placeholder and the cycling width IDENTICAL for all four, so the layout work is already done
and a variant costs one branch. An image is laid out **square and keeps its aspect ratio** —
a square BOX with aspect-preserved content, so a non-square source letterboxes rather than
distorting (`gui_image_keep_aspect_ratio_center`, which `overlay_hero` already uses).

**The four are not equally ready.** Only two are square today:

| visual | layout class | square today | note |
|---|---|---|---|
| `face` | `pages/layout/face.py` | **yes** (`square = True`) | shipped |
| `icon` | `pages/layout/icon.py` | **yes** (`square = True`) | drops straight in |
| `ship` | `pages/layout/ship.py` | **NO** — `#self.square = False`, inherits Column's False | must be forced |
| `image` | `pages/layout/image.py` | **NO** — never sets it; has its own `measure()` | must be forced |

A ship or an image left unsquared is a **flex** column: it takes half the strip and pushes the
text out of the box — the exact failure the 22/78 split produced. So forcing it is not cosmetic.

**There is no `square` style keyword.** `StyleDefinition.parse` is a `match key:` with **no
default case**, so an unknown key is not rejected - it is silently DROPPED. `square: true` in a
style string today does nothing and looks like it worked.

**The answer is `col-width: square`**, not a boolean `square:` style and not a
`gui_square(item)` wrapper.

`col-width` already carries a KEYWORD FAMILY - `content`, `min-content`, `max-content`,
`1fr`/`auto`, `fit-content` - in one table (`_CONTENT_BY_NAME`, parsers.py). `square` joins an
existing enum rather than introducing the style system's first boolean, and it reads as what it
actually is: another **rule for deriving width**. `content` means "as wide as my content";
`square` means "as wide as I am tall". Same category, same slot in the grammar.

It is also the smallest change, because the layout already anticipates it:

1. `parsers.py` - `SQUARE = ContentSize("square")`, registered in `_CONTENT_BY_NAME`;
2. `column.py` `set_col_width` - the SQUARE sentinel sets `self.square = True`. Style application
   happens well before layout, and `_resolve_col_widths` reads `col.square` at the TOP of its
   loop, so there is no ordering problem;
3. **nothing else.** `resolved_size` already returns None for any `ContentSize` (so the column
   falls to the flex/square path), and BOTH content-measuring branches are already guarded with
   `if not col.square:`, so they no-op. The existing square math sizes it from the row height.

**It also fixes a latent bug.** A square column given an explicit width is counted TWICE:
`squares += 1 if col.square` and then `assigned_space += default_width` / `assigned_cols += 1`,
while `need_assigned = len - squares - assigned_cols` subtracts it twice and the row reserves
its space twice over. That double-count is why the 22/78 split did not merely look wrong but
threw content clean outside the strip. Making the two spellings mutually exclusive - a
non-square `col-width` CLEARS `square` - removes the illegal state rather than documenting it.
That is a behavior change for any existing screen that sets a width on a face, which today gets
the double-count; it should be called out in the release note.

Rejected: **`gui_square(item)`** exists only because a style cannot say it. Once `col-width:
square` exists, `gui_ship("x", style="col-width: square")` is already one call, and a wrapper is
a second way to say the same thing - the kind of duplication that later makes authors ask which
one is correct. It also cannot be written in an AMD field, a style def, or a per-control default.

Worth doing alongside, separately: **a default case in `StyleDefinition.parse` that logs an
unknown key**. Silent-drop is the reason a typo'd `sqaure: true` would cost an afternoon, and it
helps far more than this one feature.

**One kind, not four.** `lower_third_portrait` keeps its name (it is the *portrait slot*) and
grows `icon=` / `ship=` / `image=` beside `face=`, **first set wins, in `overlay_hero`'s
existing order** (face, ship, icon, image) so the two cards agree. Four kinds would quadruple
the registry, `_KIND_DEFAULT_SLOT`, `_CYCLE_KINDS`, `_KIND_LOOP_DEFAULT` and
`_KIND_PRIMARY_FIELD` for zero behavioral difference — and would need four AMD record types
where one takes four fields.

Built:

1. **`col-width: square`** — `SQUARE = ContentSize("square")` in the keyword table;
   `apply_col_width` in `column.py` is the single rule keeping `square` and an explicit width
   mutually exclusive, shared by `Column` and `Layout`. `row-height: square` raises rather than
   silently doing nothing. `tests/test_layout_square_width.py` (15 tests), documented in
   `mkdocs/docs/cosmos/gui_content_sizing.md`.
2. **The builder special-cases nothing** — all four sources go through the same
   `style="col-width: square"`, so the two that were never square are no longer a separate case.
3. `overlay_lower_third_portrait(..., ship=, icon=, image=)`, first set wins in `overlay_hero`'s
   order; an image goes through `gui_image_keep_aspect_ratio_center` so it letterboxes.
4. A variant matrix in `tests/test_overlay_portrait.py` (31 tests) — every source square, none
   carrying a width, both aligns, and **the emitted layout identical whichever source**, which is
   the claim square is making.
5. The specimen plays all four at one row height so the claim is checkable by eye.

**Settled, not open**: a ship is a LIVE 3D render (`send_gui_3dship`), and it may read small at
a 6em square. That is **not** a reason to give the ship variant its own row height. How legibly
the engine renders a hull into a small rect is an ENGINE question, to be raised there if people
find it too small — forking the strip per source would quietly undo the one property this design
is built on, that the four are interchangeable. The row height stays a property of the STRIP.

### Phase 6 — flat button ❌ DROPPED (it already exists)

`gui_button(background_color=…)` is the flat button. `send_gui_colorbutton` draws a flat fill
with no chrome (confirmed in-engine), and `Button.background_color` already pairs it with a
text widget - so there was never anything to build, only something to notice. Its one in-tree
user is LM's `document_screen.py`.

Nothing further is needed here. If a control ever wants to be a **hot zone** over an image or a
face - click a portrait to talk to that character - that is a clickregion and a separate,
un-asked-for widget; `visual_button_chrome` in the Visual Test Range remains useful as a
reference for how the background tones read over a live view.

## 3. Sequencing

| Order | What | Why now |
|---|---|---|
| ~~1~~ | ~~Phase 0 spikes~~ | ✅ done - and section 0 above is what they found |
| ~~2~~ | ~~Phase 1 primitives~~ | ✅ done - `procedural/gui/camera.py`, 17 tests |
| ~~-~~ | ~~Phase 6 flat button~~ | ❌ dropped - `gui_button(background_color=…)` already is one |
| ~~3~~ | ~~Phase 5 lower thirds~~ | ✅ done - one square visual (face/ship/icon/image), `align` left/right, optional replies. It also earned `col-width: square` and the overlay-kind mechanism the rest of the furniture will use |
| ~~4~~ | ~~confirm the offset fold renders in-engine~~ | ✅ **CONFIRMED BY DOUG, 2026-08-01: "they all work now in engine."** The fold is real, so everything below stands on solid ground |
| ~~5~~ | ~~Phase 2 mover~~ | ✅ done - `camera_move` / `camera_orbit` / `camera_rack` / `camera_move_stop` / `camera_eye`, 22 tests |
| ~~6~~ | ~~Phase 3 cutscenes~~ | ✅ done - `cutscene_define` / `play` / `skip` / `stop` / `playing`, 22 tests |
| ~~7~~ | ~~Phase 4 rundowns~~ | ✅ done - `rundown_add/program/preview/stage/take/punch/suggest/tiles`, 22 tests. The payoff. A shot is a *(subject, lens position)* pair now, not a camera object - arguably a better model |

### AMD: a shot is a RECORD ✅ BUILT

Doug chose one heading per shot, grouped by `Scene:` (a cutscene) or `Rundown:` (a set the
director punches between) - "clearer to me". `amd_cutscene.py` loads both, so Phase 3 and
Phase 4 get AMD from ONE implementation, which is only possible because they already share
`shot_apply`.

```
## [Chapter One](intro)
---
Kind: cutscene
Letterbox: yes
---
## [Establish Phoenix](intro_1)
---
Scene: intro
Subject: station
Eye: 0, 900, -4000
Seconds: 4
Overlay: lower_third
Name: Phoenix Control
---
All quiet on the belt.
```

Why a record per shot rather than a scene body: a shot stays an ordinary AMD record, so the
existing reader, `sbs lint`, the schema and the typed VS Code widgets all work on it unchanged
(`CUTSCENE` and `SHOT` are registered archetypes). A scene body would have needed its own
positional mini-language with quoting rules - which is exactly the DSL creep the AMD dialogue
principle exists to prevent.

**`Subject:` resolves LATE, and that was the real design problem.** A shot names a live object,
and no object exists when the `.amd` loads. Doug chose cast-then-role:

1. a **cast** the mission bound (`cutscene_cast("hero", artemis)`) - the film idiom, and it lets
   one scene replay with a different ship without touching the `.amd`;
2. failing that, the **role** `hero`, for the ad-hoc case;
3. failing both, the shot is **dropped and the reason is logged NAMING the shot**. The rest of
   the scene still plays: a missing actor should not take a whole cutscene down, and a silent
   skip is far worse than one that says why.

Ordering is document order unless a shot carries `Order:` (a stable sort, so the two mix).
`amd_cutscenes(section)` loads, `cutscene_amd(key, to=...)` plays, `rundown_amd(key)` fills the
director's rundown. All three registries plus the cast are in the reset ledger AND cleared.

## 4. Standing constraints

- **Back-compat freezes signatures.** Prefer three obviously-right functions now over a
  speculative system.
- **Engine truth beats mock truth.** Every phase lands a VisualTestRange specimen, and a mock
  frame is never evidence about the engine.
- **No multi-line literals** in the MAST-facing API — keep calls single-line friendly.
- **ASCII only** in anything the engine renders.
- **Skippable, always.** Cutscenes and letterbox included.
- **The overlay system is the drawing layer.** This plan adds sequencing, framing and two
  widgets; it should not grow a second way to draw.
