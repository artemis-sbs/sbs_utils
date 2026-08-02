# NPC motivation - why an NPC does the thing it does

> **VERDICT (2026-08-02): do not build the goal selector.** The survey in section 8 found
> zero NPC decision-making in Open Universe to subsume, and no two NPCs anywhere that want
> the same thing. It is a pattern with two instances, not a system. Sections 1-7 are the
> reasoning that led there and are kept because the survey only overturns the CONCLUSION -
> the observations still hold, and 8.1 is the smaller real gap it uncovered.

Follow-on to `AMD_ACTION_PLAN.md`. **Pre-survey when written: no phases, deliberately** -
the action plan taught that designing phases before counting demand produces a vocabulary
aimed at the wrong verbs. This document did not repeat that mistake, and section 8 is why.

---

## 1. The gap

| Layer | Question it answers | Exists |
|---|---|---|
| Brain | *how* do I do this | yes - behavior tree, fixed-priority fallback |
| Objective | *which* thing am I doing | yes - owns and swaps the brain |
| **Motivation** | **which thing SHOULD I be doing, and why** | **missing** |
| `Action:` | the author overriding all of it for a beat | built |

Today an NPC's priorities are a fixed order: `brain_add(ai_chase_current)`, then
`ai_chase_npc`, then `goto`, then `ai_full_stop`. First branch that succeeds wins. Nothing
weighs whether chasing is worth more *to this character* than escorting, right now.

The missing thing is not a behavior. It is a **reason**, held as data, that picks between
behaviors - and that can be read back out to say why.

---

## 2. The evidence: Storm's Beacon says it in one file

Three characters, three different jobs for the same layer. All three already exist and all
three currently hand-wire what a motive would decide.

### 2.1 XORN vs the Second Wind - who shows up

`StormsBeacon/story.mast` runs two structurally identical countdown watchers:

| | XORN | Second Wind |
|---|---|---|
| watcher | `xorn_pursuit_watch` | `bounty_hunter_watch` |
| fuse | 45s (15s at the source) | 30s |
| bails on | cell dead, beacon lit | cell dead, beacon lit, **bribed** |
| one-at-a-time | `role("xorn")` | `role("bounty_hunter_ship")` |
| hull | `skaraan_executor` | `skaraan_enforcer` |

Everything that differs is tuning plus a reason - and **the reasons live only in
comments**: the hunters are "on Madame Skarr's contract", XORN is "a different debt". The
fiction knows why each one chases you; the data does not.

What a motive adds beyond deduplication: the two pursuers currently do not know about each
other. With motives as data, who arrives is a **contest** - XORN wanting the Beacon more
than the hunters want paying means it displaces them rather than merely arriving later.
And bribing the hunters stops being a suppress flag and becomes **outbidding Skarr**,
which is what the fiction already says is happening.

### 2.2 Crazy Eddy - what is on offer, and whose side he takes

Half of this is already built. Every purchase runs `earns crazy_eddy generous 3`, and
`if generous > 15` unlocks the Regulars Only branch at lower prices. So standing already
flows **in** through the dialogue outcome grammar, per captain, persisted across episodes.
Nothing reads it **out** except that one hardcoded threshold.

Eddy also has a want the data does not know: *"Never could unload the thing - too heavy,
too weird, hums when you look at it wrong."* He wants the Cradle gone. Today it is item
five at a flat 500cr. A motivated Eddy pushes it - raises it unprompted, drops the price
the longer it sits, mentions it every visit until someone takes it. Same data; the want
does the work instead of a static menu.

And he has no stake in the plot, which is the more interesting hole. Skarr wants the
Beacon, XORN wants the Beacon, the hunters want paying, Eddy wants credits - so what
happens when Skarr offers him credits for the player's bearing? That is the same
who-wants-it-more contest as 2.1, resolved socially instead of with an enforcer hull. The
mechanic generalises; only the actuator changes.

### 2.3 Madame Skarr - one NPC's motive creating another's

Skarr **hires** the hunters. That is delegation, already in the fiction, on two NPCs
instead of twenty ships - which makes it the cheapest possible test of the hierarchy
question in section 5. If the model works for Skarr commissioning the Second Wind, it
works for a fleet tasking its ships.

---

## 3. What already exists (most of the substrate)

1. **Quests are agent-generic.** `quest_add(agents, quest_id, ...)` takes agents, not
   players. "Quests for NPCs" is nearly free at the data layer; what is missing is the
   selector (which one matters now) and the actuator (turn the winner into an objective).
2. **The weighting vocabulary is authored, in words.** The `reputation` trait declares
   `Values: by-the-book 40, fearsome 30`, and `ARCHETYPE_TRAITS` grants it to **sides and
   lifeforms automatically** - two of the three entity types this would cover. The missing
   half is on the goal side: what this goal *serves*.
3. **Standing already moves.** `earns <who> <pole> <n>` is a registered dialogue outcome
   in production use (2.2). The input side of a motivation loop is built.
4. **Objectives are the actuator.** They own and swap brains, an agent carries several at
   once, and `objective_add` accepts a list. A selector's output is an `objective_add`.
5. **Legibility is half-built.** Every objective's `+++ test` computes a `desc` -
   *"currently heading to X"*, *"Looking for trouble at Y"*. Motivation extends that to
   *why*, which is what makes the system visible rather than mysterious. Invisible AI is
   wasted AI, and this is the direct answer to "it could drive what they communicate".

---

## 3.5 The player is already a source of motive - this half is the mature one

Three separate mechanisms already let a player change what an NPC wants, all in
production, and they were being read as unrelated features:

| Channel | Where | What it moves |
|---|---|---|
| **Direct orders** | `friendly_give_orders.mast` reads a ship's `give_orders_type` and builds a comms menu from `objective/orders/*` labels | the NPC's current objective, chosen by the player |
| **Payment** | Storm's Beacon - pay Skarr 300cr, `hunters_bribed` suppresses the Second Wind | whether a motive applies at all |
| **Standing** | Eddy's `earns crazy_eddy generous 3`, per captain, persisted | disposition, which gates what is offered |

`enemy_surrender.mast` even *sets* `give_orders_type` on a beaten enemy, so defeating a
ship changes which motives it can be given. The INPUT side of a motivation loop is built
several times over. The selector remains the only missing piece.

**A player order is therefore not a special case - it is one more motive competing with the
NPC's own.** Today `objective_add` calls `brain_clear`, so a player order overrides
absolutely and the NPC has no opinion. As a weighted motive it becomes a contest, which is
where the interesting behaviour lives: a loyal escort obeys at once; a mercenary obeys if
the pay beats what it is already doing; a defector refuses; a ship under fire defers until
it is not.

**This dissolves `AMD_ACTION_PLAN.md` s3.4.** The `brain: exclusive | layered` flag was a
mechanical proxy for "who wins when two things want the brain". Motives answer that with a
reason instead of a posture, so exclusivity stops being something an author declares and
becomes simply *this motive won*. Good evidence that the flag was a workaround for this
layer's absence.

**The landmine: a refusable player order reads as a bug.** Tell an escort to defend, watch
it not defend, and nobody thinks "interesting characterisation". Two rules follow -
a refusal must always SPEAK (the objective `desc` seam, 3.5 of section 3), and ships on the
player's own side default to obedient. Refusal is reserved for characters whose
independence IS the point: mercenaries, defectors, rivals, Skarr.

---

## 4. Three constraints, all learned from the examples

1. **The author keeps the dial.** Storm's Beacon's fuses are tuned drama, not emergence -
   the comment spells out the intended curve (*scan and go before 30s = clean; linger =
   hunters; linger past 45s = hunters AND XORN*). A system that turned that into a
   simulation would destroy the thing that makes it work. Motivation must reproduce the
   escalation **by declaration**, with `Patience:` staying a number the author sets. What
   the layer adds is *why* and *who wins*, never *when*.
2. **The author keeps the words.** Eddy's value is the writing. Motivation
   **selects among authored scenes and never synthesises one**.
3. **No magic numbers.** Utility AI usually dies as a table of tuning constants nobody can
   reason about, and emergent behaviour becomes emergent bugs. Naming the axes (`Values:`,
   `Wants:`) instead of scoring raw is the only version that passes the read-aloud test -
   and the axes already exist (3.2).

Together: **motivation decides WHICH authored thing happens, and never invents one.**

---

## 5. The question that sets the size

**Does a fleet decide and its ships comply, or does everyone decide and the fleet is
emergent?** That single choice is the difference between a medium feature and a very large
one. Skarr and the Second Wind (2.3) are the cheapest place to answer it.

---

## 6. What this changes about `AMD_ACTION_PLAN.md`

**It does not touch Phases 1-2 (built).** `Action:` is the author override, and autonomy
makes an override *more* necessary, not less - an NPC that decides for itself is one the
story needs a way to interrupt.

**It puts the deferred orders layer (that plan's Phases 5-7) at risk of being pointless.**
Those phases bind `heads to` / `targets` to `objective_add` as verbs an author writes. The
survey found zero corpus uses, and motivation explains *why*: in a scripted mission you
write the outcome directly, and in a sandbox you want the NPC to decide. Nobody writes
"X heads to Y" because the interesting question was never the command - it was the reason.

So the orders layer, if it is built at all, is **the actuator a selector drives**, not a
vocabulary authors type. That is a different design with a different test, and it should
not be started before section 7 is answered.

---

## 7. Phase 0 - the survey, before any design

Measured against OU, not LM: LM is scripted, so it would answer the wrong question (the
same trap that made the action survey's first pass useless).

1. **How many OU NPCs have hand-written behaviour a selector would subsume?** Count the
   watcher/ticker tasks whose whole job is "decide what this NPC does next".
2. **How many already branch on standing / reputation?** Eddy's `if generous > 15` is one;
   the count says whether reading standing back out is a real pattern or a one-off.
3. **How many distinct motives are actually in play** across OU + Storm's Beacon? If it is
   four, a fixed vocabulary beats a scoring system.
4. **Do any two NPCs ever want the same thing?** If not, there is no contest to resolve and
   this collapses to per-NPC scripting, which is what exists.
5. **How often does the PLAYER already change an NPC's motive** (orders given, bribes paid,
   standing gates crossed)? Section 3.5 says this is the mature half - the count says
   whether a player order should be modelled as a competing motive or stay the absolute
   override it is today.

Question 4 decides whether this is a system or a pattern. Question 5 decides whether the
first thing built is the selector or just a weight on the orders that already exist - and
the second is a far smaller starting point that would still deliver a refusal that speaks.

---

## 8. SURVEY RESULT (2026-08-02) - do not build the selector

Run against OU and Storm's Beacon. It contradicts this plan's premise.

| # | Question | Answer |
|---|---|---|
| 1 | OU NPC behaviour a selector would subsume | **zero** |
| 2 | Branches on standing | **heavy** - a whole consequence API |
| 5 | Player already moves a motive | **29 sites** |
| 4 | Do two NPCs ever want the same thing | **no** |

**Q1 is zero because OU has no NPC decision-making at all.** Not one `brain_add`,
`objective_add` or `brain_clear` in the whole mission. OU spawns LM **prefabs**
(`prefab_fleet_raider`, `prefab_npc_defender`) and the brains come with them. Its world is
**procedurally generated per system from persisted state** - `random.seed(key + N)`, then
spawn according to who owns the sector and whether it is captured / cleared / destroyed.
The model is *state -> generation*, not *agents -> decisions*. There is nothing to subsume.

**Q4 follows: no two NPCs want the same thing, because OU's NPCs do not want anything.**
What competes in OU is SIDES over territory, and that is already modelled - ownership
flags, `universe_capture_watch`, `universe_recapture_watch`. The contest the selector was
going to resolve is already resolved somewhere else.

So the goal-selector is a **pattern with two instances** (XORN and the Second Wind), not a
system. OU - predicted to supply the volume - supplies none. **Do not build it.** Storm's
Beacon's two pursuers are correctly written as two small tasks.

### 8.1 What the survey found instead, and it is worth having

OU carries 113 standing references and a rich consequence API: `reputation_reward_mult`,
`reputation_ransom_cost`, `reputation_offer_tier`, `reputation_ceasefire_cost`,
`reputation_foe_deal_standing`.

So the earlier claim that "nothing reads standing back out except one hardcoded threshold"
was true of Storm's Beacon and **wrong about OU**, where reading it out is a mature,
many-fingered pattern. But every finger lands in the same place:

> **Standing changes what things COST. It never changes what anyone DOES.**

A side you have wronged charges more for a ceasefire, ransoms your people dearer, and
offers you worse tiers - and raids you exactly as often as before. That is the actual gap,
it is one sentence, and it is far smaller than a selector.

It also lands on **sides, not ships** - which is precisely where `Values:` is already
auto-granted by `ARCHETYPE_TRAITS`, and where OU's competition already lives.

That is the candidate feature if anything here gets built: *let the standing that already
drives prices also drive behaviour, at the side level.* It needs its own demand evidence
before design - the lesson this document was written to respect. What it does NOT need is
a per-NPC goal selector.
