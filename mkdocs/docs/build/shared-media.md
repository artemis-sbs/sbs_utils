# Shared media — art that lives once

A mission that wants art someone else made used to get its own copy of it. LegendaryMissions'
27 MB of console backdrops, card decks and portraits ended up duplicated into **every**
mission that declared it — 314 MB on disk for 27 MB of art, and a re-release meant every
one of those copies went stale.

Now the pack is unpacked **once**, beside the libraries, and every mission reads it there.

```
data/missions/__lib__/
    artemis-sbs.LegendaryMissions.media.v1.4.0.zip        the artifact you fetched
    media/
        artemis-sbs.LegendaryMissions.media.v1.4.0/       unpacked once, per VERSION
            casino/terran_deck.png
            helm/consoles0001.png
```

## Using a pack

Declare it in your mission's `story.json` under **`shared_media`**:

```json
{
    "sbslib": ["artemis-sbs.sbs_utils.v1.4.0.sbslib"],
    "shared_media": ["artemis-sbs.LegendaryMissions.media.v1.4.0.zip"]
}
```

Then ask for a file by its path **inside** the pack — never by where it was unpacked:

```python
from sbs_utils.procedural.media_paths import media_shared
from sbs_utils.procedural.gui import gui_image_add_atlas

gui_image_add_atlas("card_back", media_shared("casino/terran_back"))
```

`media_shared()` searches, in order:

1. **this mission's own `media/`** — so a clone can keep editing art in place,
2. **each pack the mission declares**, in the order declared.

Mission-local first is what makes overriding one file easy: drop your own
`media/casino/terran_back.png` in and it wins, with no other change.

!!! warning "Never hardcode the unpacked path"
    `__lib__/media/<pack>-v1.4.0/...` contains the **version**. Write it by hand and your
    mission breaks the next time the pack is re-released. That is the whole reason
    `media_shared()` exists.

## `shared_media` vs `resources`

Both declare a dependency on a media zip. The difference is who copies it.

| | who unpacks it | where it lands |
|---|---|---|
| `resources` | the **engine** | copied into `<your mission>/media/` — a duplicate per mission |
| `shared_media` | `sbs.pyz` (at fetch/unpack time) | `__lib__/media/<pack>/` — **one copy, shared** |

The engine ignores `shared_media`, which is exactly why it can mean "don't copy this".
Use `resources` only when a mission genuinely needs its own writable copy.

## Publishing a pack

Add the folder to your `__lib__.json` under `zip`:

```json
{
    "version": "v1.4.0",
    "mastlib": ["consoles", "casino"],
    "zip": ["media"]
}
```

`sbs.pyz lib <folder>` builds `<owner>.<repo>.media.<version>.zip` alongside your
`.mastlib` files, and `sbs.pyz release` publishes it as a release asset.

If your repo publishes a pack, you probably also want the art **out of the source
archive** that consumers download — otherwise a fetch still drags 27 MB along that
nothing reads. `.gitattributes`:

```gitattributes
media/          export-ignore
mkdocs/         export-ignore
.github/        export-ignore
```

`export-ignore` governs `git archive` only, so a clone and CI still get everything and
the pack still builds from the real art.

## Things worth knowing

- **`sub_rect` is in pixels.** Cutting a cell out of a sheet is
  `gui_image_add_atlas(key, file, l, t, r, b)` in pixel coordinates, not 0–1 texture
  coordinates. See [Icons by name](../cosmos/gui_icons.md).
- **Re-releasing a pack doesn't reach existing copies.** `sbs.pyz fetch` skips a
  dependency already in `__lib__`; pass `-o` / `--overwrite_libs` to pull the new one.
- **Unpacking is per version**, so two missions pinned to different pack versions coexist.
- **A mission pinned to an older `sbs_utils`** has no `media_shared()`, and should keep
  its own `media/` folder as before.
- **Images, today.** Sheets, backdrops and portraits are proven from a shared pack. A
  skybox or music path is resolved by sbs_utils and opened by the engine — the resolution
  searches shared packs too, but nothing has yet asked the engine to open one from there.
