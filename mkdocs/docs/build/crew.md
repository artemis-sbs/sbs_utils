# Crew rosters &mdash; names and faces at the consoles

A console has always been able to carry a person's name: the picker asks for one, and
the Director's lower thirds and the Gamemaster's message list read it back. Almost
nobody fills it in, so almost every seat on air reads *unmanned*.

A **crew roster** is a named set of people who fill those seats without anyone typing.
It is an `.amd` file, it can carry a face or a photograph per person, and it comes from
whichever layer knows best &mdash; a mod for its own hulls, a mission for its own ships,
an operator for tonight's game, or the player themselves.

## The two kinds

A roster says which it is with `By:`, because the two real uses want opposite things.

| `By:` | What it is | Who decides |
|---|---|---|
| `console` (the default) | a **cast** &mdash; each member names a seat, so opening helm makes you whoever crews helm | the roster, automatically |
| `person` | a **group** &mdash; a list of real people, console irrelevant | you, by picking yourself |

A cast is what fills a Director bridge multiview with nobody touching anything. A group
is the "us, with our actual photographs" case: you pick yourself once and your name and
face follow you to whatever station you take, this session and the next.

## Writing one

The **section fence carries what everybody shares**, and each entry says only what makes
them them. That is the whole point of the shape &mdash; Data is three lines.

```markdown
## [Enterprise-D](tng_d)
---
crew
Hull: tng_fed_galaxy
Ship: Enterprise, Enterprise-D
Race: terran
Portraits: media/crew/tng
---
The Galaxy-class flagship's senior staff.

### [Jean-Luc Picard](picard)
---
Rank: Captain
Console: mainscreen
Face: tng1 #fff 0 0;
---

### [Data](data)
---
Rank: Lt. Commander
Console: science
Portrait: data
---
```

!!! warning "The kind is a bare noun"
    `crew` on its own line, **not** `Kind: crew`. The label `kind` infers *landmark*,
    which types the whole roster wrong and takes every member with it.

### The fields

| On the section | Means |
|---|---|
| `By:` | `console` (a cast) or `person` (a group). Defaults to `console`. |
| `Hull:` | shipData **keys** this roster crews by default &mdash; the tier a mod uses |
| `Ship:` | ship **names** bound to this roster &mdash; the tier a mission uses |
| `Race:` | face race for members with no `Face:` of their own |
| `Portraits:` | the folder every `Portrait:` below is relative to |
| `Sheet:` / `Cell:` / `Grid:` | one portrait sheet, cut exactly like an [image atlas](amd-format.md) |

| On a member | Means |
|---|---|
| `Rank:` | display only &mdash; "Captain", "Lt. Commander" |
| `Console:` | which seat. Leave it off for a floating officer who fills any spare station. |
| `Face:` | a face string, or a race keyword like `terran_male` |
| `Portrait:` | a photograph &mdash; an atlas key, or a path under `Portraits:` |
| `At:` | this person's cell on the roster's `Sheet:` |

A **portrait beats a face**, never both: a photograph is the stronger statement and
stacking them has no rule to resolve it. A portrait draws wherever Cosmos draws our own
GUIs &mdash; the picker, Director lower thirds, the Gamemaster panel, any text area.
It does **not** reach the engine's comms face slot, which only accepts face strings, so
give anybody who speaks over comms a `Face:` as well.

### A group, with photographs

```markdown
## [Thursday Night Crew](thursday)
---
crew
By: person
Sheet: media/crew/thursday/faces
Cell: 256
Grid: 4, 2
---
Pick yourself; you keep your face whichever console you take.

### [Doug](doug)
---
Rank: Captain
At: 0, 0
---
```

One 4&times;2 sheet, cut the same way an icon sheet is. `Sheet:` resolves through the
shared-media search, so it works the same in a clone and in a fetched copy.

## Loading one

A **mission** loads its own file:

```
crew_load_amd("crew/rosters.amd")
```

An **add-on or a mod** cannot use that &mdash; it resolves relative to the mission, and a
mastlib is a zip. Read your own file out of your own add-on instead:

```
shared MY_CREW = crew_declare_amd(amd_document(media_read_relative_file("crew_rosters.amd"), data_parser=amd_crew_data))
```

## Which roster staffs a console

Strongest first. Every step above the last is optional; the last one always answers,
unless you turn it off.

1. **The player.** What they typed at the picker, the face they built, or the person
   they picked out of a group. Nothing outranks somebody's own answer about themselves &mdash;
   but **per field**: what they did not answer is still answered by the step below, so naming
   yourself keeps the face the ship gave you and building a face keeps your name.
2. **The ship.** A roster declaring `Ship: Enterprise`, or `crew_bind_ship()`. This is
   how one game runs several crews at once &mdash; the Enterprise flies with one, the
   Defiant with another.
3. **The game.** The `CREW_SELECT` setting: the **Crew** dropdown on the server console,
   or `Defaults: CREW_SELECT` on a `@map`.
4. **The hull.** A roster declaring `Hull: tng_fed_galaxy`, or `crew_bind_hull()`. A mod
   sets this and every Galaxy in every mission arrives crewed.
5. **An automatic name.** A console nothing above reached gets one anyway &mdash; see below.
6. **Nobody**, only if automatic naming is off.

Two people never get the same person: a seat is taken when somebody sits in it and freed
when they leave, so a bridge with two science stations gets two different officers.

## A ship has a crew, not a client

Both steps that name somebody for you &mdash; a `By: console` cast and the automatic names
below &mdash; answer per **(ship, station)**. Helm on the Artemis is the same person every
time anything asks: before a single console has connected, while a player is only looking at
it on the picker, and after whoever was sitting there has gone.

That is what lets the picker show you who you are about to be, and what lets a Director
bridge wall name a station nobody is at:

```python
crew_seat_name(ship, "helm")        # the ship's helmsman, with or without a human in the chair
```

It also means moving from helm to weapons **renames** an automatically named player &mdash;
you stopped being the helmsman and became the weapons officer, which is what a cast has
always done. A player who typed their own name is the strongest step above and is never
renamed.

## Automatic names

A console nobody named gets one regardless, and a **different one from every other console
in the run**. Uniqueness is what makes a Director bridge wall readable &mdash; every panel is
on screen at once.

This is on by default, and it is the one part of the crew system that changes what an
**existing** mission shows: a lower third that used to read *unmanned* now reads a name.
That is the point rather than a side effect &mdash; the crew name existed for years and
almost nobody typed one.

```yaml
CREW_AUTONAME: true     # false: a seat nobody claimed reads as empty, as it used to
```

The stock names live in the library, so they work for a mission that loads no add-ons at
all. A base game or a total conversion replaces them by registering its own, which are
consulted first:

```python
crew_register_names("helm", ["Ensign Vega", "Lt. Sorm"])       # any console
crew_register_names("helm", ["K'tal"], race="klingon")         # or per race
crew_register_names("helm", ["Ensign Vega"], gender="female")  # and which face it wears
```

### The face agrees with the name, and wears a uniform

A face is **rolled** for anyone who has none of their own, and a terran face has a gender
axis &mdash; so the roll has to be told which one, or half of *Freya Laurent*'s consoles show
a man. The stock pool is gendered; `crew_name_gender()` answers for any name it knows, whole
or given-name-only, and a roster says it outright:

```
### [Tomas Vale](tv)
---
Console: helm
Gender: female        # male, female, fluid - which face to roll
---
```

The face also always **wears a uniform**. Left to chance one face in five comes back
civilian, which on a bridge is not a variation on a crew member &mdash; it is a stranger at
the helm. Same reason the identity editor keeps the uniform on: the slider stays, so *which*
uniform is still the player's, but the checkbox that removed it is gone.

Neither applies to a mod race: its faces are whole drawn portraits with no parts to steer.

A group roster (`By: person`) never hands out **its** people automatically &mdash; a seat
nobody claimed gets an automatic name instead. Giving Doug's face to whoever opened helm
first is exactly what a group roster exists to avoid.

Names are released by the mission reset, so "unique per run" is precisely that.

## At the console picker

The picker shows **who this console is about to be** &mdash; the face and the name, on one
line, following whichever station is highlighted in the list. Highlight engineering on a
Galaxy-class and it says Geordi. Nothing is written while you look: the seat's name is
worked out once and kept, so what the line shows is what the console gets.

**Edit** beside it opens the identity page, which owns the whole person:

- their **name**, typed;
- their **face**, through the [avatar editor](../cosmos/gui.md) &mdash; present only when the
  `avatar_editor` add-on is loaded. It builds the six stock races; a mod's faces are whole
  drawn portraits with nothing to slide, so those are picked from a gallery instead;
- **who they are instead**, out of a roster that staffs this ship. An *override* &mdash; a
  cast already assigns itself, so reaching for the list is reaching past the automatic
  answer;
- **Use Default**, which drops all of it and hands the seat back to the ship.

Turn editing off and the line becomes a readout: the cast still crews the console, it simply
cannot be argued with.

```yaml
CREW_EDIT:
    enable: true            # false: the identity line is a readout, with no Edit button
    allow_name: true        # the name field inside the Edit page
    allow_face: true        # the avatar editor button inside it
    allow_portrait: false
```

## What reads it

The name lands on the client as `CREW_NAME`, which is where it has always lived &mdash;
so everything that already read it keeps working with no change:

- the Director's `<<crew_name>>` overlay token, and the new `<<crew_rank>>` beside it
- the Gamemaster's "To &hellip;" message list
- anything of your own doing `get_inventory_value(client_id, "CREW_NAME")`

The face, portrait, rank, roster and *why this name was chosen* arrive as `CREW_FACE`,
`CREW_PORTRAIT`, `CREW_RANK`, `CREW_ROSTER` and `CREW_SOURCE` alongside it.

### In a cockpit, a callsign

The always-on identity badge shows the crew name on a bridge console and the pilot's
**callsign** on a flight one (`cockpit`, `hangar`) &mdash; there the callsign is what the rest
of the flight calls you, and it is already what every readout the hangar draws uses. It
replaces the name rather than joining it, because the badge shares a narrow strip with the
count of what is waiting. Dock, go back to a bridge station, and you are a crew member again.

The hangar owns the value; `crew_callsign(client_id)` is the library's one named place to
read it.

## See also

- [Sides, lifeforms & faces](sides-lifeforms.md) &mdash; face strings, and the NPCs a
  crew member is deliberately not
- [The AMD file format](amd-format.md) &mdash; fences, kind nouns, and image sheets
- [The Director](../cosmos/director.md) &mdash; where a crew name goes on air
