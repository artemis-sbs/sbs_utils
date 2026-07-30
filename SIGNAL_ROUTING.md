# Signal routing: `//signal` vs `//shared/signal`

**One rule:** if a route changes state the **server owns once** (spawn, save, reward,
modifier, counter, game-end, a random roll, a server ticker) it MUST be
`//shared/signal`. If it only changes what **this console shows** (a GUI screen, a
per-console widget), it stays `//signal`. Getting this wrong makes the body run **once per
connected console** — the classic symptom is a boss that spawns N times, a shop item bought
N times, or reputation applied N times.

---

## Why (the mechanism)

A route's prefix sets a `server` flag (`signal_register(server=…)`), and the scheduler gates
on it (`mast/mastscheduler.py`):

```python
if label_info.server and not self.main.is_server:
    # skip: a shared route runs ONLY on the server main
```

- **`//signal/x`** → `server=False` → registered on **every** story main → a single
  `signal_emit("x")` runs the body **once per connected console AND once on the server**
  (N + 1 times).
- **`//shared/signal/x`** → `server=True` → runs **only on the server main** (once).

The number of executions has **nothing to do with where `signal_emit` is called** — even a
signal emitted by one console's button press runs *every* console's `//signal` copy.

## The decision rule (litmus test)

Ask: **"If five consoles are connected, do I want this to happen five times?"**

- **No — it's server-owned →** `//shared/signal`. Spawning (`*_spawn`, `prefab_spawn`,
  `npc_spawn`), saves (`universe_save*`), rewards/modifiers (`modifier_add`,
  `reputation_apply`, granting items/credits), counters/quest state
  (`quest_*`, incrementing progress), ending the game, a **random roll** (each console rolls
  independently → conflicting outcomes), starting a **server ticker** (`task_schedule` of a
  watch loop).
- **Yes — it's per-console display →** `//signal`. Building a results screen, updating a
  console's own widget, per-console autoplay.

Note **`comms_broadcast` / `comms_message` / `universe_info_card` are server-side sends** —
called **once** on the server they reach **all** consoles. So a route that only announces
should run once (`//shared/signal`), not once per console (which sends N copies to everyone).

## The split pattern (server-once + per-console display)

When a beat needs both — do the authoritative work once **and** paint every console — split
it: the `//shared/signal` route does the state change, then `signal_emit`s a **display**
signal that a `//signal` route renders per console.

```
//shared/signal/wave_cleared          # server: authoritative, once
    spawn_reward()
    game_state.advance()
    signal_emit("show_wave_banner", {...})

//signal/show_wave_banner             # each console: display only
    gui_banner(...)
```

The shipped `game_over → show_game_results` pair is exactly this: `game_over` is the
server-once teardown; `show_game_results` builds the results GUI on each console.

## Hybrid beats (do the split, don't guard-in-place)

If a beat needs both a server-once effect and per-console display, **split it** (above) — the
authoritative work lives in the `//shared/signal` route, the display in a `//signal` route.
That uses the framework's own server/console gate and is the recommended shape.

Avoid the older ad-hoc idiom of doing the work inside a `//signal` route behind a
`shared XVER = True` "did I already run?" flag (the quest driver's `QUEST_FAIL_WATCH` /
`GAME_ENDED` guards). It works, but it's fragile (every author reinvents the flag, and a
missed guard silently duplicates). Prefer the split.

## This generalizes beyond `//signal`

Any engine-event route that runs per-main has the same hazard when its body mutates shared
state: **`//damage/killed`, `//science`, `//comms`, `//collision`** used as quest/economy
hooks can double-count. The same litmus test applies; where a `shared` variant of the route
exists, prefer it, otherwise guard with `is_server()`.

## Catch it automatically: `sbs lint`

`sbs lint <mission>` runs the signal-route checker (`sbs_utils.procedural.signal_lint`): it
flags any `//signal` route whose body calls a known side-effect (spawn / modifier /
reputation / quest mutation / save / random / task_schedule / shared-or-inventory write) and
suggests `//shared/signal`. Treat a hit as "prove it's display-only, or convert it."

---

## Audit snapshot (2026-07, first pass)

Confirmed duplication bugs found and being converted:

| Repo | Route | Duplicated effect |
|---|---|---|
| LegendaryMissions | `siege_enemies_low` | spawns boss fleets + flagships ×N |
| LegendaryMissions | `collision game_started` | starts the black-hole watcher ×N |
| LegendaryMissions | `quest_driver` mutating hooks | quest state / fail-watch (header already says "server-side") |
| OpenUniverse | `quest_finished` | `reputation_apply` ×N |
| OpenUniverse | `last_side_standing` | N victory broadcasts |
| OpenUniverse | `item_bought/sold/changed` | N `universe_save*` writes |
| StormsBeacon | `eddy_buy_*` | `modifier_add` ×N; random rolls differ per console |
| StormsBeacon | `storm_check`, `universe_arrived`, `hunters_bribed` | story-state writes ×N |

**Left as `//signal` (correct — per-console display):** `show_game_results`,
`auto_player_console game_started`.

**Root cause is understanding, not a missing feature:** the `//shared/signal` mechanism
already expresses server-once; a new `signal_emit` variant would not change *where routes
run*. The fixes are (1) this rule, (2) the split pattern, and (3) the linter that makes
violations loud.

---

# The second axis: how many times is it EMITTED?

Everything above is about **where** a route runs. `//shared/signal` guarantees the body
runs on the server, **once per emit** — it says nothing about how often the signal is
emitted. Emit an init signal twice and its route body runs twice, `shared` or not.

That is not hypothetical. `create_default_player_ships` emitted from inside its own loop
(8 emits, not 1), and a re-entered `start_server` took a live session from **8 player
ships to 33**.

## Why an init signal gets emitted again

**By accident:** two addons emitting the same one (they share a global namespace and load
in non-deterministic order) · a copy-pasted emit in both the console start and a map body ·
an emit inside a loop · a repair loop that re-emits deliberately, safe until someone adds a
spawn to the route · a per-console route emitting a server signal · a double-clicked or
laggy Start button · a mission reload that did not fully reset · a route that failed
halfway and gets re-emitted "to fix it" · a dynamic emit name produced twice.

**On purpose:** respawning a destroyed ship · resetting the scenario without reloading ·
**re-declaring sides after `sim_create()`** · a late-joining crew needing one more ship ·
a mid-mission diplomacy change · PvP side rebalance · campaign chapter transitions.

Both columns matter. A did-I-run flag is wrong for every entry in the second one.

## Prefer identity: make the work idempotent

Give the created thing a stable key and create it only if it is missing. Idempotency is
then against the **current world**, not against "have I run before" — so an accidental
re-emit is a no-op *and* a deliberate one still does the right thing.

```
# 8 ships, however many times this is emitted - and rebuilt if they are ever gone
for slot, data in enumerate(SETTINGS.get("PLAYER_LIST")):
    player_ensure(slot, 0,0,0, data["ship"], data["name"], data["side"])
```

`player_ensure` / `player_slot_id` / `players_reset` (`procedural/spawn.py`) and
`side_ensure` / `side_create` (`procedural/sides.py`) all work this way. `players_reset()`
is the explicit wipe for a deliberate re-init.

## `once` for work with no natural key

When there is nothing to key on — award starting cash, play an intro — mark the route:

```
//shared/signal/give_starting_cash once
//signal/show_intro once if IS_HOST
```

At most one run per mission. The `if` is tested first, so a route whose condition is false
keeps its shot. `signal_once_reset("name")` re-arms it; a mission reload re-arms
automatically (the flag lives in `Agent.SHARED`, which `reset_mission_state` clears).

## Never `once` a route that REPAIRS engine state

`create_sides` must stay re-runnable. `sim_create()` leaves `FrameContext.context.sim`
stale for the rest of the frame, so relations and colors written in that frame land on a
discarded simulation — silently, because the link graph survives and every scripting check
still passes while contacts render grey. The only cure is re-declaring in a later frame,
which is why a2x ships a re-assert loop. Marking that route `once` would reintroduce the
bug. Same for any route that converges toward a desired state rather than creating
something.

## What the linter catches

`sbs lint` adds three codes for this axis:

| Code | Fires on |
|---|---|
| `signal-init-unkeyed-spawn` | a `//shared/signal/create_*` route spawning without a key and not `once`-guarded |
| `signal-emit-in-loop` | `signal_emit` inside a `for`/`while` |
| `signal-multi-emit` | such a route's signal emitted from more than one place (whole-mission pass) |

A keyed create (`*_ensure`) or a `once` route silences them, because in both cases a second
emit genuinely cannot duplicate anything.
