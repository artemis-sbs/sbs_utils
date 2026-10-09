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
