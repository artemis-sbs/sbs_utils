"""Schema-versioned save/load for a single keyed-blob envelope file.

A small persistence framework extracted from the Open Universe's save layer. It
owns exactly one concern: read / migrate / merge / write one dict to one file,
with a top-level version stamp and a single-step migration ladder. Everything
domain-specific (the envelope's key names, WHAT to persist, where the file lives,
mirroring live state into inventory) stays with the caller.

Built on the fs.py primitives (`load/save_yaml_data`, `load/save_json_data`), so
`fmt` selects the reader/writer pair. The version stamp is a top-level key in the
payload (configurable `version_key`, default "save_version"), NOT a {version,
data} wrapper - so existing flat save files load unchanged.

Semantics (carried over verbatim from the OU save layer):
- migrate: absent version -> 1; `v > version` returns the data unchanged (a
  newer-than-build save loads best-effort, don't rewrite); the ladder runs
  `while v < version and v in migrations`; any exception -> None (caller treats
  as "no save" / New Game).
- load: missing/unreadable/unmigratable -> None, and `last_status` says WHICH
  (see the STATUS_ names). The file is backed up BEFORE an upgrading migration
  runs, so a migration that raises leaves a copy as well as the untouched file.
  `backup=True` writes `path + '.bak'` once; `backup="version"` writes one per
  version it climbs FROM (`path + '.v1.bak'`), so a second format change does
  not find the first one's backup in its way.
- update / modify: REFUSE to write over a file that is there but did not load
  (unreadable, unmigratable) or that a newer build wrote. `load() or {}` used to
  turn "could not read your save" into "here is an empty one", and the next
  write made that permanent. A refused write copies the file aside
  (`set_aside`) and returns None. `protect=False` restores the old behavior.
  `save()` is the raw write and is not guarded: a caller that builds a whole
  payload itself has already decided.
- Unknown top-level keys ride through load -> modify -> save untouched, so a
  later build (or an addon) can add a section without a format change.

STATE PROVIDERS (the second half of this module, `persist_provider_*`): a library
module that owns per-mission state worth keeping - what a boarding party learned,
which barrier of a ruin is open - registers a pair of functions, and a mission that
saves asks for every provider's state in one call and hands it back in one call.
The store above neither knows nor cares; the mission decides which file and key
the blobs live under. A mission that never saves never calls either, and nothing
changes for it.
"""
import os
import shutil
from ..fs import (load_json_data, save_json_data,
                  load_yaml_data, save_yaml_data)

DEFAULT_VERSION_KEY = "save_version"

# What the last load() found. MISSING is the only one where starting from
# nothing is the right answer.
STATUS_MISSING = "missing"            # no file, or an empty one
STATUS_OK = "ok"                      # loaded (and migrated, if it needed it)
STATUS_NEWER = "newer"                # written by a newer build: loaded as is
STATUS_UNREADABLE = "unreadable"      # there, with content, and would not parse
STATUS_UNMIGRATABLE = "unmigratable"  # parsed, and a migration step raised


class PersistentStore:
    """Versioned save/load for one envelope file. `migrations` is a single-step
    ladder `{v: fn(data)->data}` upgrading a v save to v+1."""

    def __init__(self, path, *, version=1, migrations=None, fmt="yaml",
                 version_key=DEFAULT_VERSION_KEY, backup=True, protect=True):
        self.path = path
        self.version = version
        self.migrations = migrations or {}
        self.fmt = fmt
        self.version_key = version_key
        self.backup = backup
        self.protect = protect
        # Facts about the last load(), for a caller that has to tell a person
        # what happened to their file.
        self.last_status = None
        self.last_version = None      # the version the file carried on disk
        self.last_backup = None       # the backup that load wrote or found
        self.last_error = None        # the migration's exception text

    # -- format seam --------------------------------------------------------
    def _read(self):
        return load_yaml_data(self.path) if self.fmt == "yaml" else load_json_data(self.path)

    def _write(self, data):
        if self.fmt == "yaml":
            save_yaml_data(self.path, data)
        else:
            save_json_data(self.path, data)

    # -- api ----------------------------------------------------------------
    def migrate(self, data):
        """Run the ladder up to `version`. Returns the upgraded dict; the dict
        unchanged if it is NEWER than this build; or None if it can't be
        migrated. No file I/O - standalone-testable."""
        if not isinstance(data, dict):
            return None
        v = data.get(self.version_key, 1)
        self.last_error = None
        if v > self.version:
            return data
        try:
            while v < self.version and v in self.migrations:
                data = self.migrations[v](data)
                v += 1
            data[self.version_key] = v
            return data
        except Exception as e:
            self.last_error = f"{type(e).__name__}: {e}"
            print(f"PersistentStore migrate failed: {e}")
            return None

    def _has_content(self):
        """True when the file is there and holds something other than whitespace.
        An empty file has nothing to lose, so it counts as missing."""
        try:
            if not os.path.isfile(self.path):
                return False
            with open(self.path, "rb") as f:
                return bool(f.read().strip())
        except OSError:
            return False

    def backup_path(self, from_version):
        """Where the backup taken before upgrading FROM `from_version` goes."""
        if self.backup == "version":
            return f"{self.path}.v{from_version}.bak"
        return self.path + ".bak"

    def _backup_before_upgrade(self, from_version):
        path = self.backup_path(from_version)
        if not os.path.exists(path):
            try:
                shutil.copyfile(self.path, path)
            except Exception:
                return None
        return path

    def load(self):
        """Read + migrate to the current version, or None when the file is
        missing/unreadable/unmigratable (`last_status` says which). Backs the
        file up BEFORE an upgrading migration runs. Never writes the file."""
        self.last_version = None
        self.last_backup = None
        self.last_error = None
        raw = self._read()
        if not isinstance(raw, dict):
            self.last_status = STATUS_UNREADABLE if self._has_content() else STATUS_MISSING
            return None
        before = raw.get(self.version_key, 1)
        self.last_version = before
        try:
            newer = before > self.version
            upgrading = before < self.version and before in self.migrations
        except TypeError:
            # A version stamp that is not a number is not a save this can read.
            self.last_status = STATUS_UNREADABLE
            return None
        if newer:
            self.last_status = STATUS_NEWER
            return raw
        if self.backup and upgrading:
            self.last_backup = self._backup_before_upgrade(before)
        data = self.migrate(raw)
        self.last_status = STATUS_OK if data is not None else STATUS_UNMIGRATABLE
        return data

    def set_aside(self):
        """Copy a file that would not load to a name nothing writes to, and
        return that name (None when there is no file). Idempotent: a copy that
        already holds the same bytes is reused, a different one is never
        replaced - the next free `.unreadable.N.bak` is taken instead.

        A file whose MIGRATION failed already has its pre-upgrade backup; that
        is the copy, and no second one is made."""
        if not self._has_content():
            return None
        try:
            with open(self.path, "rb") as f:
                content = f.read()
        except OSError:
            return None
        if self.last_backup and os.path.isfile(self.last_backup):
            try:
                with open(self.last_backup, "rb") as f:
                    if f.read() == content:
                        return self.last_backup
            except OSError:
                pass
        n = 1
        while n < 1000:
            cand = self.path + (".unreadable.bak" if n == 1 else f".unreadable.{n}.bak")
            if not os.path.exists(cand):
                try:
                    shutil.copyfile(self.path, cand)
                except Exception:
                    return None
                return cand
            try:
                with open(cand, "rb") as f:
                    if f.read() == content:
                        return cand
            except OSError:
                pass
            n += 1
        return None

    def save(self, data):
        """Stamp `data[version_key] = version` and write it. The RAW write:
        it does not look at what is on disk (see `modify`)."""
        data[self.version_key] = self.version
        self._write(data)

    def modify(self, fn):
        """Read-modify-write: load, hand the dict to `fn`, save. `fn` may change
        the dict in place or return a replacement. Returns the saved dict.

        REFUSES (returns None, writes nothing) when the file is there but did
        not load, or was written by a newer build - unless `protect=False`. A
        file that did not load is copied aside first (`set_aside`)."""
        data = self.load()
        if data is None:
            if self.protect and self.last_status != STATUS_MISSING:
                self.set_aside()
                return None
            data = {}
        elif self.protect and self.last_status == STATUS_NEWER:
            return None
        out = fn(data)
        if out is not None:
            data = out
        self.save(data)
        return data

    def update(self, **sections):
        """Read-modify-write merge: load, apply `sections`, save. Returns the
        merged dict, or None when the write was refused (see `modify`).
        Replaces the ubiquitous `data = load() or {}; data[k] = v; save(data)`."""
        return self.modify(lambda data: data.update(sections))


# --- thin functional wrappers ----------------------------------------------
def persist_load(path, *, version=1, migrations=None, fmt="yaml",
                 version_key=DEFAULT_VERSION_KEY, backup=True):
    return PersistentStore(path, version=version, migrations=migrations, fmt=fmt,
                           version_key=version_key, backup=backup).load()


def persist_save(path, data, *, version=1, fmt="yaml",
                 version_key=DEFAULT_VERSION_KEY):
    PersistentStore(path, version=version, fmt=fmt, version_key=version_key).save(data)


def persist_migrate(data, *, version, migrations, version_key=DEFAULT_VERSION_KEY):
    return PersistentStore("", version=version, migrations=migrations,
                           version_key=version_key).migrate(data)


# --- state providers ---------------------------------------------------------
# WHO OWNS WHAT. The save file belongs to a mission (Open Universe keeps it under
# one key, `state`). The STATE belongs to whichever library module holds it, and
# that module is the only thing that knows how to write it down and how to take it
# back. A provider is that pair, under a name:
#
#     persist_provider_register("relics", snapshot_fn, restore_fn)
#
#   snapshot_fn() -> a plain, YAML-safe value (dicts, lists, strings, numbers), or
#                    None / empty when there is nothing to keep.
#   restore_fn(blob) REPLACES what the provider holds with `blob`. `None` means
#                    "nothing was saved": forget everything. It must be LAZY where
#                    the world is not built yet - fill a ledger the owner consults
#                    when it builds the thing - and it must not announce anything:
#                    restored state is not news, so no quest signal, no reward.
#
# The library's own providers register as their modules import (`library=True`),
# the way the library's own dispatcher handlers do, and the per-mission reset puts
# exactly those back. A provider a MISSION registers is dropped by the reset.
_PROVIDERS = {}            # name -> (snapshot_fn, restore_fn)
_LIBRARY_PROVIDERS = {}    # the ones the reset puts back
_RESTORED = {}             # name -> the blob last handed to persist_providers_restore
_DIRTY = [False]


def persist_provider_register(name, snapshot_fn, restore_fn, library=False):
    """Register a state provider under `name`. Re-registering a name replaces it.

    If a save was already restored this mission and it held a blob under this name,
    the new provider is handed it at once - so a provider that registers late (an
    addon that loads after the campaign was opened) is not left empty.

    `library=True` is for sbs_utils' own modules, which register once as they
    import: the per-mission reset keeps those and drops the rest."""
    name = str(name)
    _PROVIDERS[name] = (snapshot_fn, restore_fn)
    if library:
        _LIBRARY_PROVIDERS[name] = (snapshot_fn, restore_fn)
    if name in _RESTORED and restore_fn is not None:
        _persist_call_restore(name, restore_fn, _RESTORED[name])
    return name


def persist_provider_unregister(name):
    """Drop a provider. A blob restored under its name is still kept for the next
    snapshot. True when there was one."""
    _LIBRARY_PROVIDERS.pop(str(name), None)
    return _PROVIDERS.pop(str(name), None) is not None


def persist_provider_names():
    """Every registered provider, sorted."""
    return sorted(_PROVIDERS)


def _persist_log(message):
    try:
        from .execution import log
        log(message, "persistence", "warning")
    except Exception:                                   # noqa: BLE001
        pass


def _persist_call_restore(name, restore_fn, blob):
    try:
        restore_fn(blob)
        return True
    except Exception as e:                              # noqa: BLE001
        _persist_log(f"state provider '{name}' would not restore: {type(e).__name__}: {e}")
        return False


def persist_providers_snapshot():
    """Every provider's state, as `{name: blob}`. What a mission writes to its save.

    Three rules, all in service of "never lose what was saved":
      * a provider with nothing to keep is left out;
      * a provider whose snapshot RAISES keeps the blob it was last restored with -
        a fault in one module must not delete that module's saved state;
      * a blob that was restored under a name NO provider claims is passed through
        as it was (an addon that is not loaded tonight keeps its state).
    Clears the "something changed" flag (`persist_providers_dirty`)."""
    out = {}
    for name, blob in _RESTORED.items():
        if name not in _PROVIDERS and blob not in (None, {}, []):
            out[name] = blob
    for name in sorted(_PROVIDERS):
        snapshot_fn = _PROVIDERS[name][0]
        if snapshot_fn is None:
            continue
        try:
            blob = snapshot_fn()
        except Exception as e:                          # noqa: BLE001
            _persist_log(f"state provider '{name}' would not snapshot: {type(e).__name__}: {e}")
            blob = _RESTORED.get(name)
        if blob not in (None, {}, []):
            out[name] = blob
    _DIRTY[0] = False
    return out


def persist_providers_restore(blobs):
    """Hand each provider its saved blob. Returns the names that were restored.

    EVERY registered provider is called - with its blob, or with None when the save
    held nothing under its name - so "Continue" and "New Game" both leave a provider
    holding exactly what the save says and nothing left over from before. Blobs under
    a name nobody has registered are kept, handed to a provider that registers later,
    and passed through `persist_providers_snapshot` untouched."""
    blobs = dict(blobs) if isinstance(blobs, dict) else {}
    _RESTORED.clear()
    _RESTORED.update(blobs)
    done = []
    for name in sorted(_PROVIDERS):
        restore_fn = _PROVIDERS[name][1]
        if restore_fn is None:
            continue
        if _persist_call_restore(name, restore_fn, blobs.get(name)):
            done.append(name)
    _DIRTY[0] = False
    return done


def persist_provider_touch(name=None):
    """A provider's state just changed: something worth saving happened. Cheap, and
    safe to call from anywhere - it sets one flag a saving mission polls."""
    _DIRTY[0] = True


def persist_providers_dirty():
    """True when a provider's state has changed since the last snapshot or restore."""
    return bool(_DIRTY[0])


def persist_providers_reset():
    """The per-mission reset: forget restored blobs and the changed flag, drop the
    providers a mission registered, and put the library's own back."""
    _RESTORED.clear()
    _DIRTY[0] = False
    _PROVIDERS.clear()
    _PROVIDERS.update(_LIBRARY_PROVIDERS)


def persist_providers_count():
    """Reset-ledger probe: what a mission left behind - restored blobs, the changed
    flag, and providers the library did not register itself."""
    return (len(_RESTORED) + (1 if _DIRTY[0] else 0)
            + len([n for n in _PROVIDERS if n not in _LIBRARY_PROVIDERS]))
