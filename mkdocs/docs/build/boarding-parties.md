# Boarding parties

A boarding mission is a scene several consoles play at once, **one character each**. Everybody
is looking at the same beat, but the scene offers each of them a different set of things to
do — the doctor can read a body, the engineer can read the reactor, and neither can do the
other's job.

That is authored once, as ordinary [dialogue AMD](amd-format.md), with **no new syntax**:

```markdown
### [The Airlock](lab)
---
Speaker: outpost
---
% The inner door is open. The lights are on a low cycle.

- [Read the body by the hatch](autopsy)  if medical >= 1
- [Force the wall panel](panel_open)     if engineering >= 1
- [Check the corners first](cover)       if security >= 1
- [Move further in](corridor)
```

The guards read the **acting character's roles**. Give one console Dr Sorel
(`Roles: boarding, medical`) and another Chief Ruiz (`Roles: boarding, engineering`) and the same
scene draws two different menus. Every character also sees `Move further in`, because it is
ungated — which is what keeps a menu from ever being empty.

!!! tip "Why this works with no new grammar"
    `dialogue_choices(scene, agent_id, speaker)` has always evaluated guards against
    whatever agent it is handed. The shipped comms driver passes the player **ship**, so
    everyone sees one menu. `boarding.py` passes the **character**.

## The short way: `boarding_visit`

Most missions need none of the pieces further down. One call runs a whole visit:

```
shared BOARDING_SCENES = dialogue_scenes(amd_section(MISSION_DOC, "boarding"))

boarding_visit(ship, BOARDING_SCENES, "airlock", title="The Hulk")
```

It opens the party, begins the room it is given, and from then on watches the scene. When
the scene closes &mdash; a choice that leads nowhere, `- [Return to the ship]()` &mdash; it
shuts the party, puts every console back at the station it left, and emits
`boarding_visit_ended` (`BOARDING_SHIP`, `BOARDING_TITLE`).

**The party is the crew.** With no `cast=`, each console goes as the person it already is:
the name, face and `Roles:` its [crew roster](crew.md) gave it, or the seat it left when the
roster gave it no role. A job nobody aboard holds is forwarded to one console, so a short
crew still reaches every choice. To put the script's own people on the bridge *and* on the
ground, write a roster and give it `Names: locked`.

Pass `cast=[...]`, a list of lifeforms, only when the people going are deliberately not the
crew.

| Call | Does |
|---|---|
| `boarding_visit(ship, scenes, first, title=, cast=, site=, area=)` | starts a visit. Returns None, and opens nothing, if one is already open or `first` names no room |
| `boarding_visiting()` | the visit in progress, or None |
| `boarding_visit_end()` | ends it now &mdash; the ship is under fire, the clock ran out |

Before this call a scene had a beginning and no end: the party stayed open after the last
room, and a console that went down late arrived in an empty one.

The rest of this page is what `boarding_visit` is built from, for a mission that has to
drive a scene itself.

## The pieces

| You need | Use |
|---|---|
| The bodies on the ground | an `## Boarding Party` section of [lifeforms](sides-lifeforms.md), spawned with `lifeforms_spawn(section)` |
| Who is playing whom | `boarding_assign(client_id, lifeform)` |
| Guards that ask about the character | `boarding_metric_install()` once, at map start |
| The current beat | `boarding_scene_begin(scenes, key, speaker=…)` |
| What THIS console may do | `boarding_choices(client_id)` |
| Taking an answer | `boarding_answer(client_id, index, seq)` |

A character is a **lifeform** — a body in the world. Who the *player* is remains a
[crew post](crew.md), a label on a seat. The two are linked, not merged.

## Writing the screen

```
=== boarding_screen
    jump boarding_beam_up if not boarding_is_open()

    boarding_said = boarding_line()
    gui_text_area("{boarding_said}")

    boarding_seq_now = boarding_seq()
    for boarding_i, boarding_ch in enumerate(boarding_choices(client_id)):
        gui_row("row-height: 2.4em;")
        boarding_label = boarding_ch.label
        gui_button("$text:`{boarding_label}`;", data={"pick_index": boarding_i, "pick_seq": boarding_seq_now}, on_press=boarding_pick)

    on change boarding_seq():
        jump boarding_screen

    await gui()

=== boarding_pick
    boarding_answer(client_id, pick_index, pick_seq)
    ->END
```

Three things in there are load-bearing:

- **`on_press=` + `data=`, never an inline `on gui_message` block.** The choices are drawn
  in a `for` loop, and a handler block registered in a loop captures the loop variable at
  its last value.
- **`on change boarding_seq()` is how the other consoles follow along.** A signal does *not*
  wake a task sitting in `await gui()`; a polled revision counter cannot miss the
  transition. Get this wrong and everyone else's screen goes stale until something else
  happens to rebuild it.
- **The console hands back the seq it rendered with.** That is the arbitration — see below.

## Two consoles pressing at once

`boarding_answer` refuses a press whose token has moved on. The token bumps on every beat and
every answer, **before** the outcome runs, so a second press arriving in the same frame is
already stale by the time it is looked at. Two officers can press different choices in the
same frame and exactly one lands, with no lock.

!!! warning "`overlay_choice` is not a substitute"
    It hands the whole audience one shared `Promise`, and `Promise.set_result` has no
    already-done guard. The first press wins *across ticks*, but two presses **in the same
    frame are last-writer-wins**. With six consoles able to act, that is the race you have.

## One line for everybody

`dialogue_pick_line` picks a **random** eligible variant. Called once per console it tells
each of them a different story, which reads as a fault in the writing rather than in the
code. `boarding_scene_begin` picks the line once and `boarding_line()` gives every console the same
one.

## Faces and pictures in the transcript

The xESS **Act** app shows a conversation as a transcript (`boarding_reader`), and a face
appears wherever someone in particular is speaking:

- **The person you are talking to.** A talk scene's lines have that person's face beside
  them. The face comes from the person's `Face:`, a face string or a keyword (`female`,
  `male`, `terran`) resolved once when the mission loads, so it stays the same all
  mission.
- **A scene's speaker.** When a scene's `Speaker:` is someone with a face, such as a cast
  member, a crew member or a role someone holds, their face is beside the line. It is
  resolved the way a hail's speaker is.
- **Who chose.** Above each choice made are the face and name of the crew member who made
  it, on every console in the conversation, so a party of several consoles can see who
  said what.

Where there is no face, a **picture** of what the scene is about stands in, drawn from the
mission's tile art:

- **A prop.** Using a terminal, a wreck or a hatch shows the prop's sprite beside its
  lines, or its open look once opened.
- **A person with no `Face:`.** Their map figure, facing you, so an alien the face art
  cannot draw still has a portrait.
- **Something picked up.** A line in that console's transcript says who picked up what,
  with the picture it lay on the map with.

A scene can also name its own picture with `Backdrop:` - an atlas key - and when the art
has it, that is the picture whatever opened the scene. It is how a relic's places are
illustrated.

Narration and a crowd get neither. Neither does a sprite the mission's art does not
have: a mission with no tile art simply shows words.

```markdown
### [Magistrate Ines Oyelaran](oyelaran)
---
Area: colony
At: 10, 14
Sprite: fig:captain_f
Face: ter #6b3a20 1 0;ter #fff 23 6;ter #6b3a20 12 1;ter #6b3a20 4 2;ter #fff 11 3;
Calm: yes
Talk scene: oyelaran
---
```

## In a relic: a party in suits

A boarding party in a ruin wears SUITS - each crew member flies their own, by destination,
through a relic volume ([Relics](relics.md)). The same xESS and the same transcript go
with them, and most of the above carries over unchanged:

| On the ground | In a suit |
|---|---|
| Walking up to a prop opens its scene | Arriving at a place with `Scene:` opens it, once, for whoever is near |
| A prop's sprite is the picture | The scene's `Backdrop:` is the picture (`Backdrop:` works on the ground too, and beats the prop's sprite) |
| Crew in the next tile help a check | Other suits within reach with the same job help a check |
| Look / Pack / Tasks / Scan | **Scan** reads the room and the nearest place's `Scan:`, and lists the finds in reach with a **Read** button; **Tasks** lists the crew member's stories, and its leads fly the suit there; **Nav** marks leads `>` and places with something still to take `+` |
| Picked up into the pack | Hooked with the tether and collected for the SHIP the suit came from; the transcript notes it with the item's `Sprite:` |

A find a suit reads with **Read** is a scan the mission hears as `eva_scanned`
(`EVA_CLIENT`, `EVA_TARGET`, `EVA_RELIC`, `EVA_ITEM`) - Storm's Beacon treats a Beacon piece
read from a suit exactly like one scanned from the ship.

## Ending a scene

A choice with an **empty target** ends the conversation:

```markdown
- [Beam back up]()
```

Without one, a scene with no choices is a dead end — the screen draws its line and no
buttons, and nothing ever closes. `boarding_is_open()` then goes False, and the repaint above
carries each console into its beam-up label.

## Showing who a character is

`boarding_job_text(lifeform)` is what a screen should print, not the raw role list:

```
    gui_text("$text:`{boarding_name}`;justify:center;font:gui-4")
    boarding_job = boarding_job_text(boarding_who, default="watching")
    gui_text("$text:`{boarding_job}`;justify:center;font:gui-2")
```

A lifeform carries machinery beside its job. `ultra_beam` is added automatically to anyone
with no space-object host — that is *every* boarding-party member the moment they beam down — and
the AMD loader stamps `amd_lifeform:<key>`. Printed raw, a medic reads
`medical, ultra_beam, amd_lifeform:sorel`. Roles are also a **set**, so an unsorted list
reads differently on each repaint, which looks like a bug in the mission.

!!! danger "Assign the whole team BEFORE rerouting anybody"
    `gui_reroute_client` ticks that client's GUI task **in the same frame**, so a screen that
    draws the whole team must not be rerouted while the team is still being built. Do it in
    one loop and the main screen — which sorts first, being client 0 — draws an empty roster
    and only fills in on the next beat. Two passes: assign everyone, then reroute everyone.

## Morphing a console, and putting it back

The order matters, and is the same recipe the Control Gallery's viewer uses:

```
    gui_widget_list_clear()                       # a console leaves an engine widget list behind
    for t in gui_get_console_types():
        remove_role(client_id, t)                 # roles OUTLIVE the page that added them
    add_role(client_id, f"console, crew")
    set_inventory_value(client_id, "CONSOLE_TYPE", "boarding")
```

Record where the console came from on the way down (`CONSOLE_TYPE`) and restore both the
type **and the role** on the way back.

!!! danger "The role is not optional, and its absence is silent"
    Audience narrowing goes through `any_role()`. A console with the right `CONSOLE_TYPE`
    and no role simply stops receiving overlays, `announce()` and comms — nothing errors.
    Note also that `add_role(cid, "console, {x}")` is **not** interpolated: a plain string
    in a function argument is not an f-string. Write `f"console, {x}"`.

!!! note "The crew post, and the half of it that does not survive"
    A morph changes `CONSOLE_TYPE`, and a crew seat is believed only while that still agrees.
    Measured: `seats=1` before the morph, **`seats=0` during**, with the member back in
    `crew_choices_for`'s free list.

    The two halves come apart. The **display** survives — `crew_post_of` reads the client's
    inventory, which a morph does not touch, so the screen still shows the right name. The
    **reservation** does not, so a console that stayed could be assigned the same person and
    you get two of them. `crew_seat_count()` will not show you this: it counts stored seats
    while the liveness filter runs at resolve time. Ask `crew_choices_for(ship_id)`.

    Restoring `CONSOLE_TYPE` does not take the seat back either — only `crew_assign` does,
    and `common_console_show` does not call it. Remember the pick on the way down and
    re-assert it on the way back. See [Crew rosters](crew.md).

## Testing it

Headless `--test` never opens a console page, so it proves the story compiles and the routes
fire — and nothing about the screen. Two things that do:

- **A panel harness** drives the real screen in-process: push two client pages, reroute each
  into the crew-console label, and read the buttons each one emitted. Assert the two lists
  *differ* — if guard evaluation ever stops seeing the character, both are still lists,
  just the same one.
- **The engine**, with a server-side driver that answers for a console every few seconds, so
  a full run — beam down, every beat, beam up — needs nobody to click.

For engine diagnostics use `logger(name=…, file=…)` **from MAST**, then `log(msg, name)`.
The engine hands back no stdout, so `print` is invisible there; and `logger` only attaches
its file handler when a MAST task exists, so calling it from `script.py` is silently a no-op.
