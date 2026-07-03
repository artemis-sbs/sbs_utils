# Persistent store (save / load)

Schema-versioned read / migrate / merge / write of one dict to one save file.

## Overview

`PersistentStore` owns exactly one concern: read, migrate, merge, and write **one
dict to one file**, with a top-level version stamp and a single-step migration
ladder. Everything domain-specific — the envelope's keys, *what* to persist, where
the file lives — stays with the caller.

The version stamp is a **top-level key** in the payload (`save_version` by
default), not a `{version, data}` wrapper, so existing flat save files load
unchanged. `fmt` selects `"yaml"` or `"json"` (built on the `fs.py`
load/save primitives).

| Method | Does |
|---|---|
| `load()` | read + migrate to the current version, or `None` if missing/unreadable/unmigratable |
| `save(data)` | stamp the version and write |
| `migrate(data)` | run the ladder (no file I/O — standalone-testable) |
| `update(**sections)` | read-modify-write merge, returns the merged dict |

Semantics:

- **migrate** — absent version → 1; a save *newer* than this build loads
  unchanged (best-effort, never rewritten); otherwise the ladder runs
  `while v < version and v in migrations`; any exception → `None` (caller treats
  as "no save" / New Game).
- **load** — missing/unreadable/unmigratable → `None`; backs the file up once
  (`path + '.bak'`) before an *upgrading* migration, so a bad migration is
  recoverable.

## Quick example

```python
from sbs_utils.procedural.persistence import PersistentStore

MIGRATIONS = {
    1: lambda d: {**d, "credits": d.pop("money", 0)},   # v1 save -> v2 (rename)
}
store = PersistentStore(get_mission_dir_filename("save.yaml"),
                        version=2, migrations=MIGRATIONS)

data = store.load()                 # None  =>  New Game
if data is None:
    data = {"credits": 100}

# read-modify-write merge (replaces `d = load() or {}; d[k] = v; save(d)`)
store.update(credits=data["credits"] + 50)
```

Thin functional wrappers — `persist_load`, `persist_save`, `persist_migrate` —
exist for one-off calls that don't need to hold a store instance.

## API

::: sbs_utils.procedural.persistence
