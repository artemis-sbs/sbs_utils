# Making add-ons (`.mastlib`)

An **add-on** packages reusable MAST (consoles, comms trees, prefabs, routes) so
other missions can load it. sbs_utils ships the Legendary Missions add-ons this
way. An add-on is a **module**: a folder with an `__init__.mast` that imports the
rest.

## Start from the template

```
sbs create MyAddon -t addon
```

That gives you the layout below already wired up &mdash; including a harness map, so
`sbs debug MyAddon --map 0` puts the add-on's console in front of you straight away.
The rest of this page is what those pieces are.

!!! note "v1.4.0 and later"
    The `addon` template uses `provides` / `requires`, which don't exist on v1.3.0, so
    it only appears on the v1.4.0 line. See [the CLI](../tooling/cli.md#release-lines).

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

## Declare what it needs

Add-ons share one global namespace and load in **no fixed order**, so "my add-on uses
a label from theirs" is only safe if you say so. Three directives at the top of
`__init__.mast` (column 0, like `import`) make the contract explicit, and they're
checked at **compile time**:

```
provides hangar.sortie_board     # this add-on supplies a capability
suggests hangar                  # SOFT: warn if absent, never fail
requires gamemaster              # HARD: fail the compile if nothing provides it
```

Tokens are opaque strings, dotted by convention; several per line is fine
(`provides casino, casino.bar`). Collection is **order-independent** — the compiler
gathers every `provides` as files compile, then validates once at the end.

Use `requires` when you call the other add-on's globals or routes, or your feature is
meaningless without it. Use `suggests` for an optional augmentation, guarded with
`default shared X = None` so it degrades gracefully.

An unmet `requires` is a compile error, surfaced by `sbs lint` and `--test` and shown
as a runtime error screen. These are compile-time only — no runtime effect — and
backward compatible: a line is a directive only when a token follows the keyword, so
`requires = 5` is still an assignment.

!!! note "v1.4.0 and later"
    Missions on the v1.3.0 line can't use these.

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

An add-on that also carries content the **engine** has to open — ships, interiors, art — is a
**mod**, and needs a media pack alongside the `.mastlib`. See [Making a mod](making-a-mod.md).
