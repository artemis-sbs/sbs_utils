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
    
    Args:
        file (str): Path to the YAML file to load.
        data (dict): Dict or object to save"""
class PersistentStore(object):
    """Versioned save/load for one envelope file. `migrations` is a single-step
    ladder `{v: fn(data)->data}` upgrading a v save to v+1."""
    def __init__ (self, path, *, version=1, migrations=None, fmt='yaml', version_key='save_version', backup=True):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _read (self):
        ...
    def _write (self, data):
        ...
    def load (self):
        """Read + migrate to the current version, or None when the file is
        missing/unreadable/unmigratable. Backs up once before an upgrade."""
    def migrate (self, data):
        """Run the ladder up to `version`. Returns the upgraded dict; the dict
        unchanged if it is NEWER than this build; or None if it can't be
        migrated. No file I/O - standalone-testable."""
    def save (self, data):
        """Stamp `data[version_key] = version` and write it."""
    def update (self, **sections):
        """Read-modify-write merge: `load() or {}`, apply `sections`, save.
        Returns the merged dict. Replaces the ubiquitous
        `data = load() or {}; data[k] = v; save(data)`."""
