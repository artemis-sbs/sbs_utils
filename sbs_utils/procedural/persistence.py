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
- load: missing/unreadable/unmigratable -> None; backs the file up once
  (`path + '.bak'`) before an UPGRADING migration, so a bad migration is
  recoverable.
"""
import os
import shutil
from ..fs import (load_json_data, save_json_data,
                  load_yaml_data, save_yaml_data)

DEFAULT_VERSION_KEY = "save_version"


class PersistentStore:
    """Versioned save/load for one envelope file. `migrations` is a single-step
    ladder `{v: fn(data)->data}` upgrading a v save to v+1."""

    def __init__(self, path, *, version=1, migrations=None, fmt="yaml",
                 version_key=DEFAULT_VERSION_KEY, backup=True):
        self.path = path
        self.version = version
        self.migrations = migrations or {}
        self.fmt = fmt
        self.version_key = version_key
        self.backup = backup

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
        if v > self.version:
            return data
        try:
            while v < self.version and v in self.migrations:
                data = self.migrations[v](data)
                v += 1
            data[self.version_key] = v
            return data
        except Exception as e:
            print(f"PersistentStore migrate failed: {e}")
            return None

    def load(self):
        """Read + migrate to the current version, or None when the file is
        missing/unreadable/unmigratable. Backs up once before an upgrade."""
        raw = self._read()
        if not isinstance(raw, dict):
            return None
        before = raw.get(self.version_key, 1)
        data = self.migrate(raw)
        if self.backup and data is not None and data.get(self.version_key, 1) > before:
            if not os.path.exists(self.path + ".bak"):
                try:
                    shutil.copyfile(self.path, self.path + ".bak")
                except Exception:
                    pass
        return data

    def save(self, data):
        """Stamp `data[version_key] = version` and write it."""
        data[self.version_key] = self.version
        self._write(data)

    def update(self, **sections):
        """Read-modify-write merge: `load() or {}`, apply `sections`, save.
        Returns the merged dict. Replaces the ubiquitous
        `data = load() or {}; data[k] = v; save(data)`."""
        data = self.load() or {}
        data.update(sections)
        self.save(data)
        return data


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
