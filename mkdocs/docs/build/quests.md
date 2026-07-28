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
Objective: Drive the raiders off the freighters
Done when: destroy 6 raiders
Pays: 500 credits
---
Escort the freighters through the belt - every raider you burn buys them time.
```

The full file format — headings, the fence, nesting, lists and how a record says what
it is — is in [The AMD file format](amd-format.md).

### Quest fields

| Field | Meaning |
|---|---|
| `Scope:` | `shared` (one quest for the whole game) or per-ship. |
| `State:` | Starting state — `active` (running immediately), or `available` (shown on the log for a player to **Accept**; omit for the same effect). A whole board of `available` jobs is a pick-up-work board. |
| `Objective:` | The sentence the player reads in the quest log. |
| `Done when:` | The completion **trigger** (see [Triggers](#triggers)). |
| `Starts when:` | What activates the quest (same grammar). |
| `Pays:` | Reward on completion — `500 credits`, an item key, … |
| `Then:` | Follow-up on completion — `reveal <quest>` (unlock another) or `signal <name>`. |
| `Display:` / `Tier:` | Optional label / ordering for the log. |
| `Show:` | **When** this quest is listed — `always` (default), `when done` (runs unseen, appears once it completes *or* fails, reading as history), or `never` (drives its events invisibly). Not the same as `State: secret`, which also stops the triggers. |
| `Accept On:` | Restrict which **consoles** may Accept/Abandon this job from the Quests tab — e.g. `comms`, or `comms, admiral`. Overrides the mission default (see [Console gating](#console-gating)). |
| `Engage On:` | Restrict which consoles may **Engage** (travel to) this job — e.g. `helm`. Only meaningful when the mission enables the Engage button. |

### Console gating

The Quests tab **displays** on every enabled console, but *who may act* is gated per
console. A mission sets the defaults (shared vars, e.g. in `settings.yaml`):

| Var | Default | Controls |
|---|---|---|
| `QUEST_ACCEPT_CONSOLES` | `comms,admiral` | Consoles that may show **Accept / Abandon**. `""` = any console (the pre-gating behavior). |
| `QUEST_ENGAGE_CONSOLES` | `helm` | Consoles that may show **Engage** (when `QUEST_ENGAGE_ENABLED`). |

Each control is also gated by the job's **state**: **Accept** shows only for an
available (not-yet-accepted) job, **Abandon** only for an accepted (active) one, and
**Engage** only for an active one. A completed or failed job — or a section header /
no selection — shows no action controls. Engage additionally means the job must be
accepted first — before that, the helm shows a short *"Accept this job … before
engaging."* hint. On a console that can't act on an actionable job, the buttons are
replaced with text naming the console(s) that can. `Accept On:` / `Engage On:` on a
single quest override these lists for that job (a station-specific task).

### Triggers

The verb in `Done when:` / `Starts when:` (or a `fail_*` field) maps to the event the quest
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

!!! tip "`Fail after:` starts counting when the quest goes ACTIVE"
    The deadline is anchored **lazily** — the clock starts on the first tick the
    quest is **active**, not when it is granted. So an `available` job's timer does not
    run until a player **Accepts** it: a timed rescue gives the crew the full window
    from the moment they take it on, instead of ticking down while it sits
    unaccepted on the board. (Pair it with **spawn-on-accept** — key the target
    spawn off the `quest_activated` signal or a state watch — so the objective's
    objects also appear only once the job is taken.)

## Signals

Quests emit signals you can react to from anywhere:

**Signals go two ways, and the names are dangerously similar.** Check the direction
before you write a route — listening on an input waits for something nothing sends, and
fails in total silence.

**Driver → you** (react to these):

| Signal | Data keys | When |
|---|---|---|
| `quest_started` | `AGENT_ID`, `QUEST_ID`, `DATA` | a quest became active |
| `quest_succeeded` | `AGENT_ID`, `QUEST_ID`, `DATA` | a quest **completed** (rewards granted, reveals done) |
| `quest_failed_done` | `AGENT_ID`, `QUEST_ID`, `DATA` | a quest **failed** (penalty applied) |
| a quest's own `Signal:` | `AGENT_ID`, `QUEST_ID` | that quest completed, if it declares one |

**You → driver** (emit these to *drive* a quest; the driver listens):

| Signal | Data keys | Effect |
|---|---|---|
| `quest_activated` | `AGENT_ID`, `QUEST_ID` | mark the quest active |
| `quest_completed` | `AGENT_ID`, `QUEST_ID` | mark the quest complete |
| `quest_failed` | `AGENT_ID`, `QUEST_ID` | mark the quest failed |
| `quest_signal` | `SIGNAL_NAME` | advance any quest whose `Done when: signal <name>` matches |

!!! warning "`quest_completed` is a request, not a notification"
    To *react* to a quest finishing, listen for **`quest_succeeded`**. `quest_completed`
    is what you emit to *ask* for a quest to be completed — the driver handles it and
    calls `quest_mark_complete`. Writing `//signal/quest_completed` to catch a
    completion is a route that never runs, and it fails in silence.

    Request → announcement: `quest_activated` → `quest_started`,
    `quest_completed` → `quest_succeeded`, `quest_failed` → `quest_failed_done`.

!!! tip "Put event bodies on `//shared/signal`"
    Every message verb addresses its own audience. On a plain `//signal` the route runs
    once per connected console **plus** the server, so a five-console bridge sends each
    message five times and performs each side effect five times.

```
//shared/signal/quest_succeeded
    log("Quest complete!")
```

See [Signals](../mast/routes/signals.md) and the
[quest API](../api/procedural/quest.md) for the full surface (`quest_set_state`
and friends).
