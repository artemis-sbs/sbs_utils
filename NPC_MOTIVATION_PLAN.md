# NPC motivation - why an NPC does the thing it does

Follow-on to `AMD_ACTION_PLAN.md`, and the reason that plan's deferred orders layer
should not be built as designed. **Pre-survey: no phases yet, deliberately.** The action
plan taught that designing phases before counting demand produces a vocabulary aimed at
the wrong verbs; this one does not repeat it.

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

Question 4 is the one that decides whether this is a system or a pattern.
