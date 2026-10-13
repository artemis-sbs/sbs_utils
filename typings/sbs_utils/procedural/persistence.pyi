def _persist_call_restore (name, restore_fn, blob):
    ...
def _persist_log (message):
    ...
def load_json_data (file):
    """Load and parse a JSON file with comment support.
    
    Strips comments (# and //) and trailing commas before parsing.
    Attempts to load using ryaml first, falls back to json.loads with preprocessing.
    
    Args:
        file (str): Path to the JSON file to load.
    
    Returns:
        dict or None: Parsed JSON data, or None if loading fails."""
def load_yaml_data (file, multi=False):
    """Load and parse a YAML file.
    
    Uses the fast ryaml parser when the engine provides it, and the bundled
    pure-Python yaml otherwise (or when ryaml refuses the file).
    
    Args:
        file (str): Path to the YAML file to load.
        multi (bool): return a generator of all documents
    
    Returns:
        dict or generator or None: Parsed YAML data, or None if loading fails."""
def persist_load (path, *, version=1, migrations=None, fmt='yaml', version_key='save_version', backup=True):
    ...
def persist_migrate (data, *, version, migrations, version_key='save_version'):
    ...
def persist_provider_names ():
    """Every registered provider, sorted."""
def persist_provider_register (name, snapshot_fn, restore_fn, library=False):
    """Register a state provider under `name`. Re-registering a name replaces it.
    
    If a save was already restored this mission and it held a blob under this name,
    the new provider is handed it at once - so a provider that registers late (an
    addon that loads after the campaign was opened) is not left empty.
    
    `library=True` is for sbs_utils' own modules, which register once as they
    import: the per-mission reset keeps those and drops the rest."""
def persist_provider_touch (name=None):
    """A provider's state just changed: something worth saving happened. Cheap, and
    safe to call from anywhere - it sets one flag a saving mission polls."""
def persist_provider_unregister (name):
    """Drop a provider. A blob restored under its name is still kept for the next
    snapshot. True when there was one."""
def persist_providers_count ():
    """Reset-ledger probe: what a mission left behind - restored blobs, the changed
    flag, and providers the library did not register itself."""
def persist_providers_dirty ():
    """True when a provider's state has changed since the last snapshot or restore."""
def persist_providers_reset ():
    """The per-mission reset: forget restored blobs and the changed flag, drop the
    providers a mission registered, and put the library's own back."""
def persist_providers_restore (blobs):
    """Hand each provider its saved blob. Returns the names that were restored.
    
    EVERY registered provider is called - with its blob, or with None when the save
    held nothing under its name - so "Continue" and "New Game" both leave a provider
    holding exactly what the save says and nothing left over from before. Blobs under
    a name nobody has registered are kept, handed to a provider that registers later,
    and passed through `persist_providers_snapshot` untouched."""
def persist_providers_snapshot ():
    """Every provider's state, as `{name: blob}`. What a mission writes to its save.
    
    Three rules, all in service of "never lose what was saved":
      * a provider with nothing to keep is left out;
      * a provider whose snapshot RAISES keeps the blob it was last restored with -
        a fault in one module must not delete that module's saved state;
      * a blob that was restored under a name NO provider claims is passed through
        as it was (an addon that is not loaded tonight keeps its state).
    Clears the "something changed" flag (`persist_providers_dirty`)."""
def persist_save (path, data, *, version=1, fmt='yaml', version_key='save_version'):
    ...
def save_json_data (file, data):
    """Save data to a JSON file with human-readable formatting.
    
    Applies regex transformations to make the JSON output more readable with
    logical line breaks and consistent spacing.
    
    Args:
        file (str): Path to the output JSON file.
        data (dict): The data structure to serialize."""
def save_yaml_data (file, data):
    """Save an object as a YAML file.
    
    Attempts to dump using ryaml first for better comment handling,
    falls back to standard yaml.safe_dump if ryaml is unavailable.
    
    WRITTEN BESIDE THE FILE, THEN SWAPPED IN. It used to open the file itself with 'w',
    which empties it before a byte is written. For as long as the dump took, anything
    reading the file - a second game finishing in the same second, on a machine running
    several - saw half a document, could not parse it, and started over from nothing:
    a rolling record of two hundred games became the last twenty six. Now the old file
    is whole until the new one is, and a dump that fails leaves it untouched.
    
    Args:
        file (str): Path to the YAML file to load.
        data (dict): Dict or object to save"""
class PersistentStore(object):
    """Versioned save/load for one envelope file. `migrations` is a single-step
    ladder `{v: fn(data)->data}` upgrading a v save to v+1."""
    def __init__ (self, path, *, version=1, migrations=None, fmt='yaml', version_key='save_version', backup=True, protect=True):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _backup_before_upgrade (self, from_version):
        ...
    def _has_content (self):
        """True when the file is there and holds something other than whitespace.
        An empty file has nothing to lose, so it counts as missing."""
    def _read (self):
        ...
    def _write (self, data):
        ...
    def backup_path (self, from_version):
        """Where the backup taken before upgrading FROM `from_version` goes."""
    def load (self):
        """Read + migrate to the current version, or None when the file is
        missing/unreadable/unmigratable (`last_status` says which). Backs the
        file up BEFORE an upgrading migration runs. Never writes the file."""
    def migrate (self, data):
        """Run the ladder up to `version`. Returns the upgraded dict; the dict
        unchanged if it is NEWER than this build; or None if it can't be
        migrated. No file I/O - standalone-testable."""
    def modify (self, fn):
        """Read-modify-write: load, hand the dict to `fn`, save. `fn` may change
        the dict in place or return a replacement. Returns the saved dict.
        
        REFUSES (returns None, writes nothing) when the file is there but did
        not load, or was written by a newer build - unless `protect=False`. A
        file that did not load is copied aside first (`set_aside`)."""
    def save (self, data):
        """Stamp `data[version_key] = version` and write it. The RAW write:
        it does not look at what is on disk (see `modify`)."""
    def set_aside (self):
        """Copy a file that would not load to a name nothing writes to, and
        return that name (None when there is no file). Idempotent: a copy that
        already holds the same bytes is reused, a different one is never
        replaced - the next free `.unreadable.N.bak` is taken instead.
        
        A file whose MIGRATION failed already has its pre-upgrade backup; that
        is the copy, and no second one is made."""
    def update (self, **sections):
        """Read-modify-write merge: load, apply `sections`, save. Returns the
        merged dict, or None when the write was refused (see `modify`).
        Replaces the ubiquitous `data = load() or {}; data[k] = v; save(data)`."""
