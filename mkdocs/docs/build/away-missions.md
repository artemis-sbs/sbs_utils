# Away missions

An away mission is a scene several consoles play at once, **one character each**. Everybody
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
(`Roles: away, medical`) and another Chief Ruiz (`Roles: away, engineering`) and the same
scene draws two different menus. Every character also sees `Move further in`, because it is
ungated — which is what keeps a menu from ever being empty.

!!! tip "Why this works with no new grammar"
    `dialogue_choices(scene, agent_id, speaker)` has always evaluated guards against
    whatever agent it is handed. The shipped comms driver passes the player **ship**, so
    everyone sees one menu. `away.py` passes the **character**.

## The pieces

| You need | Use |
|---|---|
| The bodies on the ground | an `## Away Team` section of [lifeforms](sides-lifeforms.md), spawned with `lifeforms_spawn(section)` |
| Who is playing whom | `away_assign(client_id, lifeform)` |
| Guards that ask about the character | `away_metric_install()` once, at map start |
| The current beat | `away_scene_begin(scenes, key, speaker=…)` |
| What THIS console may do | `away_choices(client_id)` |
| Taking an answer | `away_answer(client_id, index, seq)` |

A character is a **lifeform** — a body in the world. Who the *player* is remains a
[crew post](crew.md), a label on a seat. The two are linked, not merged.

## Writing the screen

```
=== away_screen
    jump away_beam_up if not away_is_open()

    away_said = away_line()
    gui_text_area("{away_said}")

    away_seq_now = away_seq()
    for away_i, away_ch in enumerate(away_choices(client_id)):
        gui_row("row-height: 2.4em;")
        away_label = away_ch.label
        gui_button("$text:`{away_label}`;", data={"pick_index": away_i, "pick_seq": away_seq_now}, on_press=away_pick)

    on change away_seq():
        jump away_screen

    await gui()

=== away_pick
    away_answer(client_id, pick_index, pick_seq)
    ->END
```

Three things in there are load-bearing:

- **`on_press=` + `data=`, never an inline `on gui_message` block.** The choices are drawn
  in a `for` loop, and a handler block registered in a loop captures the loop variable at
  its last value.
- **`on change away_seq()` is how the other consoles follow along.** A signal does *not*
  wake a task sitting in `await gui()`; a polled revision counter cannot miss the
  transition. Get this wrong and everyone else's screen goes stale until something else
  happens to rebuild it.
- **The console hands back the seq it rendered with.** That is the arbitration — see below.

## Two consoles pressing at once

`away_answer` refuses a press whose token has moved on. The token bumps on every beat and
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
code. `away_scene_begin` picks the line once and `away_line()` gives every console the same
one.

## Ending a scene

A choice with an **empty target** ends the conversation:

```markdown
- [Beam back up]()
```

Without one, a scene with no choices is a dead end — the screen draws its line and no
buttons, and nothing ever closes. `away_is_open()` then goes False, and the repaint above
carries each console into its beam-up label.

## Morphing a console, and putting it back

The order matters, and is the same recipe the Control Gallery's viewer uses:

```
    gui_widget_list_clear()                       # a console leaves an engine widget list behind
    for t in gui_get_console_types():
        remove_role(client_id, t)                 # roles OUTLIVE the page that added them
    add_role(client_id, f"console, away")
    set_inventory_value(client_id, "CONSOLE_TYPE", "away")
```

Record where the console came from on the way down (`CONSOLE_TYPE`) and restore both the
type **and the role** on the way back.

!!! danger "The role is not optional, and its absence is silent"
    Audience narrowing goes through `any_role()`. A console with the right `CONSOLE_TYPE`
    and no role simply stops receiving overlays, `announce()` and comms — nothing errors.
    Note also that `add_role(cid, "console, {x}")` is **not** interpolated: a plain string
    in a function argument is not an f-string. Write `f"console, {x}"`.

!!! note "The crew post"
    A morph changes `CONSOLE_TYPE`, and a crew seat is believed only while that still
    agrees — so the morph frees the seat and the player's name and face disappear.
    Re-assert the post after the morph with an explicit `own_pick`, and again on the way
    back. See [Crew rosters](crew.md).

## Testing it

Headless `--test` never opens a console page, so it proves the story compiles and the routes
fire — and nothing about the screen. Two things that do:

- **A panel harness** drives the real screen in-process: push two client pages, reroute each
  into the away label, and read the buttons each one emitted. Assert the two lists
  *differ* — if guard evaluation ever stops seeing the character, both are still lists,
  just the same one.
- **The engine**, with a server-side driver that answers for a console every few seconds, so
  a full run — beam down, every beat, beam up — needs nobody to click.

For engine diagnostics use `logger(name=…, file=…)` **from MAST**, then `log(msg, name)`.
The engine hands back no stdout, so `print` is invisible there; and `logger` only attaches
its file handler when a MAST task exists, so calling it from `script.py` is silently a no-op.
