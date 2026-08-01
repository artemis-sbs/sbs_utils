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
| Q2 cut or blend | cut | _unanswered_ | run `visual_camera_cut` |
| Q3 what drives a move smoothly | — | **per-tick re-apply is fine** | GM re-applies every camera change this way |
| Q4 dolly deleted mid-shot | — | _unanswered_ | run `visual_camera_cut` |
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

### Phase 2 — The mover (not the camera)

Because a camera is an object, "camera animation" is a path-follower on an anchor. Shape,
pending Q3:

```
camera_move(anchor, to, seconds, ease="in_out")     -> promise
camera_orbit(anchor, around, radius, degrees, seconds)
camera_rack(set, target)                            # change what we look at, hold position
camera_handheld(anchor, amount)                     # low-amplitude noise, sells "live"
```

Design notes:
- `ease` is ours, applied to the interpolation, since the engine has none.
- `camera_orbit` is trivial **if Q1 says local**; otherwise it is "recompute a world offset
  each tick", which is fine but costs a driver task per shot.
- Everything returns a promise so MAST can `await` a move or race it with `promise_any`.
- **A moving anchor and a moving subject are different problems.** Pinning to a live ship
  gives free "follow" with zero driver cost — prefer it over animating an anchor when the
  shot allows.

### Phase 3 — Shots and cutscenes (declarative)

A **shot** is a camera pin plus its furniture and duration. A **cutscene** is an ordered list
of shots plus a bed (letterbox, music, skippability). Authored as **data**, matching where the
project has gone with AMD — the movie-script stays a movie script and the timeline *consumes*
it rather than growing control flow into it.

```
Shot:    dolly / target / eye / look / move / seconds / ease
         overlay: kind + fields (lower third, hero card, caption)
Cutscene: shots[] + letterbox + skippable + on_skip + music
```

Runtime: `cutscene_play(name, to=role("mainscreen"))` returns a promise; `await` it, or race
it against a skip button. The furniture is **existing overlay kinds** — `letterbox`, `hero`,
`lower_third`, `credits`, `flash` are already engine-verified per the adoption plan. This
phase adds no new drawing, only sequencing.

Skip must be a first-class path, not an afterthought: a cutscene that cannot be skipped is a
bug report from a bridge crew.

### Phase 4 — Rundowns and the director punch (the streaming layer)

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

This is where the flat click-region button matters: a rundown list is a grid of labelled
tiles with a thumbnail-ish feel, not a column of engine buttons.

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
shows a single speaker with `side="left"` or `side="right"`; alternating the side across beats
is what reads as a back-and-forth, and it keeps the strip's width for the line rather than
spending it on a second portrait that is not talking. It also degrades correctly for a
three-hander or a monologue, which a fixed two-face layout does not.

Shared modifiers all kinds should take: `align` (left/right), `scrim` (translucent backing so
text survives a bright 3D view — `overlay_hero` already has `background`), `accent` (per-speaker
colour, so left and right read as different people), and an explicit `enter`/`exit` of **cut
only** until we know the engine can animate alpha.

Conversation API, one call per beat:

```
dialogue_two_shot(left_face, right_face, speaker="left", name=..., line=..., to=...)
```

with a helper that walks an AMD dialogue block so a movie-script drives faces, lines and
shots together. **The AMD stays declarative** — no control flow creeping into dialogue.

Open: whether the two faces can be rendered side by side in one region cheaply
(`gui_face` per side) or whether they need separate slots for independent update. Answer with
a Control Gallery specimen before committing the kind.

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
| **1** | **Phase 5 `two_shot`** | the conversation lower third. Wanted regardless of cutscenes, and it exercises the overlay-kind mechanism the rest of the furniture will use |
| 2 | Phase 2 mover | needs re-sketching against the one-object rule: a move is now "recompute the subject-relative offset", not "animate an anchor the camera rides" |
| 3 | Phase 3 cutscenes | sequencing on top of proven parts |
| 4 | Phase 4 rundowns | the payoff. A shot is a *(subject, lens position)* pair now, not a camera object - arguably a better model |

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
