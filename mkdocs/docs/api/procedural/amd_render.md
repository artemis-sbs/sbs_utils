# The amd_render module

AMD → a self-contained HTML document, laid out for print. Drives [`sbs docs`](../../tooling/amd-docs.md).

## Overview

Four lenses, because an `.amd` file is three documents wearing one syntax. A file with
no fence is prose and converts almost directly; a file whose content **is** the fence is
a catalog, where printing `Color: #ffcc44` as a line of text would be worthless; and a
quest tree's meaning lives in `Parent:` / `Starts when:` / `Then:`, which flattening
destroys. So the number of renderings is the number of **audiences**:

| Lens | Reader wants |
|---|---|
| `prose` | sentences — a manual or a story book |
| `catalog` | to look something up — reference cards, fields rendered as their **type** |
| `screenplay` | to perform it — Fountain geometry |
| `bible` | to see the machine — the quest spine, triggers and graph |

Field typing comes from `amd_schema`, so a color becomes a swatch, a reference a working
link, a coordinate a cell chip.

## Anchors and links

Anchors are **path-based and unique per file**. Bare keys are not unique — 40 of the
corpus's 374 repeat, one file holds three `recover` records, and five `.amd` basenames
repeat across the missions. A per-key anchor does not dangle; it aims a working link at
the wrong record.

The contents list and every cross-reference are built from what the body **actually
emitted**, so a link to a record a lens skipped is demoted to plain text rather than
offered as a jump that lands nowhere.

## API

::: sbs_utils.procedural.amd_render
