# Making add-ons (`.mastlib`)

An **add-on** packages reusable MAST (consoles, comms trees, prefabs, routes) so
other missions can load it. sbs_utils ships the Legendary Missions add-ons this
way. An add-on is a **module**: a folder with an `__init__.mast` that imports the
rest.

## Lay out the module

```
MyAddon/                 # a dev mission that hosts the add-on
├── script.py            # standard boilerplate
├── story.mast           # minimal test harness (not the add-on)
├── story.json           # sbslib + any mastlibs the add-on needs
├── __lib__.json         # declares the add-on folder for the packager
└── my_addon/            # THE ADD-ON -> becomes my_addon.mastlib
    ├── __init__.mast    # entry point - imports the rest
    ├── panels.mast
    └── helpers.py       # Python helpers are fine too
```

`my_addon/__init__.mast` just imports its files:

```
import panels.mast
import helpers.py
```

`__lib__.json` names the folder(s) to package:

```json
{
    "version": "v1.0.0",
    "mastlib": ["my_addon"]
}
```

## Develop, then package

While developing, keep the add-on folder **inside a mission** &mdash; the mission
directory is on the MAST search path, so its labels load automatically. When
ready to share:

```
sbs lib MyAddon -u your-github-user      # builds your-github-user.my_addon.v1.0.0.mastlib
```

Drop the `.mastlib` in `__lib__/` and add it to another mission's `story.json`:

```json
{ "mastlib": ["your-github-user.my_addon.v1.0.0.mastlib"] }
```

Its labels, routes, and prefabs are now available globally in that mission. Add-ons
are a great way to share partial missions &mdash; Gamemaster comms, custom
consoles, prefab libraries, and so on. See
[Sharing reusable Python](../tooling/libraries.md) for the `.sbslib` side.
