def _cli_overrides (known):
    """Settings from `var.NAME=value` command-line arguments.
    
    Prefixed because `command_line_dict()` is one flat namespace shared with the engine and
    every add-on: a bare `difficulty=` would be a collision waiting to happen, while `var.`
    is unambiguous and needs no parsing rules.
    
    An unknown NAME is applied AND warned about. Applied because a mission may legitimately
    read a setting sbs_utils has never heard of; warned because a typo that silently does
    nothing is the worst outcome - `var.DIFFICULTLY=7` would otherwise look like it worked."""
def _coerce (text):
    """A command-line value is always a string; give it the obvious type.
    
    int, then float, then true/false, else the string unchanged. Documented rather than
    clever on purpose - anything needing a list or a dict belongs in a profile file, which
    is where the boundary between the two surfaces sits."""
def _log (message):
    """Say which of two places answered. Not a warning - nothing is wrong, but "the
    profile applied" and "WHICH profile applied" are different facts once there are two
    folders it could have come from."""
def _merge_section (base, added):
    """Fold one profile's `addons:`/`media:` block into the running one.
    
    A setting is a single value, so the last profile to name it simply wins. A content
    section is not: `profile=skies,autoplay` excluding the stock skybox in one file and
    adding a debug add-on in the other must do BOTH, and a plain `|` would silently keep
    only the second. So include lists CONCATENATE (in typed order, deduped) and exclude
    lists UNION.
    
    An entry that one profile excludes and a later one includes ends up in both lists;
    the consumer applies excludes first and includes second, so the include wins. That is
    the useful direction - it lets a specific profile re-add something a broad one
    removed - and it is the same order a reader of the command line would assume."""
def _note_explicit (data):
    """Record a source's top-level keys as explicitly authored."""
def _profile_load (path_for):
    """Read `<name>.yaml`, falling back to `<name>.json`, from one profile folder."""
def _profile_load_named (name):
    """One profile by name, from the mission then from common_data. None if neither has it.
    
    Two places are searched, in order:
    
    1. `<mission>/profiles/<name>.yaml` - the mission's own, authored by whoever wrote the
       mission and shipped with it. Full featured: settings, `addons:`, `media:`.
    2. `common_data/profiles/<name>.yaml` - the OPERATOR's own, beside the missions rather
       than inside one, so a host's house setup is not written into a folder that a `git
       pull` or a re-extract owns. Equally full featured: an `addons:`/`media:` selection
       resolves through `__lib__`, which is shared, so "the Artemis 2.8 skies in whatever
       I am running tonight" is one file rather than one per mission.
    
    The mission wins on a name collision, so a mission can always ship a definitive
    profile under a name an operator also happens to use."""
def _profile_merge (base, added):
    """`base` overlaid with `added` - later wins on settings, sections accumulate."""
def _profile_names (raw):
    """`profile=a,b,c` -> ["a", "b", "c"], in the order they were typed.
    
    Comma-separated because a launch argument has no other list syntax that survives a
    Windows shortcut, and because the order IS the meaning - later profiles win.
    
    Duplicates are dropped rather than applied twice: `profile=house,house` merging a file
    into itself would be a no-op for settings but would double every `include:` entry."""
def _profile_overrides ():
    """Settings from `profile=<name>` on the command line -> `profiles/<name>.yaml`.
    
    The command line is for a HANDFUL of short, memorable arguments; a profile is how a
    launch carries twenty settings without twenty arguments. `cmd.exe` caps a command line
    at 8191 characters, shortcuts truncate, Windows quoting around spaces and `=` is
    painful, and none of it is diffable or reviewable. A file is all of those things.
    
    **Several may be named**, comma separated - `profile=autoplay7,tng_all` - and they are
    merged LEFT TO RIGHT, so the last one typed wins a settings key the earlier ones also
    set. That is what makes profiles composable instead of combinatorial: a host with three
    house settings and four mods needs seven files, not twelve. `addons:` and `media:`
    accumulate rather than replace (see :func:`_merge_section`) - excluding the stock
    skybox in one profile and adding a debug add-on in another has to do both.
    
    A name that matches no file is warned about and SKIPPED; the rest still apply. One
    typo in a list of four must not silently discard the other three, which is what a
    single-name reader did when handed a comma list."""
def _profile_section (name):
    """One `include:` / `exclude:` section of the profile, lowercased.
    
    Tolerant of shapes on purpose - a profile is hand-written YAML. A bare string is one
    entry, a list is many, and a missing section is empty rather than an error.
    
    Returns:
        tuple[list, set]: (include, exclude), both lowercased."""
def _runtime_settings_override ():
    """Settings overrides supplied at runtime via the ``COSMOS_SETTINGS`` env var
    (a JSON object), highest priority and requiring no ``settings.yaml`` edit.
    
    Used by tooling such as ``sbs debug --set AUTO_START=true``. Top-level keys
    replace the file/built-in values (e.g. ``{"AUTO_PLAY": {"enable": true}}``
    replaces the whole AUTO_PLAY entry)."""
def _set_path (target, dotted, value):
    """Set `a.b.c` inside nested dicts, creating levels as needed.
    
    Dotted paths exist for exactly one reason: the interesting settings are nested.
    `var.AUTO_PLAY.enable=true` is the case that motivated it - turning autoplay on from a
    launch argument is the whole point, and AUTO_PLAY is a dict."""
def _settings_add_races (key, races):
    """Append ``races`` to the comma-separated setting ``key``, keeping what is there.
    
    Shared by :func:`settings_add_playable_races` and :func:`settings_add_npc_races`."""
def _warn (message):
    """Loud about a launch argument that did nothing.
    
    Worth its own function because the quiet version of this cost real time: a launch
    argument whose value matched nothing selected an empty set, ran, and reported a pass -
    the result was believed before the typo was noticed. An argument that does not land
    must say so."""
def get_mission_dir_filename (filename):
    """Get the full path to a file in the current mission directory.
    
    Args:
        filename (str): The relative path from the mission directory.
    
    Returns:
        str: The full path to the file in the mission directory."""
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
def settings_add_defaults (additions):
    """Merge additional keys into the global settings defaults.
    
    ``additions`` acts as a fallback — existing values from ``settings.yaml``
    or ``setup.json`` take precedence, so this only fills gaps.
    
    Args:
        additions (dict): Default key-value pairs to add if not already present."""
def settings_add_npc_races (*races):
    """Add races to ``NPC_RACES``, keeping whatever is already listed.
    
    The NPC twin of :func:`settings_add_playable_races` - same semantics, same ordering
    caveat. Separate from the playable list on purpose: the races a player may BE and the
    races that raid them are different questions.
    
    Args:
        *races: race names, as separate arguments, a comma-separated string, or a list.
    
    Returns:
        list: the names actually added, in order."""
def settings_add_playable_races (*races):
    """Add races to ``PLAYABLE_RACES``, keeping whatever is already listed.
    
    The call a MOD that ships player-flyable hulls should make. Accepts names as separate
    arguments, one comma-separated string, or a list::
    
        settings_add_playable_races("Federation", "Klingon")
        settings_add_playable_races("Federation, Klingon")
    
    ADD rather than replace, so a mod can put a Galaxy alongside a TSN crew instead of
    taking the mission's own races away. A total conversion stays a MISSION's choice - it
    sets the setting to its own races alone - rather than something installing a mastlib
    does to you.
    
    WHY NOT `settings_set_mod_default`. That is the right tier for "a value the library
    ships and the mission did not override", and it deliberately returns False once the
    mission has spoken (`_explicit_keys`). Adding a race is not overriding a choice, it is
    widening a list, and it has to work even when the mission named the key - a mission
    that lists `TSN, Ximni` has said nothing at all about the Federation. So this edits the
    live settings dict, which is what every mod doing this had to hand-roll.
    
    ORDER MATTERS, and this is the one sharp edge. Addons decide which floor plans and
    fleet ladders to load by READING these settings at load time, and addon load order is
    non-deterministic. Adding a race the mod supplies hulls for is safe, because the mod's
    own addon merges those. Adding a race to unlock ANOTHER addon's content is a race with
    that addon's own load - call this as early as possible (the first line of the mod's
    ``__init__.mast``) and do not rely on it.
    
    Args:
        *races: race names, as separate arguments, a comma-separated string, or a list.
    
    Returns:
        list: the names actually added, in order. Empty when every one was already listed."""
def settings_get_defaults ():
    """Return the merged default settings dict, loading ``settings.yaml`` or ``setup.json`` if present.
    
    Results are cached after the first call. Mission-specific values from the
    YAML/JSON file override the built-in defaults.
    
    Returns:
        dict: The default settings mapping."""
def settings_get_profile ():
    """The selected profile file, PARSED - not merged.
    
    `settings_get_defaults()` folds a profile's settings keys into the settings dict and
    then forgets the file, which is all a setting ever needed. A profile that also selects
    ADD-ONS has to be read as a document, by the compiler, before any settings exist to
    merge into - so the parse is cached here and both callers share it.
    
    Returns:
        dict: the profile, or an empty dict when none was named or it did not load."""
def settings_npc_races ():
    """The races that can appear as NPCs, lowercased, from ``NPC_RACES``."""
def settings_playable_races ():
    """The races a player ship may be, lowercased, from ``PLAYABLE_RACES``."""
def settings_profile_addons ():
    """The profile's `addons:` include/exclude, by addon FOLDER name."""
def settings_profile_media ():
    """The profile's `media:` include/exclude, by media pack name."""
def settings_profile_reset ():
    """Forget the parsed profile. Called from ``reset_mission_state`` - a reused
    interpreter can be pointed at a different mission, and its profile."""
def settings_race_is_npc (race):
    """Whether a race can appear as an NPC.
    
    Used by the ``race_*`` addons to skip loading a fleet ladder for a race this mission
    never spawns. As with :func:`settings_race_is_playable`, matching ignores case and
    spacing, and an EMPTY setting means no restriction rather than no races."""
def settings_race_is_playable (race):
    """Whether a race may be flown as a player ship.
    
    Used by the ``interiors_*`` addons to skip loading floor plans for a race no player
    can be, since an interior is only ever built for a player ship.
    
    An EMPTY or missing ``PLAYABLE_RACES`` means "no restriction" rather than "nothing is
    playable" - a mission that clears the setting should get every race, not a game where
    no ship has an interior."""
def settings_seed_apply (value=None):
    """Seed the global RNG so a run is reproducible.
    
    Every random draw in sbs_utils flows through Python's single global
    ``random.Random`` instance -- both module-level ``random.*`` calls and the
    ``from random import ...`` bindings (scatter, vec) resolve to it -- so one
    seed here makes terrain scatter, fleet-race weights, dialogue ``%``
    selection, faces, and names all reproducible.
    
    Args:
        value (int|None): explicit seed. If ``None`` the ``seed_value`` setting
            is used. A falsy seed (the default ``0`` = "don't care") means pick
            one: a fresh entropy-based seed is generated, applied, and returned,
            so a run can always be reproduced later by passing the value back.
    
    Returns:
        int: the seed actually applied."""
def settings_set_mod_default (key, value):
    """Set a setting on behalf of a MOD - unless the mission already spoke for it.
    
    The tier that was missing. There are two kinds of "default" and the existing
    :func:`settings_add_defaults` only expresses the weaker one: it does
    ``additions | setting_defaults``, so anything already in the built-ins wins, and a mod
    can therefore only fill a key sbs_utils has never heard of. For a key the library ships
    a value for - ``MUSIC_SELECT``, ``PLAYABLE_RACES`` - a mod had no way to be heard at all.
    
    So the precedence is now, strongest first::
    
        var.NAME= (command line)  >  COSMOS_SETTINGS  >  profiles/<name>.yaml
                                  >  settings.yaml / setup.json
                                  >  settings_set_mod_default   <- this
                                  >  the library built-in
    
    which is the order an author would expect: a mod re-skins the game, and anything the
    mission or the operator actually typed still beats it.
    
    Last mod loaded wins between two mods, and load order is non-deterministic - so two mods
    claiming the same key is a genuine conflict, not something to paper over. Use a key the
    mod owns.
    
    Args:
        key (str): the setting name.
        value: the value.
    
    Returns:
        bool: whether it applied. False means the mission (or the launch) had already set it."""
