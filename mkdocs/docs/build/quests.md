# Quests

A signal-driven quest system ties gameplay together: objectives that trigger on
in-game events (kill / collect / scan / dock / reach / arrive), a quest log
players accept and abandon quests from, and multi-step stories.

## Authoring in AMD

Quests are authored in **AMD files** (a movie-script-style dialogue/story format)
rather than hand-written control flow, which keeps the writing readable and the
logic consistent.

## Signals

Quests emit signals you can react to from anywhere:

| Signal | Data keys | When |
|---|---|---|
| `quest_activated` | `AGENT_ID`, `QUEST_ID`, `QUEST` | a quest becomes active |
| `quest_completed` | `AGENT_ID`, `QUEST_ID`, `QUEST` | a quest is finished |

```
//signal/quest_completed
    log("Quest complete!")
```

See [Signals](../mast/routes/signals.md) and the
[quest API](../api/procedural/quest.md) for the full surface (`quest_set_state`
and friends).
