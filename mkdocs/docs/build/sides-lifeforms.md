# Sides, lifeforms & faces

Narrative missions need factions to fight (sides), characters to talk to
(lifeforms), and faces for comms.

## Sides

Create sides with `prefab_side_generic`, then set how they feel about each other.
`await` captures the side id the prefab yields:

```
tsn      = await prefab_spawn(prefab_side_generic, data={"key":"tsn"})
side_set_display_name(tsn, "TSN")
side_set_description(tsn, "The Terran Stellar Navy")
side_set_icon_color(tsn, "#07F")

# or set it all in the prefab data:
raider   = await prefab_spawn(prefab_side_generic, data={"key":"raider", "name":"Raider", "color":"#F00", "desc":"Hostile Aliens"})
amb_side = await prefab_spawn(prefab_side_generic, data={"key":"ambassador", "name":"Ambassador", "color":"#FFF"})

side_set_relations(tsn, raider, sbs.DIPLOMACY.HOSTILE)
side_set_relations(tsn, amb_side, sbs.DIPLOMACY.NEUTRAL)

sim.set_diplomacy_color(sbs.DIPLOMACY.HOSTILE, "#F00")
sim.set_diplomacy_color(sbs.DIPLOMACY.NEUTRAL, "#077")
```

An object's side is the **first role** in its `npc_spawn` roles string
(`"tsn, station"` → side `tsn`).

### Declaring sides as data

A whole faction set can be authored in an AMD document and declared with
`sides_load_amd("maps/sides.amd")` — one heading per side, the fence carrying its identity
and diplomacy. That call reads a file whose TOP-LEVEL headings are the sides. For a Sides
section inside a larger file, hand it the section instead:

```
sides_declare_amd(amd_section(MISSION_DOC, "sides"))
```

(`sides_load_amd("mission.amd")` on a file with sections makes one side named after the
file's own heading.) A record's key, the word in round brackets, is what every other line
uses to name the side: `Enemies: raider`, and `Side: raider` on a landmark.

```
# [Raider](raider)
---
Color: #F00
Enemies: players, civilians
---
Hostile Aliens.

# [Civ](civ)
---
Color: white
Civilian: true
Neutral: players
---
Civilians. Protect them from attack.
```

**Relations exist only where you declare them.** Nothing defaults an unnamed pair, so a set
of factions that each name one enemy produces a *star* — one side hostile to everyone, and
every other pair with no relation at all: `unknown`, which is not the same as neutral (no
Comms, no docking, no scan text). That failure is invisible in testing, because what breaks
is the shooting rather than the script: ships spawn on the right sides, correctly armed, and
simply never fire.

`sbs lint` reports a side key that names nothing as `dangling-side` (`Enemies: tsm`, two
keys with no comma between them, `Side: braker` on a landmark, `Side: gild` on a
character), and the game writes `Side not found` to `mast.runtime.log` the first time it
meets one. A side counts when a record declares it, in any file of the mission, or when
the story or an addon the mission loads names it in quotes.

Three reserved words save you from naming every pair. **Explicit names always win over a
token.**

| Token | Means |
|---|---|
| `*` | every other side **in this document** |
| `players` | every side in `PLAYER_LIST`, plus any side a player ship is actually on |
| `civilians` | every side declaring `Civilian: true`, **in any document** |

`players` and `civilians` deliberately reach **across documents**, which is what lets an
addon and a total conversion coexist: neither can name the other's sides, so `Enemies: tsn`
is inert beside a mod whose crews fly `federation`. Written as `Enemies: players`, raiders
prey on whoever turns up. `*` stays inside its own document, so an addon cannot silently
redefine a relation with a side it has never heard of.

Sides are declared before any ship exists, so `players` resolves from the roster at that
point. Call `sides_apply_audiences()` after the crew is real — or after a mission moves a
crew to another side — and the same rules re-resolve against the live ships.

### Reputation: a side that values deeds

Relations say whether two sides are at war. **Reputation** is how one side sees one *ship*:
a number that deeds move, and that a line or a choice can ask about. It needs no MAST - a
mission made with `sbs create -t amd` already loads everything below.

A side says what it values, and a character says whose side they speak for:

```
### [Harbor Guild](guild)
---
Color: #0C6
Values: honest 40, generous 30
---

### [Harbormaster Quill](quill)
---
Side: guild
---
```

A deed is `earns <side> <trait> <number>` - in a quest's `Reward:` (or `Penalty:`), or
after the `;` of an answer:

```
Reward: 150 credits, earns guild honest 30

- [Give our fee to the tug crews.]() ; earns guild generous 30
```

And `standing` asks, on a `%` line or a choice:

```
%{standing < 30} The Guild yard is for members. Hold outside the markers.
%{standing >= 30} The tug crews told me what you did. The yard is open to you.

- [Request a berth at the yard.]() if standing >= 30
```

| Word | Reads |
|---|---|
| `standing` | the acting ship's standing with the **speaker's side**, -100 to 100 |
| a trait: `honest`, `fearsome`, ... | that ship's reading on one trait with the same side |

**Standing is the ship's.** The traits come in pairs, and earning one lowers the other:
honest / liar, fearsome / cowardly, peaceful / violent, generous / selfish, kind / cruel,
resourceful / by-the-book, intellectual / foolish. Standing is the average of the traits
a side values, weighted by the numbers on its `Values:` line - so `earns guild honest 30`
with the Guild above is a standing of 17 (`40 x 30 / 70`), and adding `generous 30` makes
it 30. A side with no `Values:` line counts everything earned with it equally.

Who the "speaker's side" is: a character's `Side:`; else the side the speaking object is
on (a station that hails the crew); else the speaker's own key when that is a side
(`Speaker: guild`). A speaker with none of those reads 0.

Who is paid: an answer pays the ship that gave it. A `Scope: shared` quest pays every
player ship flying when it completes; a ship that joins later starts at 0. A quest held by
a station or a side carries no reputation at all.

`sbs lint` reports `earns-unknown-side` (`earns gild honest 20`), `earns-unknown-trait`
(`earns guild honset 20` - a made-up trait no side values) and `earns-shape` (no number,
or no comma before `earns` in a `Reward:`). A deed may be written against a trait
(`honest`, `liar`) or against the name of the line the trait is one end of (`honesty`):
`earns guild honesty 30` and `earns guild honest 30` do the same thing, and neither is
reported. A condition is stricter: `if honesty >= 30` reads nothing; ask with the trait.

It also reads a side's `Values:` line: a word that is not a trait, or two entries with
the comma missing (`Values: honest 40 generous 30` is ONE trait with a long name), is
`values-unknown-trait`; an entry with no number (`Values: honest, generous`) is
`values-no-weight`, since a side whose values all weigh nothing has a standing of 0 with
everybody. A universe that names traits of its own (an `Axis:` line, or a `reputation:`
block) is not judged.

One thing reads reputation without being asked: LegendaryMissions' fleets leave a ship
alone once everything it has earned with their side **adds up to 60** - the plain sum of
the traits, not the weighted standing. Two generous answers can end a war for one ship
while the rest of the table is still being shot at.

## Lifeforms (NPCs)

A lifeform is an NPC used for comms, names, and faces. Create them at the top level
(shared) so every task can reach them:

```
shared admiral = lifeform_spawn("Admiral Harkin", "ter #964b00 8 1;ter #fff 3 5;", "admiral")
```

Arguments: display name, a **face string**, and a role. Read its face and name
later with `get_face(admiral.id)` and `admiral.name`.

Attach a lifeform to a player ship as crew (shown in interior views):

```
ensign_rachel.host = artemis_id
```

## Faces

Faces are strings. Build random ones, or set an object's face directly:

```
set_face(station_id, random_terran(civilian=True))
set_face(amb_id, random_terran(civilian=False))
set_face(raider_id, random_kralien())
face = get_face(admiral.id)      # e.g. to pass to a comms message
```

Use the face when sending a message (see [Story & NPC messages](messages.md)) or in
comms dialogue. See the [faces API](../api/utility/faces.md) and the
[lifeform API](../api/procedural/lifeform.md).
