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
and diplomacy:

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
every other pair silently neutral. That failure is invisible in testing, because what breaks
is the shooting rather than the script: ships spawn on the right sides, correctly armed, and
simply never fire.

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
