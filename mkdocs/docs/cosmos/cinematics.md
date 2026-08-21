# Cinematics — camera, cutscenes and rundowns

Everything here rests on four facts about the engine's camera. They are not trivia:
each one was found by a black screen, and each one shapes the API.

| Fact | What it forces |
|---|---|
| **A camera IS an object.** The lens sits at an object's position plus an offset. | "Move the camera" is always "move an object". There is no FOV, roll, or shake. |
| **The offsets are WORLD-space**, not object-local. | An orbit *recomputes the offset and re-aims*; it does not rotate a local frame. |
| **The dolly and the target must be the SAME object.** Two different ids draw a **black frame** — no error, no log. | A shot is one object named twice, with the lens offset away from it. The library folds a two-object request into that shape for you. |
| **The console must be ASSIGNED to the object the lens rides.** | `camera_track` assigns for you. Pointing without assigning leaves a black screen. |

Two more, confirmed in-engine:

- **Cuts SNAP.** No blend, so nothing needs a hold-off.
- **A deleted dolly does not freeze the frame** — the view falls to the engine's own
  default. So **release or re-point the camera BEFORE deleting anything it was riding.**

---

## Placing a shot

```python
camera_shot(role("mainscreen"), station, Vec3(0, 900, -4000))
```

"Look at the station, from up here." The lens position is **world coordinates** — the
library works out the offset from wherever the subject is at the time, so the framing
survives the subject moving.

A camera on a ship at zero offset is **inside its hull**. For a shot that is not on a
real object, make an invisible anchor:

```python
cam = camera_anchor(0, 0, 0)
camera_shot(to, cam, Vec3(0, 400, -1200))
```

Hand the camera back to the engine's own director with `camera_auto(to)`.

## Moving it

The engine interpolates nothing, so a move is a driver that re-aims every tick. Each
returns a **Promise**, so MAST can `await` it.

```python
await camera_move(to, hero, Vec3(0, 900, -4000), Vec3(0, 120, -600), 6, ease="in_out")
await camera_orbit(to, station, distance=2000, from_yaw=0, to_yaw=360, seconds=12)
await camera_chase(to, fighter, distance=600, height=100, seconds=30)
camera_rack(to, other_ship)      # look elsewhere, hold the lens where it is
camera_move_stop(to)             # stop, leaving it put
```

`camera_chase` is the third-person follow: it holds the lens **behind** the subject as
it turns, rebuilding the offset from the ship's heading every tick. It is the one move
whose lens depends on where the subject is *pointing* rather than on elapsed time, so
`seconds` is only how long this leg runs — re-issue it to keep chasing.

!!! note "Why following is re-aiming, not a tractor"
    The obvious way to chase is to attach the camera to the target and let the engine
    drag it. There is nothing to attach: the dolly and the target must be the **same
    object** or the frame is black, so the lens already rides the subject. A tractored
    camera object would be dragged along with nothing looking through it.

    It also has to run on the tick. The engine interpolates nothing, so the driver *is*
    the animation — following from a mission loop at a few hertz reads as a stutter.

`ease` is ours — `in_out` (default), `in`, `out`, `linear`. An unknown name falls back
to linear rather than killing the shot.

!!! note "A move ends if its subject dies"
    The driver stops and the promise **resolves**, so an `await`-driven scene advances
    to its next shot instead of holding on a dead id. It does not pick a replacement
    shot — that is a directing decision the library cannot make.

## Cutscenes

A **shot** is a subject, where the lens sits, how long it holds, and optional
furniture. A **cutscene** is an ordered list plus a bed.

```python
cutscene_define("intro", [
    {"subject": station, "lens": (0, 900, -4000), "seconds": 4,
     "overlay": {"kind": "lower_third", "name": "Phoenix", "line": "Standing by."}},
    {"subject": hero, "move": [(0, 400, -3000), (0, 120, -600)], "seconds": 6},
])

result = await cutscene_play("intro", to=role("mainscreen"))
if result["skipped"]:
    ...
```

The furniture is the ordinary [overlay kinds](overlays.md) — this layer adds no drawing.

**Skip is a parameter, not a race you write.** `cutscene_skip(to)` honours the scene's
`skippable`, so one global skip button can be wired once and left alone.
`cutscene_stop(to)` overrides it — the teardown path, because a mission ending must not
be blocked by a scene that declared itself unskippable to the crew.

## Rundowns — the director's punch

A rundown is **not** a cutscene. A cutscene plays itself; a rundown is a set of
*available* shots a person chooses between, live. Same shot dicts.

```python
rundown_add("wide", station, lens=(0, 4000, -9000), label="Wide - the belt")
rundown_add("hero", artemis, lens=(0, 120, -420))

rundown_program(role("mainscreen"))   # the feed everyone sees
rundown_preview(director)             # what the director is lining up

rundown_stage("hero")                 # onto PREVIEW only
rundown_take()                        # promote it to PROGRAM
rundown_live()                        # the tally: what is on air
```

`rundown_tiles()` returns `{name, label, live, staged, suggested, excitement}` per shot
— everything a director's console needs, as **data**. The console itself is a mission's
to design.

**Auto-suggest is assist, never autopilot.** `rundown_suggest()` ranks shots by the
engine's own `exciting` value — the same notion its automatic camera follows — so a
suggestion agrees with what the engine would have picked. It never punches: the whole
point of a rundown is that a person is choosing.

## Authoring them as AMD

Shots are ordinary AMD records, so lint, the schema and the typed editor widgets work
on them unchanged. One heading per shot, grouped by `Cutscene:` or `Rundown:`.

```
## [Chapter One](intro)
---
Letterbox: yes
Skippable: yes
---

## [Establish Phoenix](intro_1)
---
Cutscene: intro
Subject: station
Lens: 0, 900, -4000
Seconds: 4
Overlay: lower_third
Name: Phoenix Control
---
All quiet on the belt.

## [Push in on Artemis](intro_2)
---
Cutscene: intro
Subject: hero
Move: 0,400,-3000 -> 0,120,-600
Seconds: 6
---
```

The **bed** is the record carrying neither `Cutscene:` nor `Rundown:`; the shots find it
by key. Shots play in document order unless one carries `Order:`.

`Subject:` names a live object, and no object exists when the `.amd` loads — so it
resolves **late**:

1. a **cast** the mission bound — `cutscene_cast("station", phoenix)`. The film idiom:
   the script says "station", the production decides which one, so the same scene
   replays against a different ship without editing the file;
2. failing that, the **role** of that name;
3. failing both, that shot is **dropped and the reason is logged naming it**, and the
   rest of the scene still plays. A missing actor should not take a whole cutscene down.

```python
cutscene_cast("station", phoenix)
cutscene_cast("hero", artemis)
amd_cutscenes(amd_root_node(amd_document(get_mission_dir_filename("cinematics.amd"))))
await cutscene_amd("intro", to=role("mainscreen"))
rundown_amd("patrol")        # loads declared shots into the live rundown
```

## Gotchas

- **`Lens:`, not `Eye:` or `Camera:`.** A *camera* here is an object, which is what
  `Subject:` already names; `Lens:` is where you look **from**.
- **`Cutscene:`, not `Scene:`.** `Scene:` is a lifeform's dialogue scene, and the schema
  infers the lifeform archetype from it — a shot carrying it is typed as a character.
- **No `Kind:` on a bed.** `Kind:` infers the *landmark* archetype.
- **Release before you delete.** A deleted dolly drops the view to the engine default.
- **A cutscene and a rundown fight over one console.** Starting either stops the other;
  that is deliberate, and it is why there is one tally.
