# The amd_assets module

Resolving `image://`, `face://` and `ship://` for a document rendered **outside** the engine.

## Overview

`media_paths` already answers "where does this art live", but through
`fs.get_mission_dir_filename`, which needs an install and a running mission. A static
exporter has only a folder, so this mirrors that module's **search order** against a
folder handed to it — the mission's own `media/`, then each pack `story.json` pins, then
the engine's `data/graphics`.

| Scheme | Resolves? |
|---|---|
| `image://` | **Yes.** Including engine built-ins like `ball`, which live in the install rather than any mission |
| `face://` | **No file — but it composites.** The value names cells of a race atlas, and those atlases are real PNGs. `cosmos_dev/mockgui/face.js` is the canonical compositor and carries a `setSheetResolver` hook precisely so another host can use it |
| `ship://` | **No.** The tag names a 3D hull; the `.png` beside each mesh is its *diffuse texture*, a near-white sheet that prints as a blank box |

A placeholder is a real answer, not a failure: a printed page should say "a ship goes
here" rather than closing the gap silently, because art nobody can see is missing is art
nobody restores.

## API

::: sbs_utils.procedural.amd_assets
