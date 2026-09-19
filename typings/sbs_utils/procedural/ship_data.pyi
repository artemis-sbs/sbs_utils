def _art_map (name):
    """The RACE_ART / ART_KEYS map, lowercased keys. Empty when unset.
    
    An explicit setting WINS; otherwise the active theater supplies it. That ordering is
    what stops the three maps drifting apart: authored by hand they can disagree (and did -
    a hand-written RACE_ART said `kralien -> Cardassian` while the generated ART_KEYS said
    Kazon, so one race produced different factions depending on which code path spawned
    it), while derived from one theater they cannot."""
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
def _art_sibling_exists (graphics, root, suffix):
    """Is ``<artfileroot><suffix>`` on disk, resolved the way the engine resolves art?
    
    Same two-base search as :func:`_art_root_exists` - a STOCK root is relative to
    ``data/graphics`` and a MOD's is relative to the exe - but matching an EXACT file
    name rather than the base-name-before-the-first-dot family. That distinction is the
    whole point: the family match is what lets a bare ``.obj`` stand in for art that was
    never generated."""
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
def _engine_name (path):
    """Drop a ship-data file's extension, because the engine appends its own.
    
    Only the three the engine searches are removed (.yaml, .yml, .json); any other
    trailing dot is left alone, since a pack is free to have one in a folder or stem
    and guessing there would break a path that already works."""
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
def _hull_rank (key):
    """A rough size rank for a hull key, so a battleship maps to a capital ship.
    
    `hullpoints` where the entry has it, else `meshscale` - neither is a real tonnage but
    both order a faction's ships the same way its author intended them to be read."""
def _interior_art_that_is_not_there (text):
    """Hulls that declare an interior but ship no silhouette sprite to cut it from.
    
    THE ENGINE DOES NOT TAKE INTERIOR CELL VALIDITY FROM shipData. It cuts it from the
    alpha channel of ``<artfileroot>1024.png`` (GRID_REFERENCE.md s2). So a hull can have
    a perfect floor plan, correct ``internalmapw``/``internalmaph``, and a merged
    ``.grid`` - and still render a BLANK Engineering console, because the engine found no
    valid cells to put any of it in.
    
    That is invisible from every angle a mod author has:
    
    * the floor plan parses and merges, so ``grid_get_layout`` answers happily;
    * ``grid_rebuild_grid_objects`` spawns the objects without complaint;
    * the MOCK fabricates a hull map from ``internalmapw`` alone and never looks at the
      art, so every headless run reports a healthy grid;
    * and ``_art_root_exists`` passes, because it matches the base name before the first
      dot - a bare ``<name>.obj`` satisfies it.
    
    Which is why this is a SEPARATE check rather than a stricter version of that one.
    Found on Cosmos-TNG-Mod, where 36 of 51 hulls shipped no derived art at all: the pack
    relied on the engine generating it in place, and the engine crashes doing that from a
    bare ``.obj``, so it stopped after 15.
    
    Only entries that declare ``internalmapw`` are checked - a hull with no interior has
    no reason to carry the sprite, and every one of the 63 stock hulls that declares one
    has it.
    
    Returns a list of ``(key, root, [missing file, ...])``. Quiet when it cannot check,
    for the same reason :func:`_art_that_is_not_there` is."""
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
def _prepend_replacing (entries):
    """Put `entries` at the front of the `#ship-list`, dropping anything already there
    that carries one of the same keys.
    
    A merge used to be a blind prepend, so re-supplying a file ADDED it rather than
    REPLACED it. `add_extra` merges the file it read, and the MOCK's
    `add_extra_ship_data` merges it a second time (the real engine does not merge
    library-side at all), so every headless run doubled a mod's hulls - 51 became 102 -
    while the engine saw one copy. `get_ship_data_for` reads the newest copy first, so
    nothing looked wrong until something counted: `filter_ship_data_by_side` answering
    with eight Klingon warships where the pack declares four.
    
    Prepending still means "addon data ahead of built-in". This only stops one key being
    present twice."""
def _read_extra_ship_data (filename, path):
    """`(text, file)` for the file, trying the extensions the engine tries, or
    `(None, None)`.
    
    The FILE matters as much as the text now. The engine used to be handed a name
    and a folder and do its own extension search; it now wants "a fully-pathed
    filename (plus suffix)", so somebody has to decide whether this is the `.yaml`
    or the `.json`. Deciding it twice - once to read, once to tell the engine -
    is how the two drift apart, so it is decided once, here, by which file
    actually opened."""
def _record_extra (filename, path, reached, engine_arg):
    """Remember this file for `extra_replay()`, ONCE.
    
    The record used to be a plain append, so declaring the same file twice made the replay
    issue the engine call twice. An addon's top-level statement is only once-only when it
    says `shared`, so a second client connecting re-runs the declaration - and
    `extra_loaded()` is what the reset ledger counts, so the duplicate read as a leak too."""
def _side_split (side):
    """A side's hulls as (mobile, stations).
    
    Deliberately NOT filtered on the `ship` role. Plenty of hulls do not carry it -
    `arvonian_fighter` is `cockpit,fighter` - and a role filter silently skips them, which
    shows up as "most of the faction converted and a few ships are still stock". Stations
    are split out because a starbase must be re-skinned as a starbase."""
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
def art_faction_for (race, role=None):
    """The shipData faction whose hulls should be DRAWN for `race`. ART ONLY.
    
    Returns `race` unchanged unless a mission or profile set ``RACE_ART``, so stock behavior
    is untouched by default.
    
    THIS DOES NOT CHANGE WHOSE SIDE ANYTHING IS ON. shipData `side` is a LOOKUP field - "what
    kind of ship is this" - while the side handed to :func:`npc_spawn` is the diplomatic
    faction that drives relations, comms and contact colour. The prefabs already keep the two
    apart as `origin` and `side_value`; this maps the first and never touches the second, so
    a Cardassian hull can spawn as a `raider` and the mission's diplomacy is unchanged.
    
    WHY A MOD NEEDS THIS. Overriding a STOCK ship key with mod art works on the server and
    never on a client: a client resolves a key it already knows against its own
    `data/shipData.yaml`, so its stock artfileroot wins and the override never crosses the
    wire. Pointing the lookup at the mod's OWN keys is what reaches clients, because the
    client has no local record for those and renders what the server sends.
    
    Args:
        race (str): the mission's own faction name, e.g. ``"kralien"``.
        role (str, optional): if given, the mapping is only honored when the mapped faction
            actually has hulls in that role. Without this a typo or a partial mod would
            silently spawn nothing at all, which is much harder to notice than wrong art.
    
    Returns:
        str: the faction to look hulls up under."""
def art_key_for (ship_key):
    """The hull key to DRAW in place of `ship_key`. ART ONLY.
    
    The companion to :func:`art_faction_for`, for the OTHER way a hull gets chosen. Some
    callers do not look a ship up by faction at all - they name the key outright:
    
      * stations (``station_type``), and
      * fleet ladders, which list their hulls class by class so a wave keeps its shape.
    
    A faction map cannot help those, so they get a key map instead - ``ART_KEYS``, keyed by
    the STOCK key being replaced. Mapping per key also PRESERVES THE LADDER'S CHOICES: a
    battleship is replaced by a specific hull rather than by a random ship of some faction.
    
    Returns `ship_key` unchanged when unset, or when the replacement is not in the ship
    table - a half-written map should degrade to stock art, never to nothing spawning."""
def art_key_in_faction (ship_key, faction):
    """Pair one hull into ``faction`` by size rank. Identity when it cannot.
    
    The single-key form of what :func:`art_keys_from_theater` does in bulk, for the case
    where a caller wants a DIFFERENT faction than the theater's own race map gives - the
    crew flying Orion hulls while the theater still re-skins `tsn` allies as Federation.
    
    Falls back to ``ship_key`` when the faction has no comparable hull, because spawning
    stock art is recoverable and spawning nothing is not."""
def art_keys_cache_clear ():
    """Drop the generated ART_KEYS pairing. On the reset ledger with the theaters."""
def art_keys_from_theater ():
    """Generate a stock-key -> mod-key map from the active theater's ``Art:`` map.
    
    The faction map (`RACE_ART`) only reaches hulls that are LOOKED UP by faction. A fleet
    LADDER names its hulls outright, class by class, so a wave keeps its shape - and those
    never consult a faction map at all. This bridges them: for every race the theater
    repoints, pair that race's stock hulls against the target faction's hulls BY SIZE RANK,
    so the ladder's shape survives the re-skin (its biggest ship is still the biggest).
    
    Cached per theater - the pairing is deterministic, and recomputing it per spawn would
    walk the whole ship table every time."""
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
    
    `create_new_sim()` REBUILDS the engine's ship data table (engine 1.3.4 also re-reads the
    mission's `extraShipData.json` inside that call; later engines appear not to), and
    everything `add_extra_ship_data` registered beforehand is gone. Nothing reports it. The library keeps its own merged copy, so the
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
def extra_report_untold ():
    """Name the mods the engine does not have, while it can still be acted on.
    
    Called from sim_create() right after extra_replay() - the point where the table has
    just been rebuilt and re-fed, so anything still missing is missing for the rest of
    the mission. Goes to debug.log too, the channel that survives an engine session."""
def extra_reset ():
    """Forget the record. Called by the per-mission reset, not by missions."""
def extra_ship_data_enabled ():
    """Whether extra ship data may be loaded at all.
    
    Reads the `EXTRA_SHIP_DATA` setting, defaulting to False. A caller that has to
    decide before settings exist - or a test - overrides it with
    `extra_ship_data_force`."""
def extra_ship_data_force (on=True):
    """Override the setting. `None` hands control back to it."""
def extra_untold ():
    """Which mods have hulls in the LIBRARY that the ENGINE was never (re-)told about?
    
    [(mod, hull_count)], sorted. Empty is the healthy answer.
    
    A mod that calls sbs.add_extra_ship_data() ITSELF is not in _extra_ship_data_loaded,
    so extra_replay() has nothing to replay for it - and create_new_sim() rebuilding the
    table is what takes its hulls away. Everything library-side keeps working, which is
    why it goes unnoticed: every lookup, picker, headless run and lint reports the hulls
    present. The bill arrives as a spawn dying inside the engine, in a mission that never
    mentions ship data. Three shipped mods were in exactly that state on engine 1.3.6.
    
    Matched on the ship KEY, not on the #mod stamp: under the MOCK, add_extra_ship_data
    merges the file a second time and re-stamps every entry with its own name, so a name
    comparison reports a correctly-declared mod as untold."""
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
def ship_art_image (id_or_key, size=1024):
    """The image key for a ship's flat art -- e.g. ``ships/TSNBattleship1024``.
    
    The engine ships a top-down sprite beside every hull mesh, named
    ``<artfileroot><size>.png``: 1024 is the big one the hull mask is cut from,
    256 the small one. It is the only picture of a ship a GUI can draw without
    asking the engine for a 3d render, so it is what a panel uses to show WHICH
    ship it is talking about.
    
    ``artfileroot`` carries the whole path (``ships/<name>``) and the base for it
    is ``data/graphics`` -- so what comes back here can be handed straight to
    ``gui_image*`` or to a ``background-image:`` style. Neither wants the ``.png``.
    A bare root (no ``/``) is the spelling engine 1.3.6 stopped resolving; it is
    returned unchanged rather than guessed at, because ``_art_root_exists`` is
    where that judgement belongs.
    
    Args:
        id_or_key (Agent | int | str): A space object, its id, or a shipData key.
        size (int, optional): Which sprite - 1024 or 256. Defaults to 1024.
    
    Returns:
        str | None: The image key, or ``None`` when the ship data has no art.
    
    Example:
        art = ship_art_image(target_id)
        gui_sub_section(f"col-width: square; background-image: {art}; background: white;")"""
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
