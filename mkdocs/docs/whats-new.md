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

## 🪝 Grav-tether

A tractor beam for Weapons and fighters — one system, scaled by hull.

- **Weapons hold-click** any contact for a context menu: **Reel** cargo in (it's
  collected on contact), **Tow** a ship or derelict at distance, **Lock** for a rigid
  grab, or **Release**. The mode is chosen by what you grabbed.
- **Fighters** get a cockpit button with **nose-aim** targeting (it grabs what you're
  pointing at): reel salvage, or **swing** around an asteroid on a tether that holds
  your radius while you orbit. The button glows cyan while tethered.
- **Impulse only** (the canonical rule): a tether can't hold at warp — it caps you
  back to impulse, or optionally snaps and drops the load.

Built on the engine's native tractor, with the mock now simulating the pull so the
behavior is testable outside the game. API: [grav_tether](api/procedural/grav_tether.md).

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

## 🤝 Peacetime, with more than one ship

Bring a second ship to a peacetime patrol and a single **Quest Mode** (set on the map
panel) decides whether you cooperate or compete for the same board of jobs:

- **Co-op** — nothing is claimed. Deliver a barge and *every* ship holding that job is
  paid, and the multi-step arcs run for the whole crew together.
- **Protected** *(default)* — the moment you work a target it's **locked to you**. A rival's
  grav-tether is refused (*"claimed by another ship"*) and only you are paid. Friendly by
  default, nobody can spoil your job.
- **Claim-jump** — claims are **stealable**: the [grav-tether](api/procedural/grav_tether.md)
  becomes the competitive tool, letting you tow a rival's salvage out from under them.
  Payment follows whoever delivers, and each ship banks its **own** earnings for a
  top-earner readout.

The ownership, per-ship credit, and kill-attribution rules are all locked down by headless
conformance tests, so the guarantees hold without standing up five clients to check.

Player guide: [Multiplayer jobs](legendarymissions/playing/multiplayer-quests.md).

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

## 🛰️ Sensor Beacons & the Fabricator

Engineering has a new job. A **Fabricate** tab turns materials into gear over a **build
timer**, and its headline product is **Beacons** — a **fabricate-only** ordnance the
crew builds, hands to the tube, fires, and later flies over to **recover**.

- **A two-console loop, on purpose.** Beacons don't come pre-loaded — a ship spawns with
  **zero rounds**. Weapons *tells* Engineering what to build, Engineering **fabricates**
  it (spending inputs over a timer) and **delivers** it to the tube, and only then can
  Weapons fire it. The coordination *is* the gameplay.
- **Bio Beacons herd the [bestiary](#a-living-bestiary).** Program one to **attract** or
  **repel** a chosen space monster, fire it, and it broadcasts across the sector —
  baiting a Reaver into a minefield or shooing a Grazer off your six.
- **Sensor Beacons — the old Probe, brought forward.** The passive sensor-relay
  **Sensor Beacon** folds in Artemis 2.8's **Probe** concept. Ported 2.8 missions that
  stocked Probes come across as Sensor Beacons the crew can build and deploy.
- **Recover and reprogram.** Fly over a deployed beacon to add the round back and keep
  its program; **Science** can scan any beacon to read what it's broadcasting.
- **Recipes are data.** Every beacon (and any other craftable) is an **AMD recipe** —
  inputs, build time, and program — so a mission adds its own without touching the addon.

Authors: [Fabrication & Beacons addon](legendarymissions/addons/fabrication.md) ·
Porting Probes: [Porting from Artemis 2.x](mast/porting-2x.md).

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

## 🎭 Overlays — cards, HUDs & cutscenes on top of the view

A whole new **[overlay system](cosmos/overlays.md)** for drawing on top of a console's
page **and** its live 3D view — chapter cards, notifications, a modal choice, a live
HUD — that update **without repainting the page underneath**.

- **One-liners for the whole toolkit.** `overlay_hero("CHAPTER TWO", subtitle="…")` for
  a scene title (with a **face, ship, icon, or image**); `overlay_lower_third(name, line)`
  for someone speaking over the action; `overlay_banner`, `overlay_toast` (**toasts
  stack** — several coexist, each clearing on its own), `overlay_letterbox` and
  `overlay_flash` for a cutscene, `overlay_credits(..., roll=)` for rolling credits.
- **Aim it anywhere.** Every overlay takes `to` — the current console, one client, or a
  role set: `overlay_hero("FLEET ALERT", to=role("mainscreen"))`. Server story logic
  pushes straight to the players, or fires it with a one-line `//shared/signal` bridge.
- **A modal that returns a value.** `result = await overlay_choice("Fire?", ["Yes","No"])`
  — a full-screen card you can await, resolving to the button they pressed.
- **A live HUD over the view.** `overlay_hud(rows=…, controls=…)` floats a sticky panel
  over the 3D view; `overlay_hud_update` refreshes just its values, no repaint.
- **Author overlays as data.** Declare them in an `.amd` file and fire by key
  (`overlay_amd("ch2")`), and a **quest fires overlays on accept / complete / fail** to
  its participants — `Complete Overlay: convoy_saved` or an inline `On complete: hero
  CONVOY SAVED`, no wiring.
- **Your own cards, in pure MAST.** A `//overlay/<kind>` route builds a custom card with
  the usual `gui_*` verbs and registers itself — no Python:
  ```
  //overlay/briefing
      gui_face(face)
      gui_text(f"$text:`{name}`;font:gui-5")
  ```

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

- **[Rows and columns can size themselves](cosmos/gui_content_sizing.md).** Add
  `row-height: content` or `col-width: content` and a row is as tall as its text,
  a label as wide as its word — at every window size, with no percentages to
  maintain. `min-content` and `max-content` give finer control, and **`1fr` is
  now the default**: a column still shares the leftover space but is never
  squeezed below the widest word it has to show. (`1fr` is what CSS calls an
  equal share with a minimum; the older spelling `auto` still works.)

- **[`overflow:` for text that cannot fit](cosmos/gui_overflow.md).** Because the
  engine never clips, text too big for its box is drawn over its neighbours. When
  there is genuinely no space to give — a user-entered name, a fixed strip — a
  widget can now say `shrink` (step the font down), `ellipsis` (truncate with
  `...`) or `hide`. The default is unchanged, so nothing moves unless you ask.

- **Text no longer overlaps itself in a scrolling text area.** A `gui_text_area`
  measured its wrapping against the full width but drew 20px narrower to leave
  room for its scrollbar, so roughly one paragraph in eight gained a line the
  layout had not counted — and drew it on top of the next one. It also broke
  lines by *estimating* characters from an average glyph width, which ended lines
  short of the edge for no visible reason; it now wraps on measured words.

- **Sizes add up.** `row-height` and `col-width` accept full arithmetic —
  `1em+10px`, `62-25px`. A `+` or `-` term used to be **silently dropped**, so a
  layout could have been running with a size it never asked for.

- **Text no longer draws on top of the row below it.** Three separate causes,
  all now fixed: a content-sized column got the exact width its text needed and
  no more, so rounding tipped it into an extra line; raising one row to fit its
  text could starve its neighbours to zero height, and a zero-height row still
  draws; and a nested panel measured its own rows unwrapped, so it asked for
  less room than its content needed.

- **A list box no longer shrinks around its tallest row.** Slot budgeting divided
  the available space by the largest item, so a single tall row could halve how
  many rows a list showed and leave half the box empty. Rows are now packed by
  their real heights; a list with equal rows is unchanged.

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

## 🎨 Design a screen without writing the code — the GUI Editor

Lay out a console screen **visually** and it writes the MAST for you. Drag sections,
rows, buttons, lists and tables from a **palette**, size a section by dragging its corner,
rearrange the **tree**, and watch a live **preview** — then **Copy** the generated code or
**Insert** it into your `.mast` (it updates just a `# <gui-designer>` block if you have
one).

- **`*.gui.mast` files open *as* the editor** — the whole file is the screen, edited
  visually and saved back as MAST, with a one-click toggle to the raw text and back.
- **Round-trips** — reopen a screen and keep editing; your comments and anything the editor
  doesn't model are left untouched.

Docs: [The GUI Editor](tooling/gui-editor.md).

---

## 🛸 The old missions fly again

Every mission your crew ever flew in **Artemis 2.8** can come back into service. Hand
one over and it returns as a Cosmos mission you can host tonight: the same fleets
waiting in the same corners of the map, the same enemies with the same tempers, the
same voice cutting in over comms.

**All 27 missions in our archive made the crossing** — and not just far enough to
load. They play: hostiles pick fights, stations answer hails, the timers still run
out on you, and each mission still ends the way it always did.

- **The briefing is no longer a memory test.** The mission's goals arrive as real
  Cosmos [quests](build/quests.md), ticking over in the crew's quest log as you go —
  or, if you'd rather have the original exactly as it was written, you can have that
  instead.
- **Enemies remember they're enemies.** Old missions never spelled out who hated
  whom; that gets worked out and declared, so hostiles open fire, Science sorts
  friend from foe, and contacts show in the right colours.
- **The Game Master keeps the con.** Menus stay nested the way they were laid out,
  shortcut actions survive, and a spawn lands **where the GM is pointing** rather
  than in the corner of the map.
- **The details survive.** Elite Skaraan tricks, captains with a temper, fighters
  and shuttles in the hangar, science scans, hail text — the flavour comes with the
  fleet, not just the ships.

Anything the old script left genuinely ambiguous is written down for whoever finishes
the port, rather than quietly guessed at.
→ [Porting from Artemis 2.x](mast/porting-2x.md)

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
- **`sbs swap`** — keep several mission sets side by side and switch between them
  without copying anything (see below). → [The `sbs` CLI](tooling/cli.md)
- **`signal_next`** — one-shot await of the next signal. → [Signals](api/procedural/signal.md)
- **An Artemis 2.8 → Cosmos porting-comfort layer** (`a2x_*` in MAST, no import) plus
  [`arme2cosmos`](https://github.com/artemis-sbs/arme2cosmos), the converter that uses
  it — `pip install arme2cosmos`, stdlib-only, no Cosmos needed to *run the tool*.
  Emits either a declarative quest tree (`--target amd`) or a hand-editable MAST
  scaffold (`--target mast`), plus a `MIGRATION_NOTES.md` punch-list. The whole 27-mission
  reference corpus compiles and runs headless in both styles, 26 of them with zero
  leftover TODOs. → [Porting from Artemis 2.x](mast/porting-2x.md)
- **A faster, friendlier MAST compiler** — quicker parsing, *all* errors reported at
  once, sturdier crash handling, more Python built-ins available in scripts, and now
  **multiline expressions** (see below). → [The MAST language](mast/overview.md)
- **Declare addon dependencies** — `provides` / `requires` / `suggests` make
  cross-addon contracts explicit and compile-checked (see below).
- **Deterministic building blocks** — keyed terrain fields, position-keyed
  [scatter](api/utility/scatter.md), and reusable game-code encode/decode.

!!! tip "✨ New — `sbs swap`, switch mission sets in place"
    Cosmos loads exactly one `data/missions` folder. If you keep more than one set
    — a converted 2.8 port, a work-in-progress copy, the stock missions — you have
    been copying folders around. Instead, park each set beside it as
    `data/missions_<name>` and let `data/missions` be a link:

    ```
    sbs swap            # which set is active, and what else is available
    sbs swap amd        # load data/missions_amd
    sbs swap mast       # load data/missions_mast
    ```

    Any folder named `missions_<name>` is a valid target, so adding a set is just
    creating the folder. If your `data/missions` is a normal folder, the first swap
    renames it to `missions_cos` rather than deleting it, so `sbs swap cos` puts you
    back on the stock missions. Close Cosmos first — a running client holds files
    open under the link. → [The `sbs` CLI](tooling/cli.md)

    !!! warning "Back up your missions first"
        This moves and re-creates the `data/missions` link, and renames a real
        `data/missions` folder aside. It is written to never delete a mission
        folder — only the link — but it is rearranging the folder that holds all
        your work. **Take a backup of `data/missions` before your first swap**,
        especially if you have edits in there that aren't in source control.

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

!!! tip "✨ New — declare addon dependencies"
    Addons share one global namespace and load in no fixed order, so "this addon
    needs that one" used to be an unwritten rule that failed with a cryptic
    `NameError`. Now an addon states its contract at the top of its `__init__.mast`,
    checked at **compile time**:

    ```mast
    provides hangar.sortie_board
    suggests hangar        # optional: warn if absent, never fail
    requires gamemaster    # hard: fail the build if it's not loaded
    ```

    A `requires` not satisfied by some loaded addon's `provides` **fails the
    compile** (caught by `sbs lint` / `--test`, and shown as a runtime error screen);
    `suggests` only logs a warning. Checking is **order-independent** and fully
    backward compatible. → [The MAST language](mast/overview.md)

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
