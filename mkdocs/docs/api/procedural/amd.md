# AMD fact-sheet reader

Coerce a friendly `Label: value` fenced block into a dict — a companion parser
for AMD documents.

## Overview

AMD documents are `#`/`##` headings with `---` fences (the same shape quests,
clans, and universes are authored in). `document_get_amd_file` already parses the
headings and fences; this module is the companion **`data_parser`** that turns a
single fence's `Label: value` lines into a dict, with light value coercion:

| Helper | Coerces | Example |
|---|---|---|
| `amd_num` | int → float → str | `8` → `8` |
| `amd_pct` | percent or number | `40%` → `0.4` |
| `amd_list` | comma list | `a, b` → `["a", "b"]` |
| `amd_weighted` | `name N` weights | `by-the-book 40` → `{"by_the_book": 40}` |
| `amd_makeup` | `N% name` / list / scalar | `60% X, 40% Y` → `{"X": 60, "Y": 40}` |
| `amd_coords` | first N ints | `6, 4` → `[6, 4]` |
| `amd_norm` | canonicalize a token | `By-The-Book` → `by_the_book` |

A fence that uses YAML **flow** (`{` or `[`) is parsed as YAML instead, so YAML
fences keep working through the same reader.

The **domain** interpretation — what "Yields" or "Values" *means* — is the
caller's job, supplied via a `handler(data, label, value)` callback; this module
stays content-agnostic (just parsing + coercion). See the Open Universe's
`universe_amd.py` for a worked example.

## Quick example

```python
from sbs_utils.procedural.amd import amd_parse_facts, amd_list, amd_num

def handler(data, label, value):
    if label == "yields":
        data["yields"] = amd_list(value)
        return True          # consumed
    return False             # fall through to the default coercion

# fence_text is one `---` block: "Yields: ore 8\nReserve: 4000"
facts = amd_parse_facts(fence_text, handler=handler, default=amd_num)
# -> {"yields": ["ore 8"], "reserve": 4000}
```

`handler` receives the mutable `data` dict, so it can `setdefault` / nest /
append freely; return truthy to consume a label, falsy to let `default(value)`
handle it under `amd_norm(label)`.

## API

::: sbs_utils.procedural.amd
