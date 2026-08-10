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
Starts when: at once
Objective: Drive the raiders off the freighters
Done when: destroy 6 raiders
Reward: 500 credits
---
Escort the freighters through the belt - every raider you burn buys them time.
```

The full file format — headings, the fence, nesting, lists and how a record says what
it is — is in [The AMD file format](amd-format.md).

### Quest fields

| Field | Meaning |
|---|---|
| `Scope:` | `shared` (one quest for the whole game) or per-ship. |
| `At start:` | The older way of saying the same thing — `running` / `offered` / `hidden`, and `active` / `available` / `idle` / `secret` before that. All still parse. |
| `At start: posting` | **Posted, not acceptable.** It is listed like an available job, but the Accept button does not show — the only way to take it is whatever else offers it, typically answering an [incoming hail](amd-format.md#hails--the-beat-opens-with-an-incoming-call). |
| `Objective:` | The sentence the player reads in the quest log. |
| `Done when:` | The completion **trigger** (see [Triggers](#triggers)). |
| `Starts when:` | **When it arms** — `at once`, `accepted` (the player takes it off the board), `revealed` (another quest reveals it). |
| `Fails when:` | What fails it — the same grammar, plus `all dead <role>` and a bare time (`5 minutes`). |
| `Reward:` | What completing it gives — `500 credits`, an item key, … (`Pays:` also parses). |
| `Penalty:` | What failing it costs — same grammar. Abandoning an accepted job fails it, so this is what walking away costs. |
| `Then:` | Follow-up on completion — `reveal <quest>` (unlock another) or `signal <name>`. Those two words only; anything else is read as a reveal target, and the linter says so. |
| `Display:` / `Tier:` | Optional label / ordering for the log. |
| `Show:` | **When** this quest is listed — `always` (default), `when done` (runs unseen, appears once it completes *or* fails, reading as history), `with children` (a grouping heading: a row only while something under it is listed), or `never` (drives its events invisibly). Not the same as `Starts when: revealed`, which also stops the triggers. |
| `Accept On:` | Restrict which **consoles** may Accept/Abandon this job from the Quests tab — e.g. `comms`, or `comms, admiral`. Overrides the mission default (see [Console gating](#console-gating)). |
| `Engage On:` | Restrict which consoles may **Engage** (travel to) this job — e.g. `helm`. Only meaningful when the mission enables the Engage button. |
| `Action:` | What the world does the moment this beat **starts** — including `<who> hails <scene>`, which calls the crew. See [`Action:`](amd-format.md#action--stage-directions). |
| `Speaker:` | **Who this quest talks as** — a character or ship key. Today it is the voice of the [deadline reminders](#deadline-reminders); anything else the quest needs to say uses it too. |
| `Signal says:` | The words a deadline reminder transmits. `{time}` interpolates the clock — see [deadline reminders](#deadline-reminders). |

!!! tip "Say `Beat` or `Arc` instead"
    A record that calls itself a **`Beat`** (a moment the crew lives through) already
    means `Show: when done`, and an **`Arc`** (the heading over a run of beats) already
    means `Show: with children` — see [screenplay words](amd-format.md#screenplay-words).
    Write `Show:` only to contradict the word.

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
| `all dead` | every object of a role is gone | role |
| *a time* | `5 minutes` / `30 seconds` — a time is a trigger like any other | — |
| `accepted` / `revealed` | the player takes the job off the board / another quest reveals it | — |

### Mission tree & end-game

Quests form a **tree** so a mission's whole win/lose condition is authored in AMD,
not hand-wired in script:

| Field | Meaning |
|---|---|
| `Part of:` | Attach this quest to a parent quest (its `key`), aggregating into that mission. |
| `Required:` | The parent isn't won until this child completes. |
| `Fatal:` | Failing this quest **loses** the game. |
| `Win:` | Completing this quest **wins** the game. Bare flag, or prose that becomes the end-screen reason. |
| `Lose:` | Completing (or failing) it **loses** the game. Bare flag, or prose reason. |
| `Fails when:` | Fail the quest — `signal base_lost`, `all dead convoy`, `5 minutes`. |

This is the same vocabulary Open Universe uses and the Siege bosses hang their
objectives on.

!!! tip "A `Fails when:` time starts counting when the quest goes ACTIVE"
    The deadline is anchored **lazily** — the clock starts on the first tick the
    quest is **active**, not when it is granted. So an `available` job's timer does not
    run until a player **Accepts** it: a timed rescue gives the crew the full window
    from the moment they take it on, instead of ticking down while it sits
    unaccepted on the board. (Pair it with **spawn-on-accept** — key the target
    spawn off the `quest_activated` signal or a state watch — so the objective's
    objects also appear only once the job is taken.)

### Deadline reminders

A countdown that only lives on the Quests tab is one the crew discovers by failing. A
job with a `Fails when:` deadline calls in as its clock runs down, on comms, in the
voice of whatever is transmitting:

```amd
## [Rescue the Shuttle](rescue_shuttle)
---
Job
Speaker: shuttle_pilot
Fails when: 6 minutes
Signal says: LIFE SUPPORT CRITICAL. {time} TO FAILURE.
---
Their air is going. Reach them before the clock does.
```

**Cadence** is absolute marks — **5:00, 2:00, 1:00 and 0:30** — filtered to the ones
that fit under the deadline. A six-minute job gets all four; a forty-five-second job
gets two. They are sparse early and tighten as it matters, which a fixed interval
cannot do: every-minute is spam on a long job, and fractions of the deadline land
three messages seconds apart on a short one. A mark equal to the deadline never fires,
so a five-minute job does not announce "5:00 remaining" the instant it is accepted, and
a tick that crosses several marks at once (a long frame, a restart) sends only the most
urgent rather than a burst.

**Who speaks** is resolved in the order of how much you asked for it:

| Order | Source |
|---|---|
| 1 | `Speaker:` on the quest. |
| 2 | `Held by:`, when it resolves to something that can talk — a station's job speaks with the station's face for free. |
| 3 | The mission's registered dispatch voice (`quest_dispatch_voice(<agent>)`). |
| 4 | **Silence.** A reminder from nobody is worse than no reminder. |

The mission registers its own dispatch voice, because the library has no business
knowing which faction is in charge — and it is resolved lazily, so you may register it
before the cast has spawned.

**What it says** comes from `Signal says:`, with `{time}` replaced by the remaining
clock. Without one, the wording follows the voice: a speaker with **no face** is a
machine and *transmits* ("AUTOMATED SIGNAL - 2:00 REMAINING"), a cast character *speaks*
("2:00 remaining."). Either way the message arrives on **comms**, titled with the
quest's name — a crew can hold several timed jobs at once, and an urgent line about the
wrong one is worse than none. The last mark is marked **final** and colored red.

!!! note "`Signal says:` is not `Done when: signal <name>`"
    Same word, two jobs: in `Done when: signal breach` the signal is an **event name**;
    in `Signal says:` it is the thing **transmitting**. One is a field value, the other
    a field label, which is the only reason the collision is safe.

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

!!! note "`Then: signal X` reaches other quests too"
    `Then: signal X` fires the raw signal `X` — so a `//signal/X` route still matches
    what you wrote — **and** the `quest_signal` milestone, so another quest's
    `Done when: signal X` advances. A choice in a hail written `; signal X` does the
    same. Before this the two lines read as if they met and never did.

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

!!! tip "A trigger in `Starts when:` is a real gate"
    `Starts when: signal relief_authorised` **opens** the quest; its `Done when:` then
    decides what finishes it. The two are separate, so a gate can no longer complete the
    job it was only meant to unlock. A quest with a start trigger is not advancing until
    that trigger fires.
