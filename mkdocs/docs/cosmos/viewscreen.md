# "On screen" — the main screen, driven from science

The captain says *"on screen"*, and somebody has to make it happen. That somebody is
science: they already have the contact selected.

A drop-down beside the science console's **Follow** checkbox hands the ship's main
screen a shot of whatever is selected, and puts a column of what science knows about it
beside the picture.

```
[x] Follow   [ On Screen - Orbit   v ]
                Off
                On Screen - Dolly
                On Screen - Orbit
                Tactical 2D
```

| Shot | What the main screen does |
|---|---|
| **Off** | Hands the screen back, restoring the view the crew had before |
| **On Screen - Dolly** | A slow push in and out along a fixed angle, following the subject |
| **On Screen - Orbit** | A slow turn around the subject |
| **Tactical 2D** | The radar, focused on the subject, reflowed to leave the data column room |

Changing the science selection while a shot is running re-points it — the crew picked a
new contact, not a black screen. Destroy the subject and the viewer stands down.

---

## The data column

A tall panel in the right-hand gutter, in **both** 3D and 2D modes, so the crew's eye
does not move when the mode changes. In Tactical the radar is genuinely reflowed to
leave that space; over a 3D shot the engine draws full-bleed, so the column is an
overlay on top of it.

It shows one page at a time and moves on when the page has had its reading time. Pages
with nothing to say are skipped entirely, so a slideshow never lands on a blank.

| Page | What it says |
|---|---|
| `vitals` | Name, side, origin, range, bearing, shields, hull |
| `science` | **Every scanned tab, together** — Scan, Status, Intel, Materials, Bio |
| `comms` | The last few exchanges with this contact |
| `quest` | Quests bound to the object — what the crew has been told about it |

The science page deliberately carries **all** the tabs at once. One page per tab was the
first design and it read wrong: the slideshow shows a single tab at a time, so a contact
scanned on three tabs looks like a contact scanned on one until you happen to glance
back at the right moment. The tabs are facets of one readout.

### A mission can add its own page

```python
def page_cargo(subject_id, ship_id):
    manifest = get_inventory_value(subject_id, "cargo", None)
    if not manifest:
        return None            # nothing to say -> no page, not a blank one
    return "# Cargo\n\n" + "\n".join(f"- {k}: {v}" for k, v in manifest.items())

viewscreen_page_register("cargo", page_cargo, order=30)
```

A page is a **pure function of `(subject_id, ship_id)` returning markdown**, or `None`.
The built-ins go through the same registry, so overriding one is registering your own
under the same name. A page that raises is skipped rather than taking the column down.

---

## The one thing to know if you write a main-screen console

**While a shot is running, the console is ASSIGNED to the subject.** That is not a
choice the library made: the engine only honors a camera change when the console and the
lens ride the same object (see [Cinematics](cinematics.md)). So during a shot,
`sbs.get_ship_of_client(client_id)` on a main screen answers with **the enemy being
filmed**.

```python
ship_id = viewscreen_home_ship(client_id)     # our own ship, shot or no shot
```

Anything that means *"this console's own ship"* must ask `viewscreen_home_ship`. Reading
`get_ship_of_client` instead is how a main-screen label ends up reading the enemy's
state and linking the enemy as its owner. Standing down puts the assignment back.

### And one that is not fixed

**A bare variable in a main-screen label can land on the enemy's inventory.** MAST's
`assigned` scope resolves through `sbs.get_ship_of_client`, so during a shot a plain
`foo = 1` in a mainscreen label reads and writes the SUBJECT's agent, silently.

It is not fixed because it is the hot path for every variable read on every console in
the game, and changing it is riskier than the bug. Write main-screen state explicitly and
it cannot bite you:

```
set_inventory_value(ship_id, "my_thing", value)      # ship_id from viewscreen_home_ship
foo = 1                                              # fine - a TASK variable
```

The exposure is a variable that falls through to `assigned` scope specifically.
LegendaryMissions' main-screen label avoids it by naming the ship on every read and
write, which is the pattern to copy.

---

## Who owns the screen

Seven things can drive a main screen: science's drop-down, the same drop-down on
weapons, an incoming hail, docking, a cutscene, the Director, and helm or weapons
reaching for the engine's own main-screen control. So a screen has an **owner**.

The state lives in the **player ship's inventory** — the same place Cosmos already keeps
`MAIN_SCREEN_VIEW` — which buys the scope for free: science on the Artemis cannot change
what the Intrepid's screen shows, and it goes away with the mission like any other agent
state.

### A claim carries a name

```
viewscreen_set(ship, "orbit", target, owner=viewscreen_owner_token("science", client_id))
viewscreen_owns(ship, owner)      # is it still mine?
viewscreen_clear(ship, owner)     # refused if it is not
```

The token is what lets a console tell *"still mine"* from *"weapons took it"*. Without
one, a console has to guess — and the guess used to be `viewscreen_is_live`, which asks
whether **anybody** is driving the screen, so science re-pointing on a new selection
yanked whatever contact weapons had put up.

`viewscreen_revision(client_id)` moves whenever the screen changes hands. Watch it with
`on change` so a drop-down that lost the screen repaints to *Off* instead of advertising
a shot that is no longer its own. **`on change`, not `on signal`** — a GUI task sitting
in `await gui()` does not repaint because a signal fired.

### Two tiers, and what helm can take

| Tier | Who | Helm's main-screen control |
|---|---|---|
| `console` | science, weapons, docking | **takes the screen.** Helm's choice IS the new state |
| `story` | a cutscene, a hail, a mission beat | **does not.** The press is parked and applied when the beat ends |

The crew's physical control is their escape hatch from another *console*, not from a
directed moment. A press that arrives during a story beat is not lost — it is held, and
fires the instant the beat releases. A console pick made during one is held the same way.

### Flat, not a stack

**Releasing goes back to what the CREW had, never to the previous claimant.** Science
puts a contact up, a hail takes the screen, the hail ends — the screen returns to the
view the crew were flying with, not to science's shot. There is exactly one recorded
baseline, captured the moment the screen goes from unclaimed to claimed, and everything
restores to that. Every subsystem used to keep its own note of "before" and they
overwrote each other, which is how a bridge ended up with no way back at all.

A console re-reporting the state it is already in — a screen reconnecting — is not a
takeover either way, so a shot survives a console joining the bridge.

---

## From a mission

```python
viewscreen_set(ship, "orbit", target)      # off | dolly | orbit | tactical
viewscreen_clear(ship)                     # hand it back
viewscreen_mode(ship)                      # what is running
viewscreen_subject(ship)                   # what it is looking at
viewscreen_consoles(ship)                  # that ship's main screens
viewscreen_home_ship(client_id)            # see above

# ownership
viewscreen_set(ship, "orbit", target, owner=tok, tier="story")
viewscreen_owner_token("science", client_id)   # -> "science:<id>"
viewscreen_owns(ship, owner)                   # still mine?
viewscreen_revision(client_id)                 # poll with `on change`
viewscreen_restore(ship, owner=None)           # the door home; owner=None forces
viewscreen_take(ship, owner, tier)             # claim it, drive the camera yourself

# for a main-screen console to call
viewscreen_console_enter(client_id)            # FIRST line: record where it belongs
viewscreen_view_modes(client_id)               # -> (view, facing, mode)
```

**`viewscreen_set` returns `False` for two different reasons now** — "already showing
exactly that", and "a story beat holds the screen, so your request was parked". Ask
`viewscreen_owns` when you need to tell them apart; that is the question a console
actually has.

`viewscreen_take` is for anything that drives the screen its **own** way and still needs
arbitrating — a cutscene, the Director, a beat pointing the camera by hand. It records
the baseline without starting one of the viewer's shots, so `viewscreen_restore` can put
the bridge back afterwards.

Everything the console does is one of these calls, so a mission can drive the main
screen from a story beat exactly the way science drives it from the drop-down — and a
cutscene still takes the screen off the viewer, because cutscenes and hero cards draw
above it.
