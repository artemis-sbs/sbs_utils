# The amd_blocks module

One AMD record body, read into a list of typed blocks.

## Overview

`amd_core.parse` gives a renderer everything about a document's **structure** — the
record tree, the fence facts, the reference spans — and nothing about its **body**,
which arrives as raw lines exactly as typed. Every consumer used to re-derive meaning
from those lines itself, which is how the same `%` and the same `- [label](target)`
came to be read four slightly different ways.

This reads them once:

```python
[{"type": "cue",    "line": 12, "speaker": "vex", "surface": "comms"},
 {"type": "speech", "line": 13, "variants": [{"text": "...", "gate": None}]},
 {"type": "choice", "line": 15, "label": "Pay", "target": "paid", ...}]
```

Every block is a plain JSON-able dict with a 1-based `line`, so blocks cross a process
boundary — the language server, a `--format json` dump, a golden test — untouched.

!!! note "This module owns no grammar"
    Every mark is recognized by the function in `procedural.amd` that already owned it.
    What lives here is the **order** those recognizers are tried in, and where one block
    ends — which is exactly the part that has to be identical between the game and a
    printed page.

Deliberately absent: measuring, wrapping, styling, or anything needing the engine. A
block says "these lines were a table"; how wide its columns are is the renderer's
business, and the in-game one answers differently from a sheet of paper on purpose.

## Profiles

`profile="player"` is a **hard filter**, not a stylesheet class. An author-only `= `
synopsis, a choice's guard and its outcomes are *absent* from the result, because
"print to PDF" and "view source" have to agree about what a player was told.

## API

::: sbs_utils.procedural.amd_blocks
