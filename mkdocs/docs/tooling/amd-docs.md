# Printing a mission: `sbs docs`

AMD is where a mission's design lives - the quests, the dialogue, the factions,
the lore, the help text. Until now the only thing that could read it was the
game, so a writer reviewing dialogue, a modder looking up faction keys and a
playtester reading a mission bible all had to open a code editor and read markup.

`sbs docs` renders a mission's `.amd` files into **one self-contained HTML file
laid out for paper**.

```
sbs docs .                       # the prose edition, into ./__docs__/
sbs docs . --lens all            # all four editions
sbs docs . --lens catalog --open # build one and open it
```

## Getting a PDF

```
sbs docs . --pdf                 # HTML and PDF, side by side
sbs docs . --lens all --pdf      # four editions, plus one bound book
```

**No Python library is involved**, and that is deliberate: `sbs` runs on the
embedded CPython in `PyRuntime`, whose `python311._pth` has `import site`
commented out, so `site-packages` is never on `sys.path` and `PYTHONPATH` is
ignored. A pip-installed PDF library would be invisible to it. So `--pdf` shells
out to a program instead.

### Two engines, and they are not interchangeable

| | Faces | Contents page numbers | Install |
|---|---|---|---|
| **Headless Chrome / Edge** | composited | no | none - Edge ships with Windows |
| **`weasyprint` CLI** | **blank - it runs no JavaScript** | yes, plus exact `@page` margins | needs GTK/Pango natives |

`auto` picks the **browser when the document has faces**, because weasyprint
would print every one of them as a blank box, and **weasyprint otherwise**,
because it is the better typesetter and turns on the `target-counter` page
numbers the stylesheet already emits. It says which it chose, and why, in one
line. Override with `--pdf-engine chrome|weasyprint`.

When weasyprint is used on a document that *does* have faces, they are rendered
as honest placeholders rather than blank boxes - the same rule the on-screen
renderer follows when the compositor is unavailable.

### Two tables of contents

The **Contents page** is part of the document and is always there.

The **PDF outline** - the bookmark tree a reader navigates by in the sidebar -
has no HTML equivalent, and is built two different ways:

- **weasyprint** builds it from the `bookmark-level` CSS the stylesheet emits.
- **Chrome** has no bookmark facility at all. But it does write a named
  destination for every anchor, using the page's own ids, so the page each
  record landed on is already recorded in the file. With `pypdf` installed the
  tree is added from those:

```
sbs deps install pypdf
```

That also binds `--lens all --pdf` into a single book with each edition as a
chapter. Without pypdf you get the four PDFs and no outline, which is a
document, not a failure - `sbs docs` says so once and moves on.

### Other PDF options

| Option | Effect |
|---|---|
| `--pdf-engine auto\|chrome\|weasyprint` | Force an engine |
| `--browser <path>` | Point at a specific `chrome.exe` / `msedge.exe` (also `SBS_BROWSER`) |
| `--pdf-timeout 90` | Seconds to allow the engine |

`--pdf` also upgrades `--assets` from `none` to `link`, unless you passed
`--assets` yourself - a PDF is where the art matters, and linking costs nothing
because the paths are relative to `__docs__`, where the HTML lands.

## Four lenses, because AMD is three documents wearing one syntax

The number of renderings is the number of **audiences**, not the number of record
kinds.

| Lens | Reads | What it is for |
|---|---|---|
| `prose` | every record, in document order | A manual or a story book. The lens the fence-less files were written for - `help_docs.amd`, `library_docs.amd`, `lore.amd`, where the body already *is* markdown. |
| `catalog` | every record that has a `---` fence, grouped by archetype | A sourcebook. Reference cards you look things up in. |
| `screenplay` | dialogue, cutscenes, and anything with spoken lines | A script someone could read aloud, in Fountain geometry. |
| `bible` | the whole mission, structured by the story timeline | A design document: the quest spine, its triggers, and the causal graph. |

A file with no fence at all is prose and converts almost directly. A file whose
content **is** the fence is a catalog - printing `Color: #ffcc44` as a line of
text would be worthless, so the catalog renders each field as its **type**: a
color becomes a swatch, a reference becomes a working link, a coordinate becomes
a cell chip. That typing comes from `amd_schema`, the same registry the editor
and the linter use.

## Two profiles

```
sbs docs . --profile author      # default
sbs docs . --profile player
```

`player` is a **hard filter, not a stylesheet class**. What it withholds is
absent from the file, because "print to PDF" and "view source" have to agree
about what a player was told.

| Content | `player` | `author` |
|---|---|---|
| `= ` synopsis (author-only note) | dropped | shown as a margin note |
| `/* ... */` cut text | never parsed at all | never parsed at all |
| Choice guard, outcomes, target key | label only | in full |
| Speech gate (`%{standing < -20}`) | variants print flat | condition chip |
| Trigger fields (`Then:`, `Starts when:`, `Action:`, `Scope:`, `Show:`) | dropped | in full |
| Player-facing fields (`Objective:`, `Reward:`, `Scan says:`) | shown | shown |

**The bible has no player profile and refuses one.** It exists to show the
machine - every trigger, every hidden beat, every branch. The bible *is* the
spoiler.

## Art

```
sbs docs . --assets embed        # inline the bytes (self-contained)
sbs docs . --assets link         # relative paths (smaller, breaks if moved)
sbs docs . --assets none         # placeholders everywhere (default)
```

Three schemes, three different answers - and only one of them is a real
limitation.

**`image://` resolves to a file.** The search covers the mission's own `media/`,
each pack `story.json` pins, **and the engine's `data/graphics`**. That last one
matters: keys like `ball` and `test` are engine built-ins that live in the
install, not in any mission, so a search stopping at the mission folder reports
art as missing that is sitting right there.

**`face://` has no file, but composites.** The value is a face-*builder* string
naming cells of a race atlas, and those atlases are real 4096x4096 PNGs in the
engine graphics folder. `cosmos_dev/mockgui/face.js` is the canonical compositor
and carries a `setSheetResolver` hook precisely so a host other than the mock
server can say where a sheet comes from - the printed page is simply a third
host. Faces render onto a `<canvas>`, drawn on load and again on `beforeprint`.

Only the atlases a document actually references are pulled in, so a cast that is
all Zimni costs 0.44 MB rather than the 6.8 MB of all six sheets.

**`ship://` genuinely cannot resolve, and stays a placeholder.** The tag names a
3D hull. The `.png` beside each mesh is its *diffuse texture*, not a picture of
the ship - `ships/tsn_light_cruiser.png` is a near-white sheet that would print
as a blank box. The browser mock does not draw one either.

!!! tip "Watch the page size"
    `--assets embed` inlines every atlas, which for a mission spanning all six
    races is around 9 MB. `--assets link` references the art by relative path
    instead: the same document drops to about 110 KB. It stops working if the
    file is moved, which is the right trade while iterating and the wrong one for
    something you hand to someone else. `sbs docs` prints the page size, and
    suggests `link` when a page gets large.

## Other options

| Option | Effect |
|---|---|
| `-o, --out PATH` | Where to write (single lens only). Default `<folder>/__docs__/<name>-<lens>.html` |
| `--format json` | The block model as data instead of a page - for tools, and the artifact the golden test pins |
| `--title TEXT` | Document title. Default: the folder name |
| `--include` / `--exclude` | Glob filters over the `.amd` files, repeatable |
| `--show-internal` | Show fields the schema marks internal (schema debugging) |
| `--open` | Open the result in a browser |

## How it fits together

```
.amd  ->  amd_core.parse   ->  AmdDocument   (records, fences, spans)
          amd_blocks       ->  typed blocks  (cue, speech, choice, table, ...)
          amd_schema       ->  field types   (color, ref, coord2, trigger, ...)
          amd_timeline     ->  the spine     (beats, tracks, causal edges)
          amd_render       ->  one HTML page
```

Three things are worth knowing if you extend it.

**The renderer owns no grammar.** Every body mark is recognized by the function
in `procedural/amd.py` that already owned it, and `amd_blocks` decides only the
*order* those recognizers are tried in. That matters because the in-game text
area reads the same marks: the game and the printed page must not come to read
the same bytes differently, and `tests/test_amd_blocks_one_grammar.py` pins that
they cannot.

**Anchors are path-based, and unique per file.** Bare keys are not unique - 40 of
the corpus's 374 repeat, one file holds three `recover` records, and five
`.amd` basenames repeat across the missions (`OpenUniverse` alone has two
`ashfang.amd`).

**The contents list and every cross-reference are built from what the body
actually emitted.** Each lens renders a different subset, so a link to a record
that lens skipped is demoted to plain text rather than offered as a jump that
lands nowhere. That makes a dangling anchor structurally impossible instead of a
promise each lens has to keep.
