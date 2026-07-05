# What's New in v1.4.0 ✨

A whirlwind tour of everything that landed in v1.4.0 — across the
**LegendaryMissions** content and the **sbs_utils** library that powers it. Links
go to the relevant docs.

---

## 🛩️ Hangar

- **Sortie board.** Fighter and shuttle pilots pick their own missions from a board.
- **Loadouts as upgrades.** Craft loadouts are now deltas over the ship hull —
  shields and ammo applied through the item/upgrade system — with an image-based
  cockpit overlay.

See the [LegendaryMissions addon reference](legendarymissions/addons/index.md).

## 🎰 The Casino is open

Dock in the hangar bay and step into the **Casino** — a self-contained hangout
that adds a **Casino** tab to the bay (leave it out and nothing changes). It runs
on an Arvonian **bit-card deck**, dealt in some games by **the Understander**,
their revered master computer.

- **Play with chips.** Start with a stack; the **cage** lets you **Buy** more or
  **Cash Out** — buying dips into the crew's shared credits so you can always get
  back in, and a hot session earns **comp** chips.
- **Eight games**, from a ten-second flutter to a full poker duel: **Parity**
  (quick XOR bet), **Blackjack**, **Nibble**, **Gates** (bit-card baccarat),
  **Choga**, **Video Poker**, and the new **KoraTa — Ghost-Writing**, a five-round
  head-to-head where you play cards as **values** to build your run or as
  **opcodes** to corrupt your rival's (3-bit and 4-bit tables).
- **The bar.** Toast the room, buy a regular a drink, and **ask for a rumor** —
  act on it to see if it pans out. Reliable patrons earn your trust; enough trust
  opens the **grey market**.
- **Pilot market.** Spend your winnings on **real ship upgrades and gear** —
  chips first, then side credits.

Play guide: [How to play the Casino](legendarymissions/playing/casino.md) ·
Authors: [The Casino addon](legendarymissions/addons/casino.md).

## 🧭 Quests & Stories

- **A signal-driven quest engine** with kill / collect / scan / dock / reach /
  arrive triggers and real rewards — all **authored in simple AMD files**.
- **A proper Quest Log** you can accept and abandon quests from.
- **Multi-step bridge stories** that unfold a step at a time.
- **Quest-driven end-game.** A mission is now a **tree of quests** — a parent mission
  with children marked **required** (must finish to win) or **critical** (fail one and
  the game is lost). Quests can carry an **end_win** / **end_lose** outcome and **fail
  triggers** (a signal fires, a target dies, or a timer expires), so the whole win/lose
  condition is **authored in AMD**, not hand-wired in script. The Siege bosses use this
  to hang their objectives on the siege's mission tree.

Docs: [Quests](build/quests.md).

## 💱 Items & Upgrades

- **Discoverable items and upgrades** driven by a data registry — collect them in
  space and activate them through a generic **Upgrades GUI**.

Docs: [Items & Upgrades](build/items-upgrades.md).

## 🌐 Web pages, written in MAST

- Author browser pages with `//web/<path>` routes using the same `gui_*` layout you
  already know, and open them in a browser while a mission runs — **live** pages
  that update in place and are parameterized by the URL query (`/web/scores?title=Hi`).
- **Living pages** (leaderboards, dashboards) update during the game and are kept as
  a snapshot for after it.
- Bake a read-only page to a **standalone HTML** file, front **many engines from one
  address** (`/web/<engine>/…`), or run it from a non-engine MAST tool — all with
  **no engine changes**.

Docs: [Web pages](build/web-pages.md) · [Serving web pages](tooling/web-proxy.md).

## 🛡️ The Siege Map, Refined

- **Pick your battlefield size** with a new **Map Size** option.
- **Consistent, repeatable maps** from phased, keyed seeding (no more surprise
  spawns inside an asteroid).
- **Share the exact setup** with per-map **seed options** and a **shareable game
  code**.
- **Optional bonus objectives** for skilled crews.
- **Survive Clock option.** Choose what the time limit *means*: **Win** = outlast the
  clock to hold the line, or **Loss** = break the siege before time runs out or you
  lose. One dropdown flips a defensive hold into a race against the clock.

### 💀 Bosses

The Siege can now escalate into a **boss** that warps in when the raiders thin out —
picked from a new **Boss** dropdown:

- **Warlord** — a named enemy flagship and honor-guard reinforcements.
- **Continuous** — endless waves until the clock nears its end, then the attackers
  break off in retreat for a hard-won defender victory.
- **Ragnarok** — the renegade "42 Fleet" led by a Terran juggernaut. Beat it outright,
  or have your comms officer **hail XORN** and turn one of its captains to your side.
- **Infestation** — a **BioMech** swarm that drifts neutral and feeds on asteroids
  until you provoke it, then wakes as a collective, **evolves through four stages**,
  and **breeds** — with the sentient Stage 4 hailable to calm or enrage.

Bosses are **data-driven and folder-scanned** — each is a small file in `maps/bosses/`,
so authoring a new one is just dropping in a file.

Playing & hosting: [LegendaryMissions](legendarymissions/index.md) ·
Authors: [Writing a Siege boss](legendarymissions/script/bosses.md).

## 🏆 Game Results & Scorekeeping

The end-of-game screen is now a **tabbed results board** with real scorekeeping —
built for bragging rights, and for running a scored event.

- **Five tabs:** **Summary**, **Fleet**, **Air Wing**, **Quests**, and **Enemies**.
- **Objective scoring.** Every kill is credited to the ship (or pilot) that landed
  the final blow, and tallied three ways:
    - **Kills** — enemies destroyed.
    - **Tonnage** — naval-style "tonnage sunk," scaled by each hull's size, so
      bigger kills are worth more than swatting fighters.
    - **Damage dealt** — raw impact, so crews who soften targets without stealing
      the kill still show up.
- **Fleet** ranks each bridge ship (kills / tonnage / damage / hull remaining);
  **Air Wing** ranks each fighter & shuttle **pilot by call sign** (sorties / kills
  / tonnage / objectives). Bridge and cockpit credit never double-count.
- **Every game is saved** to a rolling history — with an even denser
  per-ship / per-pilot / per-quest breakdown than the screen shows.

!!! tip "Running a tournament? — for Convention Operators"
    Pair the scoreboard with **repeatable seeds** and a **shareable game code**:
    hand every crew the same code and they all play the **identical** map and enemy
    layout, then rank them by their **Fleet / Air Wing** boards (kills, tonnage,
    damage) for an objective result. The **Director** console gives you a
    spectator / big-screen view for the venue floor.

Details: [LegendaryMissions &rsaquo; Game features](legendarymissions/playing/features.md).

## 🎬 Quality-of-Life & Presentation

- **The Director console** (formerly Console View) — pair and rotate multiple
  views, with a cinematic mode for the big screen.
- **Shareable game codes** and per-map seed options so crews can replay the exact
  same setup.

Details: [LegendaryMissions &rsaquo; Game features](legendarymissions/playing/features.md).

---

## 🛠️ For Mission Makers & Tinkerers

!!! warning "For testing only — not an engine replacement"
    The mock GUI and headless runner exist to **test and debug missions outside
    Cosmos**. They are **not** a reimplementation of the engine, and **100% parity
    is not a goal** — many engine behaviors are approximated or absent by design.
    Please **don't file issues or feature requests asking for more engine parity**.
    If something must behave exactly like the engine, verify it in Cosmos.

- **Run missions outside Cosmos.** A full **headless test mode** plays a mission
  for N seconds and reports a pass/fail verdict with coverage — great for CI — plus
  a browser-based **mock GUI** with a 3D cinematic view and 2D radar.
  → [Testing missions](tooling/testing.md)
- **Web pages, written in MAST** — see above. → [Web pages](build/web-pages.md)
- **A coverage "exerciser"** that drives real gameplay (scans, torpedoes, docking,
  comms) to shake out routes automatically. → [Testing missions](tooling/testing.md)
- **A faithful mock simulation** calibrated to the real engine: ship speeds, 3D
  steering, per-facing shields, heat, energy, and a full weapons model (beams,
  torpedoes, drones, mines, EMP). → [Testing missions](tooling/testing.md)
- **`--use-working-tree`** to smoke-test local library edits, and **`--seed`** for
  reproducible runs. → [The `sbs` CLI](tooling/cli.md)
- **`signal_next`** — one-shot await of the next signal. → [Signals](api/procedural/signal.md)
- **An Artemis 2.8 → Cosmos porting-comfort layer** to ease bringing older content
  forward. → [Porting from Artemis 2.x](mast/porting-2x.md)
- **A faster, friendlier MAST compiler** — quicker parsing, *all* errors reported at
  once, sturdier crash handling, more Python built-ins available in scripts, and now
  **multiline expressions** (see below). → [The MAST language](mast/overview.md)
- **Deterministic building blocks** — keyed terrain fields, position-keyed
  [scatter](api/utility/scatter.md), and reusable game-code encode/decode.

!!! tip "✨ New — multiline expressions in MAST"
    Python dicts, lists, and function calls can now **span multiple lines**, just
    like Python. No more cramming a spawn onto one giant line or reaching for
    `~~ ... ~~` fences — write it the natural way:

    ```mast
    prefab_spawn("prefab_fleet_raider", {
        "race": "skaraan",
        "fleet_difficulty": 2,
        "START_X": fleet_pos.x,
        "START_Y": fleet_pos.y,
        "START_Z": fleet_pos.z,
    })
    ```

    Works for any bracketed expression — dict/list/call literals and multiline
    `if` conditions alike. Error line numbers stay accurate, and every existing
    script compiles exactly as before. → [The MAST language](mast/overview.md)

!!! tip "✨ New — colons inside quoted strings"
    A `:` inside a quoted string no longer confuses the parser, so you can write
    handler labels naturally — no more assigning the button to a variable first:

    ```mast
    on gui_message(gui_button("Test Upgrades:")):
        show_upgrades()
    ```

    Previously the `:` in `"Test Upgrades:"` was mistaken for the end of the
    `on ...:` header and the line failed to compile. The same fix applies to
    `await ...:` blocks, and button/text **labels** with colons
    (`gui_button("Score: 5")`) now render as text instead of being misread as a
    style key.

---

*Thanks for playing, building, and tinkering. There's more under the hood than ever
— go build something great.* 🚀
