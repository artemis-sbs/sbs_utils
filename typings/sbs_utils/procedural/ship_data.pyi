def _art_root_exists (graphics, root):
    """Is there art for this `artfileroot`, named the way the engine now resolves it?
    
    A BARE ROOT IS NO LONGER VALID, and this is the check that has to say so. Engine
    1.3.6 regenerated `data/shipData.yaml` with every entry reading `ships/<name>`: the
    base moved up from `data/graphics/ships` to `data/graphics`, and a bare `<name>` no
    longer resolves. MEASURED, one hull per run so the failure could be attributed
    (`data/missions/artroot_probe`): `ships/monster2` drew and its mesh was opened, while
    bare `monster1` put up
    
        Assertion failed!  false && "the artfileroot of this ship was not found."
        ObjectTypeDrawData.cpp:44
    
    - a modal dialog on the player's machine. The hull spawns fine on the server; the
    bill is paid by the first client that has to draw it. So a bare root is reported as
    missing even when the art is sitting right there under `graphics/ships`, because
    "the file exists" and "the engine can find it" have stopped being the same question.
    
    Left alone: a root that escapes the install (`../..`, or absolute). That really is
    art this function cannot judge.
    
    Matching is on the base name before the first dot, because one root covers a family:
    `<name>.paxmesh`, `<name>1024.png`, `<name>_diffuse.png`."""
def _art_that_is_not_there (text):
    """Which `artfileroot` values in this file have no art in the install?
    
    A hull whose art is missing spawns FINE on the server - nothing raises, the object
    exists, the mission carries on - and then kills the first client that has to draw it:
    
        Assertion failed! art3D && "the artfileroot of this ship was not found."
        ObjectTypeDrawData.cpp:40
    
    That is a modal dialog on the player's machine, from a typo in a data file. LM's turret
    entries asked for `tsn-fighter` when the art is `TSNfighter`, and it went unnoticed for
    as long as the engine was rejecting that whole file for unrelated reasons (2026-08-14).
    
    Quiet when it cannot check. Art lives in the Artemis install, not in the repo, so a CI
    runner has nothing to compare against - and a check that reported every hull as broken
    because it could not find the game would be worse than no check at all.
    
    Parsed with `load_yaml_string`, which uses the BUNDLED `sbs_utils.yaml`. A bare
    `import yaml` reaches PyYAML in site-packages, which exists on a developer machine and
    nowhere else: not in the embedded engine (site is off) and not on a CI runner that
    installs nothing. The `except` below would then swallow the ImportError and return "no
    art is missing" - so this check silently did nothing everywhere it was meant to run,
    which is the failure mode it exists to prevent."""
def _engine_path (path):
    """A path in the form the ENGINE wants: relative to the Cosmos root.
    
    Their own example is `add_extra_ship_data("extraShipDataAAA",
    "data/missions/BeamArcTest")` - root-relative, not absolute, and not relative
    to the mission. Every caller building that string by hand would get it wrong
    in a different way, and a wrong path is not an error here: the engine is
    forgiving about data it cannot find, so it fails as ships with no stats.
    
    An absolute path under the install is converted; anything else is passed
    through, since a caller who wrote a relative path already knew what it meant."""
def _find_extra_root (folder, filename):
    """The folder holding a logical ship-data path: the mission, then each media
    root, in the order `media_paths` already searches.
    
    Chosen by whether the FILE is there, not whether the folder is. An addon's
    logical folder name usually matches its own source folder - `turrets/` is both
    the mastlib's name and a real directory in the mission - so picking the first
    directory that exists silently picks the addon folder, which is exactly where
    the file no longer is.
    
    THE UNPACKED MEDIA PACK WINS. An addon developed in place has the same file twice -
    once in its source `media/` folder and once in the pack unpacked under `__lib__` -
    and the engine can only read the second. ENGINE-MEASURED 1.3.5, the whole of a
    morning:
    
        add_extra_ship_data("extraShipData_monsters",
                            "data/missions/__lib__/media/<pack>/prefabs")  -> works
        add_extra_ship_data("extraShipData_monsters",
                            "data/missions/LegendaryMissions/media/prefabs") -> silently
                            loads NOTHING
    
    The call does not fail either way, and the LIBRARY reads the file fine from both, so
    everything looks correct: the mission runs, the mock is happy, `sbs lint` is happy.
    The bill arrives when something spawns one of those hulls and the ENGINE is asked for
    a ship type it never received - `MemoryError: bad allocation` from
    `create_space_object`, minutes later, in a mission that never mentions ship data.
    (Measured harder still: asking the engine to build one directly is an access
    violation, not an exception.)
    
    Falls back to the mission folder, so a genuinely missing file still reports
    against somewhere a person can go and look."""
def _looks_like_hjson (text):
    """Is this extra ship data in a shape the ENGINE can read?
    
    The engine parses these files as **HJSON**, not YAML - its own
    `data/shipData.yaml` says so in the header. HJSON is JSON with comments, so
    a key cannot contain whitespace and there are no block sequences: a perfectly
    valid `- key: thing` list, or a `"beam Primary Beams":` block mapping, is a
    parse error.
    
    And it fails in SILENCE. `add_extra_ship_data` raises, we carry on, and the
    library still merges the file with PyYAML - which accepts both shapes - so
    every headless run, every unit test and every library lookup sees the ships.
    Only the engine does not, and the bill arrives later as a hull it was never
    given: LegendaryMissions' turrets spawned and never fired for exactly this
    reason (found 2026-08-14).
    
    So check the shape at load, where the file is in front of us."""
def _read_extra_ship_data (filename, path):
    """`(text, file)` for the file, trying the extensions the engine tries, or
    `(None, None)`.
    
    The FILE matters as much as the text now. The engine used to be handed a name
    and a folder and do its own extension search; it now wants "a fully-pathed
    filename (plus suffix)", so somebody has to decide whether this is the `.yaml`
    or the `.json`. Deciding it twice - once to read, once to tell the engine -
    is how the two drift apart, so it is decided once, here, by which file
    actually opened."""
def _tag_mod_entries (entries, mod):
    """Stamp every entry (in place) with its source mod so spawns can post-process it."""
def add_extra (name, path=None, mod=None):
    """Load another ship-data file for this mission.
    
    `name` has **no extension** - `.yaml` or `.json` is found here, so a mod can
    change format without the caller changing. It may include a logical folder
    (`"turrets/extraShipData_turrets"`). The engine now wants the fully-pathed
    file WITH its suffix, so the extension search that used to be the engine's job
    happens in `_read_extra_ship_data` and its answer is what the engine is handed
    - one decision, not two that can disagree.
    
    With no `path`, the file is looked for where the media system already looks:
    this mission's folder first, then each media pack it pinned. That matters
    because an ADD-ON cannot put a file where the engine can read it - a mastlib
    is a zip - while a media pack is unpacked to disk once. So an addon ships its
    hulls in its media pack and names them here, and neither it nor the library
    has to write anything.
    
    Returns True when the engine was told, False when only the library was.
    Missing files are not fatal, matching the engine's habit: a mod with a broken
    path should be a ship with no stats, not a dead mission."""
def add_ship_data (entry, mod=None, prepend=True):
    """Add a single entry to the in-memory ship data.
    
    Inserts ``entry`` into the ``#ship-list`` so it is returned by
    :func:`get_ship_data`, :func:`get_ship_index`, :func:`get_ship_data_for`,
    :func:`filter_ship_data_by_side`, and the ``*_keys`` helpers -- letting a
    script register a ship/terrain/pickup type at runtime without editing
    ``shipData`` or shipping an ``extraShipData.json``.
    
    The entry is **prepended** by default, matching how ``extraShipData.json`` is
    merged (script data ahead of built-in data). The derived caches
    (``ship_index`` and every ``*_keys`` cache) are cleared so the new entry shows
    up on the next lookup; the loaded ``ship_data_cache`` itself is preserved.
    
    Args:
        entry (dict): A ship data dict. Must include a ``"key"`` (used to index
            it); typically also ``"name"``, ``"side"``, ``"roles"``, and
            ``"artfileroot"``.
        mod (str, optional): Name of the mod/addon this entry comes from; stamped on
            the entry as ``#mod`` so the low-level spawn post-processes it (see
            :func:`mod_ship_data_process`). Defaults to None (untagged).
        prepend (bool, optional): Insert at the front of the list (script
            priority) when ``True`` (default); append to the end when ``False``.
    
    Returns:
        dict | None: The updated ship data cache, or ``None`` if ship data could
            not be loaded."""
def alien_keys ():
    """Return all pickup keys containing ``"alien"`` (cached).
    
    Returns:
        list[str]: Alien pickup type keys."""
def arvonian_ship_keys ():
    """Return all Arvonian ship keys (cached).
    
    Returns:
        list[str]: Arvonian ship type keys."""
def arvonian_starbase_keys ():
    """Return all Arvonian starbase keys (cached).
    
    Returns:
        list[str]: Arvonian starbase type keys."""
def asteroid_keys ():
    """Return all asteroid ship keys from the ship data (cached).
    
    Returns:
        list[str]: Asteroid type keys."""
def container_keys ():
    """Return all pickup keys containing ``"container"`` (cached).
    
    Returns:
        list[str]: Container pickup type keys."""
def crystal_asteroid_keys ():
    """Return all crystal asteroid keys, excluding plain asteroids (cached).
    
    Returns:
        list[str]: Crystal asteroid type keys."""
def danger_keys ():
    """Return all pickup keys containing ``"danger"`` (cached).
    
    Returns:
        list[str]: Danger pickup type keys."""
def extra_enable (enabled=True):
    """Allow or forbid the ENGINE side of `add_extra`.
    
    Off, the ships are still merged into sbs_utils, so headless runs and every
    library lookup behave the same; only the engine is not told. Use it to take
    the engine path out of play without touching any caller."""
def extra_enabled ():
    """Is the engine call currently allowed?"""
def extra_loaded ():
    """`[(filename, path, reached_engine, engine_arg)]` for every call so far, so a
    report can say what was loaded, what exact file the ENGINE was pointed at, and
    whether it heard about it. `engine_arg` is None when no file was found."""
def extra_replay ():
    """Tell the engine again about every extra ship data file it has been given.
    
    `create_new_sim()` REBUILDS the engine's ship data table - it reads the mission's
    `extraShipData.json` inside that call - and everything `add_extra_ship_data` registered
    beforehand is gone. Nothing reports it. The library keeps its own merged copy, so the
    ships still have stats everywhere sbs_utils can see, and the loss surfaces later as
    `MemoryError: bad allocation` from a spawn, against whichever mission line asked for
    one of those hulls.
    
    Missions register at story load, which is BEFORE the first map calls `sim_create()`, so
    this is the ordinary case rather than an edge one. LegendaryMissions declares its
    monsters with a top-level `shared`, which by design runs once and then becomes a no-op,
    so nothing ever re-issued them: every monster in the game was unspawnable from the first
    map start onward, and had been for as long as anyone could remember (measured
    2026-08-14 - inside LM every hull fails and re-issuing this exact call fixes all five).
    
    Replayed from the record rather than from the files: the library merge already happened
    and only the engine forgot."""
def extra_reset ():
    """Forget the record. Called by the per-mission reset, not by missions."""
def filter_ship_data_by_side (test_ship_key, sides, role=None, ret_key_only=False):
    """Return ship data entries matching a key substring, side filter, and optional role.
    
    Args:
        test_ship_key (str | None): Substring that must appear in the ship key,
            or ``None`` to match all keys.
        sides (str): Comma-separated side names to include (case-insensitive).
        role (str, optional): Single role that must be in the ship's role list.
            Defaults to None (no role filter).
        ret_key_only (bool, optional): Return a list of key strings instead of
            full data dicts. Defaults to False.
    
    Returns:
        list[str | dict]: Matching ship keys or data entries."""
def get_artemis_data_dir ():
    """Get the path to the Artemis Cosmos data directory.
    
    Returns:
        str: The data folder path (executable directory + "/data")."""
def get_mission_dir ():
    """Get the directory of the current mission.
    
    Returns:
        str: The script directory path."""
def get_mod (key_or_entry):
    """Return the source mod of a ship data entry, or ``None`` if it is engine-known.
    
    Exposed to MAST as ``ship_data_get_mod`` (the ``ship_data_`` prelude prefix); named
    ``get_mod`` here so it doesn't double-prefix to ``ship_data_ship_data_get_mod``.
    
    Args:
        key_or_entry (str | dict): A ship key, or a ship data entry dict.
    
    Returns:
        str | None: The mod name stamped at merge time, or ``None`` for built-in data."""
def get_mod_dir (mod):
    """Get the directory path for a mission module.
    
    Args:
        mod (str): The module/mission name.
    
    Returns:
        str: The full directory path for the module."""
def get_ship_data ():
    """Load and cache the full ship data, merging ``extraShipData.json`` if present.
    
    Results are cached after the first call. The mission-directory
    ``extraShipData.json`` is prepended to the ``#ship-list`` so mission ships
    take priority over built-in data.
    
    Returns:
        dict: The merged ship data dictionary."""
def get_ship_data_for (ship_key):
    """Return the full ship data entry for a given key.
    
    Args:
        ship_key (str): The ship type key.
    
    Returns:
        dict | None: Ship data dict, or ``None`` if not found."""
def get_ship_index ():
    """Return ship data indexed by ship key for fast O(1) lookup.
    
    Returns:
        dict[str, dict]: Mapping of ship key → ship data entry."""
def get_ship_name (ship_key):
    """Return the display name of a ship type by key.
    
    Args:
        ship_key (str): The ship type key.
    
    Returns:
        str | None: Ship display name, or ``None`` if the key is not found."""
def kralien_ship_keys ():
    """Return all Kralien ship keys (cached).
    
    Returns:
        list[str]: Kralien ship type keys."""
def kralien_starbase_keys ():
    """Return all Kralien starbase keys (cached).
    
    Returns:
        list[str]: Kralien starbase type keys."""
def load_data (file):
    """Load a data file as YAML or JSON, dispatching on the extension.
    
    ``.yaml``/``.yml`` are parsed as YAML; ``.json`` as JSON (comment- and
    trailing-comma-tolerant). When ``file`` has no recognised extension it is
    treated as a BASE path and the ``.yaml``, ``.yml`` then ``.json`` siblings are
    tried in turn -- so a caller can pass ``"shipData"`` (no extension) and get
    whichever form is present, YAML preferred.
    
    Args:
        file (str): Path to the data file, with or without a
            ``.yaml``/``.yml``/``.json`` extension.
    
    Returns:
        dict | list | None: The parsed data, or ``None`` if nothing loaded."""
def load_yaml_string (s):
    """Parse a YAML string.
    
    Attempts to parse using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
    Args:
        s (str): YAML content as a string.
    
    Returns:
        dict or None: Parsed YAML data, or None if parsing fails."""
def merge_mod_ship_data (mod, file=None):
    """Merge a mod folder's extra ship data (YAML or JSON) into the ship data cache.
    
    Args:
        mod (str): Mod directory name (resolved via ``get_mod_dir``).
        file (str, optional): The data file within the mod folder. Defaults to
            the base name ``"extraShipData"``, which loads ``extraShipData.yaml``
            or ``extraShipData.json`` (YAML preferred). Pass a name WITH a
            ``.yaml``/``.yml``/``.json`` extension to force a specific format.
    
    Returns:
        dict: The updated ship data cache."""
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
def mod_ship_data_process (so, entry):
    """Apply a runtime-merged (mod) ship data entry to a freshly spawned object.
    
    The engine's built-in shipData table doesn't contain entries merged at runtime
    (:func:`merge_mod_ship_yaml` / :func:`merge_mod_ship_data` / :func:`add_ship_data`),
    so ``create_space_object`` returns a bare object that never got the values the engine
    normally derives from a KNOWN shipData entry. The low-level spawn (``spawn_common``)
    calls this for such objects to reproduce that derivation.
    
    The shipData-field -> object mapping mirrors ``cosmos_dev.mock.sbs``'s reverse-engineered
    ``_apply_ship_data_to_object`` (the engine's data_set names are NOT the shipData spellings):
    
    * **Art** via ``set_ship_data_key(artfileroot)`` when the modded key differs from its art
      (the engine picks the mesh from ``data_tag``, not a data_set field). ``meshscale`` /
      ``radarscale`` are engine-internal render props with NO data_set key -- not applied.
    * **``exclusionradius``** -> the physics attribute ``engine_object.exclusion_radius``
      (not a data_set field).
    * **1-to-1 float scalars** (``turn_rate``, ``speed_coeff``, ``interactionradius``, ...).
    * **``hullpoints``** -> ``armor`` / ``armorMax`` (stations only; ships use another system).
    * **``baycount``** -> ``bay_count``; **``tubecount``** -> ``torpedo_tube_count``.
    * **``shields``** array -> ``shield_count`` + ``shield_val`` / ``shield_max_val`` per facing.
    * **``hull_port_sets``** beams -> ``beamCount`` + ``beamRange`` / ``beamDamage`` (coeff *
      6.0) / ``beamCycleTime`` / ``beamArcWidth`` / ``beamBarrelAngle`` per port.
    * **``torpedostart``** -> ``{Type}_NUM`` / ``_MAX`` / ``_VAL`` + ``torpedo_types_available``.
    
    Fields with no known engine mapping (and the meta key/name/side/roles/#mod) are skipped;
    a prefab may still set anything extra afterwards (it runs after spawn, so it wins).
    
    Args:
        so: The spawned SpaceObject (exposes ``.data_set`` and ``.set_ship_data_key``).
        entry (dict): The ship data entry (as merged, carrying ``#mod``)."""
def pirate_ship_keys ():
    """Return all pirate ship keys (cached).
    
    Returns:
        list[str]: Pirate ship type keys."""
def pirate_starbase_keys ():
    """Return all pirate starbase keys (cached).
    
    As of v1.2.2 no pirate starbases exist in ``shipData``; this returns an
    empty list.
    
    Returns:
        list[str]: Pirate starbase type keys."""
def plain_asteroid_keys ():
    """Return all plain asteroid keys, excluding crystal asteroids (cached).
    
    Returns:
        list[str]: Plain asteroid type keys."""
def reset_ship_data_caches ():
    """Clear the DERIVED ship data caches (index and key lists), not the data itself.
    
    Called by the merge/add functions after they change the ``#ship-list`` so the next
    lookup sees the new entries. For the mission-boundary reset that also drops the
    loaded data, use :func:`ship_data_reset_for_mission`."""
def ship_data_is_loaded () -> int:
    """Reset-ledger probe: 1 while ship data (possibly mod-merged) is held, else 0."""
def ship_data_reset_for_mission ():
    """Drop the loaded ship data ENTIRELY, including any merged mod entries.
    
    Deliberately NOT the same as :func:`reset_ship_data_caches`, which clears only the
    DERIVED caches and is called by the merge functions themselves - clearing
    ``ship_data_cache`` there would throw away the entries just merged.
    
    This is the MISSION-BOUNDARY reset. The next mission has its own mission directory
    (its own ``extraShipData``) and its own set of mods, so a ``#ship-list`` carrying the
    previous mission's merged entries must not survive into it. The engine forks a fresh
    process per mission and hides this; ``cosmos_dev`` reuses one interpreter and does
    not. Registered in the reset ledger as ``ship_data_cache``."""
def skaraan_ship_keys ():
    """Return all Skaraan ship keys (cached).
    
    Returns:
        list[str]: Skaraan ship type keys."""
def skaraan_starbase_keys ():
    """Return all Skaraan starbase keys (cached).
    
    Returns:
        list[str]: Skaraan starbase type keys."""
def terran_ship_keys ():
    """Return all TSN ship keys (cached).
    
    Returns:
        list[str]: Terran ship type keys."""
def terran_starbase_keys ():
    """Return all USPF station (Terran starbase) keys (cached).
    
    Returns:
        list[str]: Terran starbase type keys."""
def torgoth_ship_keys ():
    """Return all Torgoth ship keys (cached).
    
    Returns:
        list[str]: Torgoth ship type keys."""
def torgoth_starbase_keys ():
    """Return all Torgoth starbase keys (cached).
    
    Returns:
        list[str]: Torgoth starbase type keys."""
def ximni_ship_keys ():
    """Return all Ximni ship keys (cached).
    
    Returns:
        list[str]: Ximni ship type keys."""
def ximni_starbase_keys ():
    """Return all Ximni starbase keys (cached).
    
    Returns:
        list[str]: Ximni starbase type keys."""
