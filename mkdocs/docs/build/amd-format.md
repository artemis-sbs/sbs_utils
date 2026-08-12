# The AMD file format

AMD is how you author mission **content as data** — quests, characters, places, items,
scans — so the MAST holds only the logic that reacts to it. It is written to be read and
written by people who write stories, not by programmers.

A file is a tree of **records**. Each record is a heading, an optional block of facts,
and prose.

```amd
# [Sweep the Belt](job_sweep)
---
At start: offered
Objective: Clear the hazard asteroids from the shipping lane
Reward: 150 credits
---
The freighters cannot run the lane until the rocks are gone.
```

Three parts, in order: the **heading** names it, the **fence** between the `---` lines
holds its facts, and everything after is the **body** the player reads.

---

## Headings

```amd
# [Display Name](key)
```

The display name is what a player sees; the key is what other records point at. Deeper
headings nest — a `##` sits inside the `#` above it, a `###` inside that.

`#` is only a heading when it has the `[Display](key)` shape. A plain `# Heading` in a
body is ordinary markdown text, which is why briefings can use markdown freely.

### Naming a record from somewhere else

A key does not have to be unique — short names like `recover` or `scan` read well inside
several different jobs. When a name is used more than once, point at it by **path**:

```amd
Then: reveal florbin/recover
```

A bare key resolves **nearest first** — from the record making the reference, then
outward — so a step can refer to a sibling by its short name. If a bare key really is
ambiguous, the linter says so and names the candidates rather than guessing.

### The key is an identity, so records don't duplicate

Because a record is named, loading one **twice** does not make two of it. Landmarks and
characters are created against their key, so a section that gets loaded again — a map
label that runs twice, a setup signal emitted more than once — gives you back the station
or the person you already have, not a second one sitting on top of it.

It's checked against the live game rather than a "have I loaded this?" flag, so it still
does the right thing when you *mean* to load again: if the station was destroyed or the
cast was cleared, loading the section re-creates it.

Characters are keyed by their record **and their host**, so casting the same crew onto two
different stations gives each station its own people.

---

## The fence

Everything between the `---` lines is the record's facts, one per line.

```amd
---
Characters                   <- what these are (optional; see below)
Color: #3399ff               <- a fact
Home: 6, 4
Citation: a long line that   <- an inline value: indented lines CONTINUE it
  wraps onto the next line
Properties:                  <- an EMPTY value: indented lines NEST under it
  Monster: 'gui_drop_down(...)'
Lines:                       <- ...or become a list
  - "First bark."
  - "Second bark."
// a comment
---
```

One rule tells wrapping from nesting: **if the label has a value on its own line, the
indented lines continue it; if it does not, they nest underneath it.**

A few details worth knowing:

- **Colours and colons are safe.** `Color: #86c` keeps its `#`, and
  `Reveals: Survey logged: 3 crates` keeps its colon. Values are text unless the format
  says otherwise.
- **Blank lines are free** — use them to group facts.
- **A line that is not a fact is an error**, not a silent omission. If you write a line
  with no colon, the linter tells you and suggests putting it in the body below the
  `---`.
- **The escape hatch:** a value starting with `{` or `[` is read as a structured value
  (`Modifiers: {speed: 2}`). Anything the plain form cannot express can be written this
  way, so the format never has to change to make room for it.

### The `---` fence itself

A fence opens **immediately after a heading** and closes at the next `---`. Anywhere
else, `---` is just a horizontal rule in your prose. A heading always closes an open
fence, and one left open at the end of the file is reported.

---

## Writing the body

Below the fence is your prose, and **a line the format does not recognize is prose,
always**. That rule is the reason it is safe to keep adding to this list: a sentence you
wrote last year cannot change meaning because a new build learned a new mark. It is also
why every mark below is unmistakable — a whole line starting with a specific character,
never a guess about how you were writing.

### `= ` — a note to yourself

What a beat is *for*, written for you and never shown to a player:

```amd
### [Identify the Kidnapper](trail)
= Midpoint. The crew learns Florbin is alive; raises stakes before the boarding.
---
Starts when: revealed
Done when: signal suspect_identified
---
Follow the cargo trail: interview stations and bio-scan suspect holds.
```

It shows in hover, in the Story Outline and on the Timeline, so the shape of your story
is readable without opening every record. The space after `=` is required — `=$name` is
still a [line style](#writing-values).

### `/* ... */` — cut, not deleted

You cut scenes far more often than lines, and you want them back next week:

```amd
/*
### [The Casino Detour](detour)
---
Starts when: revealed
---
Maybe next draft.
*/
```

Everything between the marks is gone from the mission — heading, fence and all — and
still sitting in the file. `//` still comments a single line.

### `[[key]]` — linking from inside prose

Prose can point at other records:

```amd
Talk to [[cmdr_vell]] before you reach [[ds1|the station]].
```

A bare `[[key]]` shows that record's display name; `[[key|your words]]` shows your words.
These are real references, so **Find All References**, **Rename** and the **Story Graph**
all see them.

A link to something you have not written yet is not an error — it is a note to self:

```
$ sbs lint --missing
3 thing(s) referenced but not written yet:
  cmdr_vell
      linked from `brief`   story.amd:6
```

So you can draft a whole mission as prose, link freely to scenes that do not exist, and
let the linter hand you the list of what to write next. In the editor the same targets
get a **Create this record** quick fix.

### `@Speaker` — a scene that holds a conversation

A dialogue scene used to have one speaker, named in its fence. Put the cue in the body
and one scene can hold a whole exchange:

```amd
# [The Standoff](standoff)
---
Dialogue
When: comms
---
@Ashfang
% You're a long way from friends, captain.
% Brave or stupid, flying in here.

@Vell (comms)
(shaken)
He means it, captain.

- [Apologize](ashfang_backoff)
- [Offer a cut](ashfang_deal) if credits >= 200 ; costs 200 credits
```

- `@Name` names who speaks. It matches a character record, so `@Ashfang` and `@ashfang`
  are the same person, and a name nobody defines is reported.
- `(shaken)` on its own line is **how** the line is delivered. Write anything you like —
  an unrecognized direction is kept as flavor, and a registered one can drive a face or a
  color.
- `(comms)`, `(over)` and `(card)` on the cue itself say **where** the line is delivered.
- `Speaker:` in the fence still works and is still the right thing for a scene with one
  voice; it covers any lines above the first `@`.

### `> [!NOTE]` — in-fiction documents

A callout, for library entries and briefing documents:

```amd
> [!WARNING] Quarantine Notice
> Do not dock. Contact TSN Command on channel 4.
```

`NOTE`, `TIP`, `WARNING` and `DANGER` are built in; an unknown kind reads as a plain
quote and warns, so a document from a newer mission is still readable.

### `![[key]]` — write it once, use it everywhere

On its own line, an embed pulls in another record's body:

```amd
# [Docking Procedure](dock_help)
Hold at 2000 and hail. Clearance is verbal.

# [Starbase Aurora](aurora)
Approach from the south.
![[dock_help]]
Then request a berth.
```

The shared paragraph lives in one place and every document that needs it says so.
A record that would include itself, directly or in a ring, is left as
`[circular include: key]` rather than hanging the mission; a target that does not
exist reads `[missing: key]`.

It must be a whole line — a transclusion is a block, and allowing it mid-sentence
would splice paragraphs into the middle of one.

### `Aka:` — other names a record answers to

```amd
# [The Florbin Affair](florbin)
---
Aka: The Florbin Job, florbin_case
---
```

Now `[[The Florbin Job]]`, `Then: reveal florbin_case` and anything else pointing at
those names resolves here. Use it when you rename something and would rather not
chase every reference, or when a generated key needs a human name.

A real key always wins — an alias can never shadow a record that genuinely has that
key. (Not to be confused with `Also:`, which is [traits](#what-it-also-does).)

### The title page

Fountain's title page is the fence **before the first heading**, and the words are
the ones a screenwriter already types:

```amd
---
Title: The Florbin Affair
Author: D. Reichard
Draft: 3
---

# [Jobs](jobs)
```

This is where document-wide settings live; a mission reads them with
`amd_root_data`.

### `FADE IN:` — cutscene transitions

In a cutscene shot, a screenplay transition says how the shot arrives, and stays out of
the words on screen:

```amd
## [Florbin, Recovered](florbin_recover)
---
Cutscene: finale
Subject: hero
Seconds: 6
---
FADE IN:

The transport slips its mooring and turns for home.
```

`FADE IN:`, `FADE OUT.`, `CUT TO:`, `SMASH CUT TO:`, `DISSOLVE TO:` and friends are
recognized as written; anything else works with Fountain's `>` in front (`> SLAM TO
BLACK`).

---

## Saying what a record is

Most of the time you never say — the **section name** already does:

```amd
## [Jobs](jobs)
### [Sweep the Belt](job_sweep)      <- a quest, because the section is called Jobs
```

`Jobs`, `Goals`, `Narrative`, `Characters`, `Cast`, `Crew`, `Landmarks`, `Regions`,
`Items`, `Drops`, `Sides`, `Scans`, `Dialogue`, `Relics` and their singular forms are all
understood, and a mission can teach the format its own names (`Contracts`, `Bounties`)
so it never has to say this twice.

When the name does not say it, write the word on the **first line of the fence**:

```amd
## [The Crew of the Meridian](meridian_crew)
---
Characters
---
```

Singular or plural both work. It applies to everything underneath, and a single record
can override it. `These are: characters` is the same declaration written out in full.

### Screenplay words

A story is not all to-do list. The same quest machinery plays three different parts, and
the word you write is the part it plays:

| word | what it is | where it shows in the quest log |
|---|---|---|
| `Quest` / `Job` / `Objective` | something the crew can go and do | listed from the start |
| `Beat` | a moment they live through | appears once it has happened, as history |
| `Arc` / `Chapter` / `Act` / `Sequence` | the heading over a run of beats | only once something under it shows |

```amd
# [Ramscoop](ramscoop)
---
Arc
---
The ramscoop thread.

## [The Coils Overheat](ramscoop/coils)
---
Beat
Starts when: signal ramscoop_online
---
Engineering reports the coils running hot.
```

A **`Cue`** is the fourth: a stage direction. It happens — a flag set, an effect played
— and is never listed at all.

Two more say whose the work is. A **`Job`** is taken by a ship — it waits on the board
until someone accepts it. An **`Objective`** is the crew's, and is live from the start.
That difference *is* `Scope:` and the arming word, so neither needs writing.

They add no new fields. What they do is save you writing what they already say: a story
moment belongs to the whole crew and is already running, so a `Beat` needs neither
`Scope:` nor `At start:`. Write a field only where the record **differs** — a beat that
waits to be revealed says `At start: hidden`, one that should stay on screen says
`Show: always`.

### What it also does

A record is one thing, but it can have more than one concern. A worldlet is a
**Landmark** — a place on the map — that also happens to **yield** ore. That second half
is a **trait**, and `Also:` claims it:

```amd
# [Cinder World](cinder)
---
Landmark
Also: economy
At: 6, 4
Yields: ore 8
Reserve: 4000
---
A cracked, mineral-rich ember of a world.
```

`Yields:` and `Reserve:` come from the `economy` trait, so nothing had to invent a
"worldlet" kind for the half that isn't a landmark. What a record **is** always wins a
name clash; a trait only fills in words the archetype never declared.

| trait | what it lends |
|---|---|
| `economy` | `Yields:` · `Reserve:` · `Price:` · `Costs:` · `Time:` |
| `reputation` | `Values:` · `Standing:` · `Reliability:` · `Rival when:` |

**Some traits you never have to write.** A side is always regarded some way, and so is a
person — so `Side` and `Character` carry `reputation` already. `Also:` is for the
concerns that are *optional*: a landmark that happens to yield.

!!! note "The word has to be on the record"
    A kind line on a *section* says what its records **are**, but the field defaults come
    from each record's own word. Write `Beat` on the beat.

A whole file can say it once, in a fence before the first heading:

```amd
---
Characters
---

# [Ana Reyes](ana)
```

If you write a word the format does not know, it tells you and lists the ones it does.

---

## Quest fields

The most-used vocabulary. Anything unrecognised is kept as-is and flagged by the linter,
never dropped.

| Field | Meaning |
|---|---|
| `At start:` | `running`, `offered` (on the board for a player to Accept), `hidden`, `done`, `failed` |
| `Objective:` | The sentence the player reads in the quest log |
| `Done when:` | What completes it — `destroy 6 raiders`, `reach 6, 4`, `signal drone_down` |
| `Starts when:` | What activates it (same grammar) |
| `Action:` | What happens the moment it **starts** — see below |
| `Then:` | What happens next, once it **finishes** — `reveal <key>` or `signal <name>` |
| `Reward:` | What completing it gives — `500 credits` |
| `Penalty:` | What failing it costs |
| `Fails when:` | What fails it — `signal base_lost`, `all dead convoy`, `5 minutes` |
| `Part of:` | The larger mission this is a step of |
| `Win:` / `Lose:` | Ends the game, with optional end-screen text |

### `Action:` — stage directions

A screenplay page has three things: a slug line, an action block, and dialogue. AMD could
already write the dialogue. `Action:` is the action block — what the world does the moment
a beat begins.

```
### [The trap closes](ambush)
---
Starts when: signal alarm
Action:
  - Kidnapper is no longer a suspect
  - Kidnapper becomes a pirate
  - Kessel Station arrives
---
The freighter lights her engines. The raider swings to follow.
```

A line reads **who — does what — to what**. The verb sits between the two names, which is
what tells you which one is acting.

| Verb | What it does |
|---|---|
| `becomes` | Gives it a role — `Kidnapper becomes a pirate` |
| `is no longer` | Takes a role away — `Kidnapper is no longer a suspect` |
| `joins` | Changes side — `Xorn joins tsn` |
| `arrives` | Places a landmark you declared — `Kessel Station arrives` |
| `departs` | Removes it from the world |
| `hails` | Calls the crew — `DS 1 hails ds1_brief`. See below |

**`Action:` fires when the beat starts. `Then:` fires when it finishes.** That is the whole
difference between them, and it is why both exist.

**The lines all happen at once.** The order you write them in is not an order of events. If
one thing has to follow another, that is a second beat with its own `Starts when:` — and a
time is a trigger like any other, so `Starts when: 3 seconds` works.

There are no conditions, loops or sequences here, on purpose. A direction is a statement.
When you want *"but only if the player scanned it"*, write two beats with different
`Starts when:` — the same way a branching quest is already written.

**Who can act.** An actor is a landmark you declared, or a role — and a role covers
everyone who has it, so `Raiders become hostile` moves all of them at once. A name nothing
recognises is reported in the log rather than silently skipped, and the linter catches a
misspelled verb before the mission ever runs.

**Repeating is safe.** A beat can start more than once — re-revealed, reloaded, a
repeatable thread. Every verb above survives that: `arrives` is keyed to the landmark, so
it will not place a second one, but it *will* re-place one that was destroyed.

#### `hails` — the beat opens with an incoming call

An incoming hail is a conversation the *script* starts: it appears in the crew's Incoming
Hails list, and answering it is a thing they do. That makes it a natural way to hand out a
quest — somebody calls, and taking the job is what you say back.

Write the conversation as a dialogue scene, and let the beat open it:

```
### [DS 1 Briefing](ds1_brief)
---
Speaker: ds1
When: hail
Title: Ambassador Kidnapped
Presentation: portrait
---
Artemis, DS 1. Ambassador Florbin was taken off this station inside a cargo container.

- [Take the case]() ; completes florbin/brief
- [Not now]()
```

```
#### [Take the Case](brief)
---
Scope: shared
Starts when: at once
Action:
  - DS1 hails ds1_brief
Then: reveal florbin/trail
---
```

The scene carries everything the hail looks like and everything it says, so the direction
only has to name it. Written bare — `DS1 hails` — it opens that speaker's `When: hail`
scene, so a character with one call to make needs no key at all.

**Who gets called** follows `Scope:`, and you do not have to think about it: a shared beat
runs once and calls every player ship; a per-ship beat runs for its own ship and calls
that one.

**What an answer means** is written on the choice, next to the words that earn it:

| Written after `;` | What it does |
|---|---|
| `accepts <quest>` | Starts it — the same thing the Accept button does |
| `completes <quest>` | Finishes it, with its `Reward:` and its `Then:` |
| `fails <quest>` | Fails it, with its `Penalty:` |
| `signal <name>` | Fires a signal, for anything the three above do not cover |

An answer is arbitrated on the server, so it happens exactly once however many consoles
are connected — you do not have to guard against two officers pressing at the same moment.

**A board you take by answering.** `At start: posting` lists a quest without a working
Accept button, so the only way to take it is to answer the call that offers it.

#### When it applies — and when it doesn't

`Action:` is for a beat that **causes** a change in the world. Read it as: *this moment
arrives, and because of it these things happen.* An ambush springs on a timer; a captain
defects when the evidence lands; a fleet warps in when the alarm goes out.

It is **not** for a change that causes a beat. That is the more common shape in an
existing mission, and it looks like this:

> The crew scans a cargo hold. Code unmasks the smuggler — flips its roles, changes its
> side, sends it running — and *then* marks the quest step done.

Here the world changed first and the beat is the consequence. Putting those directions in
the next beat's `Action:` would run them *after* the step advances, which is later than
the moment they belong to — the ship would already be fleeing while still flying its
disguise.

The test is which way the arrow points:

| | |
|---|---|
| The beat happens, **so** the world changes | `Action:` |
| The world changes, **so** the beat happens | leave it where it is |

A useful sign you are in the second case: something is polling or translating state into a
signal to advance the quest. That translation is the arrow pointing the other way.

### Older spellings still work

Nothing you have written stops working. These are the same fields under their previous
names, and a file may use either:

| Older | Now |
|---|---|
| `Goal:` | `Done when:` (plus `Objective:` for the text it used to double as) |
| `When:` | `Starts when:` |
| `State: idle` / `State: available` | `At start: offered` — the word the player already sees |
| `State: active` / `secret` | `At start: running` / `hidden` |
| `Parent:` | `Part of:` |
| `Critical:` | `Fatal:` — it says what happens, not how much it matters |
| `Pays:` | `Reward:` — the word the player reads in the log, and it leaves `Penalty:` free for the other side |
| `Fail on signal:` / `Fail on all dead:` / `Fail after:` | `Fails when:` — one trigger grammar for all three |
| `Complete after: 30 seconds` | `Done when: 30 seconds` — a time is a trigger |
| `Reveals:` (a scan's text) | `Scan says:` — `Then: reveal` is a different thing |

---

## Art: sheets, cells and icons

A sheet of art is a catalog, so it is authored like one. An image section registers atlas
keys - the names `gui_image`, `gui_text_area` and `gui_icon_name` draw by - with no Python
at all. What every cell shares is written ONCE on the section, so an entry is one line:

```amd
## [Cards](cards)
---
images
Sheet: casino/terran_deck
Cell: 190, 280
Domain: casino
---

### [Back](card_back)
---
At: 0, 0
---

### [Console backdrop](console_bg)
---
Sheet: helm/consoles0001
---
```

| field | means |
|---|---|
| `Sheet:` | the file, without the extension. Looked up in a [shared media pack](shared-media.md) first, so it resolves the same in a clone and in a fetched copy. On the section, or overridden per entry. |
| `Cell:` | cell size in **pixels** - `64`, or `190, 280` |
| `Grid:` | cells across and down (`8, 8`) - measures the cell off the sheet instead |
| `At:` | which cell, as `col, row` |
| `Rect:` | explicit pixels (`left, top, right, bottom`) for an irregular cell |
| `Color:` | a default tint; a drawing call may override it |
| `Domain:` | a namespace, so two add-ons can't silently claim one key |

An entry with neither `At:` nor `Rect:` takes the **whole file** - which is why `Sheet:`
can be overridden per entry, for one loose image among cells.

Load it with `images_load_amd("art.amd")`, or `images_declare_document(doc)` when the
section lives in a bigger file.

### Icons are the same thing, in the icon domain

A section whose kind noun is `icons` registers into the **icon domain**, which is what
`gui_icon_name` resolves against - so its keys are the *looks* the game draws by name, and
naming one re-skins every screen that draws it:

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

That scoping is deliberate: an ordinary image called `square` or `flag` must not change
every state pip in the game. See [Icons by name](../cosmos/gui_icons.md).

!!! tip "`sbs lint` checks these"
    A sheet that is not on disk, an `At:` with no `Cell:` or `Grid:` to measure against,
    and a cell that falls off the edge of the sheet. All three draw a blank widget with no
    error anywhere otherwise.

## Writing values

The format understands the shapes an author naturally writes:

| Written | Read as |
|---|---|
| `Home: 6, 4` | a map cell |
| `Reward: 200 credits` | what completing it gives |
| `Fail after: 6 minutes` | a duration |
| `Offers: patrol, escort, strike` | a list |
| `Values: by-the-book 40, fearsome 30` | weighted choices |
| `Flies: 60% Kralien, 40% Arvonian` | a mix |
| `Inputs: salvage x5, bio_sample x1` | a shopping list |
| `Program: kind=bio, range=medium` | settings |
| `Color: #3399ff` | a color |

---

## Checking a file

```
sbs lint <mission>
```

reports the things that used to fail silently: a heading that will not parse, a fence
line that is not a fact, a reference that points at nothing, an ambiguous name, a value
outside a field's allowed set, a field no one declares, and non-ASCII text the engine
cannot render.

The VS Code extension shows the same findings as you type, and gives each field an
editor suited to it — a dropdown for a fixed set of values, a picker for a reference, a
swatch for a color, the face builder for a face.

To see what you have *not* written yet rather than what is wrong:

```
sbs lint <mission> --missing
```

Every reference that resolves to nothing, grouped by target and always exiting 0. It is
a work list, not a failure — see [`[[key]]`](#key-linking-from-inside-prose).

See [AMD authoring tools](../tooling/amd-tools.md) for the outline, timeline, graph and
map views over the same files.
