# Shared media, and custom icon sheets

Art is copied once per consuming mission today. This is the plan to make it live once,
to let `sbs.pyz` own the unpacking, and — on top of that — to give missions custom icon
sheets that a non-programmer can declare.

Status: **the probe is built; nothing else has started.**

---

## Where we are

```
LegendaryMissions/media/LegendaryMissions/**     27 MB, tracked in LM's git   <- source
  __lib__.json: "zip": ["media"]
  -> sbs.pyz lib -> __lib__/artemis-sbs.LegendaryMissions.media.v1.4.0.zip
       -> SecretMeeting/media/LegendaryMissions/**   27 MB, gitignored
       -> OpenUniverse/media/LegendaryMissions/**    27 MB, gitignored
```

**81 MB of disk for 27 MB of art**, growing by 27 MB per mission that declares the pack.
`fetch_deps` only downloads the zip into `__lib__/` — it never unpacks — so today's
per-mission copies come from somewhere else (the engine at load, or a hand copy).

## What makes "live once" possible

Every image path handed to the engine is **relative to `data/graphics`** — `ImageAtlas`
ends with `os.path.relpath(file, get_artemis_graphics_dir())`. So a mission asset already
reaches the engine as `..\missions\<mission>\media\...`: the renderer is *already*
walking out of `data/graphics` to find art.

A shared copy is the same shape with a different folder name:

```
..\missions\SecretMeeting\media\LegendaryMissions\casino\terran_back   <- works today
..\missions\__lib__\media\LegendaryMissions\casino\terran_back         <- the question
```

`__lib__/` is the right home: already shared, already versioned, already gitignored, and
already where dependencies land. It reads as a build product rather than source, which
is what an unpacked pack is.

## The two things the probe answers

`missions/media_probe` renders the same art four ways and lets the ENGINE decide.

1. **Where may art live?** A control tile (this mission's own `media/`) beside a shared
   tile (`__lib__/media/...`). If both draw, the shared layout is legal and the rest of
   this plan is unblocked. If only the control draws, the engine restricts paths to the
   mission folder and we fall back to directory junctions.

2. **What unit is `sub_rect`?** The casino passes **pixels** (`value * 190`); the browser
   mock reads the same numbers as **0..1** texture coordinates ([client.html:383-392]).
   They cannot both be right. Two tiles ask for the same card each way — whichever shows
   one clean card is the engine's unit, and the other consumer has a bug to fix.

Everything below assumes answer 1 is "both draw". If it is not, stop and re-plan.

---

## Phase 1 — `sbs.pyz` owns the unpack

The CLI builds the zip; it should place the unpacked copy too, so nothing depends on the
engine's behaviour and a developer working from source gets the same layout as a player.

- `sbs.pyz lib <folder>` writes the zip as it does now, then unpacks it to
  `__lib__/media/<pack>/` **when the stamp says it is stale**.
- `sbs.pyz fetch` does the same after downloading a `resources.media` zip.
- **Stamp** at `__lib__/media/.stamp.json`:
  ```json
  { "artemis-sbs.LegendaryMissions.media": { "version": "v1.4.0", "hash": "<names+sizes+mtimes>" } }
  ```
  Version alone is not enough: during development the art changes while the version stays
  `v1.4.0_dev`, which is exactly when a stale copy bites. Hash the source listing, not the
  file bodies — 27 MB of art hashed on every build is a tax nobody will pay.
- Unpack is idempotent and safe to interrupt: write to `__lib__/media/.tmp-<pack>/`, then
  replace.

## Phase 2 — prove it on real LM art

1. Register an existing card back from BOTH paths under two keys, render side by side in
   a mission that already uses the casino. Same art, two homes, one screen.
2. When that holds, point the casino at the shared path and delete a per-mission copy.
   Nothing else changes: `CASINO_MEDIA` is one constant.
3. Then the other consumers, one at a time.

**Do not migrate audio, music or skyboxes with them.** Those are resolved by the ENGINE
from mission-relative paths, not by `ImageAtlas`, and may not tolerate a shared root at
all. Graphics first; the rest is a separate question with its own probe. If graphics
prove out, that is the evidence to take to the engine team for the other types.

## Phase 3 — the sheet provider

With art living once, custom icon sheets become worth building.

- `gui_image_add_atlas_grid(sheet, cols, rows, names, cell=None)` — the casino hand-loops
  cell arithmetic in `casino_media.py`; this replaces it with one call.
- `domain=` namespacing on registration, the way the AMD schema does it, so two addons
  cannot silently claim the same key. (`ImageAtlas.all` is one process-wide dict today.)
- `is_valid()` wired into `sbs lint`: a missing sheet or an out-of-range cell should be
  loud. Today it renders nothing, silently.
- `gui_icon_named(name, color)` — an icon-shaped wrapper that takes a NAME and renders
  whichever backing that name has: a built-in `icon_index` or an atlas cell. This is the
  indirection that lets consumers be written before any art exists.

## Phase 4 — icons declared in AMD

An icon is a catalog entry: not an Agent, not dialogue. It earns a small `icon`
archetype, the way `recipe` did.

```amd
## [Icons](icons)
---
Sheet: media/LegendaryMissions/icons/quest-sheet
Cell: 64
---
The quest log's glyphs. White silhouettes - color is applied per use.

# [Job](quest.job)
---
At: 0, 0
---

# [Beat](quest.beat)
---
At: 1, 0
Color: #888
---
```

Three things fall out for free:

- **`At:` is already `coord2`**, so the Inspector renders a two-cell picker with no new
  widget work.
- `icons_declare_amd(section)` mirrors `sides_declare_amd` — walk the records, call
  `gui_image_add_atlas`.
- A mission can **re-declare `quest.job`** and re-skin every consumer without touching
  library code; a mission that ships no sheet falls back to the registered built-in
  index, so a row is never blank.

## Phase 5 — the sheet itself

Draw `media/LegendaryMissions/icons/quest-sheet.png` — an 8x8 grid of 64px **white
silhouettes**. Color is applied per use, so one glyph serves every state and a small
sheet goes a long way. Ships in LM's media pack, so every mission that already declares
it gets the icons free.

## Phase 6 — the consumers

The quest log is the first: shape per kind (Job / Objective / Beat / Arc), and the
redundant state sub-line replaced by progress, pays, or time remaining. **Parked until
the media work lands** — deliberately, so the log is written once against names rather
than twice against glyphs.

---

## Open questions

- **Who unpacks today?** If the engine unpacks `resources.media` into the mission folder
  at load, it will keep doing so after phase 1 and we get both copies until the consumer
  stops declaring the pack. Worth knowing before phase 2 step 2.
- **Is `resources.media` a single string or a list?** It is a string in every `story.json`
  here. If it is single-valued, a separate icons pack would compete with LM's rather than
  add to it — which is the argument for icons living inside LM's pack.
- **Does `..` out of `data/graphics` survive on every platform** the engine ships on?
  The probe answers it for this machine only.
