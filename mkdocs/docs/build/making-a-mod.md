# Making a mod

!!! warning "Experimental"
    The pieces below are new and the engine side is still moving. **Ship data, interiors,
    fleet ladders and races work today.** **Hull art does not yet** — see
    [Art](#art-and-the-paxmesh-trap). Build against this if you want to help shape it;
    do not build a release schedule around it.

A **mod** adds content the game does not have — ships, a race, interiors, art — *without
editing a single file in your Cosmos install*. If you have written an add-on before, this is
an add-on that also carries things the **engine** has to open.

Prerequisites: [Making add-ons](addons.md) and [Shared media](shared-media.md).

## The one idea: who opens it?

Everything about a mod's layout falls out of one question — **is this file read by MAST, or
by the engine?**

| Read by | Lives in | Why |
|---|---|---|
| **MAST** — labels, routes, interiors, fleet ladders, dialogue | a `.mastlib` | MAST reads straight out of the zip |
| **The engine** — ship data, meshes, textures | a **media pack** | the engine opens real files; it cannot read into a zip |

So a mod is normally **two artifacts**, built from one folder.

!!! danger "Never overwrite the game's files"
    The traditional way to ship a mod is to replace `data/shipData.yaml`,
    `data/grid_data.json` and `data/preferences.json`. Measured on a real mod, installing it
    that way **deleted five ships** and **reverted twenty-two more** — because its
    `shipData.yaml` was copied from an older build, and replacing a whole file ships
    *everything else in it* frozen at that version. Its `preferences.json` also rolled back
    render distances and network tuning that had nothing to do with the mod.

    None of that was intended by its author. A mod that **declares** can only ever add what
    it means to add.

## The example

We will build **Driftwake** — salvager clans who strip the debris fields — with three hulls.

| key | role |
|---|---|
| `dw_scrapper` | light salvage tug |
| `dw_breaker` | medium warship |
| `dw_hoarder` | heavy carrier |

**Keys are global, so pick a prefix nobody else will use.** `dw_` here. Two mods that both
add `raider` collide; two that add `dw_breaker` and `xx_breaker` never can.

!!! tip "Do not re-use a key the game already owns"
    Naming your ship `tsn_light_cruiser` *does* work — the engine takes your entry over its
    own. But then every mission that spawns a light cruiser gets yours, two such mods can
    never be installed together, and nothing can spawn both. Add ships; do not replace them.

### Layout

```
Driftwake/
  __lib__.json          {"version":"v1.0.0","mastlib":["dw_races"],"zip":["media"]}
  .gitignore            derived art — see below
  media/                -> artemis-sbs.Driftwake.media.v1.0.0.zip
    dw_ships.yaml          the ENGINE opens this one
    ships/                 meshes and textures (later)
  dw_races/             -> artemis-sbs.Driftwake.dw_races.v1.0.0.mastlib   (FLAT)
    __init__.mast
    dw_scrapper.grid  dw_breaker.grid  dw_hoarder.grid
    dw_fleets.yaml
```

`sbs.pyz lib Driftwake` builds both and unpacks the media pack once into
`__lib__/media/<pack>/`, where every mission reads the same copy.

## Ship data

The engine learns your ships from **your own file**, in the media pack:

```yaml title="media/dw_ships.yaml"
# Driftwake hulls. YAML, so it can have comments like this one.
'#ship-list':
- key: dw_scrapper
  name: Scrapper
  side: Driftwake              # what it IS - how a prefab finds "a Driftwake ship"
  origin: Driftwake            # what science and the hangar display show
  artfileroot: longbow         # borrowed engine art, for now
  meshscale: 0.0656711384654045
  radarscale: 1.0
  exclusionradius: 50.0
  meshrotate: 0
  long_desc: Driftwake Scrapper^A salvage tug with a cutting beam.
  roles: ship,warship,light,patrol
  shields: [80, 80]
  hullpoints: 2
  tubecount: 1
  torpedostart: [{Homing: 4}, {Nuke: 0}, {EMP: 0}, {Mine: 0}]
  internalmapscale: 1.0
  internalmapw: 9
  internalmaph: 12
  internalsymmetry: 1
  turn_rate: 1.2
  speed_coeff: 1.1
  scan_strength_coeff: 1
  ship_energy_cost: 1
  warp_energy_cost: 1
  jump_energy_cost: 2
  hull_port_sets:
    beam Primary Beams:
    - position: [0.0, 0.0, 60.0]
      color: green
      arccolor: '#090'
      cycle_time: 6
      damage_coeff: 1
      range: 1000
      arcwidth: 144
      barrel_angle: 0
```

!!! danger "Completeness is load-bearing"
    Copy a **whole** entry from `data/shipData.yaml` and change what you need. An entry
    missing `hull_port_sets` or `torpedostart` has **crashed the engine at load**. This is
    not a place to be minimal.

Name it from your add-on. One line, nothing written:

```mast title="dw_races/__init__.mast"
provides dw_races

ship_data_add_extra("dw_races/dw_ships", mod="dw_races")
```

The name takes **no extension** — the engine tries `.yaml` then `.json` itself, so you
can change format without changing the call. It may include a logical folder, and with
no path it is looked for where the media system already looks: this mission, then each
media pack it pinned.

!!! tip "Put the file in your media pack, not your mastlib"
    A mastlib is a **zip**, and the engine cannot read inside one. A media pack is
    unpacked to disk once, so the engine can be handed a real folder. This is the whole
    reason the older route had to generate a file.

!!! note "Two consumers, one call"
    Your ships have to reach **two** places: the engine (which resolves `artfileroot`,
    and is what makes a `behav_station` fire at all) and sbs_utils' own table (which is
    what `filter_ship_data_by_side` and `get_ship_name` read, and what headless and the
    mock use). `ship_data_add_extra` does both from the one file, so they cannot drift.

    Turning the engine half off with `ship_data_extra_enable(False)` leaves the library
    merge in place, so headless keeps behaving identically.

!!! warning "Do not use `ship_data_merge_mod` — it is broken"
    The older route reaches the engine by **generating** `extraShipData.json` in the
    *mission* folder. That file stays on disk, and on the next run `get_ship_data()`
    prepends it whole — `#mod` entries and all — while your add-on declares the same
    entries again. Measured at **51 hulls becoming 102** from run 2 onward. The file the
    feature generates is the input that breaks it.

## Races

A **race** is the gating name a mission uses to turn your content on. Add yours to the
settings rather than replacing them, so your ships can fight alongside the shipped ones:

```python title="dw_races/dw_setup.py"
def dw_register_race():
    from sbs_utils.procedural.settings import settings_get_defaults
    settings = settings_get_defaults()          # the live dict
    for key in ("PLAYABLE_RACES", "NPC_RACES"):
        raw = settings.get(key) or ""
        if "driftwake" not in raw.lower():
            settings[key] = (raw + ", " if raw.strip() else "") + "Driftwake"
```

!!! warning "Skip this and your mod is silently inert"
    `settings_race_is_playable` answers **False** for a race missing from a non-empty
    `PLAYABLE_RACES`. No interior loads, every hull gets a dead Engineering console, and
    nothing says why.

**Origin is per ship; race is the gate.** They are different units. A pack of six hulls from
four different builders keeps four `origin` values — that is what science shows — while
sharing *one* race name, because four races of one hull each would mean four settings
entries and four fleet ladders that could only escalate by count.

Note that in sbs_utils `SpaceObject.race` **is** `origin`, so `origin` also decides which
taunt group and which hail scene a ship gets.

Your fleet ladder is a normal ladder — see **[Fleets & raiding](fleets.md)** for the file
format, the difficulty encoding and per-faction sides.

```mast title="dw_races/__init__.mast"
if settings_race_is_playable("Driftwake"):
    grid_merge_ascii(media_read_relative_file("dw_scrapper.grid"), "dw_races")
    grid_merge_ascii(media_read_relative_file("dw_breaker.grid"), "dw_races")
    grid_merge_ascii(media_read_relative_file("dw_hoarder.grid"), "dw_races")

if settings_race_is_npc("Driftwake"):
    fleet_table_load_yaml(media_read_relative_file("dw_fleets.yaml"), "dw_races")
```

## Interiors

One ASCII floor plan per hull — the rooms and system nodes Engineering shows. Format and
authoring: [The races add-on](race-addons.md) and `GRID_ASCII_FORMAT.md`.

!!! danger "A new key has no interior to fall back on"
    Stock hulls have plans shipped with the game. **Yours do not.** A hull you forget to
    plan gets *no* Engineering console at all — no system nodes, no damcons, no internal
    damage — and nothing reports it. Plan every hull a player can fly.

Three things that bite when writing plans:

- **The plan must fit `internalmapw` × `internalmaph`.** The renderer draws that box and
  **silently drops** anything outside it. If you resize a hull, re-check its plan.
- **One name means one roleset.** The legend maps a room name to its roles once. Using one
  name for two different rolesets loses the distinction — and the room registry picks the
  survivor, so e.g. a single `SHIELD` name for both facings can quietly turn every forward
  shield into an aft one.
- **The interior decides the drive.** Warp-vs-jump is derived from whether the plan has
  `warp` or `jump` nodes, not from shipData.

Match beam and torpedo **cell** counts to what the hull actually carries, or the ship gets a
weapons damage pool its guns do not match.

## Art, and the paxmesh trap

Art is two fields working **together** — the base name and the folder it lives in, relative
to the executable:

```yaml
artfileroot: dw_breaker
artfilepath: data/missions/__lib__/media/artemis-sbs.Driftwake.media.v1.0.0/ships
```

`artfilepath` **cannot be typed by hand**, because it carries the pack version. Bake it at
build time from `__lib__.json` — every part of the pack name (`{owner}.{repo}.media.{version}`)
is known before release, so your build script or CI can write it in.

!!! danger "Never commit — or ship — a `.paxmesh`"
    A `.paxmesh` is **baked for a location**. It stores its texture paths as length-prefixed
    strings (`ships/<root>_diffuse`), so a mesh baked in one folder looks for its textures
    relative to *where it was baked*, not where it ends up. A committed one points at its
    author's disk.

    Ship the `.obj` and the textures. Put this in `.gitignore`:

    ```gitignore
    *.paxmesh
    *.pointcube
    *.rawbitmap
    *1024.png
    *256.png
    ```

    They are all generated from the `.obj`, and they have to be rebuilt where the art is
    finally placed.

!!! warning "Hull art does not render yet"
    The path mechanism above works and is engine-verified. What does not: **generating
    derived art from a bare `.obj` crashes the engine.** Art that already has its
    `.paxmesh`/`.pointcube`/`1024`/`256` renders fine, which is why the engine's own example
    never hits it — but a mod cannot produce those files.

    Until that is fixed, point `artfileroot` at **art the game already owns** (as the example
    above does with `longbow`). Your ships get correct stats and a familiar hull, and the day
    the crash is fixed you swap in your own meshes and change nothing else.

## Versioning

Put the version in **`__lib__.json` and nowhere else**. Everything derives from it: the
mastlib name, the pack name, `artfilepath`, and a stamp written into your ship file and your
manifest. Log it at load and publish it as a shared variable, so a running game can say which
build it has.

That stamp is what catches a **half-updated install** — a mastlib from one release sitting
beside a media pack from another. Without it that combination loads quietly and renders the
wrong hulls.

## Publishing on GitHub

Recommended, because the tooling already understands it. Model the workflow on
LegendaryMissions': it builds its matrix straight from `__lib__.json`, so adding an add-on
there ships it automatically.

Two things it must get right, both load-bearing:

- **The asset name** is `{owner}.{repo}.{addon}.{tag}.mastlib` — exactly what `sbs lib` writes
  and what a `story.json` refers to. Publish a bare add-on name and no consumer can resolve it.
- **The `.mastlib` must be FLAT**, with `__init__.mast` at the zip root. Nested, MAST cannot
  open it and the add-on **silently never loads**.

Keep the art out of the source archive consumers download:

```gitattributes
media/     export-ignore
mkdocs/    export-ignore
.github/   export-ignore
```

`export-ignore` governs `git archive` only, so a clone and CI still get everything.

!!! warning "The tag is the version"
    The workflow names assets from the **git tag**, while `artfilepath` is baked from
    `__lib__.json`. If the two disagree, the baked path points at a pack that does not exist
    and your art silently is not found. Bump `__lib__.json` and tag with the same string.

Consumers then use `sbs.pyz fetch`, which downloads and unpacks in one step.

## Shipping without GitHub

A mod is just two files. Build locally:

```
sbs.pyz lib Driftwake
```

and send what lands in `__lib__/`:

```
artemis-sbs.Driftwake.dw_races.v1.0.0.mastlib
artemis-sbs.Driftwake.media.v1.0.0.zip
```

The recipient drops both into `data/missions/__lib__/` and then has to get the pack
**unpacked**, which is the step that catches people out:

| Route | How | Cost |
|---|---|---|
| **CLI** | `sbs.pyz lib <any mod folder>` — unpacks every pack in `__lib__` as a side effect | needs `sbs.pyz` |
| **By hand** | extract the zip into `__lib__/media/<zip name minus `.zip`>` | the folder name must match exactly |
| **`resources`** | declare the pack under `resources` instead of `shared_media` and the **engine** unpacks it into the mission | one copy per mission — the duplication shared media exists to remove |

!!! danger "A missing pack is silent"
    Get the folder name wrong and there is **no error**. `media_shared` returns its fallback,
    your ships are never declared, and fleets spawn nothing. On a real mod, removing the
    unpacked pack failed thirteen checks in its test range — but in a game it just looks like
    an empty map.

    Which is the argument for the next section.

## Ship a test range with it

A mastlib that fails to load still reports `PASS - no runtime errors`. So verification has to
assert the **data arrived**, not that the mission survived:

```mast title="Driftwake_TestRange/story.mast"
@map/dw_verify "VERIFY Driftwake"
    await delay_sim(1)
    shared report = dw_verify_run()
```

Worth asserting: every hull exists; nothing stock moved; every playable hull has an interior;
no interior overflows its map; the ladder names only keys that exist; and the mastlib and
media pack versions agree.

Make it a **separate mission folder** with no copy of your add-on inside it — then the
compiler cannot substitute your source folder and it tests the **built** artifact, which is
what people install. It also has to be top-level under `missions/`, because pack pinning only
looks one level deep.

## Related

- [Making add-ons](addons.md) — the `.mastlib` basics
- [Shared media](shared-media.md) — packs, pinning, `export-ignore`
- [Fleets & raiding](fleets.md) — ladders, difficulty, per-faction sides
- [The races add-on](race-addons.md) — how the shipped races do all of this
- [Sides, lifeforms & faces](sides-lifeforms.md)
- [Damage](damage.md) — what an interior's system nodes do
