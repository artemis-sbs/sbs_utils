# Design record - surveys, probes, and the decisions they produced

Evidence, not documentation. Nobody authoring a mission needs this file; it exists so a
future change does not re-litigate a question that was already measured, and so the
measurements do not have to be gathered twice.

Each entry is a survey, what it found, and the decision it forced - **including the two
cases where the evidence overturned the design it was gathered to support**. That is the
pattern worth keeping: count the demand before designing the vocabulary.

Sections 1-5 are **corpus surveys**; 6-7 are **engine probes** - measurements taken in a real
Cosmos session, which is the only place several of these questions can be answered at all.

Consolidated 2026-08-09 from `AMD_PLAN.md`, `AMD_SCRIPT_PLAN.md`, `AMD_ACTION_PLAN.md`,
`URGE_PLAN.md`, `NPC_MOTIVATION_PLAN.md`, `GUI_LAYER_CLIP_PLAN.md` and `CINEMATIC_PLAN.md`,
which were deleted once their phase lists were spent. Full text of any of them:
`git log --diff-filter=D -- '*_PLAN.md'`.

---

## 1. AMD fence dialects (2026-07) -> the format redesign

**Surveyed:** 31 `.amd` files, 280 fences, 114 distinct fence labels, 150 section keys,
headings 4 deep (94 / 94 / 212 / 32 by level), plus 34 a2x-generated files.

| Finding | Evidence |
|---|---|
| Four fence readers, chosen by CALL SITE rather than by the file | default `load_yaml_string`; friendly `amd_parse_facts`; the brace-triggered whole-fence YAML flip; loaders bypassing both (`amd_recipe_data`) |
| Tooling and runtime read the same bytes differently | `recipes.amd`: runtime got `Properties` as a nested dict, `amd_core` got `properties: ''` plus two colliding keys. `bar.amd`: runtime got 5 chatter lines, `amd_core` got `lines: ''` |
| The schema was a hand-written second copy that had drifted BOTH ways | 114 authored labels, `amd_schema` declared 47, only 31 overlapped. 83 labels / 394 uses undeclared (`pays` x50, `goal` x32); 16 declared fields never authored |
| Keys were a flat last-wins namespace | 374 keys, 40 duplicated. `peacetime_remastered.amd` alone: `recover` x3, `scan` x3, `florbin` x2 |
| ...which produced a FALSE lint error | `Then: reveal florbin/recover` is a correct path, but flat last-wins `parent_of` made `path_resolves` say False |
| Heading LEVEL meant nothing consistent | records at level 1 in 9 files, level 3 in 5, level 2 elsewhere - so `section_of()` only worked when records happened to land at level 3 |
| Malformed headings demoted to prose silently | `_RE_SECTION` used `match` not `fullmatch`, so `# [X](k) trailing` dropped the trailing text; a greedy `.*` made `# [A](a) and [B](b)` parse as key `b` |
| Author words != player words | `State: idle` rendered to the player as **"Available"** |
| Prose genuinely collides with field syntax | 12 of 279 record bodies opened with a field-shaped line (`COMMS: hail the freighter.`) - which is why the `---` fence stays |

**Decision:** one fence reader, a field-descriptor registry (`amd_schema.field()` / `enum()`
/ `amd_register_fields()`), kind resolution by nearest ancestor, and path-indexed headings
using `fullmatch`. Shipped; OU and LM now depend on it, so the layer is no longer free to
change. Growth rules for adding a field live in `mkdocs/docs/build/amd-format.md`.

---

## 2. AMD body sigils (2026-08) -> `= ` for synopsis, `=$` untouched

**Surveyed:** every proposed sigil grepped at line start across all `.amd` in the missions
tree plus the 34-file a2x corpus.

| Sigil | Uses | Verdict |
|---|---|---|
| `@` `(` `/*` `[[` `> [!` | 0 | free |
| `~` | 0 | free, but **rejected** - reads as MAST inline-Python in this tree |
| `=` | **14** | **COLLIDES** - all 14 are `=$name font:...;color:...`, the line-style declaration |

**Decision:** a synopsis is `=` followed by a **space**; `=$` stays exactly what it is. Zero
existing lines matched `^=\s`, so the split was clean and needed no migration.

**The two laws this produced**, which outlive any particular sigil:

1. **Strict inside the fence, forgiving in the body.** Inside `---` an unrecognized line is
   an error, because a silently dropped field loses authored data. In a body an unrecognized
   line is prose, forever. That is Fountain's rule, and it makes every future body sigil
   backward compatible in the direction that matters - an older `sbslib` reading a newer
   mission renders an unknown sigil as literal text instead of failing to load.
2. **Every ambiguity gets a forcing character.** Auto-detect the common case, always provide
   a one-character override.

---

## 3. AMD stage directions (2026-08) -> ship `becomes`/`arrives`, defer the orders layer

**Surveyed:** runs of consecutive world-action statements across LM, OU, SecretMeeting,
WalkTheLine, StormsBeacon, HereThereBeMonsters and MiningDays. Excluded inventory plumbing,
engine infrastructure and objective `+++ enter` blocks. **25 runs, 62 statements**; 19 of the
25 were only 2 lines.

| Verb | Uses |
|---|---|
| `becomes` (role / side change) | 30 |
| `arrives` (spawn) | 20 |
| `orders` (objective / brain) | 8 |
| `says` (comms) | 2 |
| `departs` (delete) | 2 |
| **`targets`** | **0** |
| **`heads to`** | **0** |

**The evidence contradicted the design.** `becomes` and `arrives` were 81% of all statements
and need no objective layer at all, while the `orders` machinery that most of the design
effort went into covered 8 uses. The two verbs the whole plan grew from appeared nowhere.

**A correction that matters more than the count.** Counting *runs of >=2 consecutive*
statements favours verbs that CLUSTER and hides verbs that appear ALONE. The raw count of
`target_pos(` / `target(` outside `prefabs/` and `ai/` was **16, not 0**. Reading them
changed the conclusion again: most are `BRAIN_AGENT_ID` brain internals no author writes, and
the roughly 6 author-level ones all take a coordinate. `Kidnapper heads to 90000, 0, 90000`
is the same numbers with more ceremony.

**Decision:** ship `becomes` / `arrives` / `says` / `departs`; defer the orders layer. The
deferral is falsifiable rather than permanent - **orders are not unused, they are unnamed**.
`heads to` pays off only when the destination has a NAME. If landmarks become the normal way
to say where, revisit.

---

## 4. Unprompted speech (2026-08) -> urges are clock-driven, and sit on any agent

**Surveyed:** 209 direct speech call sites across LegendaryMissions, OpenUniverse and
Storm's Beacon (`comms_message`, `comms_broadcast`, `comms_receive`/`_internal`,
`comms_transmit`/`_internal`, `comms_info_card`, `gui_info_panel_send_message`, `announce`),
each attributed to its enclosing label and classified by what reaches it.

| Trigger | Sites | Share |
|---|---|---|
| Prompted - player hailed, clicked, scanned or bought | ~122 | 58% |
| Scripted plot beat - author wrote the moment | 38 | 18% |
| Unprompted - a clock or an event decided | ~36 | 17% |
| Dev tooling / autoplay | 13 | 6% |

Who speaks in that unprompted 36: dispatch / faction ops / narrator ~18, UI notification ~11,
grid lifeform 3, **named cast character 4** - and two of those four are the same character
duplicated across two copies of one mission. Every character line in the event bucket is a
*reply*. No character in three missions initiates anything.

**Two design changes it forced:**

- **The clock beats the event.** Clock-driven unprompted speech outnumbers event-driven
  roughly 2.5:1, so the shared ticker is the primary path, not a fallback.
- **This is not a lifeform feature.** The dominant unprompted speaker is a dispatcher, not a
  person, so an urge attaches to **any agent** - a station or a side as readily as a
  character.

**The ten decisions this locked**, cited from `urge.py`, `amd_schema.py`, `quest_driver.py`
and the urge tests:

1. Urges attach to **any agent**, not lifeforms.
2. **Stakes are quests.** An urge never carries its own consequences, so there is one clock
   and one place to tune it.
3. **One shared ticker**, never a task per actor.
4. `Weight:` is **intra-actor only**. Cross-actor contest is the stop line.
5. Escalation is derived from the deadline, not a second clock.
6. Server-only, scoped sends, `//shared/signal` discipline.
7. Quest tickers iterate `has_inventory("__quests__")` - no new registry.
8. Reputation consequences are **player/SHARED-held only**; world stakes are world state.
9. `Whenever:` is a fixed vocabulary plus a registry, never a bare expression.
10. A character's last line belongs to the character, not to the quest's `Then:`.

**Limit of the survey, stated because it cuts against its own verdict:** nobody authors
content for a mechanism that does not exist. Three intended uses were named that the corpus
cannot contain - a diplomat waiting at a station, hint traffic, and bar rumors with weight.
The census is evidence about *shape*, not a verdict on demand.

---

## 5. NPC motivation (2026-08-02) -> do not build the goal selector

**Surveyed:** Open Universe and Storm's Beacon, against the plan's own premise.

| Question | Answer |
|---|---|
| OU NPC behaviour a selector would subsume | **zero** |
| Branches on standing | **heavy** - a whole consequence API |
| Player already moves a motive | **29 sites** |
| Do two NPCs ever want the same thing | **no** |

**Zero, because OU has no NPC decision-making at all** - not one `brain_add`, `objective_add`
or `brain_clear` in the mission. OU spawns LM prefabs and the brains come with them; its
world is procedurally generated per system from persisted state. The model is *state ->
generation*, not *agents -> decisions*. What competes in OU is SIDES over territory, already
modelled by ownership flags and the capture watchers.

**Decision: do not build it.** A goal selector is a pattern with two instances, not a system.
The mission predicted to supply the volume supplies none.

**The smaller real gap the survey found instead**, which is the candidate if anything here is
ever built:

> **Standing changes what things COST. It never changes what anyone DOES.**

OU carries 113 standing references and a mature consequence API (`reputation_reward_mult`,
`reputation_ransom_cost`, `reputation_offer_tier`, `reputation_ceasefire_cost`,
`reputation_foe_deal_standing`). A side you have wronged charges more for a ceasefire and
offers worse tiers - and raids you exactly as often as before. That lands on **sides, not
ships**, which is where `Values:` is already auto-granted by `ARCHETYPE_TRAITS`. It needs its
own demand evidence before design.

---

## 6. draw_layer occlusion probe (2026-08-05) -> the `layer:` style key

**Measured in a real Cosmos session**, not the mock - the mock sets `zIndex` from
`draw_layer` and clips at region boundaries, so it happily reports its own opinion of a
question only the engine can settle. Six cells, emitted raw via `sbs.send_gui_text` /
`send_gui_image` at explicit percent rects, bypassing the layout system so that only engine
paint semantics were in play (`VisualTestRange/maps/visual_draw_layer.mast`).

| Cell | Result | What it establishes |
|---|---|---|
| 1 control | spill runs over the caption | baseline |
| **2 fill at 2000** | **solid, nothing through it** | **an opaque fill at a higher layer HIDES an overflow** |
| 3 fill, no layer | spill drawn ON TOP of the fill | on a tie, **text beats an image even though the image was emitted later** |
| 4 fill at 500 | spill drawn on top | `draw_layer` is genuinely respected |
| 5 button under 5000 | button covered | button layer **< 5000** |
| 6 button under 500 | button visible | button layer **> 500** |

Cells 3 and 4 are what give cell 2 its meaning: **paint order is decided by the layer, not by
emission order**. Cells 5+6 bracket the button to `500 < button < 5000`, consistent with
`1001` - so the long-standing comment claiming buttons sit at `10000` was stale.

Two facts nobody was looking for:

- **Input is not stolen.** A button under an opaque fill still takes hover and click. Useful,
  and a hazard: do not hide a control and assume it is disabled.
- **The engine draws button chrome OUTSIDE the rect it was given.** In cell 5 the button and
  the fill had *identical* rects and the fill still did not cover it. So a backdrop sized to
  the widget it hides leaves a visible rim - **size backdrops to the ROW or SECTION**.

**Decision:** ship the `layer:` style key with a cascade (`mkdocs/docs/cosmos/gui_layer.md`).
The follow-on automatic occlusion banding was **parked**: `overflow: spill` stays the default
because a visible failure gets fixed and a silent one does not, and occlusion cannot work over
a `3dview`/`2dview` at all - you would punch an opaque rectangle into the view.

---

## 7. Scripted camera black-frame matrix (2026-08-01) -> shots fold to one id

**Established with `missions/CameraRepro`** - a raw `script.py`, no sbs_utils, no MAST, no
framework, every line a direct engine call. **Sent to the engine team 2026-08-01.**

| Rung | Call | Result |
|---|---|---|
| 1-3 | view modes `chase` / `first_person` / `tracking`, no cinematic | **draws** |
| 5 | `cinematic` mode, script control RELEASED (engine director) | **draws** |
| 4 | scripted, ids **0/0**, zero offsets | **draws** |
| 7 | scripted, dolly = target = NPC id, **zero** offsets | **black** |
| 8 | scripted, dolly = target = player-family cambot, **zero** offsets | **black** |
| 9 | scripted, GM replica: dolly = target = a real id, offset **500** | **draws** |
| - | scripted, **different** ids for dolly and target, offset 900 | **black** |

So the id alone is not the cause. Two candidate rules survive:

- **Do not put the camera where it is looking.** Rungs 7 and 8 place the lens at the target's
  exact position - a zero-length view vector. Rung 9 does not.
- **Dolly and target must be the same object.** Rungs 9, 4 and the GM replica all pass one id
  twice; the black bottom row is the only shape passing two different ids.

The second is the expensive one: it makes "camera here, subject there" impossible, so every
shot must be composed by moving a camera object rather than by aiming.

**Decision:** `camera_shot` / `camera_track` fold both ids to one and nudge a degenerate
vector. If the engine ever fixes the two-id case, the folding logic can be dropped - the nudge
would still be needed. A correction worth keeping: an earlier reading of this matrix claimed
only `dollyID` 0 works, which was **wrong** - a faithful GM replica renders with a real id.
