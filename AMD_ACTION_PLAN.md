# AMD: stage directions and settings

AMD can already write **dialogue**. A screenplay page has three things: a slug line, an
action block, and dialogue. This adds the other two.

Prime directive is unchanged from `AMD_PLAN.md`: **AMD is for sci-fi authors, not
programmers.** The read-aloud test gates every addition here.

---

## 1. The gap

AMD has three lifecycle slots and they are all about *conditions*:

| Slot | What it is |
|---|---|
| `Starts when:` | entry condition |
| `Done when:` | exit condition |
| `Then:` | exit **effects** (`reveal x`, `signal y`) |

There is no slot for **what happens when a record starts**. `Then:` fires on completion -
it is what unlocks the next beat. So an author who wants "when the trap springs, the
freighter runs and the raider turns to chase" has nowhere to write it, and drops to MAST.

That is the whole hole. Everything below fills it.

---

## 1.5 What the corpus says - and it contradicts the design

Surveyed LM, OU, SecretMeeting, WalkTheLine, StormsBeacon, HereThereBeMonsters and
MiningDays for **runs of consecutive world-action statements** - the thing an `Action:`
block would replace. Excluded: inventory/data plumbing (`set_inventory_value` and friends,
which no author writes as a stage direction), engine infrastructure (`prefabs/`, `ai/`,
consoles, autoplay, debug), and objective `+++ enter` blocks (those *implement* orders).

**25 runs, 62 statements.** 19 of the 25 are only 2 lines. LM 18, OU 2, StormsBeacon 2,
SecretMeeting / HTBM / MiningDays 1 each.

| Verb | Uses |
|---|---|
| `becomes` (role / side change) | 30 |
| `arrives` (spawn) | 20 |
| `orders` (objective / brain) | 8 |
| `says` (comms) | 2 |
| `departs` (delete) | 2 |
| **`targets`** | **0** |
| **`heads to`** | **0** |

Three conclusions, and the first two are unwelcome:

1. **The vocabulary is wrong.** `becomes` and `arrives` are 50 of 62 statements - 81% -
   and neither needs the objective layer at all. The `orders` machinery that sections 3.4,
   4 and 7 spend most of their design effort on covers 8 uses.
2. **The two motivating verbs have zero corpus support.** `targets` and `heads to` - the
   examples this whole plan grew from - appear nowhere. **Caveat that cuts the other way:**
   a corpus measures only *expressed* demand. Authors cannot write what the format does not
   offer, and those two verbs are precisely what a person reached for unprompted when asked
   to imagine the feature. Absence here is weak evidence, not proof of no demand.
3. **Runs are short**, which independently confirms 3.2: the inline list is the right
   default and the promoted `Actor:` record is genuinely the exception.

### 1.5.1 CORRECTION - the run-based count undercounts single-line verbs

Migrating the first site showed the "`heads to` / `targets` = 0" figure is an artifact of
the method. Counting *runs of >=2 consecutive* action statements favours verbs that
CLUSTER (you flip four roles at once) and hides verbs that appear ALONE. An order is
almost always one line with setup around it, so no run ever forms.

Raw count of `target_pos(` / `target(` outside `prefabs/` and `ai/`: **16**, not 0 - LM 11,
SecretMeeting 3, MiningDays 1.

Reading them changes the conclusion again, though. Most are `BRAIN_AGENT_ID` - brain
internals, the implementation of a tree node, which no author writes. The author-level
ones are about **six**, and every one takes a COORDINATE or a computed position:

```
target_pos(kidnapper_id, 90000, 0, 90000, throttle=1.5, target_id=0)
target_pos(COMMS_SELECTED_ID, stop_pos.x, stop_pos.y, stop_pos.z, throttle=0.0, ...)
```

`Kidnapper heads to 90000, 0, 90000` is not an improvement on that line - it is the same
numbers with more ceremony. **So the deferral stands, for a better and falsifiable
reason:** orders are not unused, they are unnamed. `heads to` pays off only when the
destination has a NAME, and today none of these do. If landmarks became the normal way to
say where, the verb would become worth having - and that is a thing to watch for rather
than a permanent verdict.

The clearest real example in the corpus is `maps/bosses/ragnarok.mast` - Xorn defects,
changes side, and turns on Ragnarok - which is a `becomes` + `orders` pair, and is almost
exactly the scenario this plan was started from.

**Recommendation: build `becomes` and `arrives` first and leave the orders layer out.**
That is 81% of measured demand, needs no brain negotiation, and makes 3.4's
exclusive/layered question - the most intricate part of this plan - unnecessary until
something asks for it.

---

## 2. What already exists (the reason this is small)

The vocabulary was already written, in `LegendaryMissions/prefabs/defender.mast`:

| Label | `display_name` | `valid_for` |
|---|---|---|
| `objective_goto_location` | Head to location | any |
| `objective_attack_target` | Attack | hostile |
| `objective_protect_area` | Protect | allies |
| `objective_full_stop` | Full Stop | self |

Every one is `type: objective/orders/defender`, takes `objective_target` /
`objective_target_point` through metadata, and is applied with
`objective_add(agent_id, label, data)` (`procedural/objective.py:346`).

Four things follow, and each one removes work:

1. **Objectives own the brain, they do not fight it.** Every order's `+++ enter` block
   calls `brain_clear(OBJECTIVE_AGENT_ID)` and then composes a new brain stack. So an
   authored direction is not a field write that the AI overwrites a tick later - it
   *replaces* the AI. (This was the open question; `defender.mast:58` settles it.)
2. **Orders are already discovered by metadata type.** `friendly_give_orders.mast` reads
   a ship's `give_orders_type` and builds a comms menu from every label of that type,
   using `display_name`. AMD's action line is the same lookup from a different surface -
   not a new mechanism.
3. **Ships already declare which orders they accept** (`give_orders_type:
   objective/orders/defender` on the prefab). "You cannot tell that ship to do that" is
   therefore checkable.
4. **Operand constraints are already declared.** `valid_for: hostile | allies | any |
   self` is on every order. `Xorn protects Ragnarok` where Ragnarok is an enemy is a lint
   error the data already supports.

---

## 3. The format

### 3.1 `Action:` - the block that fires on entry

```
### [The trap closes](ambush)
---
Beat
Starts when: signal alarm
Action:
  - Ragnarok heads to DS1
  - Xorn attacks Ragnarok
  - Regus boards Artemis
---
The freighter lights her engines. The raider swings to follow.
```

Rules:

- The lines are **simultaneous**. Order in the list is not execution order. If order
  matters, that is a second beat with its own `Starts when:` - which the trigger grammar
  already supports (`Starts when: 3 seconds`).
- No conditionals, no loops, no sequencing. A direction is a statement. The moment one
  needs an `if`, the answer is two beats with different `Starts when:`, exactly as a
  branching quest is already authored.
- The list form needs no new fence syntax - an empty value already nests into a list.
- **An order declares whether it is exclusive.** See 3.4 - two *exclusive* orders on one
  actor in one block is a lint error; layered ones stack.
- The subject is separated from the object by the verb, so two same-typed references are
  never ambiguous. (This is why `Target: ragnarok ds1` was rejected: pulling the verb out
  from between them removes the only thing that says which is which.)

### 3.2 A line is an unnamed cue

The same direction is promoted to its own record when it needs a name, its own trigger,
or a row on the Story Timeline:

```
### [Xorn closes in](xorn_closes)
---
Cue
Actor: xorn
Starts when: player_scanned_the_wreck
Attacks: ragnarok
---
```

These are not two mechanisms. It is one concept at two weights - the same escalation the
format already has between `Then: reveal x` and a child step record, and between a
dialogue choice's inline `; signal paid` and a full scene.

**A line in `Action:` is the default.** The record form is the exception. If the promoted
form is not clearly more expensive to write, authors will reach for it every time and the
format gets heavier for no gain.

### 3.3 Two kinds of line

| | Binds to | Example | Repeat behavior |
|---|---|---|---|
| **Order** (a state) | an `objective/orders/*` label | `Ragnarok heads to DS1` | Idempotent. Re-entering the beat re-issues the same order, which is a no-op. |
| **Event** (a moment) | a registered one-shot | `Regus boards Artemis` | **Not** idempotent. Needs identity or `once`. |

The split matters for exactly one reason: a beat can be entered more than once (re-reveal,
mission reload, a repeatable thread), and a second `boards` spawns a second Regus. That is
the same landmine `sbs lint` already flags in MAST as `signal-init-unkeyed-spawn`. Event
verbs must either be keyed (`ensure`, not `spawn`) or carry `once`.

---

### 3.4 Orders compose - the four existing ones just do not

An agent carries **many** objectives at once. `objective_add` accepts a list and creates
one `Objective` per (agent, label) pair; objectives are linked to the ship as a collection
(`linked_to(agent, "OBJECTIVE")`) and `objectives_run_all` polls every one of them. Concurrent
objectives are the designed model, not a stretch of it.

What makes the four `defender.mast` orders mutually exclusive is a **choice each of them
makes**, stated in its own comment - *"This objective assumes it has control of the
brain"* - and implemented by calling `brain_clear()` in `+++ enter` before composing a new
stack. That is a convention of those four labels, not a property of objectives.

So an order declares its posture, next to `valid_for`:

```
amd_verb: heads to
brain: exclusive        # clears and owns the stack (what all four do today)
```
```
amd_verb: holds formation
brain: layered          # brain_add's onto whatever is already there
```

This is the interesting half of the feature, and the reason the objective layer is worth
building on rather than around: complex behavior gets assembled from small named orders
that an author combines in one `Action:` block, instead of one bespoke brain label per
situation. The machinery is there and under-exercised.

**Open**: a layered order needs a declared priority. An objective's `+++ enter` builds a
brain stack whose *order* is its fallback chain (`ai_chase_current`, then `ai_chase_npc`,
then `goto`, then `ai_full_stop`). Two layered orders adding into one stack without a
declared priority is order-dependent, and list order in a fence should not be load-bearing
- the same reason `Action:` lines are simultaneous. Needs an answer before layering ships.

---

## 4. Verb binding

A verb is not invented in `sbs_utils`. An objective label **declares its own author-facing
phrase** with one new metadata key:

```
=== objective_goto_location
metadata: ```
display_name: Head to location
amd_verb: heads to
type: objective/orders/defender
objective_target: null
valid_for: any
```
```

Consequences:

- A mission adds a verb by writing an objective label. No core change, and `sbs_utils`
  stays domain-free (these labels are LM's, not the library's).
- `display_name` stays the *menu* word ("Head to location"); `amd_verb` is the *sentence*
  word ("heads to"). They are different registers and should not be forced to be one
  string.
- Parsing a line is: match the longest registered verb phrase, everything before it is the
  actor, everything after is the operand. Multi-word ship names work as long as the verb
  table is matched from the middle out.

Event verbs register in code, in the shape `dialogue_register_outcome` already uses
(`amd_dialogue.py:140`).

---

## 5. `Setting` - the slug line

A fact sheet for a place. Pure description, no execution semantics.

```
### [Kessel Approach](kessel_approach)
---
Setting
At: 6, 4
Skybox: sky-neb2-rvb
Music: Artemis2
Establish: kessel_station
---
A rust-colored belt. Ore haulers run silent here; the clans do not.
```

Notes:

- `Skybox:` and `Music:` are **already authored** in OU (`silver_reach.amd`,
  `default.amd`, `skirmish_arena.amd`) and StormsBeacon. They are simply undeclared, so no
  tool knows what they are. This is mostly a Phase 5 vocabulary declaration, not a new
  feature.
- **`Scene:` is taken** - a lifeform's dialogue scene (`amd_schema.py:285`, 13 live uses).
  The shot's grouping field was renamed to `Cutscene:` for exactly this reason, so do not
  reclaim it here. A `## Scenes` *section* may still map to the `setting` archetype via
  `_SECTION_ALIASES` - only the field name is blocked.
- **One archetype per section** (see 5.2). A setting living in a story section alongside
  beats needs its own `Setting` kind line, or its own section.
- **`Establish:` is a reference to a declared cutscene or rundown** - see 5.1. Not a new
  camera model.
- **No `Action:` on a Setting.** A beat has an unambiguous start; a place does not (map
  load? first arrival? every arrival?). Directions belong only on records with a
  lifecycle.

### 5.1 Cutscenes and rundowns already exist - connect, do not add

`amd_cutscene.py` is built, tested, linted against a real file, MAST-reachable and
documented (`mkdocs/docs/cosmos/cinematics.md`). A **shot is a record**, grouped by
`Cutscene:` into a cutscene or `Rundown:` into a set the director punches between, with
`Subject:` / `Lens:` / `Move:` / `Seconds:` / `Ease:` / `Overlay:` plus the overlay's own
fields inline. The **bed** is identified structurally - it is the record carrying neither
`Cutscene:` nor `Rundown:` - and needs no `Kind:` line. `cutscene_amd(key)` /
`rundown_amd(key)` play them.

Nothing here should re-model any of that. Two connections, both references:

- **`Establish:` on a Setting** is a `ref` to a declared cutscene or rundown key. My first
  draft wrote `Establish: kessel_station`, naming a landmark - that was wrong. Pointing a
  camera at a station *is* a one-shot cutscene, and the cutscene model already expresses it
  better than a second field ever would. As a ref it also lints and gets an LSP dropdown.
- **`plays <cutscene>` is an event verb** in an `Action:` block - how a beat triggers a
  cutscene. It binds to `cutscene_amd(key)`, and it is a one-shot, so it takes the event
  path (identity / `once`), not the objective path.

Deliberately NOT done: letting `Establish:` also name a bare subject as sugar. One field,
two meanings is the `Win:` mistake `AMD_PLAN.md` P2 already had to undo.

### 5.2 RESOLVED - and it taught this plan two things

The archetype-unreachability defect this section used to describe is **fixed** (commits
`2c4e55a`, `9929055`): `Scene:` -> `Cutscene:` on shots, the bed identified structurally
instead of by `Kind:`, the section words (`Cinematics` / `Cutscenes` / `Shots` /
`Rundowns`) registered, and the inline overlay fields declared. Nothing is owed here.

Two findings from that work change decisions below, and both cost the other session real
time to discover:

**A section resolves to ONE archetype.** `CUTSCENE` and `SHOT` could not stay separate -
beds and shots share a section, so splitting them left half of every cinematics file
untyped. This lands directly on the `Setting` archetype proposed above: settings sitting
in a story section alongside beats will not both type. Either give settings their own
section, or have each setting carry its own kind line - `amd_resolve_kind` checks the
record's own kind before the section name, so a per-record `Setting` line overrides. Worth
deciding rather than discovering.

**A function is not MAST-callable until it is registered in
`mast_sbs_procedural.py`.** `cutscene_cast` / `cutscene_amd` / `rundown_amd` existed, were
tested, and were invisible to every author, because importing a function in a mission's own
`.py` does not make it a MAST global. For a layer whose entire audience writes MAST, that
is the difference between shipped and not. Phase 3 must register every runtime entry point
it adds. It was found by writing a specimen that used it - which is also the strongest
argument for building a specimen mission alongside Phase 3 rather than after it.

### The ASCII sketch, inverted

An ASCII map as an *input* format is whitespace-significant, which `AMD_PLAN.md` rule 7
fences off from the narrative core, and it competes with the VS Code map view's draggable
`coord2` editor.

As an *output* it is close to free: the tooling already knows every landmark's `At:`, so
it can **render** the sketch into the Inspector, `sbs lint` output, and docs. Same benefit,
no new syntax, no parse ambiguity.

---

## 6. What the tooling gets

This is the actual argument for putting directions in AMD rather than MAST - none of it is
available today.

- **Misspelled actor** is a squiggle instead of a silent runtime no-op. The subject is a
  `ref`, so the LSP offers a dropdown of real keys.
- **Wrong order for the ship**: the prefab's `give_orders_type` says which family it
  accepts.
- **Wrong operand**: `valid_for: allies` rejects `protects <an enemy>`.
- **Two exclusive orders, one actor, one block**: the second would silently discard the
  first's brain stack (see 3.4). Layered orders stack and are fine.
- **Story Timeline** currently sees only what unlocks what. Action edges put the world's
  own moves on the beat chart.

---

## 7. New objectives worth adding

The existing four cover "go", "attack", "protect", "stop". Gaps a story author hits
immediately:

| Proposed | Phrase | Brain | Notes |
|---|---|---|---|
| `objective_follow` | `follows` | exclusive | Escort a *moving* target. `goto` does not re-acquire. |
| `objective_break_off` | `breaks off` | exclusive | The off switch for `attacks`. Every state verb needs one, and today there is no retreat. |
| `objective_dock_at` | `docks at` | exclusive | |
| `objective_patrol` | `patrols` | exclusive | A route, not a point. |
| `objective_hold_fire` | `holds fire` | layered | A posture, not a destination - the first real test of 3.4. |
| `objective_stay_near` | `stays near` | layered | A leash on top of whatever else the ship is doing. |

The last two matter more than their size suggests: they are the proof that layering works,
and they are the shape that lets an author build behavior by combining orders rather than
asking for a new bespoke one.

Event verbs (no objective - one-shot world changes on a different path):

| Phrase | What it does |
|---|---|
| `boards` | Set a lifeform's `Host:` - the field already exists (`amd_schema.py:282`) |
| `arrives` / `departs` | Spawn / despawn a landmark as a story beat |
| `hails` | Play a dialogue scene |
| `joins` | Change `Side:` |
| `plays` | Play a declared cutscene - `cutscene_amd(key)` (see 5.1) |

---

## 8. Open questions

1. **Runtime failure surface.** Lint catches a misspelled name; it cannot catch Ragnarok
   being dead, never spawned, or spawned after the beat. Default must not be "silently do
   nothing" - that is the failure mode the AMD tooling exists to end. Log, or fail the
   beat?
2. **Presentation verbs.** The most screenplay-ish lines have no field and no objective -
   *the lights flicker*, *an alarm sounds*. Out of scope here, but the answer should not be
   "bend the order vocabulary until it fits".
3. **`Action:` vs `Then:` is a third way to say "make something happen at a moment."**
   Defensible as one concept at three weights, but `AMD_PLAN.md` exists because dialects
   grew. Worth confirming the entry/exit split earns its keep.

---

## 8.5 The orders layer may be answering the wrong question

`NPC_MOTIVATION_PLAN.md` is the follow-on, and it changes the shape of what is left here.

Phases 5-7 bind `heads to` / `targets` to `objective_add` as **verbs an author types**. The
survey found zero corpus uses of either, and motivation supplies the reason: in a scripted
mission you write the outcome directly, and in a sandbox you want the NPC to decide. Nobody
writes "X heads to Y" because the interesting question was never the command - it was the
reason behind it.

So if the orders layer is built at all, it is most likely **the actuator a motive selector
drives**, not a vocabulary in an `Action:` block. Different design, different test. Marked
AT RISK below rather than deleted, because the migration in Phase 4 is what will say.

Nothing here threatens Phases 1-2, already shipped: `Action:` is the author's override, and
NPCs that decide for themselves make an override *more* necessary, not less.

---

## 9. Phases

Re-sequenced against the survey (1.5): the two verbs the corpus actually uses come first,
and the orders layer moves behind a decision point instead of leading.

| # | Phase | Touches |
|---|---|---|
| ~~0~~ | ~~Register the cinematic archetypes~~ - **done** by the cutscene work, see 5.2 | - |
| ~~1~~ | ~~`Action:` field: parse, list form, verb match, actor/operand refs~~ - **DONE** (`procedural/amd_action.py`, 35 tests) | sbs_utils |
| ~~2~~ | ~~the event-verb registry~~ - **DONE**. Ships `becomes` / `is no longer` / `joins` / `arrives` / `departs`; registered in `mast_sbs_procedural.py`; `arrives` is idempotent through the landmark key so no `once` flag is needed | sbs_utils |
| ~~3~~ | ~~Lint~~ - **DONE**. `amd_lint_actions` flags an unknown verb / missing actor / bad operand, sharing the runtime parser so the two cannot disagree. Actor existence deliberately NOT checked - roles are minted in MAST and shipData, and guessing would flag correct files | sbs_utils |
| 4 | Migrate the corpus sites (1.5); record what stays unsayable. **RE-ESTIMATE - see 9.1** | LM, OU, SB |
| - | **DECISION POINT** - not "did we need orders?" but **"did we need orders, or did we need MOTIVES?"** See `NPC_MOTIVATION_PLAN.md` s6. Answer this before starting 5-7 | - |
| 5 | AT RISK - `amd_verb` metadata key; order-label discovery by `type: objective/orders/*`; bind to `objective_add` | sbs_utils, LM |
| 6 | AT RISK - `brain: exclusive \| layered` (3.4); `valid_for` / `give_orders_type` lint | sbs_utils, sbs_cli |
| 7 | AT RISK - new objective labels (section 7) | LM |
| 8 | ~~`Setting` archetype~~ - **DROPPED, see 9.2.** The fields are already authored on `map` and `region` records, and the real problem is kind resolution, not vocabulary | - |
| 9 | Timeline action edges; Inspector widgets | sbs_cli, editors/vscode |
| ~~10~~ | ~~Docs~~ - **DONE**. `Action:` documented in `build/amd-format.md` beside the quest vocabulary (not a new page - it is a quest field, and the format doc is where an author already looks) | mkdocs |

Verification per phase: unit tests, `sbs lint` across LM + OU + StormsBeacon, a headless
`--test` run, then a browser pass where a GUI surface is involved.

---

## 9.1 What starting Phase 4 actually found

Three things, from reading `peacetime.mast:878 kidnapper_discovered` - the site picked as
the *easiest* migration.

**1. Actor resolution needs no new convention.** The worry was that these sites hold their
actor in a MAST variable. They do - but it is derived FROM a role:
`kidnapper_id = to_list(role("kidnapper"))[0]`. The role is already the identity, so
`kidnapper becomes a pirate` resolves with nothing added. (One semantic difference worth
knowing: the MAST takes `[0]`, a single member; `becomes` acts on ALL members. Identical
here because there is exactly one kidnapper, and the set form is the better default.)

**2. A real bug in shipped code.** LM changes side with `side_set_object_side`, which sets
`side_display` as well as `side` and routes an unknown key through a warning gate. The
first `joins` implementation assigned `.side` directly, so a converted ship would have kept
showing the display name of the faction it just left, and a typo'd side would have stuck
silently. Fixed, with a test. **This is the argument for migrating early**: 39 unit tests
did not find it; one real site did, immediately.

**3. Phase 4 is not mechanical, and that is the big one.** These sites are not AMD records.
`kidnapper_discovered` is a MAST label that a science-scan handler reaches through
`task_schedule`. To carry an `Action:` block it must first BECOME a beat record with a
trigger - which is mission surgery on shipped content, not a conversion. So the phase is
better read as *"pick two sites worth restructuring"* than *"convert 25 sites"*, and its
cost is much closer to authoring than to refactoring.

That also weakens what Phase 4 can prove. It will say whether `Action:` expresses the
directions well, but a small hand-picked sample cannot say much about demand for orders.
Section 1.5.1 is the better evidence on that question, and the motivation survey
(`NPC_MOTIVATION_PLAN.md` s7) is better still.


---

## 9.2 Phase 8 is dropped, and what killed it is worth more

`Setting` was to be a new archetype carrying `Skybox:` / `Music:` / `Establish:`. Checking
where those are actually written killed it, and turned up something larger.

**They are already authored, on existing archetypes.** `Skybox:` and `Music:` sit on **map**
records in OU (`default.amd`, `silver_reach.amd`, `skirmish_arena.amd`) and on a **region**
record in Storm's Beacon. A new archetype would help neither - and since a section resolves
to ONE archetype, those records cannot be settings as well as what they already are.
`Establish:` is speculative vocabulary nobody writes. Adding it would repeat the mistake
1.5 was written to stop.

**The larger finding.** Ranking every `unknown-field` warning across LM + OU + Storm's
Beacon gives 336 warnings over 88 distinct (field, archetype) pairs - and the top of the
list is not obscure vocabulary, it is *core declared fields flagged against the wrong
archetype*: `Done when` (19), `Values` (18), `State` (16), `Reward` (14), `Speaker` (12),
`Center`/`Radius` (7 each) - all "not a known **map** field".

The cause is one line. `silver_reach.amd` opens with a kind line on the ROOT record:

```
# [The Silver Reach](the_silver_reach)
---
Universe
---
```

`Universe` maps to `map`, and **kind inherits downward**, so every record in the file
becomes a `map` - overriding `## Sides`, `## Regions`, `## Jobs`, `## Narrative`. Verified
directly: with the root kind line a region record resolves `map`; without it, `region`.

**And it is not only lint noise - it changes parsed VALUES.** `node.kind` drives
`amd_read_field` coercion, so in `silver_reach.amd` today:

```
Center: 5, -4     ->  '5, -4'   (str)     because the record typed as `map`
Center: 5, -4     ->  [5, -4]   (list)    when it types as `region`
```

Inheriting a kind DOWN is right for `## Characters` over its records. It is wrong for a
document ROOT, whose kind line names the FILE rather than its contents. The likely fix is
that resolution should take the NEAREST of (ancestor kind, ancestor section name) rather
than letting any ancestor kind beat every section name.

**Not fixed here, deliberately.** It is core kind resolution, another session has been
working in that exact table, and because it changes coercion it can change runtime values
in OU - possibly fixing them, possibly breaking code written against the current strings.
That wants its own change with OU exercised, not a drive-by at the end of an unrelated
phase. It is the highest-value AMD work now visible.
