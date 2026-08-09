# What's New in v1.4.0 ✨

A whirlwind tour of everything that landed in v1.4.0 — across the
**LegendaryMissions** content and the **sbs_utils** library that powers it. Links
go to the relevant docs.

---

## ⚠️ The `races` add-on — add it to your `story.json`

**This one needs action.** Ship interiors and fleet compositions used to be built into the
game; in v1.4.0 they ship as **per-race add-ons**, and a mission has to ask for them.

If your mission loads LegendaryMissions' `ai` or `fleets` add-on, add one line:

```json title="story.json"
"artemis-sbs.LegendaryMissions.races.v1.4.0.mastlib"
```

**Leave them out and two things break quietly.** Your player ship gets a **dead
Engineering console** — no system nodes, no damcons, no internal damage — and
`fleet_create` finds no ladder for any race, so **nothing raids you**. Neither failure
prints an error, which is exactly why it is worth checking now.

New missions from `sbs create` already include it.

**What you get in return** is content that was previously unreachable. Interiors lived in
the engine's own `data/grid_data.json`; fleet ladders were Python literals behind an
`if race == "..."` chain. Now a race owns both, `"random"` picks from the races that
actually registered, and **a new race joins the rotation by existing**. Two settings —
`PLAYABLE_RACES` and `NPC_RACES` — turn races off per mission.

Every hull that declares an interior now has one, so ships that were never really
flyable — Kralien, Torgoth, Skaraan, Biomech and the pirates — have a working Engineering
console for the first time.

See [The races add-on](build/race-addons.md).

---

## What you already have, working differently

Everything in this part is something a v1.3.0 crew or mission already has, met again
the moment you launch — and a few of them change what your mission looks like whether
you ask for them or not. After these come the things that did not exist before.

---

## 📻 The text waterfall is gone — say hello to the ship's log

**This one changes what your mission looks like whether you opt in or not.** The engine
never wrote to the waterfall, script could not control its background, and no mission
could style it. It has been removed from every console and replaced by a log with two
halves, fed by one record:

- **The strip** — one line, the newest message, where the waterfall used to sit. Always
  visible, no interaction, read at a glance.
- **The tab** — the history, in the info panel: scrollable and filtered into **Log**,
  **Ship** and **Mission**.

Newest is **first** in both, so the latest line never moves.

You write to it exactly as before — `comms_broadcast(...)` — with two new optional
arguments: `category` picks the tab (everything still shows in **Log**, so a filter can
never hide a message), and `severity` (`tip` / `warning` / `danger`) renders the line as a
coloured callout.

**The corner toast retired into the same log.** `overlay_toast()` and the `toast <text>`
quest directive still work and still compile — they write a log line instead of drawing a
card. `announce(level="status")` and `level="minor"` draw no overlay at all now. They were
the one pair of levels carrying information on a surface that kept no record: a console
that connected a second later never saw it.

**Nothing seizes the console.** An urgent line does not switch the info panel to the log
tab — the strip already shows it, in its severity colour, everywhere. A mission that wants
the interrupt sets `RAISE_ON = ("danger",)`.

Docs: [Messages & the ship's log](build/messages.md), [Overlays](cosmos/overlays.md).

## 🗂️ Console tabs stop drawing over each other

The tab strip divided a fixed width evenly, so more tabs only ever meant narrower tabs —
and the engine does not clip text, it draws it anyway, over the neighbour. Every tab was
present, clickable and illegible, which is why *adding* a tab broke ones that already
worked.

Eight tabs are shown; the rest go behind a **`More (N)`** menu that behaves exactly like
clicking a tab. BACK is never overflowed. Nothing to configure.

See [The console tab strip](build/players-consoles.md#the-console-tab-strip).

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

- **[`col-width: square`](cosmos/gui_content_sizing.md#square-as-wide-as-it-is-tall).**
  A column as wide as the row is tall. The other keywords derive a width from the
  column's own content; this one derives it from the *other axis*, which is what a
  portrait, an icon, a ship render or a badge nearly always wants. `gui_face` and
  `gui_icon` were already square; **`gui_ship` and the image widgets were not** — so a
  ship placed beside text used to flex and take half the row. Now they all say the
  same thing.

    **Behavior change**: `square` and an explicit width are mutually exclusive, and
    setting either clears the other. A square column that *also* carried a width used
    to be counted twice when the row was divided up, so the row reserved its space
    twice over and — since the engine never clips — drew the surplus over and outside
    its neighbours. If a screen of yours puts a `col-width` on a face or an icon, it
    now gets the width it asked for instead of that double-count.

- **[`overflow:` for text that cannot fit](cosmos/gui_overflow.md).** Because the
  engine never clips, text too big for its box is drawn over its neighbours. When
  there is genuinely no space to give — a user-entered name, a fixed strip — a
  widget can now say `shrink` (step the font down), `ellipsis` (truncate with
  `...`) or `hide`. The default is unchanged, so nothing moves unless you ask.

- **[`layer:` — paint order you can set](cosmos/gui_layer.md).** The other half of
  the same problem. `overflow:` changes the *text*; `layer:` changes what is drawn
  *on top*. Raise a row or section's background above its neighbour's content and an
  overflowing string is simply covered — not clipped (the engine cannot clip), but
  invisible, which is what a player cares about. It cascades like `color` and `font`,
  so one declaration can raise a whole panel. Two fixes came with it: a background
  could not be lifted above content at all before, and `gui_image` was **silently
  discarding** any `draw_layer` you gave it. Opt-in — a layout that never says
  `layer:` is byte-for-byte unchanged.

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

## 📜 The Quest Log says something new

Every row used to be the same square, over a caption repeating the state the square's
color already showed. Now the **shape is what the thing is** — job, objective, beat, arc
— and the **color is what state it's in**: two facts in one glyph.

The second line has to earn its place. It says how far along you are (`2 of 6`), what a
job pays while it's still a choice (`Reward: 120 credits`), or how long is left
(`1:30 left`) — and falls back to the state only for **Done** and **Failed**, where the
state *is* the news.

Quests written before kinds existed still render; they just say less. And because every
glyph is asked for by name, a mission that ships its own icon sheet re-skins the whole
log without touching a line of it.

## 🧭 Quests & Stories

- **A signal-driven quest engine** with kill / collect / scan / dock / reach /
  arrive triggers and real rewards — all **authored in simple AMD files**.
- **A proper Quest Log** you can accept and abandon quests from.
- **Multi-step bridge stories** that unfold a step at a time.
- **Quest-driven end-game.** A mission is now a **tree of quests** — a parent mission
  with children marked **required** (must finish to win) or **fatal** (fail one and the
  game is lost). Quests carry a **Win:** / **Lose:** outcome and a **`Fails when:`**
  trigger (a signal fires, a target dies, a timer expires), so the whole win/lose
  condition is **authored in AMD**, not hand-wired in script. The Siege bosses hang
  their objectives on the siege's mission tree with **`Part of:`**.
- **A quest log that isn't a spoiler.** `Show:` says *when* a quest is listed, apart
  from when it runs — so a story beat can drive its event unseen and appear once it has
  happened. A converted 2.8 mission went from **48 rows of story** to **9**: the six
  things the crew can act on, and history accruing underneath.

Docs: [Quests](build/quests.md).

## 💱 Items & Upgrades

**One pickup can be worth several units.** `item_spawn(key, x, y, z, qty=24)` stamps a
quantity on the pickup and collecting it credits the lot. A job wanting 24 salvage used
to mean 24 collectibles scattered across the map — object churn, and a tedious flight
rather than a pickup. Pickups that don't ask for a quantity are unchanged.


- **Discoverable items and upgrades** driven by a data registry — collect them in
  space and activate them through a generic **Upgrades GUI**.

Docs: [Items & Upgrades](build/items-upgrades.md).

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

- **Seven new species over one behavior:**
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

Who owns a job, who gets paid, and who gets credit for a kill are firm rules rather than
best effort — they hold however many ships are flying.

Player guide: [Multiplayer jobs](legendarymissions/playing/multiplayer-quests.md).

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

## 🚢 Fleets, written down at last

Fleet ladders became per-race data in v1.4.0, but how you actually *spawn* one was folklore.
Now documented: **[Fleets & raiding](build/fleets.md)** — `prefab_fleet_raider`, what a
variant is, per-faction sides via `faction_side`, and the difficulty encoding, which has two
forms nobody guessed:

| You pass | You get |
|---|---|
| `0` | the mission's `DIFFICULTY` setting |
| `200` | `DIFFICULTY + 2` — a *relative* offset |

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

## 🏷️ Icons have names now

`gui_icon("icon_index:111;")` asked you to remember that 111 is a wanted poster. Every
one of the built-in sheet's **176 glyphs now has a name**, and there is one call that
takes one:

```python
gui_icon_name("quest.job", "#cc0")
```

Two kinds of name, and the difference is the point. A **look** — `square`, `bell`,
`wanted` — is what a glyph *is*. A **meaning** — `quest.job`, `quest.state`,
`list.expand` — is what it's *for*, and points at a look. Ask for the meaning, and
re-pointing it changes every screen at once.

The same names reach **your own art**. Register a cell of your sheet under a look and it
wins over the built-in one:

```python
gui_icon_add_atlas("wanted", media_shared("icons/quest-sheet"), 0, 0, 64, 64)
```

Every `gui_icon_name("quest.job")` in the game now draws your art — **with no edit to the
code that draws it**. Screens can be written before their art exists, and an add-on can
re-skin screens it doesn't own. An unknown name draws *nothing* rather than a plausible
wrong glyph, because a wrong icon looks deliberate.

Claiming a look is deliberate: only the **icon domain** re-skins, so an ordinary image
that happens to be called `square` or `flag` can't silently change every state pip in the
game.

**Or write the sheet as a fact sheet.** An `## [Icons]` section registers the same keys
with no Python — the sheet, the cell size and the domain are written once on the section,
so an entry is a single line:

```amd
## [Icons](icons)
---
icons
Sheet: icons/quest-sheet
Cell: 64
---

### [Job](wanted)
---
At: 0, 0
---
```

The same section type registers **any** atlas, not just icons — a card deck or a set of
console backdrops is the same format with a different word (`images`, `art`) and its own
`Domain:`. `sbs lint` checks them: a sheet that isn't on disk, an `At:` with no `Cell:`
to measure against, a cell off the edge of the sheet. All three used to draw a blank
widget with no error anywhere.

The whole named set, with pictures: **[Icons by name](cosmos/gui_icons.md)**.

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
  friend from foe, and contacts show in the right colors.
- **The Game Master keeps the con.** Menus stay nested the way they were laid out,
  shortcut actions survive, and a spawn lands **where the GM is pointing** rather
  than in the corner of the map.
- **The details survive.** Elite Skaraan tricks, captains with a temper, fighters
  and shuttles in the hangar, science scans, hail text — the flavour comes with the
  fleet, not just the ships.

Anything the old script left genuinely ambiguous is written down for whoever finishes
the port, rather than quietly guessed at.
→ [Porting from Artemis 2.x](mast/porting-2x.md)

## 🎬 Quality-of-Life & Presentation

- **The Director console** (formerly Console View) — pair and rotate multiple
  views, with a cinematic mode for the big screen.
- **Shareable game codes** and per-map seed options so crews can replay the exact
  same setup.

Details: [LegendaryMissions &rsaquo; Game features](legendarymissions/playing/features.md).

---

## Now the new things

None of this existed in v1.3.0, and none of it is required — a mission that adopts
nothing here still runs exactly as it did.

---

## ✍️ AMD — write the mission, don't program it

**AMD** is the new way to author content: a mission's jobs, characters, places and
story beats are written as plain **fact sheets**, in the words you would use describing
them to someone. No script, no wiring — you say what a thing is, and it behaves that way.

**A record says what it is, and that decides how it behaves.** A `Beat` is a moment the
crew lives through — it runs unseen and appears in the log once it *has* happened, as
history. A `Cue` is a stage direction: it fires and is never listed. An `Arc` is the
heading over a run of beats. A `Job` is taken by a ship; an `Objective` is the crew's.
The word you choose carries the rest:

```amd
# [The Coils Overheat](ramscoop/coils)
---
Beat
Done when: signal ramscoop_online
---
Engineering reports the coils running hot.
```

**One grammar answers three questions.** `Starts when:` / `Done when:` / `Fails when:`
all take the same thing — `signal X`, `destroy 6 raiders`, `reach 6, 4`, `5 minutes`,
`all dead convoy`, `accepted`, `revealed`. Learn it once and you can say when anything
opens, finishes or fails.

**`Reward:` and `Penalty:`** say what a job pays and what failing it costs — so a timed
job with something at stake is two lines.

**Traits — what a record ALSO does.** A worldlet is a *Landmark* that happens to yield
ore; that second half is a trait, not a new kind of thing:

```amd
Landmark
Also: economy
Yields: ore 8
Reserve: 4000
```

Two traits ship: **`economy`** (`Yields:` `Reserve:` `Price:` `Costs:` `Time:`) and
**`reputation`** (`Values:` `Standing:` `Reliability:` `Rival when:`). A Side and a
Character are always regarded some way, so they carry `reputation` without asking;
`Also:` is for the optional half.

See [The AMD file format](build/amd-format.md).

## 🎞️ AMD prose reads like a screenplay

The fact sheets were only half the file. The other half is the **prose**, and it learned
six marks — borrowed from Fountain, the screenplay format, and Obsidian, where linked
notes come from. A line the format does not recognize is still prose, always, so nothing
you have already written changes.

**A scene can hold a conversation.** The speaker's cue goes in the body, the way a
script writes it, so one scene carries as many voices as it needs:

```amd
@Ashfang
% You're a long way from friends, captain.

@Vell (comms)
(shaken)
He means it, captain.
```

`(shaken)` is how the line is delivered — write anything you like. `(comms)` is *where*
it is delivered, so who-says-what-and-where is decided in the script instead of in code.

**Prose can point at things.** `Talk to [[cmdr_vell]] before you reach
[[ds1|the station]].` These are real references, so Find All References, Rename and the
Story Graph all see them — and a link to something you have not written **is not an
error**:

```
$ sbs lint <mission> --missing
3 thing(s) referenced but not written yet:
  cmdr_vell
      linked from `brief`   story.amd:6
```

Draft the whole mission as prose, link freely to scenes that do not exist yet, and let
the linter hand you the list of what to write next. In the editor each one gets a
**Create this record** quick fix.

**And three smaller ones.** `= a note to yourself` records what a beat is *for* — it
shows in hover and the outline and never reaches a player. `/* ... */` cuts a scene
without deleting it. `> [!WARNING]` gives an in-fiction document in-fiction formatting.
In a cutscene, `FADE IN:` and `> CUT TO:` say how a shot arrives without appearing on
screen — so a cutscene file reads as a screenplay and is still the shot list the engine
plays.

See [Writing the body](build/amd-format.md#writing-the-body).

## 💀 `Drops:` — what a kill leaves behind

Loot is authored now, keyed by **role**, because what a ship drops follows from what it
*is*:

```amd
### [Raider](raider)
---
Drops: salvage x2-4, contraband 20%
---
```

The defaults stay the defaults — a mission that authors nothing behaves exactly as
before. What changes is that an author can *see* the answer and change it, instead of a
condemned hulk on a live-fire range leaving contraband because it happens to be spawned
hostile. `Drops: none` means **this one drops nothing**, which is not the same as having
no table at all, and `sbs lint` flags a drop key that names no item.

See [What a kill leaves behind](build/items-upgrades.md#what-a-kill-leaves-behind).

## 📍 Markers — naming a place

"Clear the asteroids in the shipping lane" needed the crew to know which asteroids, and
prose written at authoring time could only name coordinates that go stale. So put the
place **in the world** instead: `marker_area` for a region, `marker_point` for a spot,
and `marker_object` for a spot the crew has to select.

See [Naming a place](build/world-building.md#naming-a-place).

## ⏳ A deadline you can hear coming

A job with a `Fails when:` clock **calls in as it runs down**, on comms, rather than
counting itself out silently on a tab nobody is looking at. Marks are absolute — 5:00, 2:00, 1:00,
0:30 — filtered to the ones that fit under the deadline, so a six-minute job gets four
reminders and a forty-five-second one gets two.

Who speaks is whoever the job asked for: `Speaker:` outright, else `Held by:` when it can
talk (a station's job speaks with the station's face for free), else the mission's
registered dispatch voice — and **silence** if none of those resolve, because a reminder
from nobody is worse than no reminder. `Signal says:` gives it words, with `{time}`
interpolated, so an automated beacon sounds like one:

```amd
Speaker: shuttle_pilot
Fails when: 6 minutes
Signal says: LIFE SUPPORT CRITICAL. {time} TO FAILURE.
```

See [Deadline reminders](build/quests.md#deadline-reminders).

## 🗣️ Characters who ask, and leave if nobody comes

A quest could always count down. It just did it **in silence** — you learned the
ambassador had given up when the fare quietly vanished from the board.

An **urge** is what an actor keeps asking for: a condition, a cadence, and a pool of
authored lines. Anyone can hold one — a passenger, a station, a whole side.

- **The stakes stay in the quest.** An urge declares no consequence of its own; it is the
  voice of a quest that is already counting down. One clock, one place to tune, and
  deleting the urge costs the drama but not the mechanics.
- **The countdown IS the drama curve.** Write `%` while there is time, `%%` as it runs
  short, `%%%` at the end, and `Escalates: with deadline` reads the quest's own clock.
  The number of markers is the curve; `Fails when:` is the tempo. Nothing has to agree
  with anything else.
- **They know when to shut up.** A per-actor floor stops one character monologuing, and a
  global floor stops five of them piping up the moment a jump makes them all eligible —
  shared with mission dispatch, so nobody talks over the Admiral. Only something urgent
  (`Weight: 90`) jumps that queue.
- **A station can hold a quest now**, which is what lets a resupply run have a deadline
  and a cost that lands on the world instead of on whoever happened to fly past.
- **Standing is a consequence.** `Reward:` and `Penalty:` take
  `earns <faction> <pole> <n>`, so finishing a job — or abandoning one — can move how a
  faction feels about you, not just what it charges.

In Open Universe, **Doctor Voss** now waits on the docking ring at her pickup, asks more
insistently as her window closes, and takes a berth on someone else's freighter if nobody
comes. In Legendary Missions, **Ambassador Florbin's** famous passenger requests are the
same character, rewritten as five lines of data instead of a hand-written loop.

API: [urge](api/procedural/urge.md).

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

## 🖥️ "On screen" — science can finally answer the captain

The captain says *"on screen"* and, until now, nobody could make it happen. A drop-down
beside the science console's **Follow** checkbox hands the ship's main screen a shot of
whatever science has selected.

```
[x] Follow   [ On Screen - Orbit   v ]
                Off
                On Screen - Dolly
                On Screen - Orbit
                Tactical 2D
```

**Dolly** pushes slowly in and out, **Orbit** turns around the contact, and **Tactical
2D** puts the radar on it. Change the selection and the shot follows; destroy the
contact and the viewer stands down.

Beside the picture is a **data column** carrying what science actually knows: vitals
(range, bearing, shields, hull), **every scanned tab together** — Scan, Status, Intel,
Materials, Bio — recent comms with that contact, and any quest bound to it. It pages
itself when there is more than one screenful, and skips pages that have nothing to say.
A mission adds its own page with `viewscreen_page_register`.

Nothing has to be co-ordinated with helm: the viewer writes the same main-screen state
helm's own control does, so **last writer wins** — helm reaching for the control simply
takes the screen back, and the drop-down falls back to *Off*. It is scoped per ship, so
science on one bridge cannot change what another's crew is looking at.

!!! warning "Writing your own main-screen console?"
    While a shot runs, the console is **assigned to the subject** — the engine only
    honors a camera change when the console and the lens ride the same object. So
    `sbs.get_ship_of_client()` on a main screen answers with *the contact being filmed*.
    Use `viewscreen_home_ship(client_id)` for "this console's own ship".

See [On screen](cosmos/viewscreen.md).

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

Built on the engine's native tractor.
API: [grav_tether](api/procedural/grav_tether.md).

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

## 🎛️ The Control Gallery — every widget, running, with its source

Stop guessing what a widget looks like. The **[Control Gallery](cosmos/control-gallery.md)**
is a mission you start: **54 entries in six categories**, each one live on screen with
**the code that built it directly underneath**.

- **The snippet cannot be out of date**, because it is not a copy. It is sliced out of
  the mission's own file at runtime between two comment markers — so what you read is
  literally what drew the thing above it. **Copy** puts the real line on your clipboard.
- **It opens on the server screen.** No console to pick, no ship needed. Start the map
  and browse.
- **A Traps category**, which may be the most useful part: mistakes that produce a
  *plausible* screen and therefore survive review — a `1em` row under a bigger font,
  padding eaten out of the row height, a starved `content` row, `update()` quietly
  dropping the rest of your style string, a handler built in a `for` loop that captures
  the wrong item. Each runs **broken and fixed side by side**.
- **A layout playground** where dropdowns set `row-height`, `col-width` and the font and
  the boxes move under you — sizing is one of those things you have to push around
  rather than read about.
- **"Take the tour"** walks all 54 entries, narrating each through the overlay system's
  own lower third — the gallery introducing itself with the feature it was originally
  built to demo.

One entry is a record in a `.amd` file plus a marked span in the code, joined by a key,
so adding to it costs nothing.

```
sbs debug control_gallery --map 0     # then http://localhost:8765/server
```

Docs: [The Control Gallery](cosmos/control-gallery.md) ·
Repo: [artemis-sbs/control_gallery](https://github.com/artemis-sbs/control_gallery).

## 🗂️ Art that lives once

Shared art used to be copied into every mission that used it — LegendaryMissions' 27 MB
of backdrops and card decks became **314 MB across twelve missions**, and a re-release
left every copy stale. Now a media pack is unpacked **once** beside the libraries, and
missions read it there.

```json
{ "shared_media": ["artemis-sbs.LegendaryMissions.media.v1.4.0.zip"] }
```

```python
gui_image_add_atlas("card_back", media_shared("casino/terran_back"))
```

`media_shared()` looks in your mission's own `media/` **first**, then in each pack you
declare — so overriding one file is dropping your own copy in, and nothing hardcodes the
unpacked path (which carries the version). Publishing a pack is a `zip` entry in
`__lib__.json`; `export-ignore` then keeps the art out of the source archive consumers
download, so a fetch no longer drags along 27 MB nothing reads.

**272 MB reclaimed.** Guide: **[Shared media](build/shared-media.md)**.

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

## 🧪 Mods — ships, races and art from an add-on *(experimental)*

An add-on can now add **ships the game does not have** — with their stats, interiors, fleet
ladder and race — **without editing a single file in your Cosmos install**.

The idea that makes it work is a split by *who opens the file*: MAST reads happily out of a
`.mastlib`, but the **engine** needs real files on disk, so a mod's ship data and art travel
in a [shared media pack](build/shared-media.md) and everything else in the mastlib.

```yaml title="your ships, in the media pack"
'#ship-list':
- key: dw_scrapper           # YOUR key - never one the game already owns
  side: Driftwake
  origin: Driftwake
```

```mast title="your add-on"
sbs.add_extra_ship_data("dw_ships", pack_folder)     # the engine learns your hulls
grid_merge_ascii(media_read_relative_file("dw_scrapper.grid"), "dw_races")
fleet_table_load_yaml(media_read_relative_file("dw_fleets.yaml"), "dw_races")
```

Add your race to `PLAYABLE_RACES` / `NPC_RACES` rather than replacing them and your ships
fight alongside the shipped ones instead of replacing them. Two mods that pick distinct key
prefixes can be installed together.

**What works:** ship data, interiors, fleet ladders, races, sides — all verified in the
engine. **What does not, yet:** hull art. The path mechanism is in place, but generating
derived art from a bare `.obj` crashes the engine, so for now a mod points `artfileroot` at
art the game already owns. There is also a trap worth knowing before you start: **never
commit a `.paxmesh`** — it bakes its texture paths, so a committed one points at its author's
disk.

Marked experimental because the engine side is still moving. Full walkthrough, including
publishing on GitHub or as a plain zip: **[Making a mod](build/making-a-mod.md)**.

---

## And the tools you build it with

New as well — none of these shipped with v1.3.0.

---

## 🚀 Launch it without clicking — `sbs run` and command-line arguments

Cosmos can now be started with arguments, and **a mission can read them**. A shortcut, a
batch file or a CI job can bring up a full bridge on a particular map with particular
settings, untouched by human hands.

```
sbs run                                        server + five consoles, nothing to click
sbs run comms,weapons                          just those two
sbs run -m LM_TestRange map=sandbox            a mission and a map
sbs run --dry-run                              show the command lines, launch nothing
```

The mission comes from `-m` (default `LegendaryMissions`) and is passed as
`defaultmission=`, so **`preferences.json` is no longer edited** to choose one. Consoles
are selected per process instead of by rewriting a file inside the game install — two runs
at once no longer fight over it, and a crash cannot leave it changed.

**Anything you add on the end reaches the mission**, because the engine hands unrecognized
`key=value` arguments straight to script:

| | |
|---|---|
| `map=` `console=` | start a map, open a console |
| `profile=` `var.NAME=` | settings, in bulk or one at a time |
| `seed=` `run=` | reproducible runs, labelled |
| `record=` | transcribe what you click |
| `test=` | a pass/fail verdict from the **real engine** |

Settings merge `defaults < settings.yaml < profile= < COSMOS_SETTINGS < var.NAME=`, so a
profile file carries the bulk and the command line names it:

```
sbs run -m MyMission profile=soak var.DIFFICULTY=3 var.AUTO_PLAY.enable=true
```

`test=30` is the one worth knowing about if you automate anything: the mission plays for
that long and writes `records/verdict.json`, which means **the real engine can be checked
by a script** rather than by someone watching it. It counts runtime errors, not MAST
coverage — `sbs debug . --test` remains the stronger check for whether your mission
actually did anything.

Anything that matches nothing says so, rather than quietly doing nothing.

→ [Command-line arguments](tooling/command-line.md)

## 🚀 Start a mission in one command

Writing your first mission used to begin with "download this repository, rename the
folder, edit these four files, then work out which libraries you need." Now:

```
sbs templates              # see what you can start from
sbs create MyMission       # make one — libraries and all
```

There are five boilerplates, and they are whole missions rather than empty shells:

| Template | What you get |
|---|---|
| `minimal` | One `@map` and a line of narration — the smallest thing that runs. |
| `sandbox` | Two sides, a station in an asteroid field, player ships, and raider waves that ramp with the difficulty setting. |
| `addon` | A shareable add-on — `provides` / `requires`, packaged as a `.mastlib` — plus a harness map to run it. |
| `amd` | Quests and science scans authored as data in a `.amd` fact sheet, with MAST holding only the logic that reacts. |
| `ou` | A whole procedurally generated universe, built on the OpenUniverse engine. |

**It won't hand you a mission your game can't launch.** Missions are pinned to a
release line, and everything a mission loads comes from the same one. `sbs create`
picks the newest line your install already has libraries for — capped by your version
of Cosmos — tells you which it chose and why, and never reaches for a newer one just
because it exists. Not every template is on every line, either: `addon`, `amd` and
`ou` need v1.4.0 language and library features.

The templates live in the
[mast_starter](https://github.com/artemis-sbs/mast_starter) repository and are read
straight from it, so new ones show up without updating the tool.
→ [Creating a mission](home/start.md) · [The `sbs` CLI](tooling/cli.md#starting-a-mission)

## 🧰 The AMD editor knows the format

The VS Code extension reads AMD as a format rather than as coloured text:

- **"This is a" picker** — a record's word is visible and settable, grouped Story / Work
  / Content, and it tells you what choosing it means (*"scope: shared, show: when done"*).
- **Completion answers where you are**: nouns on the fence's first line, field labels on
  a fence line, that field's values after the colon.
- **Hover explains the field** — the format's own words for it and its allowed values.
- **Your mission's own vocabulary is learned**, by reading the Python that declares it
  (never running it), so a mission's private fields get the same widgets and lint as the
  core ones.
- **Edits are safe** — changing one field leaves the kind line, `//` notes and list
  continuations exactly as you wrote them.

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
- **`sbs compile` can gate a build.** It used to print an error and exit 0, so any
  script or CI reading its exit code saw success on a compile that never happened. It
  now reports the errors and exits non-zero. (It still can't see a multi-line `{ }` —
  only a `--test` run finds that.) → [The `sbs` CLI](tooling/cli.md#validating-amd)
- **An in-game Avatar Editor** — an opt-in addon that customizes a character face
  **inside Cosmos**, with a **live `gui_face` preview** that updates as you move the
  sliders (unlike the extension's blind builder). Pick a race, tweak each feature,
  and the face is **copied to your clipboard** on every change — paste it straight
  into a `.amd` `Face:` field. → [Avatar Editor addon](legendarymissions/addons/avatar.md)
- **`sbs swap`** — keep several mission sets side by side and switch between them
  without copying anything (see below). → [The `sbs` CLI](tooling/cli.md)
- **`signal_next`** — one-shot await of the next signal. → [Signals](api/procedural/signal.md)
- **`once` routes, and creates that can't duplicate.** `//shared/signal` runs a route
  server-once *per emit* — it never promised the signal is only emitted once, so setup
  that got emitted twice used to build everything twice. Now mark a route
  **`//shared/signal/give_starting_cash once`** and it runs at most once a mission. Better
  still, where the thing being made has a natural name, creating is **idempotent**:
  `player_ensure(slot, …)` and AMD landmarks and characters key off the slot or the
  record's own key, so asking twice gets you the same ship, station or person — while a
  deliberate rebuild after a reset still works. → [Signals](mast/routes/signals.md)
- **Bring an old Artemis 2.8 mission forward.** `pip install arme2cosmos`, point it at
  the old XML, and it writes the Cosmos mission for you — as a quest tree, or as plain
  MAST you can edit — plus a notes file listing anything worth a second look. It's
  ordinary Python, so you don't need Cosmos to run it. Porting by hand instead? The
  `a2x_*` helpers are waiting in MAST, no import needed. We tried it on 27 of the old
  missions and they all run. → [Porting from Artemis 2.x](mast/porting-2x.md)
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
    backward compatible. → [Making add-ons](build/addons.md#declare-what-it-needs)

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
