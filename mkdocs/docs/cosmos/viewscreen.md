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

---

## Who owns the screen

The state lives in the **player ship's inventory** — the same place Cosmos already keeps
`MAIN_SCREEN_VIEW`. Three consequences, all of them free:

- **Scope.** Science on the Artemis cannot change what the Intrepid's main screen shows.
- **Arbitration.** Helm's main-screen control writes the same key, so **last writer
  wins**: helm reaching for the control simply takes the screen, and the science
  drop-down falls back to *Off* on its next repaint. No negotiation, no lock.
- **Reset.** It goes away with the mission, like any other agent state.

A console re-reporting the state it is already in — a screen reconnecting — is not a
takeover, so a shot survives a console joining the bridge.

---

## From a mission

```python
viewscreen_set(ship, "orbit", target)      # off | dolly | orbit | tactical
viewscreen_clear(ship)                     # hand it back
viewscreen_mode(ship)                      # what is running
viewscreen_subject(ship)                   # what it is looking at
viewscreen_consoles(ship)                  # that ship's main screens
viewscreen_home_ship(client_id)            # see above
```

Everything the console does is one of these calls, so a mission can drive the main
screen from a story beat exactly the way science drives it from the drop-down — and a
cutscene still takes the screen off the viewer, because cutscenes and hero cards draw
above it.
