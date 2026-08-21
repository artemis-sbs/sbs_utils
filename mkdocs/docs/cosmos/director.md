# The Director — stream your game like a broadcast

Cosmos looks best from outside the ship, and a stream of it is only as good as the
shot it is on. The **Director** is a console for cutting that stream live: you build
a list of shots, you see the next one before it goes out, and you take it to air when
it is right.

It is a **streaming tool, not a bridge station**. It never commandeers a mainscreen or
a crew seat — Cosmos has plenty of other ways to put something on a bridge screen, and
taking a console away mid-game ruins somebody's game. Instead you open extra clients
and tell each one what it is.

Pick **Director** in the console list. It is part of **LegendaryMissions**; a mission
that loads the `director` add-on has it.

## Two feeds

| Feed | On | Showing |
|---|---|---|
| **PROGRAM** | every console that opened as Program | what is going out — capture this one |
| **PREVIEW** | every console that opened as Preview | the next shot, or whatever the editor is building, live |

Every Program screen shows the **same** thing, and every Preview screen shows the same
thing. Open a second Program window and it stays in step with the first, so you can
capture one and put the other on a projector. Preview is where you check a shot before
the audience sees it.

## Setting it up

Open a client for each screen you want, choose **Director**, and the entry screen asks
one question: what is this console?

- **Program** — an output screen. Capture this window.
- **Preview** — the same, showing the shot before it goes out.
- **Director** — the control console, with the tabs below.

The screen names itself from that answer — `PROG01`, `PRE01`, `DIR01`, taking the
lowest free number — so four windows open at once are told apart at a glance without
typing anything. The holding page each screen sits on says its own name, so you know
which window is which before anything is playing.

!!! tip "Lock it if you want"
    `DIRECTOR.pin` gates the console. Set it to `""` to skip the prompt entirely; the
    entry screen still appears, because that is where the mode is chosen.

## Rundowns — the running order

A **rundown** is a named, ordered list of shots. Four come with it and are built from
the live game every time they are used, so they track ships that spawn and die instead
of going stale:

| Rundown | What is in it |
|---|---|
| **Bridge wall** | one console view per console type per player ship — the classic multiview |
| **Player ships** | a slow orbit of each player ship |
| **The action** | a chase on whatever is most exciting right now, best first |
| **Stations & terrain** | orbits of stations and named terrain — the establishing shots |

Plus any you build yourself. The main page shows them as a **tree**: each rundown a
heading, its shots underneath. **The shot on air is green**, and so is the rundown
holding it — so a collapsed branch still tells you where the show is.

### Two ways to pick

A **Pick** switch decides what the list is for:

- **Rundowns** — the list shows rundowns alone. Tick as many as you like and press
  **Send to Program**; the play set is the union of them, and the show advances
  through it on the dwell.
- **Items** — the list opens up, and **picking a shot puts it on air immediately**.
  No Send, no confirmation. Use it like a clip launcher when you are cutting by hand.

**Dwell** is how long each shot holds before the next one. **Stop** hands every screen
back and parks it; **Resume** gives the running order back after a hand-picked shot.

### Let the game direct

Turn on the **auto-director** and the running order follows the fighting: it ranks by
the same "exciting" signal the engine's own cinematic camera uses, so it agrees with
what the engine would have chosen. It holds its choice through noise — a contender has
to be clearly better before the shot moves — and in a lull it falls back to the order
you built rather than to an arbitrary one.

## Building a shot

The **rundown** tab is the editor: your running order down the left, the tools that
make a shot on the right.

**Stage** is the usual way in. A 2D view fills the top with the **science object list**
beside it — click a contact on the radar or pick its name from the list, either works.
Then choose how to film it:

| Shot | What it does |
|---|---|
| **Dolly** | pushes in and back out |
| **Orbit** | circles the subject |
| **Chase** | rides behind it as it turns — third person |
| **Tactical** | a full-screen 2D view instead of a camera |

These are the **same shots the bridge already has** — the science and weapons *On
Screen* list — so a Director shot and a bridge shot of the same ship look identical.
Framing comes from the ship's own hull size, which is why a starbase and a fighter both
fill the frame.

**Hold** sets how long *this* shot stays up, overriding the dwell — an establishing
shot of a starbase can want ten seconds where a chase in a firefight wants three. Leave
it at zero and the dwell decides.

Then **Add to rundown**, or **Send to Program** to put it straight on air.

!!! note "The same shot twice is two shots"
    Wide on a station with a title, then the same shot clean, is ordinary direction —
    so a rundown holds both. Two entries only count as one when *everything* about
    them matches, so a double-click still collapses.

**Console** is the other tool: pick a ship and one or more console types, and add one
item per console. That is what fills a bridge multiview.

## Overlays — titles over the shot

Any shot can carry cards, and several at once because each draws in its own place:

| Overlay | Fields |
|---|---|
| **Lower third** | name, line |
| **Hero** | title, subtitle |
| **Top status** | text |
| **Letterbox** | line |

Every Preview screen shows them for real, at full size, as you build them.

### The text writes itself

A generated rundown makes one item **per ship**, so there is nowhere to type
"Artemis". The fields take a **template** filled in from whatever the shot is pointed
at:

```
name:  <<name>>
line:  <<class>>
```

...gives you `Artemis` / `Light Cruiser` on that ship, and the right thing on every
other ship in the rundown.

| Token | Gives you |
|---|---|
| `<<name>>` | the ship's name |
| `<<class>>` | its hull — "Light Cruiser" |
| `<<side>>` | its side |
| `<<role>>` | raider, station, monster |
| `<<race>>` | its origin |
| `<<comms_id>>` | "Artemis (TSN)" |
| `<<hull>>` | hull percent |
| `<<shields>>` | front / rear percent |

Write `<<class|contact>>` to say what to fall back to when a token has nothing to give
— a rock has no hull class, and a blank line reads as a broken card. A token you
mistype stays visible as `<<shpi>>` rather than blanking the card, so you can see what
went wrong.

Each row has a **preset** picker — Ship ID, Ship and side, Condition, Contact — and a
**Save** to add your own beside them.

## Try it

Open three windows: one Director, one Program, one Preview.

1. On the Director, pick **The action** and press **Send to Program**.
2. Watch Preview — it is showing what Program will cut to next.
3. Switch **Pick** to **Items**, open a rundown, and click a shot. It is on air at once,
   and it goes green.
4. On the **rundown** tab, click a ship, choose **Chase**, tick **Lower third**, and
   press **Send to Program**.
5. Press **Resume** to give the running order back.

## Settings

```yaml
DIRECTOR:
    enable: true
    pin: "000000"     # "" to skip the prompt
```

## See also

- [Cinematics](cinematics.md) — the camera moves underneath all of this, including
  `camera_chase`.
- [Overlays](overlays.md) — the card system the Director drives.
- [On screen](viewscreen.md) — the same shot vocabulary, from a science console.
