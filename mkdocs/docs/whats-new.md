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
- **Rearming takes time.** A craft's refit now runs longer the more torpedoes it
  has to reload — every empty tube adds time (tunable per dock), so a bomber that
  spent its payload turns around slower than one that never fired. Fit the new
  **Torpedo Autoloader** upgrade to cut that per-torpedo cost.

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

## 🕵️ Peacetime Remastered — a mission written in AMD

**Peacetime Remastered** is a border-patrol shift that doubles as a worked example of
authoring a whole mission as **data**. Almost everything the crew sees — the story, the
job board, the cast, the clues, even the chatter — is declared in one `.amd` fact-sheet;
MAST holds only the *logic* that reacts to it.

| What the crew sees | Authored as |
|---|---|
| The **Ambassador Florbin kidnapping** | a **quest tree** — take the case, identify the kidnapper, subdue, recover |
| The **cast** (a deck chief, the Admiral, the Ambassador…) | **lifeforms** — hosted contacts appear as comms **badges** you hail |
| The **40 allergy clues** | generic **AMD records** — each heading is a container the ambassador could hide in, its body the clue |
| The Ambassador's **passenger complaints** | a **chatter line-pool** — one picked at random |
| Briefings, cargo manifests, interview reports | **prose templates** filled in at send time |
| **Object scans** (cargo ships, anomalies) | dialogue-native scans (`Scan of:` / `Tab:` / `%` variants) |
| The **job board** — gunnery, rocks, poacher, mercy, customs, survey | **quests** with goals, rewards, and fail triggers |

**The job board is a pick-up-work board.** Every job starts **idle** — shown as
*Available* — and the crew **Accepts** the ones they want from the Quest Log. Accepting is
when a job's clock starts *and* when its targets spawn, so a timed rescue gives you the
full window (the Mayday arrives, then the shuttle) and nothing clutters space for work
nobody took. Weapons stays busy in peacetime: qualify on drones, break hazard rocks, and
**disable — don't destroy** a poacher.

Under the hood the whole kidnap mystery is built by a **pure, seeded Python core** — one
kidnapper, the Ambassador hidden in exactly one cargo hold, a decoy-laced clue trail —
that is **unit-tested over many seeds**, so the puzzle is always solvable however the dice
fall.

Authoring reference: [Quests](build/quests.md) · [Sides, lifeforms & faces](build/sides-lifeforms.md).

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
  and **breeds** — with the sentient Stage 4 hailable to calm or enrage. BioMechs are a
  reusable [addon](legendarymissions/addons/biomech.md) you can drop into any mission.

Bosses are **data-driven and folder-scanned** — each is a small file in `maps/bosses/`,
so authoring a new one is just dropping in a file.

Playing & hosting: [LegendaryMissions](legendarymissions/index.md) ·
Authors: [Writing a Siege boss](legendarymissions/script/bosses.md).

## 🐙 A Living Bestiary

Space monsters are no longer just one hostile Typhon. The **Monsters** map option
now seeds a **weighted mix of species** — some deadly, some harmless, some that
actually *help* you — and a Game Master can drop any of them from the spawn menu.
**Scan** an unknown creature and its science readout tells you what it is before you
decide to shoot.

- **Seven new species over one behaviour:**
  **Reaver** (fast hunter that *enrages* — faster and redder with every wound),
  **Ravener** (an apex predator that **feeds on weapon fire** — beams and torpedoes
  only heal it; the one thing it can't eat is a black hole),
  **Grazer** (a placid drifter that's **tame unless provoked**, then turns on you),
  **Bulwark** (colossal, inert living reef — harmless unless you ram it),
  **Sparkfeeder** (a docile creature that **recharges your ship's energy**),
  **Siphon Leech** (its parasitic twin — **drains** energy, non-lethal), and the
  **Warden** (a friendly guardian that hunts *raiders*, never you).
- **Every monster has an age.** Individuals spawn **Young**, **Mature** or **Ancient** —
  older ones are tougher and larger (age never changes the damage they deal), and an
  aged Ancient eventually seeks out a **black hole** to die.
- **Black holes bite again.** Player ships *and* fighters that drift into a black
  hole's pull are now reliably destroyed — no more bobbing at the edge or warping
  free (fixes the long-standing "black holes don't kill" bug).

Authors add a species by dropping in a prefab file over `behav_typhon`; the roster
and mix live in one weight table.

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

## 🤖 Attract Mode — the ship flies itself

Flip on **Auto Play** (`AUTO_PLAY: enable: true`) and every bridge runs itself — a
great **lobby / attract screen** or hands-free demo. The autoplayer doesn't just
wander and shoot; it plays like a coordinated crew:

- **Stand-off alpha strike.** Against an enemy at range it holds at **5000u**, opens
  with an **EMP** to strip shields, then a **single Nuke**, waits for the blast to
  clear, and only then closes to **mop up with beams and homing torps** — so it never
  catches itself in its own explosion.
- **Fires only what it has.** It reads real magazine counts and launches only loaded
  types — no more phantom Homing torpedoes once the tubes run dry — and it **won't
  friendly-fire**: area torps are held whenever an ally sits in the blast, and
  **wrecks get beams only**, never torpedoes. A **PShock** finishes a target whose
  shields are down.
- **Talks like a crew.** It hails enemies to **taunt** them with the *right* line — the
  one an **intel scan** reveals — **demands their surrender** once shields drop, and at
  the start of a match asks friendly **stations to build Nukes** to keep itself armed.
- **Plays engineer.** It **overpowers drive and weapons** for a faster, harder-hitting
  ship and **balances the heat with coolant**, easing off when energy runs low.
- **Survives sensibly.** It **flees lethal terrain** — steering clear of a **black hole's**
  pull well before it's caught in the well — **docks to repair** when hurt, and if its
  **maneuvering is shot out** it **holds station** to keep fighting instead of burning off
  into deep space.

Turn it on — and tune its **stand-off range** and **engineering overpower** — in
[LegendaryMissions](legendarymissions/index.md) settings.

## 🤝 Friend or Foe — decided by Diplomacy, not by labels

A deep pass reworked how the game answers one deceptively simple question: *"is this
ship a friend or an enemy?"* It used to be answered by **hardcoded role labels** —
`raider` meant "the bad guys" and `tsn` meant "the good guys" — an assumption quietly
baked into targeting, victory checks, docking, comms, loot, and quests. Now those
questions are answered by **diplomacy**: the actual **side relationships**. A side's
*name* no longer decides its allegiance.

What that unlocks:

- **Runtime ceasefires & alliances that actually stick.** Negotiate peace with a
  hostile faction and it *really* stops being a target — your fleets break off, its
  ships stop counting as "enemies remaining," you can claim its systems, and killing
  it no longer pays a bounty. Ally with a faction and its bases count as **your**
  friendly bases.
- **Many enemy factions, not one lump.** Enemies can field their **own faction
  sides**, each independently at war or at peace — instead of everyone sharing a
  single "raider" side.
- **More than one player side.** Co-op or rival player factions work without
  assuming everyone is `tsn`: friendly stations, escorts, and win/lose conditions
  all derive from **who the players actually are**.
- **Quests that mean "enemies," not "raiders."** A kill objective can be authored as
  **`destroy N enemies`** — faction-agnostic and ceasefire-safe — right alongside the
  familiar `destroy N raiders`.

For authors it arrives as a symmetric **sides & diplomacy vocabulary** — ask
`side_are_enemies` / `side_are_friendly`, or grab the whole set of what's hostile (or
allied) to a ship or to the players — so you never hardcode `role("raider")` or
`role("tsn")` again. Every stock single-side mission plays **exactly as before**; the
new reach is there when you want it.

Docs: [Sides & Diplomacy](api/procedural/sides.md).

## ⚡ Smoother with big fleets

Large battles used to **stutter on a beat**. Every few seconds the game processed
**every NPC brain in a single frame** — then, on another beat, **every mission
objective** — so the frame time spiked periodically. The bigger the fleet, the
bigger the hitch.

That work is now **spread evenly across frames**. Each brain and each objective
still updates on the same schedule as before — the AI is exactly as sharp and
reacts just as fast — but instead of one big burst, the load is smoothed out tick
by tick. On a busy Siege those **periodic frame spikes are largely gone**, and it
**scales far better** as fleets grow. Nothing to configure; every mission gets it
automatically.

!!! note "For tinkerers — how it works"
    Per-tick work that iterated a whole set at once (all brains, all objectives)
    now runs a **rolling slice** each tick, sized by a shared `RollingSlicer` so a
    full pass still completes in the same period regardless of set size or tick
    rate — same cadence and total cost, no batch spike. If you're chasing a
    `mission_tick` that overruns its budget, the engine's **`Elapsed time`** log
    line now prints a **per-phase breakdown** (`dispatch_tick` / `gui_present` /
    `gc` / …) so you can see exactly which subsystem caused a given spike.

---

## 📋 Richer GUI — tables, and text that does more

- **[`gui_table`](cosmos/gui_table.md).** Describe a table as **rows + column
  specs** and get back a real, selectable, scrollable list box with the columns
  **auto-sized to their content**. Cells aren't just text — a column `type` can be a
  **checkbox, dropdown, input, or button**, and interactive cells write straight back
  to the row and fire an `on_cell_change` callback. An editable data grid in one call.

- **[`gui_list`](cosmos/gui_list.md) — design your own rows, in pure MAST.** When a
  row needs more than columns (a picture, a button, two lines), write the row *once*
  as a `with` block and it repeats for every item — scrolling and selectable, no
  Python helper required:
  ```
  with gui_list(ships, select=True) as ship:
      gui_text("{ship.name}")
      gui_button("Hail"):
          jump hail
  ```
  Keep the handle to read what they picked: `ship_list.get_selected()`.

- **[`gui_grid`](cosmos/gui_grid.md).** `with gui_grid(3):` arranges items in even
  rows of N — a palette of buttons or a board of tiles — breaking to the next row
  for you. Great with a `for` loop.

- **Pipe tables, links & rules in `gui_text_area`.** The rich-text area learned a few
  new tricks in its mini-markdown:
    - **GFM pipe tables** — `| Ship | Hull |` with a `|:--|--:|` alignment row —
      render as a real grid, columns sized to fit.
    - **Hyperlinks** — a `[Torgoth](ref://torgoth)` line becomes a clickable link that
      **navigates within the same document** (give the area a `link_resolver`), so a
      Kralien entry can link straight to the Torgoth one. Perfect for a codex.
    - **`<hr>`** draws a horizontal rule.

- **Text areas use their full width.** A long-standing measuring bug made
  `gui_text_area` wrap text at roughly **60%** of the available width; it now measures
  properly and fills the space.

---

## 🐞 Debug your mission — pause it and look inside

Ever chased a bug by sprinkling `print` lines and replaying? Now you can **pause your
mission while it plays and look inside it** — right in VS Code. Put a **pause point** on
any `.mast` line, play your mission, and it stops there: the exact line, every value your
story is tracking, and how it got there. Then step through one line at a time and watch it
unfold.

- **One click.** Pick **"MAST: Debug mission (one click)"** and press play — the mission
  launches with its game window, you set pause points and debug, and pressing **Stop**
  shuts it all down. No terminals, no leftover processes to hunt for.
- **Proper debugging tools.** Pause points that stop **only when a condition is true**
  (`hp < 20`), on the **Nth hit**, or that **just log a note without pausing**; step
  over / into / out; a live **Variables** panel (Task / Shared / Global) you can **edit
  while paused**; a **call stack**; and **watch** expressions.
- **Step into the engine.** On a line that calls a built-in like `terrain_to_value(...)`,
  **Step Into** drops you into the engine's own Python — real source and its values — then
  Step Out brings you back to your story. Even library code that ships **zipped** shows its
  source.

It costs **nothing** when you're not debugging — normal mission runs and the shipped game
are completely unaffected.

Docs: [Debugging your mission](tooling/mast-debugger.md).

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
- **An in-game Avatar Editor** — an opt-in addon that customizes a character face
  **inside Cosmos**, with a **live `gui_face` preview** that updates as you move the
  sliders (unlike the extension's blind builder). Pick a race, tweak each feature,
  and the face is **copied to your clipboard** on every change — paste it straight
  into a `.amd` `Face:` field. → [Avatar Editor addon](legendarymissions/addons/avatar.md)
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

!!! danger "⚠️ Don't call `sbs.delete_object` — use `delete_object` instead"
    Deleting an object with the raw engine call **`sbs.delete_object(id)`** is a
    known way to **crash Cosmos to the desktop**. Delete through the procedural
    **`delete_object(id)`** (or **`obj.delete_object()`**) instead:

    ```mast
    # ✗ risky — frees the object immediately
    sbs.delete_object(DAMAGE_TARGET_ID)

    # ✓ safe — tombstoned now, freed safely later
    delete_object(DAMAGE_TARGET_ID)
    ```

    **Why it crashes.** `sbs.delete_object` frees the native C++ object — and its
    `engine_object`/`data_set` pointers — **the instant you call it**. But MAST
    tasks run **interleaved across a tick**: another task (or even the next line,
    in a different task) may still be holding that object. When it touches the
    freed object it reads dead memory — a **use-after-free** that crashes to the
    desktop, or, if the memory slot has been reused for a new object, **silently
    corrupts** that unrelated object and crashes later somewhere else.

    **Why `delete_object` is safe.** It **tombstones** the object immediately —
    `object_exists()` and `to_object()` report it gone at once, and it stops
    ticking — but **defers the actual native free** to the end of the event
    handler, once every task for that tick has finished. So a reference held
    elsewhere this tick still points at valid memory instead of crashing. It also
    **does nothing if the object is already gone**, so a double delete can't
    double-free. Scripts that already use `delete_object` / `obj.delete_object()`
    need no change — only direct `sbs.delete_object` calls should be swapped.

---

*Thanks for playing, building, and tinkering. There's more under the hood than ever
— go build something great.* 🚀
