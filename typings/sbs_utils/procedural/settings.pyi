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
def _note_explicit (data):
    """Record a source's top-level keys as explicitly authored."""
def _profile_overrides ():
    """Settings from `profile=<name>` on the command line -> `profiles/<name>.yaml`.
    
    The command line is for a HANDFUL of short, memorable arguments; a profile is how a
    launch carries twenty settings without twenty arguments. `cmd.exe` caps a command line
    at 8191 characters, shortcuts truncate, Windows quoting around spaces and `=` is
    painful, and none of it is diffable or reviewable. A file is all of those things."""
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
