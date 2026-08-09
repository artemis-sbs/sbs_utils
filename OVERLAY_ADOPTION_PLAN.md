# Overlay Adoption — where overlays replace (and where they pair with) the existing surfaces

> **Status: ACTIVE (2026-08-09).** P1-P5 done; **P0 is the open gate** - the in-engine
> verification pass for every overlay kind but `hero`. Everything below P0 is headless-green
> only, and a mock frame is not evidence about the engine.
>
> Also unbuilt: the `amd_announce` vocabulary (library item 4). `procedural/amd_overlay.py`
> exposes only `amd_overlays` / `overlay_amd`. P3 did land: `procedural/announce.py` with
> `announce`, `announce_headline`, `announce_clear` and the traffic helpers, plus
> `tests/test_announce.py`.

Companion to the overlay system itself (built; documented in
`mkdocs/docs/cosmos/overlays.md`). This one
answers the *authoring* question: **given LM and HTBM as they exist today, what should
become an overlay, what should stay, and what should become BOTH.**

Short version: **overlays are an attention layer, not a record layer.** They are the
only surface that can draw over the 3D view and the tactical map, and the only one
that can be cinematic — but they auto-dismiss, keep no history, target *consoles* (not
ships), and are invisible to a console that connects a second later. So the rule is:

> **An overlay never carries information alone.** Anything a player might need to act
> on later gets a durable twin — a `comms_message` (in-fiction, from a character) or a
> `comms_info_card` (panel, with history and an optional button). The overlay makes
> them *look*; the twin lets them *look it up*.

---

## Compare & contrast — the five surfaces

| Surface | Lives where | Persists? | Targets | Interactive | Can draw over the view | Cost of noise |
|---|---|---|---|---|---|---|
| `comms_broadcast` | text waterfall | scrolls away | ship **or** client | no | no | very low salience — spam is invisible, so it hides real news |
| `comms_message` / `comms_receive` | comms panel conversation | **yes** — with sender, face, colour | ship / player | comms tree | no | in-fiction; wrong for mechanical status |
| `comms_info_card` (`gui_info_panel_send_message`) | info panel | **yes** (history) + auto-dismiss timer | **console** | **button → awaitable Promise** | no | needs the panel to be on that console |
| `sbs.send_story_dialog` | engine narrative popup | no | one client — **you fan it out by hand** | no | it *is* the view | interrupts; no history; nothing to review |
| **overlay** | slot over the whole page | **no** | **console** | modal choice / HUD buttons | **yes** | disappears; late joiners never see it |

Read down the "persists" column and the policy writes itself.

**Preference order for the durable twin** stays as it is today: `comms_message` >
`comms_info_card` > `comms_broadcast`. Overlays sit *beside* that ladder, not on it.

### When to use which

| You want to… | Use |
|---|---|
| Mark a chapter / scene / boss reveal | `overlay_hero` **+** `comms_info_card` (so it's re-readable) |
| Show someone speaking over the live view (esp. while audio plays) | `overlay_lower_third(face=…)` **+** `comms_message` from that character |
| Warn about something time-boxed (countdown, alert state) | `overlay_banner` (re-call to update) **+** one `comms_message` at each real beat |
| Say "that worked" for a small mechanical action | `overlay_toast` — **replaces** the waterfall line |
| Sensory punctuation (hull hit, jump, system down) | `overlay_flash` / `overlay_letterbox` — no twin needed, it carries no facts |
| A live readout over a cockpit / 3D view | `overlay_hud` (sticky) — establish once at console start |
| Ask for a decision | **keep `comms_info_card(button=…)`** — engine-proven, has history. `overlay_choice` only for a genuinely cinematic, must-answer-now moment |
| End-of-game results, quest log, standings tables | **keep the page / tab.** Optionally a hero card as a curtain *before* it |
| Dense combat feedback (crit chance, shield ticks) | **keep `comms_broadcast`.** High frequency + low importance is exactly what the waterfall is for |
| Debug / dev tracing | **keep `comms_broadcast`** (or `log`). Never an overlay |

### Five rules that stop information loss

1. **Durable twin.** New information ⇒ a `comms_message` or an info card as well.
2. **Headline, not payload.** Overlay text is a glance: ~60 ASCII chars, no paragraphs.
   The paragraph goes in the twin. (Engine text is ASCII-only — no em-dashes/emoji.)
3. **Never gate progress on an overlay.** If a button must be pressed to advance,
   it belongs on the info panel (history + reconnect-safe), not in a slot that
   auto-dismisses.
4. **Persistent state ⇒ sticky slot or a tab, never a transient card.** Objectives,
   standings, timers survive a late joiner only if they're re-established.
5. **No required buttons over the 2D tactical view** until the engine honours overlay
   input routing (`input: capture` is plumbed but deferred). Cinematic and HUD
   *displays* over it are fine today.

---

## What LM does today, and what to do about it

| Site | Today | Change | Why |
|---|---|---|---|
| [mission_helper_functions.py:11](../LegendaryMissions/maps/mission_helper_functions.py#L11) `send_general_message` | `send_story_dialog` fanned out to server + every mainscreen, then `comms_message` per player | **Highest-value single edit.** Keep the signature; swap the story-dialog fanout for `overlay_lower_third(nName, textLine, face, to=role("mainscreen"))`, keep the per-player `comms_message` untouched | One helper body upgrades **peacetime, florbin_case, deepstrike, WalkTheLine, SecretMeeting, Infinite_Cosmos** at once. The twin already exists — nothing to lose |
| [hangar.py:250-270](../LegendaryMissions/hangar/hangar.py#L250) objective start/complete | 2–3 `comms_broadcast` lines into the cockpit's ~9%-tall waterfall strip | `overlay_hud` on the `objective` slot for the live objective; `overlay_toast` on completion; keep the one `comms_broadcast(OBJECTIVE_ID, …)` to the carrier | A pilot's objective is *persistent state* squeezed into a scrolling strip — the exact rule-4 case |
| [hangar.mast:377-412](../LegendaryMissions/hangar/hangar.mast#L377) cockpit | readouts hand-placed in fixed `gui_section` rects over a cockpit image | live values via `overlay_hud` / `overlay_hud_update` from a watcher sub-task | Value updates stop repainting the cockpit page. Leave `fighter_control`/`grid_control` engine widgets alone |
| [borderwar.mast:179-211](../LegendaryMissions/maps/borderwar.mast#L179) war countdown | `comms_broadcast` **and** a per-player `comms_receive_internal` at 5 fixed marks | `overlay_banner("WAR IN 4:00", to=…)` re-called each minute (re-show is generation-guarded — no new API); **keep** `comms_receive_internal`; drop the duplicate broadcast | A countdown is the textbook banner. The record already exists twice; one is enough |
| [item_collect.mast:55](../LegendaryMissions/items/item_collect.mast#L55), [fabrication.mast:44](../LegendaryMissions/fabrication/fabrication.mast#L44), [beacon.mast:33](../LegendaryMissions/fabrication/beacon.mast#L33), [beacon_workflow.mast](../LegendaryMissions/fabrication/beacon_workflow.mast) | `comms_broadcast` one-liners | `overlay_toast` **replaces** them (toasts stack, each self-clears). Add an info card only when the item is quest-relevant | Pure "that worked" feedback. No facts lost — the inventory/Fabricate tab is the record |
| [docking.mast:82,194](../LegendaryMissions/docking/docking.mast#L82) | `comms_broadcast` docking state | `overlay_toast` to that ship's consoles | Same class. Low priority |
| [peacetime_remastered.mast](../LegendaryMissions/maps/peacetime_remastered.mast) (~25 `comms_info_card` dispatches, 4 nested arcs at :660/:732/:793/:847) | info cards only | **Keep every card.** Add `overlay_toast("New job: …")` on accept and `overlay_hero` at each arc's opening beat — and prefer authoring these as quest AMD `On accept:` / `On complete:` fields, which already fire overlays to the quest's participant consoles | The arcs already read as chapters. Zero new mission code via the quest hooks |
| [game_results.mast:75](../LegendaryMissions/consoles/game_results.mast#L75) | full results page (quest log listbox, stats) | **Keep the page.** Optionally `overlay_letterbox` + `overlay_hero(START_TEXT)` for ~4s before it, mainscreens only | A results table is a page, not a card. The hero is a curtain, not a replacement |
| [manual_weapons.mast:173-231](../LegendaryMissions/consoles/manual_weapons.mast#L173) crit feedback | `comms_broadcast` | **Keep.** At most an `overlay_flash` when the *player's own* hull takes a crit | High-frequency combat chatter. A toast per crit is a screen full of toasts |
| [collision.mast](../LegendaryMissions/collisions/collision.mast), [debug.mast](../LegendaryMissions/consoles/debug.mast), [grid_ai.py](../LegendaryMissions/ai/grid_ai.py) | `comms_broadcast` (mostly commented-out debug) | **Keep.** Never overlay | Dev tracing |
| [gamemaster_comms_messages.mast](../LegendaryMissions/gamemaster_comms/gamemaster_comms_messages.mast) | GM sends via info panel / comms | Add "as banner" and "as hero card" send modes to the GM message tool | A GM's whole job is directing attention; give them the attention layer |

## What HTBM does today, and what to do about it

HTBM is the best pilot in the codebase: **its entire narrative flows through two
helper functions**, so the pairing lands in one file.

| Site | Today | Change |
|---|---|---|
| [here_helpers.py:21](../HereThereBeMonsters/here_helpers.py#L21) `here_comms_incoming_info_message` | `comms_receive` + `comms_info_card(button=…)` → Promise | **Keep the card and the Promise verbatim** (it's the mission's spine, has history, is reconnect-safe). Add `overlay_lower_third("INCOMING TRANSMISSION", title, face=…)` to that ship's consoles + mainscreens |
| [here_helpers.py:54](../HereThereBeMonsters/here_helpers.py#L54) `here_receive_info_message` | `comms_receive` + info card + `play_audio_file` | Add `overlay_lower_third(title, message, face=face, seconds=time)` — **subtitles while the audio plays.** Today the audio plays over a main screen showing nothing |
| Scene labels — `scene_distress_call_one/two/three`, `salvage`, `strange_object`, `scene_web_trap`, `scene_hostage_message` ([story.mast:302-700](../HereThereBeMonsters/story.mast#L302)) | plain inline labels | One `overlay_hero("DISTRESS CALL", subtitle=…, seconds=4, to=role("mainscreen"))` at each scene head | One line per scene, no state |
| System breaks — `sensor_array_break`, `weapons_break`, `engine_break`, `shields_break` ([story.mast:737-790](../HereThereBeMonsters/story.mast#L737)) | `play_audio_file("audio/hullhit")` only | `overlay_flash("#f006")` + `overlay_banner("SENSOR ARRAY OFFLINE", seconds=6)` to that ship's consoles | Cheapest, most visceral win in the mission. Carries no facts ⇒ needs no twin (the damage itself is the record) |
| Monster reveal | comms text | `overlay_hero(name, ship=<art key>)` | The hero builder already takes `face` / `ship` / `icon` / `image` |
| `temp_ending` ([story.mast:706](../HereThereBeMonsters/story.mast#L706)) | ends | `overlay_letterbox` + `overlay_credits(roll=…)` | Credits roll already ships |

**Do not** convert HTBM's button/promise flow to `overlay_choice`. It would trade a
history-keeping, engine-proven, reconnect-safe interaction for a transient one.

---

## Library work this implies (sbs_utils)

1. **Make `to=` an audience expression** (and export the resolver as `consoles_of`).
   Today `comms_broadcast(ship_id, …)` works while `overlay_*(to=ship_id)` **raises
   `AttributeError`** — `gui_page_for_client` does `Agent.get(id).page`, and `page` is
   a `GuiClient` property ([gui.py:104](sbs_utils/gui.py#L104)), so a `SpaceObject`
   blows up inside the caller's task. Overlays target consoles; nearly every migration
   above needs ships→consoles, and `quest_driver._quest_overlay_audience`
   ([quest_driver.py:49](sbs_utils/procedural/quest_driver.py#L49)) is already this
   function hand-rolled for one case. One resolver, dispatching on the bit-typed id:

   | `to` | resolves to |
   |---|---|
   | `None` | the current console |
   | client id (`is_client_id`) | that console |
   | space-object id (`is_space_object_id`) | `linked_to(id, "consoles")` |
   | side — key string or side agent id | consoles of every ship on that side |
   | set / list | union of the above, elementwise |
   | anything else | skipped |

   Mixed sets then work for free, which matters because `role(side)` holds console
   clients **and** ships. `to=role("__player__")` goes from crash to "every player
   console" — what the line already looks like it means.

   - **Ship → which consoles?** All of them is the wrong default half the time (a
     lower third usually wants mainscreen). Optional filter:
     `to=ship, consoles="mainscreen"` → `linked_to(ship,"consoles") & any_role(…)`,
     mirroring HTBM's existing `consoles="science, engineering"` idiom.
   - **Strings are side keys only** (`to_side_id(key, warn=False)`); `role(...)`
     returns a set, so there's no ambiguity.
   - **A side means "consoles of ships on that side"** (`side_members_set` ∩ players) —
     the split the peacetime PvP work needs.
   - **Server (id 0)** included when passed explicitly, never swept in by expansion.
   - **Failure policy:** zero pages from a *set* is normal (nobody connected, NPCs in
     the set) and stays quiet; zero pages from a *scalar* `to` logs once. Separately
     harden `gui_page_for_client` with `getattr(gui, "page", None)` so no `to=` value
     can crash a story task.
2. **`announce(...)` — the pairing helper.** So missions stop hand-rolling
   overlay + twin (HTBM's two helpers, LM's `send_general_message`, and
   `pr_claim_notify` are three independent hand-rolls of the same idea):

   ```
   announce(text, title=None, face=None, ship=None, to=None, level="info", seconds=None)
   ```

   | `level` | overlay | durable twin |
   |---|---|---|
   | `chapter` | `hero` | info card (history) |
   | `hail` | `lower_third` + face | `comms_message` from the sender |
   | `alert` | `banner` | info card |
   | `status` | `toast` | none |
   | `minor` | `toast` | none |

   Resolves `ship=` → consoles, keeps the twin's preference order, ASCII-clamps and
   length-clamps the overlay headline. One call, rule 1 enforced by construction.
3. **Publish `_show_transient`** (or an `overlay_kind(kind, …)` front door) — quest_driver
   imports the private one today.
4. **`amd_announce` vocabulary**, so the pairing is declarative in `.amd` alongside
   `amd_overlays` — matching the existing "content as data" direction.

## Verification reality check — sequence the rollout around it

Of the built system, only **show + clear of the `hero` card** is
**engine-verified**. `toast`, `banner`, `lower_third`, `hud`, `letterbox`, `flash`,
`choice`, `credits` are headless-green (suite ~1517) but **engine-pending**. Also
engine-real, not mock-real: overlay stacking, the first-show repaint, and input over
engine widgets. So:

- **P0 — engine-verify each kind** in a browser mock session, then a real engine
  session, via `LM_TestRange` (or `control_gallery`). ⏳ **OPEN — the user checkpoint.**
  Everything below is headless-green but unproven on screen.
- **P1 — HTBM** ✅ **DONE.** `here_helpers.py`: a lower third on both message helpers
  (subtitles while the audio plays), plus `here_scene` / `here_system_break`; 7 scene
  chapter cards and 4 sabotage flash+banners in `story.mast`. The card + promise flow
  is untouched. `--test` PASS.
- **P2 — `send_general_message`** ✅ **DONE.** The per-mainscreen `send_story_dialog`
  fanout is now `overlay_lower_third`; the server/host dialog and the per-player
  `comms_message` twin are unchanged. Upgrades peacetime, florbin_case, deepstrike,
  WalkTheLine, SecretMeeting, Infinite_Cosmos through one body.
- **P3 — library** ✅ **DONE.** `to` is an audience expression (client / ship / side /
  mixed set) resolved by `consoles_of`, with a `consoles=` role filter on every
  wrapper; public `overlay_kind`; per-kind slot/primary-field conventions moved into
  `overlay.py` so wrappers, AMD and quest directives agree; `announce()` +
  `announce_headline()` in `procedural/announce.py`. `gui_page_for_client` no longer
  raises on a non-console id. 24 new tests (`tests/test_announce.py`); suite 1647.
- **P4 — LM** ✅ **DONE.** Hangar objective → sticky `objective` HUD + completion toast
  (carrier's log line kept); borderwar countdown → banner (+ flash on the neutral-zone
  violation), `comms_receive_internal` record kept; item/fabrication/beacon/docking
  status lines → toasts.
- **P5** ✅ **DONE.** 18 peacetime_remastered jobs carry `On accept:` / `On complete:`
  toast directives (pure AMD authoring); 4 arc chapter cards; GM "as Banner" / "as
  Card" send modes that still send the comms_message.
- **Never** — debug broadcasts, dense combat feedback, the results page, the comms tree.

### The info panel followed (v1.4.0, unreleased)

Once overlays carried the attention job, the panel was left doing it badly and not
doing the job only it can do. Two facts settled it:

- **Every send stole the panel's tab** (`info_panel.set_tab(path)`) from whatever the
  player was reading, and `tick_tab` yanked it back when the queue drained. It was a
  popup wearing a tab strip.
- **The history was vestigial.** `$MESSAGES` was capped at 9 and nothing rendered it -
  `gui_panel_console_message_list` existed, but its registration sat commented out in
  LM behind an `is_dev_build()` block.

So the panel is now **log-first**: a card is filed and readable on the log tab, and
interrupts only when it means to. The exception is load-bearing - **a card with a
`button` always interrupts**, because it is a progression gate (HTBM awaits nine of
them) and a missed one deadlocks rather than degrades. `notify=True` is the opt-in for
everything else; `announce()` gets it right by construction.

Done now rather than staged behind a flag because **1.4.0 is unreleased** - released
missions pin the v1.3.0 sbslib in `story.json` and cannot see the change, so the only
callers were in-repo. Every site that relied on the old interrupt and has no overlay
pairing carries an explicit `notify=True` (LM dispatches, claim notices, the
legendary_comms demo, OU chatter): nothing changed on screen, and the marker is
greppable, so converting them to `announce()` is a follow-up, not archaeology.

### Found while executing

- **`to=ship_id` used to raise, not no-op.** `gui_page_for_client` did
  `Agent.get(id).page`, and `page` is a `GuiClient` property — a `SpaceObject` raised
  `AttributeError` into the caller's task. Hardened + covered by a regression test.
- **`FrameContextOverride` pinned the context.** It saved the *derived* `task`/`page`
  properties (which fall back to the client's page / its gui task) and restored them as
  *concrete* overrides — so every overlay push left `FrameContext._task` pinned to one
  page for everything that ran afterwards. It now saves the raw `_task`/`_page`. This
  was surfacing as cross-test pollution; in-engine the per-tick scheduler was masking
  it.
- **Headless can't prove an overlay renders.** With no console connected, `to=<ship>`
  correctly resolves to nothing, so `--test` only proves the call path. That is exactly
  what P0 is for.

### Gotchas carried into every phase

- **First show of a slot forces one full page repaint** to establish the sub-region;
  afterwards updates are out-of-band. Establish a sticky HUD at console start, not
  mid-combat.
- **Late joiners see nothing.** Re-establish sticky slots on `client_connect`.
- **Per-console fan-out is per-page work** — a role-set `to` on a 6-console game is 6
  region rebuilds. Fine for cards, throttle for HUD (the watcher already updates only
  on a changed value).
- **`//shared/signal`, not `//signal`**, for any server-driven overlay push — a
  per-console route would fan out N×N.
- **ASCII only**, and `draw_layer` must stay above 10000.
