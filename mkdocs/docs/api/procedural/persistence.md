# Persistent store (save / load)

Two things live in this module, and a mission that saves uses both:

- **`PersistentStore`** - schema-versioned read / migrate / merge / write of one dict to
  one save file, which refuses to write over a file it could not read.
- **State providers** (`persist_provider_*`) - how a library module's own per-mission
  state (what a boarding party learned, which barrier of a ruin is open) gets into that
  file and back out, without the mission knowing what any of it is.

## The store

`PersistentStore` owns exactly one concern: read, migrate, merge, and write **one dict to
one file**, with a top-level version stamp and a single-step migration ladder. Everything
domain-specific - the envelope's keys, *what* to persist, where the file lives - stays
with the caller.

The version stamp is a **top-level key** in the payload (`save_version` by default), not
a `{version, data}` wrapper, so existing flat save files load unchanged. `fmt` selects
`"yaml"` or `"json"` (built on the `fs.py` load/save primitives).

| Method | Does |
|---|---|
| `load()` | read + migrate to the current version, or `None`. Never writes the file. `last_status` says what it found |
| `modify(fn)` | read, hand the dict to `fn`, write. **Refuses** (returns `None`, writes nothing) on a file that is there and did not load, or that a newer build wrote |
| `update(**sections)` | `modify` with a plain merge; returns the merged dict, or `None` when refused |
| `save(data)` | stamp the version and write. The RAW write: it does not look at what is on disk |
| `migrate(data)` | run the ladder (no file I/O - standalone-testable) |
| `set_aside()` | copy a file that would not load to `<file>.unreadable.bak` and return that name |

After a `load()`:

| `last_status` | Means | Starting from nothing is right? |
|---|---|---|
| `missing` | no file, or an empty one | yes |
| `ok` | loaded, and migrated if it needed it | - |
| `newer` | written by a newer build; returned as it is | no - play it, do not write over it |
| `unreadable` | there, with content, and would not parse | **no** |
| `unmigratable` | parsed, and a migration step raised (`last_error`) | **no** |

`last_version` is the version the file carried on disk and `last_backup` the backup that
load wrote or found.

Semantics:

- **migrate** - absent version -> 1; a save *newer* than this build is returned unchanged;
  otherwise the ladder runs `while v < version and v in migrations`; any exception ->
  `None`.
- **backups** - the file is copied BEFORE an upgrading migration runs, so a migration that
  raises leaves a copy as well as the untouched file. `backup=True` writes `<file>.bak`
  once; `backup="version"` writes one per version climbed FROM (`<file>.v1.bak`), so a
  second format change does not find the first one's backup in its way.
- **protection** - `load() or {}` used to turn "could not read your save" into "here is an
  empty one", and the next write made that permanent. `modify` / `update` refuse instead,
  after `set_aside()` has copied the file. `protect=False` restores the old behavior.
- **unknown keys ride through** `load -> modify -> save` untouched, so a later build (or
  an addon) can add a section without a format change.

```python
from sbs_utils.procedural.persistence import PersistentStore

MIGRATIONS = {
    1: lambda d: {**d, "credits": d.pop("money", 0)},   # v1 save -> v2 (rename)
}
store = PersistentStore(get_mission_dir_filename("save.yaml"),
                        version=2, migrations=MIGRATIONS, backup="version")

data = store.load()
if data is None and store.last_status != "missing":
    ...                              # a save is there and will not load: do not start over it
if data is None:
    data = {"credits": 100}

# read-modify-write (replaces `d = load() or {}; d[k] = v; save(d)`)
if store.update(credits=data["credits"] + 50) is None:
    ...                              # refused: the file is untouched and copied aside
```

Thin functional wrappers - `persist_load`, `persist_save`, `persist_migrate` - exist for
one-off calls that do not need to hold a store instance.

## State providers

A save file belongs to a mission. Some of what is worth saving belongs to the LIBRARY:
`boarding.py` knows what the crew learned, `amd_relics.py` knows which barriers of a ruin
were opened. A provider is how each owner writes its own state down and takes it back,
under a name, so the mission makes two calls and never learns the shapes:

```python
from sbs_utils.procedural.persistence import (
    persist_providers_snapshot, persist_providers_restore, persist_providers_dirty)

# opening the save, BEFORE anything is built:
persist_providers_restore(saved.get("state"))     # None / {} for a new game

# writing the save:
data["state"] = persist_providers_snapshot()

# in the task that flushes saves:
if persist_providers_dirty():
    ...                                           # something the library keeps changed
```

| Function | Does |
|---|---|
| `persist_provider_register(name, snapshot_fn, restore_fn)` | register a provider. A blob already restored under its name is handed to it at once |
| `persist_providers_snapshot()` | every provider's state as `{name: blob}`; clears the changed flag |
| `persist_providers_restore(blobs)` | hand each provider its blob - or `None` when the save held nothing for it |
| `persist_provider_touch(name=None)` | a provider's state just changed (one flag) |
| `persist_providers_dirty()` | whether anything changed since the last snapshot or restore |
| `persist_provider_names()` | the registered names |

The contract a provider keeps:

- **`snapshot_fn()`** returns plain, YAML-safe data (dicts, lists, strings, numbers), or
  nothing when there is nothing to keep. Sets become sorted lists.
- **`restore_fn(blob)` REPLACES** what the provider holds. `None` means nothing was saved:
  forget everything. Every provider is called on every restore, so a new game started in
  the same process does not inherit the last campaign's opened doors.
- **Restore is lazy.** A save is handed back before the world it describes exists - a
  ruin is built when the crew reaches its system. So a restore fills a ledger, and the
  owner consults the ledger when it builds the thing.
- **Restored state is not news.** A restored barrier is simply open: no quest signal, no
  reward, no announcement. Whatever was sent when it happened is not sent again.

Three rules protect what is in the file: a provider with nothing to keep is left out; a
provider whose snapshot RAISES keeps the blob it was last restored with; and a blob under
a name NO provider claims is passed through untouched (an addon that is not loaded
tonight keeps its state), and handed to a provider that registers later.

### The library's own providers

Registered as their modules import. The per-mission reset keeps these and drops any a
mission registered.

| Name | Owner | Keeps |
|---|---|---|
| `boarding_facts` | `boarding.py` | `{place: [facts]}` - what `; learn` and `Then: learn` recorded. `""` is the campaign's pool |
| `relics` | `amd_relics.py` | `{"ruins": {relic: {"opened", "repaired", "taken", "placed"}}, "sent": [quest signals]}` |
| `boarding_props` | `boarding_props.py` | `{"opened": [prop keys], "taken": [prop keys]}` |
| `boarding_hostiles` | `boarding_combat.py` | `{"down": [keys]}` |

A mission that never saves never calls snapshot or restore, and nothing changes for it.
One thing does change for every mission: a ruin now REMEMBERS between visits within one
game (`relic_ledger`) - it used to be rebuilt from its file each time its system was.

## API

::: sbs_utils.procedural.persistence
