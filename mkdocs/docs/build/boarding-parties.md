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
| `boarding_visit(ship, scenes, first, title=, cast=, site=, area=, place=, stories=)` | starts a visit. Returns None, and opens nothing, if one is already open or `first` names no room |
| `boarding_visiting()` | the visit in progress, or None |
| `boarding_visit_end()` | ends it now &mdash; the ship is under fire, the clock ran out |

Before this call a scene had a beginning and no end: the party stayed open after the last
room, and a console that went down late arrived in an empty one.

The section that holds the rooms can be keyed `scenes`, `scene` or `boarding`:
`## [Scenes](scenes)`. Older lessons write `(boarding)`, and it keeps working.

### A visit on a tile map

On a [ground tile map](ground-tile-maps.md) there is no first room. The party walks, and
a scene belongs to the thing or the person that opens it. Give `area=` and leave the first
room out:

```
boarding_ground_load(MISSION_DOC)

boarding_visit(ship, boarding_ground_scenes(), title="Kesh Relay", area="landing",
               stories=amd_section(MISSION_DOC, "side_stories"))
```

`area` is the `area:` line of a `.tiles` file. Whoever beams down stands at that area's
`entry:`. The same call owns the whole visit, with these differences from a text visit:

| | On a tile map |
|---|---|
| The first scene | None is begun. `scenes` are what a prop's `Scene:` and a person's `Talk scene:` name. |
| When it ends | Not when a scene closes. It ends when the game does (see [endings](#how-a-visit-ends-and-two-endings)), or when the mission calls `boarding_visit_end()`. |
| Beaming up | One console can beam up and come back down as the same person. The visit is still there, and so is what the party learned. |
| Everybody down | A party that is **all** down comes round at the area's `entry:` after 8 seconds, with 1 HP. `boarding_party_revived` is sent (`BOARDING_WHO`, `BOARDING_AREA`), so a route can say what that cost. One person down is left for the others to help. |
| Side stories | Handed to each person as they arrive, exactly as in a text visit. |

Give a first room as well (`boarding_visit(ship, scenes, "airlock", area="deck")`) and it
is the text visit described above, standing in that area: the scene is begun and watched.

The `away` starter (`sbs create <Name> -t away`) is a whole mission built on these two
calls, with no Python in it.

**Where the crew reads it: the xESS.** BEAM DOWN turns the console into the boarding party's
handheld. Its bar says who you are, your job, and the room you are in; its ACT app is the
room's line with one button per choice, and CREW is who came and the way home. With an
interior or a tile area the device sits beside the map; a party with nowhere to walk (no
`site=`, no `area=`) gets the device alone, across the screen. When the visit ends each
console is put back on its own station's screen.

The label that screen lives on is MAST, so it comes from LegendaryMissions' `boarding`
addon: list it in the mission's `story.json`. A mission without it gets a line in
`mast.runtime.log` the first time it opens a visit, because a crew member who beams down
would have no screen for the scene.

## What the party works out: `learn` and `learned`

A choice can teach the party something, and a later choice or line can ask how much it
knows:

```markdown
- [Read the name tags on the suits](suits) if medical ; learn suits
- [Answer the log](last_entry) if learned >= 2

%{learned < 2} The log is locked behind a question you cannot answer yet.
```

| | |
|---|---|
| `; learn <name>` | the party now knows `<name>`. A set: the same reading taken twice counts once |
| `learned` | how many different things the party knows **at this place** |
| `learned <name>` | whether the party knows that **one** thing: 1 or 0 |

**One fact, by name.** A door that should open once the party has read the manifest, not
once it has read any two things, asks for it:

```markdown
- [Read the manifest](hold) ; learn manifest
- [Open bay nine](bay) if learned manifest
- [Leave it sealed](hold) if learned manifest < 1

%{learned manifest} The manifest said bay nine. Bay nine is right there.
```

`if learned manifest` is true once some choice with `; learn manifest` has been taken at
this place. `if learned manifest < 1` is "not yet". Capitals and spacing do not matter,
and a fact can be more than one word (`; learn cold start`, `if learned cold start`). The
count is unchanged: `if learned >= 2` still counts everything.

The facts are the **party's**, not one character's &mdash; the surgeon's reading and the
engineer's both count &mdash; and they belong to the **place**. Each place counts only its
own, and keeps them for the mission: come back and the party still knows what it worked
out there, go somewhere new and it knows nothing yet. The place is `place=` on
`boarding_visit`, which defaults to the title.

| Call | Does |
|---|---|
| `boarding_learned(fact=None, place=None)` | how many things are known here, or 1/0 for one fact |
| `boarding_facts(place=None)` | the facts, sorted |
| `boarding_place()` | the key the current place's facts are kept under |
| `boarding_facts_forget(place=None)` | forget one place's facts, or every place's |

`boarding_visit_ended` carries `BOARDING_PLACE`, so a route can ask what was learned after
the party has come home: `boarding_facts(BOARDING_PLACE)`.

`sbs lint` reports a condition the game cannot read (`if learned => 2`), an `if` written
after the `;`, and `learn` with no name. It knows both forms of `learned`: a fact that no
choice in the file learns is `guard-learned-unknown` (`if learned manifst`), and a count
with its sign missing (`if learned 2`) or a named fact asked to be more than 1
(`if learned manifest >= 2`) is `guard-learned-shape`. It cannot tell that `learned >= 5`
asks for more than the place can teach.

## How good they are: `skill` and `check`

A job says who may try (`if engineering`). A skill says how good they are, and it comes
from the crew roster:

```amd
### [Chief Okoro](okoro)
---
Console: engineering
Roles: engineering
Skills: engineering 4, science 1
---
```

The numbers reach the person with no call from the mission, and they follow the roster
member, not the name on the console: a player who has saved a name of their own keeps them.

```amd
- [Pull the sensor record](sensors) if skill science >= 3
- [Try to wake the core](core_wakes) ; check engineering 9 else core_dead, learn lockout
```

| You write | It means |
|---|---|
| `if skill science >= 3` | offered only to someone that good. Never forwarded to another console |
| `; check engineering 9` | whoever picks it rolls a ten-sided die and adds their `engineering`. 9 or more is a success |
| `else core_dead` | where a FAILED roll goes. Without it, a failure still goes to the choice's own room |
| what follows the check (`, learn lockout`) | happens only on a success |

The roll is written into the transcript of everyone in the room: `Chief Okoro -
engineering 4, rolled 5: 9 vs 9, success.` On a tile map, each crew member standing beside
the one rolling who has the skill adds 1; in a relic, each suit within reach does.

| Skill | Target 6 | Target 9 | Target 12 |
|---|---|---|---|
| 0 | 50% | 20% | never |
| 2 (a job, no number) | 70% | 40% | 10% |
| 4 | 90% | 60% | 30% |

A second `;` separates outcomes the same as a comma: `; check engineering 9 else held ;
learn lockout`.

`sbs lint` reports what would otherwise be silent: a `Skills:` entry that is not a name
and a number (`skills-shape`), a gate with no sign or no skill (`skill-gate-shape`), a job
compared with a number it can never reach (`job-gate-never`: `if science >= 3` wants the
word `skill`), a skill nobody on the roster has (`unknown-skill`), a `check` that is not
`check <skill> <number> [else <room>]` (`check-shape`: nothing is rolled and the choice
always works), and an `else` that names no room (`check-else-missing`). A check that
cannot be read is also written to `mast.runtime.log` when it is picked.

`boarding_skills_from_amd(section)` still reads `Skills:` by NAME for people who are not
on a crew roster; `boarding_skills_set(lifeform, {...})` sets them on one body.
`boarding_checks_mode("flat")` drops the die (every roll is 5) for a test.

## How a visit ends, and two endings

`- [Return to the ship]()` - an answer with empty round brackets - **ends the visit for
everybody**, at one press by anyone aboard. The party is no longer on offer afterwards, and
nothing written in AMD reopens it. So put that answer where leaving is a decision: the
arrival room and the last rooms, not every room on the way.

One person can leave without ending it: the handheld's Crew app has **Beam up** on the
ship's row. The visit stays open, and BEAM DOWN puts them back in the room the party is in.

An answer can start, finish or fail one of the ship's quests, which is how a scene has two
endings with no MAST:

```amd
- [Throw the switch and wake them](woken) ; accepts stand_by
- [Leave them sleeping and go for help](asleep) ; accepts carry_word
```

```amd
### [Stand By the Sleepers](stand_by)
---
Scope: shared
Starts when: revealed
Done when: 30 seconds
Reward: 300 credits
---
```

| Outcome | Does |
|---|---|
| `; accepts <key>` | starts a quest that is waiting (`Starts when: revealed`, or on offer) |
| `; completes <key>` | finishes it |
| `; fails <key>` | fails it |

Write the quest `Starts when: revealed`. Written `at once` it is running before anyone
answers, and finishes whichever answer is given; `sbs lint` reports that as
`outcome-accepts-running`.

**Ending the game from a scene.** A quest can carry the last sentence the crew reads:
`Win:` and `Lose:`. Completing a quest that has `Win:` wins the game with that sentence;
failing one that has `Lose:` loses it. So an ending is an answer, and no new words:

```amd
### [Relight Kesh Relay](relight)
---
Scope: shared
Starts when: at once
Win: The beacon is lit. Every convoy on the Kesh run has its way home again.
Lose: The beacon is slag. The Kesh run stays dark.
---
```

```amd
- [Call it in]() ; completes relight
- [Step back from the smoke]() ; fails relight
```

This works from a room in a text visit and from a prop's or a person's scene on a tile
map. On a tile map it also ends the visit: every console is brought home before the
results are shown. The mission needs LegendaryMissions' `quests` addon in `story.json`,
which is what turns a won or lost quest into the end of the game.

**A condition is one name.** `if medical`, `if learned >= 3`, `if learned manifest`,
`if skill science >= 3` - a name, or a name, a sign and a number. There is no `and`, `or`
or `not`, and it takes a job, not a person. A fact is asked for with `learned` in front of
it: a bare `if manifest` is read as a job. Each of those is read as one long name nobody
answers to, so the choice is offered to nobody; `sbs lint` reports them as `guard-joined`,
`guard-names-a-fact` and `guard-names-a-person`. A choice for two jobs is two choices that
lead to the same room.

A `%` line cannot wrap: its second half, typed on the next line, is a line of its own, and
the party is shown one half or the other (`line-wrapped`).

## A quest for one person: `For:` and `stories=`

A quest can belong to one member of the party. Put those quests in a section of their own
and say who each is for:

```amd
## [Side Stories](side_stories)

### [Six Names](six_names)
---
For: medical
Starts when: at once
Done when: signal names_read
---
Six suits, and nobody has written down who wore them.
```

Hand the section to the visit, and each quest goes to its person as they come aboard:

```
boarding_visit(ship, BOARDING_SCENES, "airlock", title="The Hulk",
               stories=amd_section(MISSION_DOC, "side_stories"))
```

| `For:` names | Who gets it |
|---|---|
| a job (`medical`) | one person aboard who holds that job |
| a roster member's key (`hale`) | that seat, whatever name the player has saved |
| a name or a last name (`Dr Hale`, `Hale`) | the same |

A quest is handed out once. Someone who beams down later still gets theirs, and a quest
nobody aboard answers to is handed to nobody: unlike a choice, it is not forwarded to
another console. A `Reward:` on such a quest is paid to the ship the person came from.

A choice finishes one the way it finishes any quest: `; signal names_read`.
`boarding_quests_open_unclaimed(section)` gives the ones nobody claimed to the whole party;
call it once everybody who is coming has come.

`sbs lint` reports a `For:` nobody on the roster answers to (`for-nobody`), a personal quest
that never starts or cannot finish (`for-not-started`, `for-no-end`), one with `Scope:
shared` (`for-shared`), one nested under another (`for-nested`), a quest in the section with
no `For:` (`story-no-for`), a section nothing hands out (`stories-not-handed-out`), `For:`
under the section the ship is given (`for-in-quests`), and two outcomes with no comma
between them, `; learn suits signal names_read` (`outcome-run-together`).

Before `stories=` this was a second call, `boarding_quests_grant(section)`, that a mission
had to make in a route of its own. Written under `boarding_visit(...)` it found nobody
aboard yet and handed out nothing, with nothing in the log.

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

**Getting a run onto the ground with nobody at the consoles.** The setting
`BOARDING_AUTO_BEAM` (off by default) sends every console on the ship down as soon as a
`boarding_visit` opens, once each, with nobody pressing BEAM DOWN. It is for a headless
run and for an engine check with no mouse, never for play:

```
COSMOS_SETTINGS='{"GAME_RESULTS_SAVE": false, "BOARDING_AUTO_BEAM": true}' python -m cosmos_dev.mission_runner . --test 60 --map 0 --exercise --pilot
```

`--exercise` is what gives the run a console at all, and `--pilot` keeps the exerciser
from shooting at the station the mission is about. In the engine it is
`var.BOARDING_AUTO_BEAM=1` on the launch line.

For engine diagnostics use `logger(name=…, file=…)` **from MAST**, then `log(msg, name)`.
The engine hands back no stdout, so `print` is invisible there; and `logger` only attaches
its file handler when a MAST task exists, so calling it from `script.py` is silently a no-op.
