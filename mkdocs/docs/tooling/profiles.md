# Profiles

A **profile** is one named file that decides how a mission runs — its settings, and which
add-ons and art packs it loads. You select it by name and nothing else changes:

```
Artemis3-x64-release.exe autostartserver defaultmission=LegendaryMissions profile=a28_skies
python -m cosmos_dev.mission_runner . --test 20 --map 0 --profile a28_skies
```

It lives at `<mission>/profiles/<name>.yaml`.

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
  <  profile=<name>
  <  the COSMOS_SETTINGS environment variable
  <  var.NAME= on the command line
```

Whole-key replace, not a deep merge: a profile's `AUTO_PLAY` replaces the entire
`AUTO_PLAY` entry rather than merging into it.

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

!!! note "Profiles are per mission"
    `profiles/` is read from the mission folder only. Two missions that want the same
    profile need a copy each.

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
