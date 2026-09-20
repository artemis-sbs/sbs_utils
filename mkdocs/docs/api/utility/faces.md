# The Faces module

The faces module builds character portraits for comms screens, hails, the crew roster and
the avatar editor.

A face is a stack of layers. Each layer names one cell of a race's sprite atlas, and the
cells composite on top of each other at the same box - a body, then clothes, then eyes, a
mouth, hair, a hat. Every cell is 512x512 and already drawn in position, so stacking is
all there is to it.

The atlases are registered in `data/graphics/allFaceFiles.txt`, which maps a short alias
to an image under `data/graphics`. A mod can add its own sheets there.

## The face string syntax

Layers are separated by `;`. **The first layer is the lowest.**

```
<texture-tag> <color-tint> <col> <row> [<x-offset>] [<y-offset>];
```

- `<texture-tag>` - the alias from `allFaceFiles.txt` (`ter`, `tor`, `ska`, `kra`, `zim`,
  `arv`, or a mod's own)
- `<color-tint>` - `#rrggbb` or `#rgb`. `#fff` means no tint.
- `<col>` / `<row>` - which cell
- `<x-offset>` / `<y-offset>` - optional nudge of the source rectangle. The stock sheets
  do not need them; they are drawn already in place.

```python
set_face(officer, "ter #fff 0 0;ter #fff 16 6;ter #fff 1 1;ter #fff 11 2;")
```

## The sheets

Each stock race has its own grid, and **each row of a sheet is one kind of layer**.

| Alias | Race | Grid | Rows |
|---|---|---|---|
| `ter` | Terran | 24 x 7 | body, eyes, mouth, hair, facial hair, headwear, clothes |
| `tor` | Torgoth | 11 x 5 | body, nose, hat, eyes, clothes |
| `ska` | Skaraan | 7 x 5 | body, eyes, mouth, hair/headwear, clothes |
| `kra` | Kralien | 6 x 6 | body, rank pips, eyewear/hat, eyes, mouth, clothes |
| `zim` | Ximni | 8 x 5 | body, hair/horns, eyes, mask/mouth, clothes |
| `arv` | Arvonian | 8 x 4 | body, headdress, hair, clothes |

Some rows hold **more than one feature** side by side: the Terran headwear row is hats
(columns 0-5), eyewear (6-9) and headsets (10-11), and Ximni's row 3 is masks then
mouths. They are separate features, so a character can wear a cap *and* a headset.

**Two races are not built like the others.** Torgoth has no mouth row, and Arvonian's
eight bodies are complete busts with the face painted in - it has no eye or mouth layer
at all, so it has no expressions and no skin tint. Code that walks these tables has to
tolerate a missing layer rather than assume all six races match;
`face_layer_count(race, layer)` answers `0` for exactly this reason.

`_tools/face_contact_sheet.py` renders every cell of a sheet composited over its body and
labeled `row.col`. That is the only practical way to check a layer table against the art,
because a mouth cell on its own is a few hundred pixels of lip in an empty square.

## Making a face

```python
face_build("terran", body=0, eyes=1, mouth=11, hair=3, clothes=16, skin=9)
random_face("terran", gender="female", civilian=False)
random_terran_male()   # and random_skaraan / _torgoth / _kralien / _ximni / _arvonian
```

`face_build` takes the layers by name; a layer left out is not drawn, which is how hats,
facial hair and accessories stay optional. An index larger than a race has wraps rather
than raising.

`build_face(race, values, enables)` is the editor-facing form: indices in
`FACE_FEATURES[race]` order. `parse_face` is its exact inverse, so an editor can open on a
face that already exists without changing it.

## Expressions and speech

The redrawn sheets carry expression art. An expression is a named (eyes, mouth) pair, and
swapping it leaves the body, hair, clothes and every tint alone.

```python
angry = face_expression(get_face(officer), "angry")
face_expressions("terran")   # neutral happy angry worried suspicious shocked asleep
```

A race missing a cell for an expression falls back to neutral; Arvonian has none and
returns the face unchanged.

For speech, `face_talk_frame(face, elapsed)` and `face_blink_frame(face, elapsed)` are
**pure functions of the time** - no ticker, no registry, nothing to reset between
missions. Whatever already has a clock drives them:

```
--- talking
    await delay_sim(0.15)
    the_face.value = face_talk_frame(base_face, talk_elapsed)
    talk_elapsed += 0.15
    jump talking if talk_elapsed < line_seconds
    the_face.value = base_face
```

Assigning is enough: `Face.update()` marks itself dirty, so the engine re-sends the widget
without a page rebuild. Only Terran blinks - the alien sheets draw eye *colors* rather
than eye expressions, so nobody else has a closed-eye cell.

## Tints, and what they can and cannot do

**The engine's only blend mode for a face layer is MULTIPLY, so a tint can only darken.**
That is the single most important thing to know about face color. A palette written as
"the color I want to see" is therefore half unusable: measured against the current art,
only 3 of 31 skin tones were absolutely reachable on Kralien and 8 on Skaraan.

So the shipped palettes keep each tone's hue and saturation and re-map its lightness into
the range multiply can reach. Every slider position is distinct and the ramp is
monotonic, but it is **a ramp down from the skin as painted, not an absolute color
picker**. Absolute control needs a desaturated gray body cell in the art, which is an
outstanding request to the artist.

```python
face_tint("terran", "skin", 9)                       # a palette index -> a tint hex
face_tone_names("terran", "skin")                    # names, for a control
face_tone_index("terran", "skin", "emerald")         # by name, rather than counting
face_tone_indices("terran", "skin", natural_only=True)
```

**Non-human tones need different maths, and they have it.** Multiplying a blue tint
through warm skin does not give blue - it just darkens toward the base and comes out
brown (`ice-blue` measured `#67553f`). So those tones divide the base skin out of the
tint first, which cancels its warmth and lets the hue survive. Reds land exactly, since
red is the base's strongest channel.

`EXOTIC_SKIN` lists them - `emerald`, `jade`, `ice-blue`, `cobalt`, `rust`, `crimson`,
`ashen`, `amber` - and they are excluded from the natural pool, so a random Terran never
rolls one. They read clearly on all five tinted races, Torgoth included.

Do not predict how dark one of these lands from the median skin value: the median says a
blue must come out muddy and the rendered face disagrees, because its highlights sit far
above the median and carry the hue. Render it (`_tools/face_render.py`).

The palettes live in `sbs_utils/face_tints.py`, which is **generated** by
`_tools/face_tint_calibrate.py` from the art itself - do not hand-edit it, rerun the tool.

`face_tone_indices(..., natural_only=True)` exists because the palette deliberately
carries green, blue and violet skins and fuchsia hair, for aliens and for missions that
ask. A random Terran must not roll one.

**The skin tint covers the eye and mouth layers too, not just the body.** Those cells are
not clean cutouts - an eye cell is 17-31% skin and a mouth cell 19-40%: brow ridge,
eyelid, the surround of the lips. Tint the body alone and that skin keeps the color it
was painted, so a re-toned face wears a pale mask around the eyes and a pale muzzle,
glaring on a dark or non-human tone. The Torgoth nose is skin as well. Equipment sharing
those rows is excluded: a Ximni breathing mask and a Torgoth eye-plate are hardware, and
must not change color when somebody changes complexion.

Hair and facial hair take the hair palette. Hats, clothes and accessories are never
tinted. Arvonian has no skin palette at all - its eight bodies are painted busts.

## Resting faces vs expressions

Some cells are states rather than identities: a closed eye, an eye-roll, a mouth caught
mid-word. They are what expressions and the talking animation are made of, and the editor
offers every one of them - but a randomizer must not hand one to somebody as their
standing portrait, or you get an officer who is permanently asleep or forever saying
"oh". `FACE_LAYERS[race]["resting"]` names the indices a random face may use; a layer
with no entry has no unsuitable cells.

This narrows the **randomizer only**. `face_layer_count`, `face_cell`, `face_expression`
and the editor all still reach the full set.

## No layer offsets

A face string may carry an `ox`/`oy` nudge, and the pre-redraw builder used them heavily
(`6 -2` for hair, `14 -2` for a hat, `12 4` for facial hair, `20 4` for an accessory).
**The current builders emit none.** Every cell on the new sheets is drawn already in
position, so a nudge would only move it off. The v1 parser still recognizes the old
offsets, because it has to read strings that were written with them.

## Faces authored before the 2026-09 redraw

The six stock atlases were **replaced in place** - same aliases, same filenames, different
grids and different meanings per cell. An old face string is not merely wrong-looking: it
names cells that now hold something else entirely.

It is also **indistinguishable from a current one**. `ter #fff 3 0` used to be a feminine
face and is now hair #3 - the same six tokens. Nothing can tell them apart at runtime, so
**migration is never automatic**. A caller has to know that what it is holding predates
the change.

```python
face_migrate(old_face_string)   # read against the old layout, rebuilt against the new
face_is_valid(face_string)      # every layer names a cell that exists
```

`face_migrate` is deterministic and returns a valid face of the right race. It is not
idempotent - a migrated face is a perfectly good face string, so running it twice restyles
the person again.

Where the new art dropped a feature its index is folded into one that survives (a
Torgoth's mouth into its nose; an Arvonian's eyes and mouth into the choice of bust), so
two old faces that looked different still look different.

`face_is_valid` is a **partial** check and worth knowing how partial: it catches most
stale alien faces, whose old rows 5-7 no longer exist, and almost no stale Terran one,
because the new 24 x 7 grid still contains nearly every coordinate the old 15 x 8 could
name. A `True` answer means "not obviously stale", never "current".

Two tools do the repair:

- `_tools/face_migrate_sources.py <path> --write` rewrites literal face strings in source
  files, printing every change, and keeps a ledger so a second pass cannot silently
  restyle everybody.
- Faces saved in a player's own `client_string_set.txt` carry a format stamp
  (`crew_self_pack` / `crew_self_unpack`); an unstamped record is migrated once on read
  and re-saved.

## Character faces

`Characters` holds a few ready-made face strings, useful as worked examples.

## API: faces module

::: sbs_utils.faces
