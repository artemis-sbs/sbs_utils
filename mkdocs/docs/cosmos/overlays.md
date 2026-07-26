# Overlays — cards, HUDs & cutscenes on top of the view

An **overlay** is a screen-anchored surface drawn **on top of** a console's page and
its embedded engine views (the 3D view, the tactical map). Hero cards, lower thirds,
toasts, banners, a full-screen flash, a modal choice, a live HUD — all draw over
whatever is on screen and update **without repainting the page underneath**.

Overlays live in named **slots** (centre, top strip, corner, bottom, full-screen), and
each slot draws above the page via the engine's draw-layer. You never build the
stacking or the region plumbing — you call a wrapper (or fire a signal), and the
overlay system establishes the slot, draws it, and clears it.

## Quick start — a hero card

```
overlay_hero("CHAPTER TWO", subtitle="The Long Dark", seconds=4)
```

A big centred card that lifts itself after four seconds. Give it a visual above the
title — a **face**, a **ship**, an **icon**, or an **image** (first one set wins):

```
overlay_hero("Admiral Harkin", subtitle="Hold the line, commander.",
             face=get_face(admiral.id))
```

## The built-in overlays

Each wrapper packs your arguments into content and draws the matching card. All the
transient ones take an optional `seconds` (auto-dismiss) and a `to` (which consoles —
see [Targeting](#targeting-which-consoles)).

| Wrapper | Slot | Use |
|---|---|---|
| `overlay_hero(title, subtitle, face/ship/icon/image, seconds)` | centre | chapter / scene title, boss reveal |
| `overlay_lower_third(name, line)` | bottom | someone speaking over the live view |
| `overlay_banner(text, color)` | top strip | RED ALERT, a countdown |
| `overlay_toast(text, seconds=3)` | lower-right | *Objective updated* — **toasts stack** |
| `overlay_credits(entries, title, roll=)` | full-screen | opening / closing credits |
| `overlay_letterbox(line, bar)` | full-screen | cinematic bars for a cutscene |
| `overlay_flash(color)` | full-screen | hull-hit / jump colour wash (fast) |
| `overlay_choice(title, buttons)` | centre | **modal** — returns an awaitable |
| `overlay_hud(rows, controls, title)` | anchored | **sticky** live readout + controls |
| `overlay_clear(slot=None)` | — | clear one slot, or all |

## Targeting — which consoles

Overlays draw on **consoles**, but you usually hold a ship or a side. `to` is an
**audience expression** that accepts any of them:

| `to` | goes to |
|---|---|
| *(omitted)* | the **current** console (the one whose task called it) |
| a client id | that one console |
| a **ship** (id or object) | every console linked to that ship |
| a **side** (key string or side agent) | every console of every ship on that side |
| a role set / list | the union, elementwise |

```
overlay_hero("FLEET ALERT", subtitle="Raiders inbound", to=role("mainscreen"))
overlay_banner("WAR DECLARED", to=role("__player__"))      # ships -> their consoles
overlay_toast("Cargo ejected", to=ship_id)                 # one crew
overlay_banner("BLOCKADE LIFTED", to="tsn")                # a whole side
```

A mixed set is fine — ships and clients resolve side by side, and anything that isn't
a console is skipped. Resolve it yourself with `consoles_of(to)`.

**`consoles=` narrows by console role.** A ship has a whole bridge; often you mean one
screen:

```
overlay_lower_third(name, line, to=ship_id, consoles="mainscreen")
overlay_toast("Contact bearing 040", to=ship_id, consoles="science, comms")
```

Passing a scalar `to` that resolves to no console logs a one-off warning (that is the
"I pushed an overlay and saw nothing" bug); an empty *set* is normal and stays quiet.

## Auto-dismiss & stacking toasts

`seconds` schedules a **generation-guarded** auto-dismiss: if the slot is re-shown or
updated before the timer fires, the old timer is superseded — it can never clear the
*newer* content. Toasts are special: each `overlay_toast` **appends** (capped, each
self-removing), so several notifications coexist instead of clobbering one another.

```
overlay_toast("Upgrade acquired")
overlay_toast("Objective updated")     # both visible, each clears on its own
```

## A modal choice

`overlay_choice` returns an **awaitable** that resolves to the pressed button's label.
Await it from a story / background task (not the target console's own GUI task):

```
result = await overlay_choice("Fire on the ambassador?", ["Yes", "No"], to=player)
if result.data == "Yes":
    open_fire()
```

## A live HUD

`overlay_hud` shows a **sticky** panel over the live view; `overlay_hud_update` re-fills
just that region (no page repaint). Update only when a shown value changes:

```
overlay_hud(rows={"Speed": 0, "Alert": "GREEN"}, title="SHIP HUD",
            controls=[{"label": "Toggle Alert", "action": alert_toggle_label,
                       "data": {"ship": ship_id}}], to=console)

# a watcher sub-task, once a second, when the value moves:
overlay_hud_update(rows={"Speed": speed, "Alert": alert}, to=console)
```

Rows accept a dict or a list of `(label, value)` pairs. A control's `action` is a MAST
label run as a sub-task (so a toggle never hijacks the console's own GUI).

## Fire an overlay with a signal

There is no auto-wired signal handler, but a mission drops in a one-line **`//shared/signal`
forwarder** (one dispatch on the server fans out to the `to` targets):

```
//shared/signal/overlay
    overlay_signal_show(to, slot, kind, fields)
```
```
signal_emit("overlay", {"to": role("mainscreen"), "slot": "center_hero",
                        "kind": "hero", "fields": {"title": "CHAPTER TWO"}})
```

## Declarative overlays in AMD

Author overlays as data in an `.amd` file — a projection of the AMD document form (see
[AMD tools](../tooling/amd-tools.md)) — and fire them by key. The fence fields become
content; the body is the kind's main text; `Seconds` auto-dismisses.

```
## [Chapter Two](ch2)
---
Kind: hero
Subtitle: The Long Dark
Seconds: 4
---
CHAPTER TWO
```
```
doc = document_get_amd_file(get_mission_dir_filename("overlays.amd"))
amd_overlays(amd_section(doc, "overlays"))
overlay_amd("ch2", to=role("mainscreen"))
```

## Quests fire overlays

A quest fires overlays at **accept / complete / fail**, to the quest's participant
consoles — no wiring. Two forms, both work (underscore or spaced keys):

```
## [Rescue the Convoy](rescue)
---
Complete Overlay: convoy_saved        # reference a declared amd_overlays record
On complete: hero CONVOY SAVED         # or an inline <kind> <text>
On fail: banner Convoy lost
---
Escort the convoy to the jump point.
```

## Custom cards — your own `kind`

A `kind` maps to a **builder**. Author one in **Python** or in **MAST**.

**MAST (the sugar):** a `//overlay/<kind>` route builds the card with `gui_*` verbs;
content fields arrive as task variables. It registers itself at load — no Python, no
registration call:

```
//overlay/briefing
    gui_row("row-height: 8em;")
    gui_face(face)
    gui_row("row-height: content;")
    gui_text(f"$text:`{name}`;justify:center;font:gui-5")
    gui_row("row-height: content;")
    gui_text(f"$text:`{line}`;justify:center;font:gui-3")
```
```
overlay_show("center_hero", "briefing", name="Harkin", line="Hold the line.",
             face=get_face(admiral.id))
```

**Python:** register a function for full control (or library builders):

```python
def _briefing(cid, content):
    gui_row("row-height: 8em;"); gui_face(content["face"])
    gui_row("row-height: content;"); gui_text(f"$text:`{content['name']}`;")

overlay_register("briefing", _briefing)
```

Either way, the builder decides *layout*; the content decides *what shows* — the same
card can be driven from a wrapper, a signal, AMD, or a quest.

## announce() — the overlay AND the record, in one call

An overlay is an **attention** layer: it draws over the view, then it is gone. It keeps
no history, and a console that connects a second later never saw it. So the house rule
is that **an overlay never carries information alone** — anything a player may need to
act on later gets a durable twin.

`announce()` does both halves, picked by `level`:

| `level` | overlay | durable twin |
|---|---|---|
| `chapter` | hero card | info-panel card (history) |
| `hail` | lower third | `comms_message` from `sender` (else a card) |
| `alert` | top banner | info-panel card (history) |
| `status` | corner toast | none |
| `minor` | corner toast | none |

```
announce("Raiders have crossed the line.", title="TSN Command",
         level="alert", to="tsn")

announce(line, title=admiral.name, face=get_face(admiral.id),
         level="hail", sender=admiral.id, ship=artemis_id)
```

The overlay gets a **headline** — `announce_headline()` folds it to one ASCII line and
clamps it (engine text is ASCII-only, and a card is a glance). The full text goes to
the twin. `record=False` suppresses the twin when it is already being sent another way;
`record=True` forces a card on a level that has none.

## How it draws (the one rule)

Overlays keep off the page's repaint path: each slot is its **own** sub-region,
established during the page's repaint and then updated out-of-band (clear → fill →
complete on just that region). A slot's builder is **re-run every repaint**, so keep
custom builders **build-only** — no `await`, no state changes, just `gui_*`.

Draw order is by slot (full-screen over centre over banner over the page). Overlays
draw fine over the **3D view**; controls placed over the **interactive 2D map** are a
pending engine capability.
