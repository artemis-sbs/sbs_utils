# Urges - what an actor wants, said out loud, with something at stake

Follow-on to `AMD_ACTION_PLAN.md` and `NPC_MOTIVATION_PLAN.md`. Where `Action:` is the
author overriding a beat, an **urge** is an actor with an unfinished want that keeps
speaking about it - and a consequence if nobody answers.

The short version: **quests already own stakes and deadlines but have no voice; urges are
the voice.** Almost everything below is binding two built systems together.

---

## 1. The gap

| Layer | Question it answers | Exists |
|---|---|---|
| Brain | *how* do I do this | yes - behavior tree, fixed-priority fallback |
| Objective | *which* thing am I doing | yes - owns and swaps the brain |
| Quest | what is at stake, and by when | yes - triggers, `Fails when: after`, `Penalty:` |
| **Urge** | **what do I keep asking for, and what happens if nobody comes** | **missing** |
| `Action:` | the author overriding all of it for a beat | built |

A quest counts down in silence. A player learns the ambassador gave up by noticing the
fare vanished from the board. Nothing in the mission ever says *"this is the last time I
ask."*

---

## 2. What the corpus says - and what it cannot see

A census of every speech call site in LegendaryMissions, OpenUniverse and Storm's Beacon
(209 direct sites: `comms_message`, `comms_broadcast`, `comms_receive`/`_internal`,
`comms_transmit`/`_internal`, `comms_info_card`, `gui_info_panel_send_message`,
`announce`), each attributed to its enclosing label or `def` and classified by what
reaches it:

| Trigger | Sites | Share |
|---|---|---|
| Prompted - player hailed, clicked, scanned or bought | ~122 | 58% |
| Scripted plot beat - author wrote the moment, no decision | 38 | 18% |
| Unprompted - a clock or an event decided | ~36 | 17% |
| Dev tooling / autoplay | 13 | 6% |

Then by **who speaks** in that unprompted 36:

| Speaker | Sites |
|---|---|
| Dispatch / faction ops / narrator (`"TSN Command"`, `"Sensors flag an unregistered trawler"`) | ~18 |
| UI notification (`"You claimed X"`, `"Production complete"`) | ~11 |
| Grid lifeform - damcons, which already have brains | 3 |
| **Named cast character** | **4** |

Two of those four are the same character (Florbin) duplicated across two copies of one
mission. Every character line in the event bucket is a **reply**: eleven are Crazy Eddy
reacting to a purchase, one is Skarr reacting to a bribe. No character in three missions
initiates anything.

**Read narrowly, that says do not build this.** It is the same shape as
`NPC_MOTIVATION_PLAN.md` s8 - a pattern with two instances.

**The survey cannot see forward demand, and that is its limit.** Nobody authors content
for a mechanism that does not exist. Three intended uses were named that the corpus
cannot contain: a diplomat waiting at a station, hint traffic, and bar rumors with
weight. The census is kept because it is still the best available evidence about *shape*
- and it changed the design twice (s2.1, s2.2). It is not kept as a verdict.

### 2.1 What the census changed: the clock beats the event

The first design was event-first, with a slow tick for a rare few. The measured ratio is
the reverse - clock-driven unprompted speech outnumbers event-driven roughly 2.5:1. The
ticker is the primary path, not the fallback.

### 2.2 What the census changed: this is not a lifeform feature

The dominant unprompted speaker is a dispatcher, not a person. Combined with stations
being an explicit target, the record type is **any agent**, not `lifeform`. See s7.

---

## 3. What already exists (the reason this is small)

1. **Quests are agent-generic.** `quest_add(agents, quest_id, ...)` takes agents. A
   station holding a quest is already legal at the data layer.
2. **Quests already have deadlines and consequences.** `Fails when: after 20m` ->
   `quest_tick_fail_after` -> `quest_mark_failed`; `Penalty:` -> `quest_grant_penalty`;
   `Then:`, `Reveals:` -> `quest_reveal`. Triggers cover destroy / collect / scan / dock
   / reach / signal / all-dead.
3. **Line pools are built.** `amd_chatter` treats a heading BODY as a random pool with
   `{field}` interpolation - no fence, so colons and prose are safe.
4. **Stage directions are built.** `amd_action` has the verb registry, actor resolution
   and the never-fail-silently logging.
5. **Actor resolution is built and already covers stations.** `amd_action_actors(name)`
   resolves a declared landmark key, then a role, to live agent ids.
6. **Reputation is built.** `reputation_apply(agent_id, {faction: {pole: delta}})`.
7. **The rolling-slice ticker pattern is built and hardened.** `objective.py` s20-45,
   including the reset-latch lesson in `objective_reset`.

---

## 4. The format

An `Urge` is a record under any actor. Its BODY is the line pool.

```
# [Deliver Ambassador Vell](deliver_vell)
---
Quest
Starts when: accepted
Fails when: after 20m
Penalty: 200 credits, earns tsn diplomatic -15
---

## [Vell grows impatient](vell_waiting)
---
Urge
Actor: Ambassador Vell
Whenever: quest deliver_vell active
Every: 4m
Escalates: with deadline
---
% Ambassador Vell is on the docking ring at DS1, when convenient.
%% Vell again. My transport window is closing, captain.
%%% This is the last time I ask.
```

| Field | Meaning |
|---|---|
| `Actor:` | who speaks - resolved by `amd_action_actors` (landmark key, then role) |
| `Whenever:` | the recurring condition. True = eligible |
| `Every:` | minimum gap between firings of THIS urge |
| `Until:` | retire permanently when true (optional) |
| `Weight:` | which of THIS actor's urges wins when several are eligible |
| `Escalates:` | `with deadline` \| `yes` \| absent |
| `Action:` | optional stage directions, existing `amd_action` grammar |

**The urge declares no stakes of its own.** It reads the quest's clock and speaks; the
quest fails and pays out. One deadline, one consequence, one place to tune - and deleting
the urge costs the drama but not the mechanics, which is the correct dependency
direction.

### 4.1 Escalation comes from the deadline

`Escalates: with deadline` derives the stage from the fraction of the bound quest's time
remaining. `%` / `%%` / `%%%` are stages 1/2/3, sticking at the last.

No second clock, nothing to keep in sync, and the author still holds the dial by setting
`Fails when:`. This respects `NPC_MOTIVATION_PLAN.md` s4.1 - the escalation curve stays a
number the author writes, and the count of `%` IS the curve.

`Escalates: yes` (no bound quest) advances one stage per firing.

### 4.2 A station is the same record with a different holder

```
# [DS1 runs dry](ds1_resupply)
---
Quest
Held by: ds1
Fails when: after 30m
Penalty: 500 credits
Then: DS1 goes dark
---

## [DS1 calls for resupply](ds1_calling)
---
Urge
Actor: DS1
Whenever: quest ds1_resupply active
Every: 5m
Escalates: with deadline
---
% DS1 requests a resupply run when someone has the tonnage.
%% DS1 is below reserve. We need that shipment.
%%% DS1 going to minimal power. Nobody is coming, are they.
```

`quest_grant_penalty` reads `getattr(holder, "side", None)`, and a station has one - so a
station-held penalty debits the station's side. **Player-held quests punish the player;
world-held quests punish the world.** Same mechanism, and the holder decides who pays.

**A world-held quest carries no reputation line** (s7.1). `reputation_adjust(agent_id,
faction, ...)` means *this agent's standing with that faction*, so a rep penalty on a
station-held quest would move DS1's own standing with TSN - not a stake any player can
perceive. World consequences are expressed with `Then:` / `Action:` verbs instead, which
is what "DS1 goes dark" is for.

---

## 5. The runtime

**One interval task, a `RollingSlicer` over `has_inventory("__URGES__")`**, sized so a
full pass takes `URGE_PASS_SECONDS` (30 - these are minute-scale wants). Structure copied
from `objective.py`.

**Not a per-actor loop**, though that is what both existing instances do
(`fb_pest_messages`, `bar_banter`). Two reasons:

1. **The speech budget cannot live in a per-actor loop.** What decides whether this is
   pleasant or unbearable is a floor across ALL actors. A per-actor loop cannot see that
   without shared state, and with shared state the loop has no advantage left.
2. **Forever-loop tasks are a known scar.** The pause/agent-leak work went 34.9k tasks ->
   98. N actors x a never-ending task is that shape again, and unlike a brain there is no
   `object_exists` guard to unschedule it.

### 5.1 Selection - per actor, per pass

1. Retire urges whose `Until:` is true. Permanent, stamped done.
2. Skip urges still inside `Every:`.
3. Evaluate `Whenever:`; keep the true ones.
4. Highest `Weight:` wins; ties break random.
5. Ask the budget. **If refused, do not stamp the cooldown** - retry next pass.
6. Speak, run `Action:`, stamp.

Fixed-priority with cooldowns. No scoring, no accumulators, no tuning constants - the
failure mode `NPC_MOTIVATION_PLAN.md` s4.3 named. `Weight:` only ever arbitrates one
actor's own urges, never two actors, so this does not become the cross-agent contest that
survey rejected. **That boundary is the plan's stop line** (s9).

### 5.2 The budget is the feature

| Gate | Default | Why |
|---|---|---|
| Per-urge `Every:` | authored | this specific thing should not repeat |
| Per-actor floor | ~45s | one actor should not monologue across their own urges |
| Global floor | ~20s | five actors should not pile up after a jump |

One escape: `Weight: 90+` bypasses the global floor. An actor leaving forever outranks
politeness; an actor grumbling does not.

The global floor reads `announce` traffic too, not only urges - otherwise actors talk over
mission dispatch, which is the actual perceived annoyance.

### 5.3 Cost

Per actor per pass: evaluate K conditions, K ~ 2-3, each a small `eval`. 40 actors ~ 4
evals/sec. Brains at 65 ships are ~85 **MAST task spawns** per second (`start_task` +
`tick_in_context` per node per pass). Two orders of magnitude cheaper, and cheaper per
unit as well as less frequent.

### 5.4 Lifecycle

- Host deleted -> transfer to unhosted or stop, mirroring `lifeform_transfer`'s
  `ultra_beam` path.
- `Until:` satisfied -> retire permanently, not merely cool down.
- All urges retired -> drop `__URGES__` so the slicer stops visiting.
- `register_reset_state("urges", probe)` - or run 2 of a soak plays silent, exactly the
  `objective_reset` failure.

### 5.5 Server-only

The ticker is server-side and every send goes to a scoped console set once. A per-console
urge evaluation gives five consoles five ambassadors. `SIGNAL_ROUTING.md` rules apply
throughout - this is unambiguously the "spawns, rewards, applies a modifier, counts"
category.

---

## 6. Where the voice goes

The one part with no precedent to copy, because a waiting actor is not aboard.

| Actor state | Surface |
|---|---|
| Hosted on a player ship | `comms_receive_internal` from the actor (exactly Florbin) |
| Hosted elsewhere, player in range | `comms_message` host -> that ship's consoles |
| Unhosted | galaxy-wide, OU's TSNN pattern |

Reach falls out of hosting rather than needing its own field. Scoped to
`linked_to(ship, "consoles")`, never `role("__player__")` broadly. Surface preference is
the house rule: `comms_message` > info card > text waterfall.

---

## 7. The three gaps that make stakes work

**7.1 Quest consequences cannot touch reputation.** `quest_grant_penalty` handles credits
and items only. `reputation_apply` already exists and takes the right shape. Spelling
reuses the dialogue outcome grammar already in production (`earns ashfang selfish +5`)
rather than inventing a third spelling for the same idea.

**Restricted to player-held and SHARED-held quests** (RESOLVED 2026-08-04). The rep
functions mean "this agent's standing with that faction", so the line only reads correctly
when the holder is someone whose standing a player cares about. `sbs lint` rejects a rep
line on a world-held quest and names the alternative (`Then:` / `Action:`).

**7.1a `amd_reward` silently drops what it does not understand.** Found while scoping
phase 1. The whole parser is "find the first digit token":

```python
def amd_reward(value):
    """'300 credits' -> {credits: 300}."""
    for t in str(value).split():
        if t.isdigit():
            return {"credits": int(t)}
    return {"credits": 0}
```

So `Pays: 300 credits, 2 torpedoes` yields credits only, with no warning - and `items` is
supported by `quest_grant_reward` but the parser can never produce it. Phase 1 rewrites
this function anyway; it fixes the silent drop, adds `items`, and warns on unparsed
tokens, per the `amd_action` never-fail-silently rule.

**7.2 Non-player-held quests never tick.** Four tickers - `quest_tick_fail_after`,
`quest_tick_complete_after`, `quest_tick_reach` and the proximity pass (quest_driver.py
lines 613 / 632 / 653 / 688) - all iterate:

```python
for aid in [Agent.SHARED_ID] + [s.id for s in to_object_list(role("__player__"))]:
```

Grant a quest to DS1 and its deadline never fires. **This blocks s4.2 entirely.**

**The bound is free** (RESOLVED 2026-08-04). Quest trees live in the `__quests__`
inventory key (`quest.py` `quest_folder`), so `has_inventory("__quests__")` already IS the
quest-holding agent set - the same class-level registry `brains_run_all` uses for
`__BRAIN__`. Self-limiting, no new registry, established pattern. Snapshot to a list
before iterating: `brain.py` s396-400 paid for that lesson ("Set changed size during
iteration"). If the holder set ever grows large, apply the same `RollingSlicer`.

**7.3 No voice.** s4-6.

---

## 8. Questions - all resolved before build (2026-08-04)

1. **How wide do the quest tickers go?** RESOLVED - `has_inventory("__quests__")`, which
   already is exactly the holder set. See s7.2.
2. **Does a failing urge speak its own last line, or does the quest?** RESOLVED - **the
   urge does**, via `Weight: 90` + `Whenever: quest X failed`. Keeping every word an actor
   says in one record is worth the goodbye landing up to one tick late.
3. **`Whenever:` grammar.** RESOLVED - **fixed vocabulary plus a registry**, matching
   `amd_action_register`. Checkable by lint, extensible without touching the module. A bare
   expression was rejected: powerful, but untypeable by the linter.
4. **Whose reputation moves on a world-held quest?** RESOLVED - **nobody's**; rep lines are
   player/SHARED-held only. See s7.1. "Blame the bystanders" (rep landing on players who
   could have helped) was considered and deferred - it needs an audience rule that is real
   design work, and world state is already a stake.
5. **Does the dispatch voice belong here?** OPEN, and deliberately out of scope. ~29
   hand-rolled `comms_info_card(all_roles("console, comms"), ...)` sites is the largest
   measured cluster and the "hint messages" use case. It is a mission-state decision
   wearing a character's voice - arguably an urge on `Agent.SHARED`, arguably its own
   thing. Revisit once the actor case is real.

---

## 9. What is deliberately not built

- **No brain for actors.** A behavior tree re-decides continuously because the world moved;
  an urge's world changes on events and clocks. Grid lifeforms keep their brains - they
  have position and paths and are correctly a BT.
- **No goal selector across actors.** `NPC_MOTIVATION_PLAN.md` s8 stands. If two actors
  ever contest the same want, stop and re-read that survey rather than adding a tiebreak.
- **No motive/values scoring.** `Weight:` is a fixed integer the author writes.
- **No synthesized words.** Urges select among authored lines and never invent one.

---

## 10. Phases

Each phase ships something usable alone.

| # | Phase | Contents |
|---|---|---|
| 1 | **Reputation in consequences** DONE 2026-08-04 | Rewrite `amd_reward`: `earns <faction> <pole> <n>` tokens, `items`, and a warning on anything unparsed (s7.1a). `reputation_apply` bound into `quest_grant_reward`/`_penalty`, player/SHARED-held only. Independently useful, no urge needed. See s10.1. |
| 2 | **Widen the quest tickers** | `Held by:` + iterate `has_inventory("__quests__")`, snapshot to a list (s7.2). Unblocks station stakes. Test: a station-held quest fails on its deadline. |
| 3 | **Urge parse + ticker** | `Urge` record, `__URGES__`, `RollingSlicer`, selection (s5.1), reset registration. Speech via the s6 table. No escalation yet. |
| 4 | **The budget** | Three floors + the `Weight: 90` escape + `announce` awareness. Not optional - phase 3 without it is the annoying version. |
| 5 | **Escalation** | `Escalates: with deadline` reading the bound quest's remaining fraction; `%`/`%%`/`%%%` staging. |
| 6 | **Author the diplomat** | OU passenger offers grow a waiting-actor urge. The real test: reach, escalation, `Until:`, `Action:` in one character. |
| 7 | **Migrate Florbin** | `fb_pest_messages` becomes declarative. Proves the format covers the one shipped instance. |
| 8 | **Lint + schema** | `amd_schema` typed fields, `sbs lint` checks: unknown `Whenever:` verb, urge bound to a nonexistent quest, urge with no pool, `Every:` shorter than the global floor. |

Phases 1 and 2 are independently useful and unblock everything else - start there.

**Not in any phase:** bar rumor `Reveals:` (a separate, smaller change to the casino that
does not need urges) and the dispatch voice (s8.5).

## 10.1 What building Phase 1 actually found

**A brace leak waiting in the quest log.** `_quest_reward_text` rendered the reward dict
generically:

```python
return ", ".join(f"{v} {k}" for k, v in reward.items() if v)
```

Fine while the shape was only `{"credits": n}`. The moment `items` and `reputation`
existed it would have produced `300 credits, {'torpedoes': 2} items` - and a display
string containing `{` is a runtime `SyntaxError: f-string: expecting '}'` as soon as MAST
assigns it, reported against the AUTHOR's line rather than this function (MAST_CLAUDE:
"a helper that formats text for display must not emit braces").

It now renders the three kinds explicitly - `120 credits, 2 torpedoes, +10 honest with
tsn` - and skips any unrecognized nested value rather than turning it into a crash. Other
scalar keys still render the old way, so a mission-specific key is not silently dropped.

**The lesson generalizes to the rest of this plan.** Every phase here widens a data shape
that something downstream already stringifies. Phase 3 onward should check the display
path in the same breath as the parse path - the unit tests all passed with the brace bug
in place, because nothing asserted on the rendered text.

**Verification:** 2393 unit tests OK; headless `--test 20 --map 0 --seed 7
--use-working-tree` PASS on both LegendaryMissions and OpenUniverse.

---

## 11. Decisions locked

1. Urges attach to **any agent**, not lifeforms.
2. **Stakes are quests.** Urges never carry their own consequences.
3. **One shared ticker**, never a task per actor.
4. `Weight:` is **intra-actor only**. Cross-actor contest is the stop line.
5. Escalation is derived from the deadline, not a second clock.
6. Server-only, scoped sends, `//shared/signal` discipline.
7. Quest tickers iterate `has_inventory("__quests__")` - no new registry.
8. Reputation consequences are **player/SHARED-held only**; world stakes are world state.
9. `Whenever:` is a fixed vocabulary plus a registry, never a bare expression.
10. A character's last line belongs to the character, not to the quest's `Then:`.
