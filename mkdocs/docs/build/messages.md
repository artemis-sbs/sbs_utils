# Story & NPC messages

Missions narrate through messages &mdash; an Admiral briefing the crew, a station
replying. The reusable pattern (straight from Secret Meeting) sends one message to
the server screen, every main screen, and every player's comms.

## The "admiral message" helper

```
=== send_admiral_message
    default the_message = "You forgot to set the_message"
    face = get_face(admiral.id)

    # server screen
    sbs.send_story_dialog(0, admiral.name, the_message, face, "#444")

    # every main screen
    for c in to_object_list(role("mainscreen") & role("console")):
        sbs.send_story_dialog(c.client_id, admiral.name, the_message, face, "#444")

    # every player's comms
    comms_message(the_message, to_object_list(role("__player__") & role("tsn")), admiral.id)
    ->END
```

Call it from anywhere, passing the line as task data:

```
await task_schedule(send_admiral_message, {"the_message": "The Praetor of Peace has arrived. Escort it to the starbase."})
```

`default the_message = ...` guards against forgetting the data (see
[gotchas](../mast/gotchas.md)). `send_story_dialog(client_id, name, text, face,
color)` shows the pause-screen dialog; `comms_message(text, players, from_id)`
pushes it into comms.

## Targeting a subset

Combine roles to aim precisely &mdash; e.g. only the consoles linked to one ship:

```
for c in to_object_list(linked_to(ship_id, "consoles") & role("comms")):
    sbs.send_story_dialog(c.client_id, name, text, face, "#444")
```

## Audio & voice

Play a sound or voice line from your mission's `media/` folder. Resolve the path
with `get_mission_audio_file`, and let players opt out with a shared flag:

```
shared AUDIO_ENABLED = True     # top-level default

# later, at a story beat:
if AUDIO_ENABLED:
    sbs.play_audio_file(0, get_mission_audio_file("audio/distress_call"), 1.0, 1.0)
```

For music, `sbs.play_music_file(0, "music/default/victory")`. See the
[media API](../api/procedural/media.md).

## The ship's log

The text waterfall became the **ship's log** in v1.4.0, on every console. The waterfall
did one job — show the last few lines — with its hands tied: the engine never wrote to
it, script could not control its background, and a mission could not style it. In its
place is a log with two halves, both fed by the same record.

**The strip** &mdash; one line, the newest message, sitting where the waterfall used to be
on every console. It is the *ambient* half: always visible, no interaction, read at a
glance. `gui_log_tail()` places it; LegendaryMissions already does on all six consoles.

**The tab** &mdash; the history, in the info panel: scrollable, and filtered into **Log**
(everything), **Ship** and **Mission**. `gui_info_panel_add("log", ..., gui_panel_log,
...)`.

Newest is **first** in both, so the latest line is always in the same place rather than
one that moves as the log fills.

You write to it the way you always wrote to the waterfall:

```
comms_broadcast(ship_id, "Docking moors active", category="ship")
comms_broadcast(ship_id, "Shields critical", category="ship", severity="warning")
```

`category` picks the tab (everything shows in **Log** regardless, so a filter can never
hide a message). `severity` &mdash; `tip`, `warning`, `danger` &mdash; renders the line as
a coloured callout, the same formatting `gui_text_area` markdown uses.

!!! note "Nothing seizes the console"
    An urgent line does **not** switch the info panel to the log tab. The strip already
    shows it, in its severity colour, on every console &mdash; and switching away from the
    ship data the crew chose, with nothing to switch back, left the panel stranded. A
    mission that wants the interrupt can set `RAISE_ON = ("danger",)`.

For ambient, non-blocking narrative (universe chatter, lore), the log **is** the surface;
an info-panel card is for something the crew must act on. See the
[comms API](../api/procedural/comms.md).

!!! tip "Put reusable senders in Python"
    A message helper like the above is a good candidate for a `.py` helper function
    you call from MAST &mdash; see [Sharing reusable Python](../tooling/libraries.md).
