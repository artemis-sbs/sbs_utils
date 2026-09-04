# Profiles

A **profile** is one named file that decides how a mission runs — its settings, and which
add-ons and art packs it loads. You select it by name and nothing else changes:

```
Artemis3-x64-release.exe autostartserver defaultmission=LegendaryMissions profile=a28_skies
python -m cosmos_dev.mission_runner . --test 20 --map 0 --profile a28_skies
```

It lives in one of two places, searched in this order:

| path | authored by | scope |
|---|---|---|
| `<mission>/profiles/<name>.yaml` | whoever wrote the mission; ships with it | that mission |
| `<missions>/common_data/profiles/<name>.yaml` | the **operator**; not inside any mission | every mission |

Both are full profiles - settings, `addons:` and `media:` alike. The mission's own wins a
name collision, so a mission can always ship a definitive profile under a name an operator
also uses. Which one answered is logged.

The shared tier exists because an operator's house setup is not mission content: written
into a mission folder it needs a `.gitignore` line and does not survive a re-extract, and
`common_data` sits beside the missions instead. **A shared profile can select content**,
which is most of the point - `addons: include:` falls back to `__lib__` and a media pack
matches the packs there, and both of those are shared, so "the Artemis 2.8 skies in
whatever I am running tonight" is one file rather than one copy per mission:

```
sbs run server,science,comms profile=a28_skies -m WalkTheLine
```

Only `exclude:` names something a particular mission declared, and an `exclude` that
matches nothing is a no-op filter rather than an error - so the same file is safe to point
at a mission that never had the add-on you are replacing.

## Several at once

Name more than one, comma separated, and they are merged **left to right** - the last one
typed wins any settings key the earlier ones also set:

```
... profile=house,a28_skies,soak
python -m cosmos_dev.mission_runner . --test 20 --map 0 --profile house,a28_skies
```

This is what keeps profiles from being combinatorial. Three house setups and four content
packs is seven files if they compose and twelve if they do not, and the twelve drift apart
the first time one of them is edited. Write one profile per *decision* - the venue, the
mods, the run style - and pick the ones you want at launch.

`addons:` and `media:` **accumulate** rather than replace, which is the behavior these
sections need: excluding the stock skybox in one profile and adding a debug add-on in
another has to do both, and a last-wins rule would keep only the second. Includes
concatenate in typed order and excludes union; duplicates are listed once. An entry one
profile excludes and a later one includes ends up in both lists, and the **include wins** -
excludes are applied first - so a specific profile can re-add something a broad one removed.

A name that matches no file is warned about and **skipped**, and the rest still apply. One
typo in a list of four must not discard the other three.

The merge order is logged, because the result depends on it:

```
profiles merged, later wins: house < a28_skies < soak
```

## Why a file and not more arguments

A Windows command line is capped at 8191 characters, shortcuts truncate it, quoting around
spaces and `=` is awkward, and none of it can be commented, reviewed or diffed. A file is
all of those things. Put the twenty settings in a profile and let the command line name
it — plus a `var.` or two for whatever you are changing right now:

```
... profile=soak var.DIFFICULTY=3
```

## Settings

The plain case: any settings key, exactly as it would appear in `settings.yaml`.

```yaml title="missions/MyMission/profiles/soak.yaml"
DIFFICULTY: 11
MAP_SIZE: Huge
AUTO_PLAY:
    enable: true
```

Merged in this order, each beating the one before:

```
built-in defaults
  <  a mod's settings_set_mod_default()
  <  the mission's settings.yaml
  <  profile=<name>            (several: merged left to right, last wins)
  <  the COSMOS_SETTINGS environment variable
  <  var.NAME= on the command line
```

Whole-key replace, not a deep merge: a profile's `AUTO_PLAY` replaces the entire
`AUTO_PLAY` entry rather than merging into it. The same is true between two profiles -
`profile=a,b` where both set `AUTO_PLAY` gives you b's, whole.

## Add-ons and media packs

A profile can also add and remove **add-ons** and **art packs** relative to `story.json`.
This is what turns a profile from "a bundle of settings" into "a way to run the same
mission with different content".

```yaml title="missions/LegendaryMissions/profiles/a28_skies.yaml"
addons:
    exclude:
        - basic_random_skybox      # the eight stock skies
    include:
        - a28_skyboxes             # the thirty Artemis 2.8 ones

media:
    include:
        - A28-Skybox-Mod.media     # ...and their art

PLAYABLE_RACES: "USFP"             # settings keys still work, in the same file
```

**Name the folder, never the version.** `a28_skyboxes`, not
`artemis-sbs.A28-Skybox-Mod.a28_skyboxes.v1.0.0.mastlib`. Versions belong in `story.json`;
a profile that spelled one would break on the next release of the pack. An `include`
resolves the way a declared lib does — a mission-local source folder first, then the newest
matching `.mastlib` in `__lib__`. Media packs match on a substring, for the same reason.

Names are matched case-insensitively, and a section may be a single string instead of a
list.

### Add versus replace

The two shipped LegendaryMissions profiles differ by one `exclude:` block, which is the
clearest statement of what the feature does. Measured, seed 7, map 0:

| profile | stock skies | A28 skies |
|---|---|---|
| *(none)* | 7 | 0 |
| `a28_add` | 7 | 30 |
| `a28_skies` | 0 | 30 |

### Everything is logged by name

```
[runner] profile: a28_skies
profile: dropped 1 addon(s): basic_random_skybox
profile: added addon 'a28_skyboxes' -> artemis-sbs.A28-Skybox-Mod.a28_skyboxes.v1.0.0.mastlib
profile: dropped 1 mission addon folder(s): basic_random_skybox
profile: added media pack artemis-sbs.A28-Skybox-Mod.media.v1.0.0
```

That is not decoration. An add-on that vanished silently is indistinguishable from one the
mission never declared, and the symptom of getting it wrong is a story that compiles to
**zero labels** while still reporting `PASS`.

There are two drop lines because there are two ways an add-on loads. A repo running from
its own clone — LegendaryMissions itself — resolves its declared libs to **source folders**
and loads them through the directory walk rather than the `mastlib` list. Both are filtered.

## Gotchas

!!! warning "Excluding an add-on that another one `requires` empties the whole story"
    `requires` is a hard compile barrier, so dropping `gamemaster` while `gamemaster_comms`
    is loaded compiles **nothing**. The error names the profile and what it removed, so the
    cause is in the message rather than something to deduce.

!!! warning "An add-on may own more than its name suggests"
    The quiet version of the same trap has no error at all. LegendaryMissions' stock music
    banks used to be declared inside `basic_random_skybox`, so a profile that swapped the
    **skies** turned the soundtrack off. (They now live in the `consoles` add-on, beside the
    console that picks one.) If a profile makes something unrelated disappear, look at what
    else the excluded add-on declared.

!!! note "Art needs its pack"
    `addons: include:` gets you the labels; `media: include:` gets you the files. Without
    the pack every `@media/skybox` label fails its file test and is dropped from the random
    pick — silently, with no error, leaving you the stock set.

!!! note "A mission's own profiles are per mission"
    A mission's `profiles/` folder is read from that mission only. Two missions that want
    the same *content* profile need a copy each - `addons:`/`media:` cannot be shared,
    because they name things one `story.json` declares. A **settings** profile can be
    shared: put it in `common_data/profiles/` and every mission sees it.

## It follows a restart, not a mission switch

A profile applies to every restart of the mission you launched, for as long as the
engine is running - the launch arguments do not change and the file is re-read each
time. Restart into a **different** mission and it is dropped instead, with a line in
the log: `profiles/` is per mission, so the same name there would be a different
file meaning something else entirely. See
[Switching missions](command-line.md#switching-missions).

## A profile is not a saved setup

A profile is written by a person, in an editor, and it is *input*. What the game writes -
a named preset from the server console, or the last-used setup behind
`RESTORE_LAST_SETUP` - is *output*, and lives under
`<missions>/common_data/game_codes/<mission>.yaml`. Reach for a profile when you have
several standing configurations to choose between at launch; reach for a preset when you
want to keep the setup you just built on screen.

**Player ships in particular.** A profile's `PLAYER_LIST` is the roster: name, side, hull
**and face**, per slot. A saved setup carries only names and hulls, as a capture of what
the crew actually flew. So a standing roster belongs in a profile; "the ships we flew last
time" belongs in a saved setup. A code you *share* carries neither - ship names are not
part of the match.

## What a profile cannot do

`resources` and `shared_media` packs are filtered, and `mastlib` add-ons are filtered — all
three are read by Python before anything compiles. The `sbslib` list is **not**: it is read
by `PyAddons/sbslibs.py` at `import script`, before a profile has been looked at, so the
library a mission runs against is fixed by `story.json`.

## Where it happens

Nothing about this involves the engine — it has never heard of `story.json`. The add-on
list is assembled by `Mast.find_add_ons()` and `find_imports()` in ordinary Python, inside
a live frame, before a single `.mastlib` zip is opened, which is why a profile can filter
it at all. Confirmed in the real engine on 2026-08-16.
