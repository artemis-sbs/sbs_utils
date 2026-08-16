def _read_mission_entries (path):
    """The mission's OWN entries from an existing file, with generated ones dropped.
    
    Dropping anything carrying ``#mod`` is what makes flushing idempotent: without it, the
    entries this function wrote last time would be read back as mission-authored and
    re-merged, and a mod could never be removed."""
def _strip_line_comments (text):
    """Drop HJSON `//` comment lines so a YAML or JSON parser will accept the text.
    
    The shipped `extraShipData.json` example opens with them and every hand-written one
    copies that, so an add-on's file almost certainly has them - but neither `json` nor
    YAML accepts `//`, and YAML fails especially confusingly (a comment containing a colon
    reads as a mapping). Without this, a perfectly ordinary mod file is silently rejected.
    
    Only whole lines are stripped. A `//` inside a JSON string is safe because JSON strings
    cannot contain a literal newline, so no string value can start a line."""
def get_mission_dir ():
    """Get the directory of the current mission.
    
    Returns:
        str: The script directory path."""
def load_yaml_string (s):
    """Parse a YAML string.
    
    Attempts to parse using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
    Args:
        s (str): YAML content as a string.
    
    Returns:
        dict or None: Parsed YAML data, or None if parsing fails."""
def merge_mod_ship_yaml (content, mod=None):
    """Merge ship data supplied as a YAML/JSON string into the ship data cache.
    
    Companion to :func:`sbs_utils.procedural.media.media_read_relative_file`, which
    returns a data file's CONTENTS relative to the current addon -- working whether
    the addon is a loose folder (dev) or a packaged ``.mastlib`` zip, where a plain
    filesystem path can't reach the file. So an addon can ship its own ship/terrain
    data next to its prefabs and load it in one line:
    
        merge_mod_ship_yaml(media_read_relative_file("shipData_monsters.yaml"), "MyMod")
    
    The parsed ``#ship-list`` is **prepended** (addon data ahead of built-in). Each entry
    is stamped with ``mod`` (the ``#mod`` key) so the low-level spawn can tell these
    engine-unknown entries apart and post-process them (see :func:`mod_ship_data_process`).
    The derived caches (``ship_index`` and the ``*_keys`` caches) are cleared so the new
    entries are visible on the next lookup.
    
    Args:
        content (str): YAML or JSON text (YAML is a JSON superset, so both parse).
        mod (str, optional): Name of the mod/addon these entries come from; stamped on
            each entry as ``#mod``. Defaults to None (untagged).
    
    Returns:
        dict | None: The updated ship data cache, or ``None`` if ``content`` was
            empty or carried no ``#ship-list``."""
def ship_data_flush_mod_file (mission_dir=None):
    """Write the mission's ``extraShipData.json`` so the engine can read it.
    
    Called by :func:`sbs_utils.procedural.cosmos.sim_create` immediately before
    ``create_new_sim()``, which is the moment the engine reads it. Safe to call when
    nothing is pending - it returns without touching anything.
    
    Returns:
        str | None: The path written, or ``None`` if nothing needed writing."""
def ship_data_merge_mod (content, mod=None):
    """Declare ship entries for the engine, from JSON/YAML text.
    
    .. deprecated::
        Use :func:`sbs_utils.procedural.ship_data.add_extra`, which points both the
        engine and the library at a file the addon SHIPS rather than generating one.
        This route reaches the engine by writing ``extraShipData.json``, which
        ``get_ship_data()`` then loads back on the next run while the addon declares
        the same entries again - measured at 51 hulls becoming 102 from run 2. Kept
        working for existing callers.
    
    Pair with ``media_read_relative_file`` so it works from a packaged ``.mastlib``::
    
        ship_data_merge_mod(media_read_relative_file("myships.json"), "MyMod")
    
    The entries also go into sbs_utils' own ``#ship-list`` (via ``merge_mod_ship_yaml``),
    so queries, ``filter_ship_data_by_side`` and the ``*_keys`` helpers see them without
    waiting for a sim to be created.
    
    Args:
        content (str): JSON or YAML text with a ``#ship-list``.
        mod (str, optional): Who supplied it. Stamped as ``#mod`` and used to name
            collisions.
    
    Returns:
        int: How many entries are pending, or ``None`` if nothing parsed."""
def ship_data_mod_reset ():
    """Drop pending entries at a mission boundary.
    
    Per-mission state: the next mission enables its own add-ons, and inheriting these would
    write ships it never asked for into its folder."""
def ship_data_pending_count ():
    """How many mod-contributed entries are waiting to be written. Reset-ledger probe."""
