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

## Saying what a record is

Most of the time you never say — the **section name** already does:

```amd
## [Jobs](jobs)
### [Sweep the Belt](job_sweep)      <- a quest, because the section is called Jobs
```

`Jobs`, `Goals`, `Narrative`, `Characters`, `Cast`, `Crew`, `Landmarks`, `Regions`,
`Items`, `Sides`, `Scans`, `Dialogue` and their singular forms are all understood, and a
mission can teach the format its own names (`Contracts`, `Bounties`) so it never has to
say this twice.

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
| `Then:` | What happens next — `reveal <key>` or `signal <name>` |
| `Reward:` | What completing it gives — `500 credits` |
| `Penalty:` | What failing it costs |
| `Fails when:` | What fails it — `signal base_lost`, `all dead convoy`, `5 minutes` |
| `Part of:` | The larger mission this is a step of |
| `Win:` / `Lose:` | Ends the game, with optional end-screen text |

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

See [AMD authoring tools](../tooling/amd-tools.md) for the outline, timeline, graph and
map views over the same files.
