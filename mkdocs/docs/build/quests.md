# Quests

A signal-driven quest system ties gameplay together: objectives that trigger on
in-game events (kill / collect / scan / dock / reach / arrive), a quest log
players accept and abandon quests from, and multi-step stories.

## Authoring in AMD

Quests are authored in **AMD files** (a movie-script-style dialogue/story format)
rather than hand-written control flow, which keeps the writing readable and the
logic consistent. A quest is a `## [Title](key)` heading with a fenced block of
fields, then prose:

```amd
## [Defend the Convoy](defend_convoy)
---
Scope: shared
State: active
Goal: destroy 6 raiders
Pays: 500 credits
---
Escort the freighters through the belt - every raider you burn buys them time.
```

### Quest fields

| Field | Meaning |
|---|---|
| `Scope:` | `shared` (one quest for the whole game) or per-ship. |
| `State:` | Starting state — e.g. `active`, or omitted for a quest players must accept. |
| `Goal:` | The completion **trigger** plus the objective text shown in the log (see [Triggers](#triggers)). |
| `When:` | A trigger with no objective text (same grammar as `Goal:`). |
| `Pays:` | Reward on completion — `500 credits`, an item key, … |
| `Then:` | Follow-up on completion — `reveal <quest>` (unlock another) or `signal <name>`. |
| `Display:` / `Tier:` | Optional label / ordering for the log. |
| `Accept On:` | Restrict which **consoles** may Accept/Abandon this job from the Quests tab — e.g. `comms`, or `comms, admiral`. Overrides the mission default (see [Console gating](#console-gating)). |
| `Engage On:` | Restrict which consoles may **Engage** (travel to) this job — e.g. `helm`. Only meaningful when the mission enables the Engage button. |

### Console gating

The Quests tab **displays** on every enabled console, but *who may act* is gated per
console. A mission sets the defaults (shared vars, e.g. in `settings.yaml`):

| Var | Default | Controls |
|---|---|---|
| `QUEST_ACCEPT_CONSOLES` | `comms,admiral` | Consoles that show **Accept / Abandon**. `""` = any console (the pre-gating behavior). |
| `QUEST_ENGAGE_CONSOLES` | `helm` | Consoles that show **Engage** (when `QUEST_ENGAGE_ENABLED`). |

Engage additionally requires the job to be **accepted** (ACTIVE) — before that, the
helm shows a short *"Accept this job before engaging."* hint. On a console that can't
act, the buttons are replaced with text naming the console(s) that can. `Accept On:` /
`Engage On:` on a single quest override these lists for that job (a station-specific
task).

### Triggers

The verb in `Goal:` / `When:` (or a `fail_*` field) maps to the event the quest
listens for:

| Verb(s) | Fires on | Argument |
|---|---|---|
| `destroy`, `kill` | a kill | role (+ count, e.g. `destroy 6 raiders`) |
| `collect`, `recover`, `gather` | picking up an item | item key |
| `scan`, `survey` | a science scan | role |
| `dock` | docking | role |
| `reach`, `travel` | arriving at a sector | sector (e.g. `reach 6, 4`) |
| `signal` | a named signal — the escape hatch for any game-state milestone | signal name |

### Mission tree & end-game

Quests form a **tree** so a mission's whole win/lose condition is authored in AMD,
not hand-wired in script:

| Field | Meaning |
|---|---|
| `Parent:` | Attach this quest to a parent quest (its `key`), aggregating into that mission. |
| `Required:` | The parent isn't won until this child completes. |
| `Critical:` | Failing this quest **loses** the game. |
| `Win:` | Completing this quest **wins** the game. Bare flag, or prose that becomes the end-screen reason. |
| `Lose:` | Completing (or failing) it **loses** the game. Bare flag, or prose reason. |
| `Fail on signal:` | Fail the quest when a signal fires. |
| `Fail on all dead:` | Fail when every object of a role is gone. |
| `Fail after:` | Fail after a time — `Fail after: 5 minutes`. |

This is the same vocabulary Open Universe uses and the Siege bosses hang their
objectives on.

## Signals

Quests emit signals you can react to from anywhere:

| Signal | Data keys | When |
|---|---|---|
| `quest_activated` | `AGENT_ID`, `QUEST_ID`, `QUEST` | a quest becomes active |
| `quest_completed` | `AGENT_ID`, `QUEST_ID`, `QUEST` | a quest is finished |
| `quest_failed` | `AGENT_ID`, `QUEST_ID`, `QUEST` | a quest fails (a fail trigger fired) |

```
//signal/quest_completed
    log("Quest complete!")
```

See [Signals](../mast/routes/signals.md) and the
[quest API](../api/procedural/quest.md) for the full surface (`quest_set_state`
and friends).
