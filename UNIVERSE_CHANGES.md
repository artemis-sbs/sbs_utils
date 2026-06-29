# Open Universe - Expansion Plan

A plan to grow the Open Universe from "procedural sectors with cargo/mystery
quests" into a living galaxy of **clans, diplomacy, reputation, capturable
stations, and author-written narratives**. This document organizes the raw idea
list into epics so we can agree on scope and order **before any code changes**.

Status: **planning only.** Each epic states the goal, a proposed approach
(speculation where asked), what it depends on, and the **open decisions** to
resolve first. Nothing here is built yet.

---

## Decided so far (round 1)

These set the plan's direction; details still being refined.

1. **Lead epic = Foundations (I UNIVERSE AMD + C clans).** Build the authoring
   backbone and clans-as-sides first; the interaction epics (D/F/G) build on it.
2. **Distributed play = someday.** Keep the **single shared live system** model
   for now; H stays a future spike. Size streaming (A2) and system richness (B)
   for one live system.
3. **Rename "sector" -> "system"** galaxy-wide (clean pass over labels + helper
   names). A galaxy is a grid of **systems**.
4. **Reputation is per-captain (client)**, so it follows the player across ship
   changes; persisted by client identity.

### Decided (round 2 - Phase 1 shape)

5. **Split AMD:** separate **clans.amd** (factions/data) and **narrative.amd**
   (lore/arcs); a universe = one clans file + one narrative file.
6. **6 clans at launch** (the Epic C starter table), mixed foe/neutral.
7. **Clan->system = home systems + archetype foes:** clans have **named home
   systems pinned in AMD** (stable landmarks) AND appear in keyed foe systems
   chosen by archetype/danger.
8. **Start-screen "Universe" dropdown:** pick a universe (clans + narrative) at
   game start, like the map/seed options; selecting one swaps the whole roster.

### Decided (round 3 - reputation & diplomacy)

9. **6-clan default split (proposal): 2 foe + 4 neutral** (foes = Ashfang Raiders,
   Hollow Choir), with home systems on the existing POI landmarks. See Epic C.
10. **Comms reputation = gates + optional weight** (`%{axis>N}` eligibility, plus
    optional `w:axis` bias among eligible lines).
11. **Per-captain truce overlay:** reputation can override side-wide hostility
    (hold fire / allow docking). This is the one combat-touching effect.
12. **Reputation changes = both** declarative `rep:` blocks (auto-applied like
    quest `reward`) and an imperative `reputation_adjust(...)` helper.

### Decided (round 4 - capture, systems, standby)

13. **Capture hold = presence timer:** clear clan ships within radius R for N
    seconds (no scripted waves); shields stay down while contested.
14. **Re-capture = yes (defendable frontier):** clans can assault captured docks
    back; ownership flips both ways and persists.
15. **System composition = hybrid:** kind/clan sets a template; a keyed POI deck
    fills extra detail; named homes (AMD) can override with hand-placed POIs.
16. **Standby = POI-activation:** POIs stay in standby until a player nears.
    (Spike: confirm pausing AI/stations - not just terrain - resumes cleanly.)

### Decided (round 5 - narrative, chatter, clan quests)

17. **Narrative = reveal-chain arcs:** story arcs are SHARED multi-step quest
    chains authored in `narrative.amd`, reusing `reveal` + the trigger vocab.
18. **Ambient chatter fires on all four triggers:** system arrival, near a POI,
    periodic/idle (cooldown), and on reputation/diplomacy change.
19. **Discovery = flavor only:** chatter never auto-reveals/marks the map; the map
    still reveals by visiting (fog of war preserved).
20. **Clan quests = archetype pools + reputation weighting:** clans offer quests
    from an archetype pool, weighted by the captain's reputation (the `%` idiom),
    not hard gates.

---

## Phase 1 design (Foundations) - agreed shape

Concrete target for the first build (details in the open list still apply):

- **Files:** `clans.amd` + `narrative.amd` (loaded like the existing AMD docs via
  `document_get_amd_file` + data sections). A start-screen **Universe** dropdown
  selects which pair to load.
- **Clan record (per heading in clans.amd):** name, color, archetype, default
  diplomacy (foe/neutral), **home system(s)** `[i,j]`, reputation leanings (the 7
  axes), comms flavor. Example:
  ```
  # [Iron Concord](iron)
  ---
  color: "#39f"
  archetype: military
  diplomacy: neutral        # or foe
  homes: [[6, 4]]
  leans: { by_the_book: 40, fearsome: 30, honest: 20 }
  ---
  Disciplined and territorial; respects strength and straight dealing.
  ```
  (Data fence is a line of only dashes - `---` - not `--- yaml ---`.)
- **System ownership:** named home systems (from AMD) are pinned landmarks on the
  galaxy map; other "foe"/clan systems pick an owning clan **deterministically
  from the seed**, filtered by the clan's archetype/diplomacy - so what the map
  shows still matches what spawns.
- **Clans are sides:** each authored clan becomes a side (`prefab_side_generic`)
  with its color/relations, reusing all existing side/role machinery.
- **Rename pass:** sector -> system happens here (low-risk cleanup alongside).

---

## How to read this

- **Epics** are the major workstreams. They're ordered roughly by dependency,
  not priority.
- **[spec]** marks a proposal/speculation that needs your sign-off.
- **[decide]** marks an open question that changes the design.
- The original 17 notes are preserved and mapped to epics in the table below, so
  nothing is lost.

### Idea -> epic map

| Original note | Epic |
|---|---|
| 1 Nebula density too high | A. Tuning & Streaming |
| 2 Standby list for off-screen content | A. Tuning & Streaming / H. Scaling |
| 3 Players in different parts of the universe | H. Distributed Play & Scaling |
| 4 Bigger systems, multiple stations/POIs | B. Richer Systems |
| 5 Foe groups/clans in foe systems | C. Clans & Factions |
| 6 Clans as sides with diplomatic relations | C. Clans / D. Diplomacy |
| 7 Foe/clan systems have space docks | B. Richer Systems / E. Capture |
| 8 Space-dock capture behavior (drop shields, hold, morph) | E. Capture Mechanic |
| 9 Neutral clans | C. Clans & Factions |
| 10 Comms chatter to aid discovery | G. Discovery & Ambient Comms |
| 11 Change/negotiate diplomatic relations | D. Diplomacy & Negotiation |
| 12 Reputation system (distinct from diplomacy) | F. Reputation |
| 13 Reputation spectrums (7 axes) | F. Reputation |
| 14 Reputation affects comms/rewards/quests + authoring | F. Reputation / G. Comms |
| 15 Suggest 4-8 clans + author method (AMD) | C. Clans / I. UNIVERSE AMD |
| 16 UNIVERSE AMD for narratives | I. UNIVERSE AMD |
| 17 UNIVERSE AMD as a menu option | I. UNIVERSE AMD |

---

## Guiding principles (carry over from the current universe)

1. **Deterministic + delta save.** Content is a pure function of
   `(universe_seed, i, j)`; only player-made changes are stored. New procedural
   content needs no save migration; only new *stored deltas* do (see the
   versioned save + migration ladder already in place).
2. **Author-driven.** Clans, narratives, and reputation effects should be
   describable in data (a **UNIVERSE AMD**), not hard-coded, the way quests and
   items already are.
3. **Server-authoritative.** All state (diplomacy, reputation, capture, credits)
   lives on the server; consoles only display/act.
4. **Backward compatible.** New systems are additive; existing universe saves and
   missions keep working.
5. **Reuse what exists.** Sides, the quest driver + trigger vocab, the item/
   economy system, comms `%` random lines, and AMD parsing are the building
   blocks - prefer extending them over new mechanisms.

> Terminology (DECIDED): a galaxy-map cell is a **"system"**, not a "sector" -
> avoiding the collision with Artemis's "sector" = the whole battlefield. A clean
> rename pass over labels + helpers (`universe_sector_*` -> `universe_system_*`,
> "Sector (i, j)" -> "System (i, j)"). The galaxy is a grid of **systems**.
> (Naming-only; behavior unchanged.)

---

## Epic A - Tuning & Streaming (quick wins + perf base)

**Goal:** make current systems look right and lay the performance groundwork the
bigger epics will lean on.

- **A1. Nebula density (note 1).** Pull nebula generation back ~50% at current
  system sizes. Small, isolated tuning change to the keyed-field chances.
- **A2. Off-screen streaming via standby (note 2).** When parts of a (larger)
  system aren't on screen, move them to the engine **standby list** to cut
  active-object cost; bring them back when relevant. Use a **dedicated role**
  (e.g. `universe_standby`) distinct from the hangar's `standby` role to avoid
  cross-system confusion.
  - **Trigger (DECIDED): POI-activation.** Each POI/sub-area stays in standby
    until a player nears it (then activates); re-standby when they leave. Scales
    best for bigger multi-POI systems (Epic B).
  - **RESOLVED (spike):** standby removes objects from the sim (AI/physics stop)
    and works on NPCs - already used by hangar/cag; resume re-classifies. Safe for
    NPC POIs; track parked ones with a `universe_standby` role. See Spike findings.

**Depends on:** nothing (A1) / understanding of the standby API (A2).
**Enables:** B (bigger systems) and H (more simultaneous content).

---

## Epic B - Richer Systems (notes 4, 7)

**Goal:** systems are more than one station + a field - they can hold **multiple
stations, POIs, and space docks**, with variety by system kind/clan.

- Multiple stations/POIs per system, deterministically placed from the system
  key (so revisits are stable), with delta-stored changes.
- Clan/foe systems include **space docks** (the capture targets of Epic E).
- POI variety: derelicts, anomalies, civilian outposts, clan holdings.

**Composition (DECIDED: hybrid kind-template + deck).** A system's **kind/clan**
sets a **template** (e.g. clan-foe = space dock + garrison + field; station = a
base; home = safe hub), then a weighted **POI deck** fills extra detail, **keyed
per system** so it's reproducible. Named home systems (Epic I) are pinned via AMD
and can carry hand-placed POIs that override the template. Reuses the tile-map /
deck pattern (HereThereBeMonsters/theta_quadrant).
**[decide]** The template recipes per kind + the deck contents/weights (content
tuning, settle while authoring).

**Depends on:** A2 (streaming) for object budget; C (clans) for clan holdings.

---

## Epic C - Clans & Factions (notes 5, 6, 9, 15)

**Goal:** populate the galaxy with **clans** - foe and neutral groups - each a
**side** with its own identity, holdings, and relationships.

- Clans are **sides** (`prefab_side_generic`), so existing side relations,
  colors, and role/query machinery apply (note 6).
- Mix of **foe** and **neutral** clans (notes 5, 9); diplomacy (Epic D) lets the
  player shift these.
- **DECIDED: 6 clans at launch**, each with **named home system(s)** pinned in
  `clans.amd` plus appearance in keyed foe systems by archetype.
- **Starter clans [spec]** (the agreed 6; foe/neutral split + homes below are a
  proposal - edit freely. Homes reuse the existing POI landmark coords):
  | Clan | Archetype | Default | Home | Leans (reputation axes) |
  |---|---|---|---|---|
  | Iron Concord | disciplined military | neutral | (6, 4) | By-the-Book, Fearsome, Honest |
  | Verdant Pact | peaceful traders | neutral | (-5, 3) | Peaceful, Generous, Kind |
  | Free Holders | independent settlers | neutral | (-7, -7) | Resourceful, Honest, Kind |
  | Mercury Guild | mercenary brokers | neutral | (5, -3) | Resourceful, Selfish, Fearsome |
  | Ashfang Raiders | opportunist pirates | foe | (8, -5) | Violent, Cruel, Cowardly |
  | Hollow Choir | secretive cult | foe | (-4, 6) | Intellectual, Liar, Selfish |
  - Proposed split: **2 foe + 4 neutral** - a galaxy that's mostly negotiable with
    two clear threats; diplomacy/reputation can shift any of them.
  - **[decide]** Confirm the split + homes, or adjust (e.g. make Iron Concord a
    foe for more early pressure).
- **Clan quest pools (DONE).** Each clan has a `quest_pool` of job types by
  **archetype** (clans.amd: Ashfang raid/smuggle/bounty; Verdant
  supply/escort/survey). Generic jobs are authored once per type in
  **clan_quests.amd** (key = type; data carries tier + on_* trigger + base
  reward); any clan offers the jobs in its pool. A clan station's comms surfaces
  them gated + reward-scaled by the captain's **standing**
  (`universe_reputation.clan_standing`: rep aligned to the clan's leans):
  tier 1 always, tier 2 at >=20, tier 3 at >=50; reward x1.0..2.0; **foe clans
  offer nothing until standing >=20** ("only the dangerous bargain with them").
  Accepting grants the job with the scaled reward + a rep block that earns
  standing with the offering clan on completion. Files:
  `universe_clan_quests.py` (offers/grant), `clan_quests.amd`, the
  `//comms ... station` route + `universe_accept_clan_job` in universe.mast.
  Authoring stays open: a clan may later carry bespoke quests; generic is the
  baseline.
- **Authoring:** clans are described in the **UNIVERSE AMD** (Epic I) - name,
  color, archetype, default diplomacy, home systems, reputation leanings.

**Depends on:** I (UNIVERSE AMD) for authoring; underpins D, E, F, G.

---

## Epic D - Diplomacy & Negotiation (notes 6, 11)

**Goal:** diplomatic relationships between sides/clans are **dynamic** - they can
change in play and be **negotiated**.

**Comms negotiation DONE.** A clan station's comms offers diplomacy shifts gated
by the captain's standing (`universe_reputation`): **Negotiate Ceasefire**
(HOSTILE -> NEUTRAL) costs a tribute that scales down with standing
(`clan_ceasefire_cost`: 600 cr at standing 0, free at >=30) - this breaks the
catch-22 of needing a truce to earn a foe clan's respect; **Propose Alliance**
(NEUTRAL -> ALLIED) needs standing >=60. Changes call `side_set_relations` and
persist via `universe_set_dip` + `universe_save_diplomacy`. Live relation read
with `side_get_relations`. (`universe.mast` station comms route.) Still open:
action-driven nudges (note: clan quest completion already warms standing, which
lowers ceasefire cost) and the per-captain truce overlay below.

- Persist per-pair relations (HOSTILE/NEUTRAL/ALLIED) in the universe save,
  overriding the clan's authored default.
- **Negotiation methods [spec]:**
  - **Comms-driven:** clan comms offer ceasefire / trade pact / alliance;
    acceptance is gated by reputation (Epic F) + an **offer** (credits/items/
    favors) + difficulty.
  - **Action-driven:** helping a clan (clearing its enemies, completing its
    quests) nudges relations warmer; attacking them nudges colder.
  - Each successful negotiation calls `side_set_relations` and saves the delta.
- **DECIDED: per-captain truce overlay.** Side-wide diplomacy still sets the
  baseline, but a high enough **per-captain reputation** can override it - a clan
  at war with your side may **hold fire / allow docking** for a captain in good
  standing.
  - **Implementation note (spike RESOLVED):** aggression is decided in the LM AI
    **brains** (`npc_brains.mast`/`defender.mast`: `shoot = side_are_enemies(...)`),
    so the truce is a brain-layer override - `is_hostile(agent, target)` =
    `side_are_enemies(...) and not captain_truce(...)` - **no engine change**. See
    Spike findings.
  - **Cross-addon design (do this carefully):** those brains are used by EVERY
    combat mission (siege, etc.), so `captain_truce()` must be globally defined
    even when the universe/reputation addon isn't loaded - otherwise the brain
    call NameErrors elsewhere. Plan: ship a **safe default** `captain_truce(agent,
    target) -> False` in an always-loaded place (e.g. the ai or quests addon, or
    a tiny core helper), which the universe **overrides** with the real
    reputation-based check. Truce rule (v1, tunable): a captain is at truce with a
    clan when `reputation_standing(captain_ship, clan) >= TRUCE_THRESHOLD`, where
    standing = sum (or clan-leaned weighting) of the captain's axes with that
    clan. Wire `is_hostile` into both brains' shoot AND target-selection gates.

**Depends on:** C (clans/sides), F (reputation influences odds), G (comms).

---

## Epic E - Capture Mechanic: Space Docks (notes 7, 8)

**Goal:** clan **space docks** can be **captured**: drop shields, **hold** the
area for a period, then the structure **morphs** to the capturing side.

- **Phased behavior (DECIDED):**
  1. **Assault** - bring the dock's shields down.
  2. **Hold = presence timer** - keep the area clear of clan ships within radius R
     for N seconds (no scripted reinforcement waves; the system's existing
     defenders are the contest). Shields don't recover while contested.
  3. **Capture** - on hold complete, morph the dock: reassign side + roles to the
     capturing side, switch behavior to friendly (docking/repair/market), persist
     the capture in the system delta.
- **Re-capture (DECIDED): yes, defendable.** A clan can later assault a captured
  dock back - a dynamic frontier. Ownership flips both ways and persists.
- Implement as a new **behavior** (like `behav_station`) plus a quest-driver
  objective so capture/loss can grant rewards/reputation and be tracked.
- **[decide]** Tuning only: hold seconds N, clear-radius R, and how/when a clan
  mounts a counter-assault (on revisit? on a timer? difficulty-scaled?).

**Depends on:** B (docks exist in systems), C (clan ownership), and the quest/
behavior systems.

---

## Epic F - Reputation (notes 12, 13, 14)

**Goal:** a per-captain **reputation** with each clan, **distinct from
diplomacy** - diplomacy is "are our sides at war?"; reputation is "what do they
think of you?" (DECIDED: reputation attaches to the **captain/client**, so it
follows the player across ship changes.)

- **Model [spec]:** for each `(captain/client, clan)`, a vector over **7 axes**,
  each a spectrum scored roughly -100..+100:
  - Liar <-> Honest
  - Cowardly <-> Fearsome
  - Violent <-> Peaceful
  - Selfish <-> Generous
  - Cruel <-> Kind
  - By-the-Book <-> Resourceful
  - Foolish <-> Intellectual
- Actions adjust axes (e.g. honoring a deal -> Honest; fleeing -> Cowardly;
  sparing a surrendered enemy -> Kind). Stored **per captain (client id)** in the
  universe save. (Persisting by client identity is a small addition to the save -
  today players persist by ship name; we add a captain-keyed reputation map.)
- **Effects (note 14):** reputation biases **comms outcomes, rewards, and which
  quests a clan offers**.
- **Reading rep in comms (DECIDED: gates + optional weight).** A line is eligible
  only if its gate passes; among eligible lines an optional weight biases the
  random pick. Extends today's `%` idiom (which already picks randomly):
  ```
  << [clan]
     %{honest>40} "Your word is good here. The job's yours."   # gate
     %{kind>0} w:kind "We could use someone decent."           # gate + weight
     %{honest<-40} "We don't deal with liars."
     % "State your business."                                  # fallback
  ```
  Plus a read helper for `if`/rewards/quest gates, e.g. `rep(clan, "kind") > 30`.
- **Changing rep (DECIDED: both).** Declarative rep blocks for the common case
  (auto-applied, like quest `reward`), plus a helper for bespoke logic (like
  quest `label:`):
  ```
  # declarative (on quest complete / comms choice):
  reward: { credits: 200 }
  rep: { iron: { honest: +10, fearsome: +5 } }

  # imperative (anywhere a route fires):
  reputation_adjust(clan, "kind", +5)
  ```
  - **[decide]** Final field/helper names (`rep` block key, `reputation_adjust`)
    and the exact gate/weight token spelling (`%{axis>N}` / `w:axis`).

**Depends on:** C (clans). **Feeds:** D (negotiation odds), G (comms), quests.

---

## Epic G - Discovery & Ambient Comms (notes 10, 14)

**Goal:** the galaxy **talks** - ambient comms chatter helps players discover
POIs, clans, quests, and react to their reputation.

- **Triggers (DECIDED: all four):** on **system arrival**, **near a POI**,
  **periodic/idle** (cooldown), and **on reputation/diplomacy change**. Lines are
  colored/selected by reputation (Epic F gates+weight).
- **Discovery = flavor only (DECIDED):** chatter is atmosphere/hints in text; it
  does **not** auto-reveal or mark systems - the galaxy map still reveals by
  visiting (current fog of war). Keeps exploration earned.
- Reuse the `%` line system + the Epic F gates so chatter reflects standing.
- **[decide]** Tuning only: delivery (broadcast vs targeted) and the idle
  cooldown / per-trigger rate limit to avoid spam.

**Delivery surface (DONE): info panel, NOT the text waterfall.** Chatter used to
go through `comms_broadcast` (the **text waterfall** - ephemeral, no speaker, no
history, no interaction). It now uses the **info panel**
(`gui_info_panel_send_message`) via `universe_chatter_card` (clan voice:
name+color+optional face/icon) and `universe_info_card` (non-clan ambient:
sensors/news), modeled on the **HereThereBeMonsters** `here_*_info_message`
helpers: a message *card* with the clan's name + color, kept in **history**,
auto-dismissed; an optional **button** (future) can suspend for a response. An
ambient line now reads as a *hail from that clan*, not a log blip. Pure mechanical
status (capture, +credits, job accepted) stays on the waterfall.

**Promoted to sbs_utils (DONE).** The HTBM "incoming comms card" pattern is now a
reusable library helper: **`comms_info_card(...)` / `comms_info_clear(...)`** in
`sbs_utils/procedural/comms.py` (thin wrappers over `gui_info_panel_send_message`
with title/color/face/icon/banner/button/history/auto-dismiss; `comms_info_card`
returns an awaitable Promise when a `button` is given). The universe
`universe_chatter_card` / `universe_info_card` now call it. **[follow-up]** refactor
HereThereBeMonsters' `here_*_info_message` helpers to call the core helper too, so
the pattern lives in one place.

This makes chatter the **light end of the same "voice" spectrum** as the dialogue
capstone above: ambient one-liner (info card, face+color, auto-dismiss) ->
hail-with-a-button (info card + response) -> full branching dialogue *scene*
(authored AMD). Same authored personality, three intensities. Reuse `%` variants
+ the Epic F gates throughout; keep it declarative.

**Depends on:** C, F. **Light-weight; can land early for "feel".**

---

## Epic H - Distributed Play & Scaling (notes 2, 3)  -  DEFERRED (someday)

**Status (DECIDED): someday.** We keep the **single shared live system** model
(H-opt-1) for now. This epic stays a future spike; A2 (standby) is still pursued,
but only for **in-system** culling, sized for one live system. The options below
are kept for when we revisit.

**Goal (future):** speculate on supporting **player ships in different parts of
the universe at once**, and the **player-count / map-size tradeoffs**.

- **The core constraint [spec]:** the engine simulates **one coordinate space**.
  "Different parts of the universe" must map onto that. Options:
  - **H-opt-1: Single live system, shared.** (Today.) Everyone is in the current
    system. Simple; players travel together. No real "different parts".
  - **H-opt-2: Spatial partitioning in one sim.** Place each player/group's
    current system at a large coordinate **offset** in the one space, and use
    **standby (Epic A2)** to keep distant systems cheap. Players in different
    systems literally can't see each other (far apart) until they jump together.
    - Tradeoffs: object budget scales with (#active systems x content);
      more players spread out -> more must stay live -> heavier. Map size and
      per-system richness (Epic B) trade directly against how many systems can be
      simultaneously active.
  - **H-opt-3: Group-based "live" switching.** Only the group(s) needing
    simulation are live; others are frozen/standby until they act.
- **[decide - deferred]** Which model (H-opt-2 vs H-opt-3) if/when we pursue it,
  and a target max players + "active object" budget. Not needed now.

**Depends on:** A2 (streaming) is the enabling primitive. This is the **biggest,
riskiest** epic - deferred; revisit with a focused spike before committing.

---

## Epic I - UNIVERSE AMD (notes 15, 16, 17)

**Goal:** a **UNIVERSE AMD** document that authors use to describe a universe -
its **clans** and its **narrative** - selectable from the menu. This is the
authoring backbone for C/D/F and beyond.

- **Describe clans (note 15):** name, color, archetype, default diplomacy, home
  systems, reputation leanings, starting comms flavor - one AMD heading per clan
  with a `--- yaml ---` data section (the parser already supports data sections).
- **Describe narrative (note 16) - DECIDED: reveal-chain arcs.** Story arcs are
  **multi-step quest chains** authored in `narrative.amd` (like the bridge story),
  scoped **SHARED** (game-wide), using `reveal` + the existing trigger vocab to
  span systems. Arcs ARE quests - reuses the whole driver/tab/giver stack.
- **Menu option (note 17):** pick a UNIVERSE AMD at game start (like map/seed
  options), so different "universes" (clan rosters + story) are swappable.
- **[spec]** Reuses the existing AMD pipeline (`document_get_amd_file` +
  data sections + `document_flatten`) and the quest/giver patterns from Q3/Q4.
- **DECIDED:** **split files** - `clans.amd` + `narrative.amd`; a **start-screen
  dropdown** picks a universe (a clans+narrative pair). The AMD **pins named home
  systems**; the deterministic **seed fills the rest** (keyed clan/foe systems by
  archetype), so the map still matches what spawns.

**Depends on:** AMD data-section parsing (done). **Underpins:** C, D, F, narrative.

### To explore: a unified universe document + author-facing tuning

**Observation (design feel).** Taken together the mechanics read as a
**living-frontier sandbox**: Elite Dangerous bones (seeded endless galaxy,
jump-to-system, fog-of-war discovery, station markets, a mission-board loop), EVE
politics (a contestable frontier you can capture/lose, negotiated diplomacy,
mercenary work), and - most distinctively - **Mount & Blade reputation**, where
standing is a *character* meter (honest/liar, violent/peaceful, ...) and clans
relate to *you* by how well your conduct matches their leanings. The Star Trek
bridge/scan/derelict layer is the skin, not the bones. North-star: **"the galaxy
reacts to who you are,"** not "follow the scripted hero." Authoring should make
that knob-turnable - a peaceful trade-republic galaxy vs. a brutal pirate warzone
should be a *content* edit, not a code edit.

**The gap.** A universe's configuration is currently **scattered across four
places**: `clans.amd` (factions), `universes.mast` (registry wiring),
**Python** (all the tuning), and the `@map/universe` start-screen metadata
(runtime options). So *playing* a universe is data-driven, but *authoring a new
one* is still partly a code task - which cuts against the AMD philosophy used
everywhere else. Concretely, these are hardcoded / not author-exposed today:

- **Reputation & diplomacy tuning** (in `universe_reputation.py` /
  `universe_clan_quests.py`): tier thresholds (>=20/>=50), reward-multiplier
  curve, ceasefire-cost formula, per-job rep deltas. No way to author "the
  pirates forgive quickly but the cult never forgets."
- **The reputation axes themselves** (`REP_POLES` is a code constant) - can't add
  a "pious/heretical" axis for a religious universe.
- **The shape of space**: system-kind distribution, POI-deck weights (loot %,
  derelict %, outpost %, mine %), clan-territory density, galaxy bounds/size,
  encounter cadence / fleet sizes - all in the generator/deck, keyed only off
  Difficulty.
- **Per-clan bespoke quests** and **hand-placed named systems/POIs** beyond clan
  homes: "open but not wired."
- **Narrative**: a file is referenced but not yet a load-bearing content source;
  there is no framework for universe-level **goals / win-lose** (it's a pure
  sandbox, so a *campaign* universe has nothing to hang on).
- **Per-region flavor**: skybox/music are global, not per-clan or per-kind.
- **Dialogue is code-bound.** The *only* author-spoken content in AMD today is a
  clan's flat `chatter` one-liners; every real conversation (comms menus, taunts,
  surrenders, quest hand-offs) is MAST-coded in `comms/*.mast` via
  `<<`/`>>`/`%`/`+`, and quest "speech" is one-off `comms_broadcast` strings. A
  writer can't author a *scene* without scripting.

**The idea (capstone).** Promote the universe itself to a **first-class authored
document** - a single `universe.amd` (or a much richer registry entry) that
describes a world holistically, instead of just pointing at a clans file:

- **Identity:** name, description, skybox/music theme.
- **Factions:** inline, or a pointer to `clans.amd`.
- **Generation knobs:** kind weights, POI-deck weights, clan density, bounds/size,
  encounter cadence.
- **Reputation rules:** which axes are in play, tier thresholds, per-clan
  forgiveness/grudge curves.
- **Narrative & goals:** optional arc hooks, milestones, win/lose conditions.
- **Dialogue & voice:** authored comms *scenes* (below), so a clan's personality
  is written, not coded.

**Sub-idea: a movie-script dialogue flavor of AMD.** The MAST comms primitives
(`<<` NPC line, `>>` player line, `%` random variant, `+` branching choice, `=$`
color style) are already a screenplay vocabulary - just written in code. A
*dialogue flavor* of AMD would be a friendlier wrapper that **compiles down to
those primitives**, separating *what characters say* (content, AMD) from *how
comms routes fire* (logic, MAST). A heading = a scene; lines are speaker-tagged;
choices branch with simple guards and carry outcomes (jump to a scene, shift
reputation, emit a signal).

**Syntax rule (DECIDED): markdown-shaped, and confirm before adding.** Any new AMD
syntax must be *suggested and confirmed*, never just added, and should follow
markdown-like rules reusing what AMD already has - `# [Display](key)` headings,
`[label](target)` links, `(key?a=b)` query params, `---` data fences. So choices
become a **markdown list of links** to the next scene, with guards/outcomes as
link query params (or a per-scene data fence) - not novel `>`/`->` operators.
Sketch (shape only, to be confirmed):

```
# [Ashfang Hail](scene_ashfang_hail)
---
speaker: ashfang          # resolves face / name / color from the clan
when: //comms
---
% You're a long way from friends, captain.
% Brave or stupid, flying in here.

- [Apologize](scene_back_off)
- [Threaten them](scene_standoff?if=standing>=20)
- [Offer a cut](scene_deal?if=credits>=200)
```

(The `%` random-line marker is the one non-markdown idiom carried over from MAST
comms; whether to keep it or find a markdown-shaped form is itself a [confirm].)

Wins: writers write (personality becomes content, like leanings already are);
**reuse via archetype + `{name}`** (one "pirate hail" serves every pirate clan);
it rides existing rails (compiles to comms primitives; choices reuse the
rep/diplomacy/signal hooks; localization- and test-friendly); and it **unifies
the spoken layer** - chatter, taunts, surrenders, and quest hand-offs become one
authorable "voice" instead of a data list plus a pile of routes.

**Design guardrail (DECIDED): writer's room, not engine room.** This flavor exists
to add *color that leads to richer comms interactions* - a science-fiction
writer's narrative / movie script - and must **never grow into a scripting
language.** Allowed: speakers, lines, `%` random variants, a few branching choices
with *simple* guards, and light outcomes (jump to a scene, nudge reputation, emit
a signal). Not allowed: loops, variables, expressions beyond simple guards, or any
procedural logic - that stays in MAST, and the dialogue AMD compiles down to the
existing comms primitives. If a request starts adding control flow or computed
logic to dialogue, steer it back to declarative. (Keep me honest on this.)

Right now the *clans* are authorable but the *universe* is not; making the
universe a single authored document is the missing capstone and would close most
of the gaps above at once. **[explore]** how much to inline vs. keep as split
files (clans/narrative/dialogue), and which tuning is worth exposing first
(reputation curves + generation weights are the highest-leverage; the dialogue
flavor is the highest-*delight* for content authors).

---

## Persistence additions (all additive to the universe save)

New state each epic stores. All are **new keys read with `.get(default)`**, so per
the save-format & migration design they are **additive - no version bump** unless
we restructure an existing key. Keys anchor on stable ids (side/clan key, client
id, `"i,j"` system, quest id) - the same migration anchors the save already uses.

- **Clans:** authored (from `clans.amd`), not saved. Only **deltas** save:
  - **Diplomacy deltas** - per side/clan pair, overriding authored defaults.
  - **Ownership/capture** - clan or captured-dock owner per system (system delta).
- **Reputation:** per-captain (client) -> clan axis map.
- **Narrative/arcs:** progress already persists via the quest layer (SHARED arcs
  use the existing `shared_quests`; per-ship quests by name).
- **Universe selection:** which `clans.amd` / `narrative.amd` pair was chosen, so
  **Continue** reloads the same universe.

Galaxy-map display: clan **home/owned** systems show the clan's color/marker
(reuse the existing map-cell coloring); discovery stays fog-of-war (round 5).

---

## Spike findings (read-only investigation)

Results of reading the code (no changes). All three open spikes are lower-risk
than feared.

### 1. Standby (Epic A2) - LOW RISK, confirmed
- **API:** `sbs.push_to_standby_list[_id]`, `sbs.retrieve_from_standby_list[_id]`,
  `sbs.in_standby_list[_id]`.
- **Semantics:** push removes the object from the sim entirely (`space_objects` +
  the active/terrain id sets) so its **AI/physics stop ticking**; retrieve
  restores it and **re-classifies** (NPC/station -> active, else terrain) via
  `_abits & 0x30`. Works for **any** object type, not just terrain.
- **Already proven on NPCs:** `hangar.py` and `fleets/npc_cag.py` park craft via
  `push_to_standby_list`. So NPC standby is used in practice today.
- **Caveat:** while parked, the object isn't in `sim.space_objects` (in-space
  queries/physics won't see it); the py-side Agent/roles/links persist (separate
  store), so quest/role state survives. Retrieve before code needs it "in space."
  Track parked POIs with a dedicated role (e.g. `universe_standby`), distinct from
  the hangar's `standby` role (note 2).
- **Verdict:** POI-activation standby is feasible for terrain AND NPC POIs.

### 2. Per-captain truce (Epic D) - MODERATE, no engine change needed
- NPC aggression is decided in the **LegendaryMissions AI brains**, e.g.
  `npc_brains.mast`: `shoot = side_are_enemies(BRAIN_AGENT_ID, current_target) or
  force_shoot`; `prefabs/defender.mast` similar. Target selection lives there too.
- So a personal truce = a **brain-layer override**: replace the raw
  `side_are_enemies(...)` gate with `is_hostile(agent, target)` =
  `side_are_enemies(...) and not captain_truce(agent, target)`, where
  `captain_truce` checks the target captain's reputation with the agent's clan.
- Touches the **brain MAST** (`ai/npc_brains.mast`, `prefabs/defender.mast`) + a
  reputation helper - **not engine combat code**. Scope is contained.
- **Caveat:** only governs brain-driven NPCs (the standard path); clan fleets use
  these brains (via `prefab_fleet_raider`), so they're covered.
- **Verdict:** feasible at the brain layer; spike narrowed to "edit the brains'
  shoot/target gate + add `captain_truce()`."

### 3. Clans-as-sides + universe discovery (Epic C/I) - LOW RISK, confirmed
- **Sides:** `prefab_side_generic` + `side_set_relations(a, b, relation)` +
  `side_are_enemies` all exist and are used throughout. Each clan = one
  `prefab_side_generic` (color/desc), relations set from authored `diplomacy`.
- **Dropdown discovery:** reuse the **label-registry** pattern (items use
  `labels_get_type("item/")`, maps use `@map`). Add a discoverable
  `@universe/key "Display"` label per universe naming its `clans.amd`/
  `narrative.amd`; the dropdown lists `labels_get_type("universe/")`. Consistent,
  no new mechanism. (Alternative: fs-scan a folder - but the label registry
  matches existing conventions.)
- **Verdict:** no blockers; the Appendix A helper shapes hold.

---

## Suggested dependency order (a build path)

```
LEAD -> I UNIVERSE AMD  ->  C clans  ->  D diplomacy
                                     ->  F reputation -> G comms chatter
A1 nebula tuning           (independent, trivial; fold into Phase 1)
B  richer systems     ->  E capture mechanic
A2 standby streaming       (in-system culling only; supports B)
H  distributed play        (DEFERRED - someday)
```

Phasing (lead = Foundations):

1. **Foundations (LEAD):** I UNIVERSE AMD (clan + narrative schema); C clans-as-
   sides authored via AMD; + A1 nebula tuning + the sector->system rename as
   low-risk cleanups done alongside.
2. **Interactions:** F reputation (per-captain) + `%`-style authoring; D
   diplomacy/negotiation; G ambient comms.
3. **World:** B richer systems (multi-station/POI) + A2 in-system standby; E
   space-dock capture.
4. **Deferred:** H distributed play (revisit via spike if it becomes a goal).

---

## Decisions still open (the remaining forks)

Resolved (16 decisions): lead epic (Foundations); distributed play (someday);
rename to "system"; reputation per-captain; split AMD; 6 clans; home systems +
archetype foes; universe dropdown; comms gates+weight; per-captain truce; rep
changes declarative+helper; capture presence-timer; re-capture defendable; hybrid
system composition; POI-activation standby. Remaining are **tuning + spikes**:

1. **Confirm Phase 1 authoring:** the proposed 2 foe / 4 neutral split + home
   coords (Epic C table) and the final per-clan AMD field list. Your call.
2. **Final token/helper names (Phase 2):** `rep:` block key, `reputation_adjust`,
   gate/weight spelling (`%{axis>N}` / `w:axis`).
3. ~~Spike - per-captain truce~~ **RESOLVED (spike findings):** brain-layer
   override in `npc_brains.mast`/`defender.mast` (`is_hostile` + `captain_truce`);
   no engine change. Implementation detail only.
4. ~~Spike - standby of AI/stations~~ **RESOLVED (spike findings):** standby
   removes objects from the sim and works on NPCs (already used by hangar/cag);
   resume re-classifies. Just track parked POIs with a `universe_standby` role.
5. **Tuning (Phase 3):** capture hold seconds N + clear-radius R + clan counter-
   assault cadence; per-kind system templates + deck contents/weights.

---

## Implementation status (live)

- **Phase 1 - DONE** (LegendaryMissions): clans-as-sides, deterministic clan
  ownership of systems, clan-owned stations (foe hostile / neutral dockable),
  clan-sided enemy fleets, galaxy-map clan display, start-screen Universe
  dropdown, sector->system rename. All verified headless.
- **Phase 2 - DONE:**
  - reputation core (per-ship, 7 signed axes, persisted); declarative
    `rep:` + custom `signal:` on quest complete; diplomacy deltas (change +
    persist + re-apply) via `universe_set_relation`; per-captain truce (fleets
    ignore high-standing captains via `truced_ships` subtracted from
    `ai_fleet_chase_roles` targeting; no-op without reputation); narrative-arc
    enablers (`scope: shared` in quest_grant_amd + SHARED advancement for
    on_kill/collect/scan/dock/reach); comms `%`-line **gates + weights**
    (`%N` weight, `%{cond}` gate eval'd in the task scope, `%N{cond}` both;
    backward compatible) - the shared-parser piece, with unit tests; ambient
    clan **chatter** - all four triggers (arrival, periodic, near-POI, and on
    reputation/diplomacy change); archetype/authored lines, clan-colored.

> Parser note: MAST double-quoted strings treat `{...}` as format-interpolation,
> so comms rep-gates use the `%{cond}` form on `%` lines (the gate is captured in
> the line prefix, not the interpolated text) and `.amd`/data is read from files,
> not inline MAST string literals.
- **Phase 3 - IN PROGRESS:**
  - DONE: space-dock **capture** - foe clan home spawns station + garrison;
    clear + hold the area -> station morphs to the player's side
    (obj.set_side), persisted, docking opens; captured systems re-spawn friendly.
  - DONE: **terrain network culling** (standby) - distant asteroid/nebula
    parked out of the engine network (sim+replication) while the script Agent
    persists; retrieved as players approach; cleared on jump. Terrain only
    (brains are sim-independent, so parking NPCs would let their brains act on a
    non-simulated object). Measured: 1582/2082 field objects parked at 25k.
  - DONE: **brain-aware culling** - generic brain_pause/brain_resume
    (brains_run_all skips paused); universe_cull_step pauses a parked object's
    brain and resumes on retrieve, so self-brained NPCs/POIs cull safely; cull
    set broadened to black_hole/mine. (Fleet ships still a follow-up: their brain
    lives on the fleet agent, not the ship.)
  - DONE: clan **re-capture** - revisiting a captured foe system spawns the
    clan's re-assault fleet; defend to keep it, or the clan holds the station's
    space and it reverts (set_side back, captured cleared). Dynamic frontier.
  - DONE: richer systems - **kind-template + keyed POI deck** framework
    (`universe_systems.py`): the kind if/elif spawns the template core (primary
    station / garrison / anomaly), then `universe_system_deck(key, kind, owner,
    archetype, foe, difficulty)` returns a deterministic, weighted deck of extra
    POIs that universe.mast spawns via `match poi.type`. Deck types: **loot**
    caches (trade goods, denser in nebula/anomaly; on_collect), **derelict**
    wrecks (science-scannable, on_scan, salvage; likelier in nebulae), **secondary
    outpost** (a smaller clan holding in ~40% of clan systems - tagged
    `station, outpost` so it's an extra clan-work giver; the //damage/destroy
    station-persistence guard excludes `outpost` so it doesn't nuke the primary),
    and **mine field** (lethal terrain in foe territory). Pure-Python + unit-probed
    for variety/determinism. Archetype flavors outpost art.
  - DONE: fleet-level culling (`universe_cull_fleets`) - a fleet is parked as a
    unit: when no player is within the cull radius of ANY of its ships, every ship
    (linked under "ship_list") goes to standby and the one fleet brain (on the
    raider_fleet agent) is paused; retrieved + resumed the moment a player nears.
    Completes Epic A2 - terrain, self-brained NPCs/POIs, AND fleets all cull
    safely.
  - DONE: clan **makeup** (Epic C/I) - clans.amd `makeup` sets a clan's race
    composition (single race / even list / weighted dict); `clan_pick_race`
    drives all of a clan's fleet spawns (garrison, re-assault, foe systems), so
    Ashfang flies all-Torgoth, Iron a Kralien/Arvonian mix, etc. No makeup -> the
    old random pool.
  - DONE: chatter on the **info panel** not the text waterfall (Epic G) -
    `universe_chatter_card` / `universe_info_card`; HTBM-style cards
    (name/color/history/auto-dismiss). [explore] promote a `comms_info_card`
    helper into sbs_utils (see Epic G note).

> Fixed: universe_jump_to's console loops crashed (`'int' object has no
> attribute 'client_id'`) when role("console") yielded a raw client id instead
> of a console object (seen on rapid headless jumps). Now normalized:
> `co = to_object(c); cid = co.client_id if co is not None else c`. 6-jump run
> clean.

---

## Phase 1 is specified - ready to plan the build

The Foundations shape is agreed (see "Phase 1 design" above). The only Phase-1
items left are **authoring choices** (foe/neutral split, home coords, exact AMD
fields), which we can finalize while writing the clan content. When you give the
go, the next artifact is a **Phase 1 implementation plan** (still its own doc /
section) covering:

- the `clans.amd` schema + the 6 authored clans (with homes + foe/neutral),
- the start-screen Universe dropdown + load path,
- clans-as-sides spawning from the AMD,
- keyed clan ownership of foe systems (archetype-filtered) + galaxy-map display,
- the sector -> system rename pass.

> Reminder: another session is touching code, so this stays **planning only**
> until you confirm it's safe to implement.

---

## Appendix A - Phase 1 implementation outline (planning, not code)

A concrete shape for when implementation is safe. Names are proposals.

### Files
- `clans.amd`, `narrative.amd` - content (mission folder or a shared content dir).
- `maps/universe_clans.py` (new) - clan load/spawn + system-ownership helpers.
- `maps/universe.mast` - add the Universe dropdown property; load clans at start;
  owner-aware system entry; clan colors on the galaxy map.
- `maps/universe_helpers.py` - sector->system rename; clan-ownership delta +
  new save keys (selection, diplomacy deltas, reputation map).

### clans.amd schema (per clan heading)
| field | meaning |
|---|---|
| heading key | clan id / side key (e.g. `iron`) |
| color | side icon color |
| archetype | military / trader / pirate / cult / settler / mercenary |
| diplomacy | `foe` or `neutral` (authored default vs the player side) |
| homes | list of `[i, j]` named home systems (pinned landmarks) |
| leans | reputation-axis defaults the clan rewards |
| quest_pool | archetype quest types the clan can offer |
| prose body | description (+ comms greeting flavor) |

### Helpers (proposed)
- `universe_load_clans(content)` - parse clans.amd; spawn each clan as a side
  (`prefab_side_generic`); set default relations vs the player side from `diplomacy`.
- `clan_for_system(seed, i, j, danger)` - owning clan of a keyed clan/foe system:
  named homes win, else an archetype/danger-weighted keyed pick. Pure (map-safe),
  so the galaxy map and the spawn agree.
- `universe_system_owner(sectors, i, j)` - delta override (capture / diplomacy).
- extend the map-cell color to show a clan's home/owned color.

### Universe dropdown + load
- `@map/universe` metadata gains
  `Universe: gui_drop_down("$text: {UNIVERSE_SELECT};list: ...", var="UNIVERSE_SELECT")`
  listing discovered clans/narrative pairs (Phase 1: a built-in `Default` + any
  discovered).
- On start: load the selected `clans.amd` (+ `narrative.amd`), spawn clans-as-sides,
  store the selection in the save so **Continue** reloads the same universe.

### System ownership at entry
- In `universe_enter_sector`: if the system kind resolves to a clan/foe system,
  `clan_for_system(...)` picks the owner; spawn that clan's ships/station/dock
  (Epic B template) instead of generic raiders; honor capture/diplomacy deltas.

### sector -> system rename checklist
- `universe_sector_key/kind/name/value/flag` + `UNIVERSE_SECTOR_R`
  -> `universe_system_*` / `UNIVERSE_SYSTEM_R`.
- "Sector (i, j)" label, nav-console text, cargo/mystery quest text -> "System".
- comments/docstrings. (Unreleased save -> no compat shim needed.)
- Coordinate with the other session to avoid file collisions.

### Save keys added (additive - no version bump)
`universe_selection`; `diplomacy` (per side/clan-pair deltas); `reputation`
(per client -> clan axis map); clan/dock `owner` inside existing system deltas.

---

## Appendix B - clans.amd content draft (the 6 clans)

Ready-to-author content; tweak names/colors/homes/flavor freely. Data fence is a
line of only dashes.

```
// The launch clans. Each heading is a clan (its key = side key); the data
// section sets identity + home systems; the prose is description/comms flavor.

# [Iron Concord](iron)
---
color: "#39f"
archetype: military
diplomacy: neutral
homes: [[6, 4]]
leans: { by_the_book: 40, fearsome: 30, honest: 20 }
quest_pool: [patrol, escort, strike]
---
Disciplined and territorial. Respects strength and straight dealing; honor a deal
and the Concord remembers - break one and they remember longer.

# [Verdant Pact](verdant)
---
color: "#4c8"
archetype: trader
diplomacy: neutral
homes: [[-5, 3]]
leans: { peaceful: 40, generous: 30, kind: 20 }
quest_pool: [supply, escort, survey]
---
Green-world traders and farmers. Quick to deal, slow to fight; pay them in
kindness and they pay you back in goods.

# [Free Holders](free)
---
color: "#b85"
archetype: settler
diplomacy: neutral
homes: [[-7, -7]]
leans: { resourceful: 40, honest: 30, kind: 10 }
quest_pool: [salvage, rescue, supply]
---
Independent settlers scratching a living from the drift. Self-reliant and plain-
spoken; they value a captain who gets things done.

# [Mercury Guild](mercury)
---
color: "#fb0"
archetype: mercenary
diplomacy: neutral
homes: [[5, -3]]
leans: { resourceful: 30, selfish: 30, fearsome: 20 }
quest_pool: [bounty, escort, smuggle]
---
Brokers of muscle and cargo - loyal to the contract, not the cause. Coin and a
fearsome reputation open their doors.

# [Ashfang Raiders](ashfang)
---
color: "#e33"
archetype: pirate
diplomacy: foe
homes: [[8, -5]]
leans: { violent: 40, cruel: 30, cowardly: 20 }
quest_pool: [raid, smuggle, bounty]
---
Opportunist pirates who prey on the lanes. They respect violence and despise the
weak; only the dangerous bargain with them.

# [Hollow Choir](choir)
---
color: "#93f"
archetype: cult
diplomacy: foe
homes: [[-4, 6]]
leans: { intellectual: 40, liar: 30, selfish: 20 }
quest_pool: [retrieve, escort, mystery]
---
A secretive cult chasing forbidden knowledge in the deep dark. Honeyed words hide
sharp intent; trust them at your peril.
```

> Comms greeting flavor (Epic F gates+weight) can live in the clan comms tree or
> narrative.amd, e.g.:
> ```
> << [iron]
>    %{honest>40} "Your record speaks well, captain. Proceed."
>    %{honest<-40} "We've heard how you keep your word. State your business and go."
>    % "Concord space. Identify."
> ```

---

## Appendix C - narrative.amd draft (a sample reveal-chain arc)

A galaxy story arc, SHARED, spanning systems, reusing the quest trigger vocab +
`reveal`. Each heading is one step; data sets state (active now / secret = later),
the trigger, the next step to reveal, and rewards. Data fence is a line of dashes.

```
// "The Long Truce" - broker a ceasefire between Iron Concord and Ashfang.
// SHARED arc; steps are flat keys chained by reveal.

# [The Long Truce: Summons](truce_1)
---
scope: shared
state: active
on_reach: { sector: [6, 4] }
reveal: truce_2
---
A coded hail from Iron Concord HQ at system (6, 4). Travel there to hear them out.

# [The Long Truce: The Ask](truce_2)
---
scope: shared
state: secret
on_comms: { option: truce_accept }
reveal: truce_3
reward: { credits: 100 }
---
The Concord wants a broker for a ceasefire with the Ashfang Raiders. Accept the
charge in comms to proceed.

# [The Long Truce: Proof of Resolve](truce_3)
---
scope: shared
state: secret
on_kill: { role: ashfang, count: 3 }
reveal: truce_4
---
Words are cheap. Thin the Ashfang raiders - destroy three - to show the Concord
you can hold the line.

# [The Long Truce: The Accord](truce_4)
---
scope: shared
state: secret
on_dock: { role: station }
reward: { credits: 800, rep: { iron: { honest: 20, fearsome: 10 } } }
signal: long_truce_sealed
---
Return to a Concord starbase to seal the accord.
```

**Notes (small enabling work this arc implies):**
- **`scope: shared`** tells the giver to grant the arc on `Agent.SHARED_ID` (vs a
  ship). `quest_grant_amd` already honors per-heading state; add scope handling.
- **SHARED advancement:** the driver's `on_signal` already advances SHARED quests,
  but `on_kill/on_collect/on_scan/on_dock/on_reach` currently scope to the acting
  agent/players. To drive SHARED arc steps by those triggers, **extend each
  advancer to also iterate SHARED** (one-line each, mirroring `quest_on_signal`).
  Small, additive driver change - record as a Phase-2 task.
- **`signal:` on-complete action [spec]:** a new declarative action that emits a
  named signal when a step completes (here `long_truce_sealed`), so a route can
  `side_set_relations(iron, ashfang, NEUTRAL)` and persist the diplomacy delta.
  Mirrors `reveal`/`reward`; complements the `label:` escape hatch.

---

## Appendix D - Epic B per-kind system templates

A system = **template (by kind/owning-clan)** + a keyed **deck** of weighted
extras. Templates are the fixed core; decks add procedural variety. Named home
systems (clans.amd) can override with hand-placed POIs.

| System kind | Template core (always) | Deck (weighted extras, keyed) |
|---|---|---|
| home (0,0) | friendly starbase + market + docking; safe | light asteroid field; a pickup or two |
| station (neutral) | 1 neutral-clan outpost (market, comms quests) | asteroid/nebula field; pickups; rare derelict |
| clan-foe | owning clan's **space dock** (capturable) + garrison fleet | mines/lethal terrain; reinforcement patrol; pickups |
| clan-neutral | neutral clan outpost (comms quest pool, market) | patrol ship; field; cargo POI |
| nebula | dense nebula field | hidden **derelict** (scan) ; monster; pickup |
| anomaly | black hole(s) + the mystery giver (built) | extra anomaly; rare high-value cache |
| empty | sparse field only | occasional lone POI (derelict/pickup) |

**Clan archetype flavors the clan-foe/neutral templates:**

| Archetype | Dock/outpost flavor | Garrison/patrol |
|---|---|---|
| military (Iron) | fortified dock, shields up | disciplined patrol wing |
| pirate (Ashfang) | raider den dock | fast raider pack |
| cult (Hollow Choir) | shrouded station in nebula | zealot escorts |
| trader (Verdant) | market-heavy outpost | light defense only |
| settler (Free) | ramshackle holding | militia, sparse |
| mercenary (Mercury) | guild dock, for-hire | contractors (neutral unless provoked) |

**[decide]** Exact deck weights + per-archetype fleet sizes (tuning, settle while
building Epic B).
