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

## Chatter / info panels

For ambient, non-blocking narrative (universe chatter, lore), prefer the info
panel over the text waterfall. See the [comms API](../api/procedural/comms.md).

!!! tip "Put reusable senders in Python"
    A message helper like the above is a good candidate for a `.py` helper function
    you call from MAST &mdash; see [Sharing reusable Python](../tooling/libraries.md).
