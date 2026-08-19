import os
import json
import random
from ..fs import load_json_data, get_mission_dir_filename, load_yaml_data


def _runtime_settings_override():
    """Settings overrides supplied at runtime via the ``COSMOS_SETTINGS`` env var
    (a JSON object), highest priority and requiring no ``settings.yaml`` edit.

    Used by tooling such as ``sbs debug --set AUTO_START=true``. Top-level keys
    replace the file/built-in values (e.g. ``{"AUTO_PLAY": {"enable": true}}``
    replaces the whole AUTO_PLAY entry).
    """
    raw = os.environ.get("COSMOS_SETTINGS")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _coerce(text):
    """A command-line value is always a string; give it the obvious type.

    int, then float, then true/false, else the string unchanged. Documented rather than
    clever on purpose - anything needing a list or a dict belongs in a profile file, which
    is where the boundary between the two surfaces sits.
    """
    t = str(text).strip()
    try:
        return int(t)
    except ValueError:
        pass
    try:
        return float(t)
    except ValueError:
        pass
    low = t.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    return t


def _set_path(target, dotted, value):
    """Set `a.b.c` inside nested dicts, creating levels as needed.

    Dotted paths exist for exactly one reason: the interesting settings are nested.
    `var.AUTO_PLAY.enable=true` is the case that motivated it - turning autoplay on from a
    launch argument is the whole point, and AUTO_PLAY is a dict.
    """
    parts = [p for p in str(dotted).split(".") if p]
    if not parts:
        return
    node = target
    for part in parts[:-1]:
        nxt = node.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            node[part] = nxt
        node = nxt
    node[parts[-1]] = value


_profile_data = None            # the parsed profile file, or {} once we have looked
_PROFILE_UNREAD = object()


def settings_get_profile():
    """The selected profile file, PARSED - not merged.

    `settings_get_defaults()` folds a profile's settings keys into the settings dict and
    then forgets the file, which is all a setting ever needed. A profile that also selects
    ADD-ONS has to be read as a document, by the compiler, before any settings exist to
    merge into - so the parse is cached here and both callers share it.

    Returns:
        dict: the profile, or an empty dict when none was named or it did not load.
    """
    global _profile_data
    if _profile_data is None:
        data = _profile_overrides()
        _profile_data = data if isinstance(data, dict) else {}
    return _profile_data


def settings_profile_reset():
    """Forget the parsed profile. Called from ``reset_mission_state`` - a reused
    interpreter can be pointed at a different mission, and its profile."""
    global _profile_data
    _profile_data = None


def _profile_section(name):
    """One `include:` / `exclude:` section of the profile, lowercased.

    Tolerant of shapes on purpose - a profile is hand-written YAML. A bare string is one
    entry, a list is many, and a missing section is empty rather than an error.

    Returns:
        tuple[list, set]: (include, exclude), both lowercased.
    """
    section = settings_get_profile().get(name) or {}
    if not isinstance(section, dict):
        return [], set()

    def _items(key):
        raw = section.get(key) or []
        if isinstance(raw, str):
            raw = [raw]
        return [str(x).strip().lower() for x in raw if str(x).strip()]

    return _items("include"), set(_items("exclude"))


def settings_profile_addons():
    """The profile's `addons:` include/exclude, by addon FOLDER name."""
    return _profile_section("addons")


def settings_profile_media():
    """The profile's `media:` include/exclude, by media pack name."""
    return _profile_section("media")


def _profile_load(path_for):
    """Read `<name>.yaml`, falling back to `<name>.json`, from one profile folder."""
    data = load_yaml_data(path_for(".yaml"))
    if data is None:
        data = load_json_data(path_for(".json"))
    return data if isinstance(data, dict) else None


def _profile_strip_content(data, name):
    """Drop `addons:`/`media:` from an OPERATOR-tier profile, loudly.

    Those two sections are resolved against one mission's `story.json` - an `exclude` names
    an add-on that mission declares, an `include` names one it can find. A profile shared
    across missions cannot mean anything by them. Honoring them anyway is the worst option
    available: excluding an add-on another one `requires` compiles the story to ZERO labels
    while still reporting PASS, and an unmet `include` loses art silently. So they are
    refused, by name, and the settings in the same file still apply.
    """
    dropped = [k for k in ("addons", "media") if k in data]
    if not dropped:
        return data
    _warn(f"profile='{name}' is a shared profile, so its "
          f"{' and '.join(dropped)} section(s) were ignored - add-on and media selection "
          f"only resolves against one mission's story.json. Put it in "
          f"<mission>/profiles/{name}.yaml instead.")
    return {k: v for k, v in data.items() if k not in ("addons", "media")}


def _profile_overrides():
    """Settings from `profile=<name>` on the command line -> `profiles/<name>.yaml`.

    The command line is for a HANDFUL of short, memorable arguments; a profile is how a
    launch carries twenty settings without twenty arguments. `cmd.exe` caps a command line
    at 8191 characters, shortcuts truncate, Windows quoting around spaces and `=` is
    painful, and none of it is diffable or reviewable. A file is all of those things.

    Two places are searched, in order:

    1. `<mission>/profiles/<name>.yaml` - the mission's own, authored by whoever wrote the
       mission and shipped with it. Full featured: settings, `addons:`, `media:`.
    2. `common_data/profiles/<name>.yaml` - the OPERATOR's own, beside the missions rather
       than inside one, so a host's house setup is not written into a folder that a `git
       pull` or a re-extract owns. **Settings only** (see :func:`_profile_strip_content`).

    The mission wins on a name collision, so a mission can always ship a definitive
    profile under a name an operator also happens to use.
    """
    from .command_line import command_line_get
    from ..fs import get_common_data_filename
    name = command_line_get("profile")
    if not name:
        return None
    name = str(name).strip()

    data = _profile_load(
        lambda ext: get_mission_dir_filename(os.path.join("profiles", name + ext)))
    if data is not None:
        return data

    data = _profile_load(lambda ext: get_common_data_filename("profiles", name + ext))
    if data is not None:
        _log(f"profile='{name}' came from common_data/profiles - shared across missions")
        return _profile_strip_content(data, name)

    _warn(f"profile='{name}' matched neither profiles/{name}.yaml in the mission nor "
          f"common_data/profiles/{name}.yaml - ignoring it")
    return None


def _cli_overrides(known):
    """Settings from `var.NAME=value` command-line arguments.

    Prefixed because `command_line_dict()` is one flat namespace shared with the engine and
    every add-on: a bare `difficulty=` would be a collision waiting to happen, while `var.`
    is unambiguous and needs no parsing rules.

    An unknown NAME is applied AND warned about. Applied because a mission may legitimately
    read a setting sbs_utils has never heard of; warned because a typo that silently does
    nothing is the worst outcome - `var.DIFFICULTLY=7` would otherwise look like it worked.
    """
    from .command_line import command_line_dict
    out = {}
    for key, value in (command_line_dict() or {}).items():
        if not str(key).lower().startswith("var."):
            continue
        path = str(key)[4:]
        if not path:
            continue
        root = path.split(".")[0]
        if root not in known:
            _warn(f"var.{path} is not a known setting - applying it anyway, but check the "
                  f"spelling")
        _set_path(out, path, _coerce(value))
    return out or None


def _log(message):
    """Say which of two places answered. Not a warning - nothing is wrong, but "the
    profile applied" and "WHICH profile applied" are different facts once there are two
    folders it could have come from."""
    try:
        from .execution import log
        log(message, "settings")
    except Exception:
        print("settings:", message)


def _warn(message):
    """Loud about a launch argument that did nothing.

    Worth its own function because the quiet version of this cost real time: a launch
    argument whose value matched nothing selected an empty set, ran, and reported a pass -
    the result was believed before the typo was noticed. An argument that does not land
    must say so.
    """
    try:
        from .execution import log
        log(message, "settings", "warning")
    except Exception:
        print("settings warning:", message)


setting_defaults = None
# Keys an author set EXPLICITLY for this run - settings.yaml/setup.json, the profile,
# COSMOS_SETTINGS, or var.NAME= on the command line. A mod may not override these; see
# settings_set_mod_default.
_explicit_keys = set()


def _note_explicit(data):
    """Record a source's top-level keys as explicitly authored."""
    if isinstance(data, dict):
        _explicit_keys.update(data.keys())


def settings_get_defaults():
    """Return the merged default settings dict, loading ``settings.yaml`` or ``setup.json`` if present.

    Results are cached after the first call. Mission-specific values from the
    YAML/JSON file override the built-in defaults.

    Returns:
        dict: The default settings mapping.
    """
    global setting_defaults
    if setting_defaults is not None:
        return setting_defaults
    
    setting_defaults = {
        "OPERATOR_MODE": {
            "enable": False,
            "logo": "media/operator",
            "show_logo_on_main": True,
            "pin": "000000"
        },
        "AUTO_START": False,
        "AUTO_START_DELAY": 10,
        # Come back on the setup screen with the settings the LAST game started with,
        # instead of the ones in settings.yaml. Off by default, deliberately: a venue or
        # convention machine wants every group to start from the same known state, and
        # that is the behavior it already has - turning this on is a choice a host makes.
        # A host who wants it always on puts it in a profile.
        #
        # It remembers per mission AND per map (see procedural/maps.py game_code_last_*),
        # so switching maps, or missions, does not drag another setup along.
        "RESTORE_LAST_SETUP": False,
        "WORLD_SELECT": "siege",
        "MAP_SIZE": "Medium",
        "TERRAIN_SELECT": "some",
        "LETHAL_SELECT": "none",
        "FRIENDLY_SELECT": "few",
        "MONSTER_SELECT": "none",
        "UPGRADE_SELECT": "max",
        "seed_value": 0,
        "GAME_STARTED": False,
        "GAME_ENDED": False,
        "DIFFICULTY": 5,
        "PLAYER_CREATE_DEFAULT": True,
        "PLAYER_COUNT": 1,
        "GRID_THEME": 0,
        # Which music bank plays. A bare folder name under data/audio/music, the display
        # name of an @media/music label, or "random" to pick from every declared one.
        #
        # It lives HERE, in the library built-ins, rather than in a mission's settings.yaml,
        # and that placement is the feature: a key present in settings.yaml is explicit and
        # outranks a mod, so writing "MUSIC_SELECT: random" into LegendaryMissions would stop
        # every mod built on it - the TNG mod being the case in hand - from ever setting its
        # own soundtrack. A mission that genuinely wants to pin one still can, and should.
        "MUSIC_SELECT": "random",
        # Whether set_music_folder may be handed a PATH. Leave it False: on engine 1.3.6 a
        # path HANGS the engine (data/missions/music_probe). Exists so that probe can test a
        # newer build without a library rebuild.
        "MUSIC_ENGINE_ACCEPTS_PATHS": False,
        # Which races a player ship may be. Comma separated, matched against a hull's
        # shipData "side" (case and spacing are ignored).
        #
        # Ship INTERIORS are the main consumer: `grid_rebuild_grid_objects` only ever
        # builds a grid for a player ship, so an interior for a race nobody can fly is
        # parsed at load and never used. LegendaryMissions' interiors_* addons skip
        # themselves when their race is not listed here.
        #
        # The default lists every race that HAS interiors, so behavior is unchanged out of
        # the box. Narrow it - "TSN" alone, say - when a mission knows what its players
        # fly, and widen it when a mod adds a race.
        "PLAYABLE_RACES": "TSN, USFP, Ximni, Arvonian, Torgoth, Skaraan, Kralien, "
                          "Biomech, Pirate",
        # Which races can show up as NPCs - specifically, whose raiding fleet ladders get
        # loaded. A race not listed here has no fleet composition, so nothing will spawn
        # one, and "random" will not pick it.
        #
        # Separate from PLAYABLE_RACES on purpose: the races a player may BE and the races
        # that raid them are different questions, and most missions want few of the first
        # and many of the second.
        "NPC_RACES": "Kralien, Torgoth, Arvonian, Skaraan, Ximni, Pirate",
        "PLAYER_LIST": [
            {
                "name": "Artemis",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Intrepid",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Aegis",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Horatio",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Excalibur",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Hera",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Ceres",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
            {
                "name": "Diana",
                "id": None,
                "side": "tsn",
                "ship": "tsn_battle_cruiser",
                "face": "terran",
            },
        ],
    }
    setup_data = load_yaml_data(get_mission_dir_filename("settings.yaml"))
    if setup_data is None:
        setup_data = load_json_data(get_mission_dir_filename("setup.json"))
    if setup_data is not None:
        setting_defaults = setting_defaults | setup_data
        _note_explicit(setup_data)
    # Runtime overrides (e.g. `sbs debug --set ...`) win over the file/built-ins
    # without editing settings.yaml.
    # A named profile: `profile=soak` -> profiles/soak.yaml. Bulk config belongs in a file
    # that the command line merely NAMES.
    profile = _profile_overrides()
    if profile is not None:
        setting_defaults = setting_defaults | profile
        _note_explicit(profile)
    # Runtime overrides (e.g. `sbs debug --set ...`) win over the file/built-ins
    # without editing settings.yaml.
    override = _runtime_settings_override()
    if override is not None:
        setting_defaults = setting_defaults | override
        _note_explicit(override)
    # `var.NAME=value` on the command line is LAST: typing it is the most explicit
    # per-launch act there is, so it beats the file, the profile and the env var. Kept
    # deliberately small - it is for deltas, not configuration.
    cli = _cli_overrides(set(setting_defaults))
    if cli is not None:
        _note_explicit(cli)
        for key, value in cli.items():
            if isinstance(value, dict) and isinstance(setting_defaults.get(key), dict):
                setting_defaults[key] = setting_defaults[key] | value
            else:
                setting_defaults[key] = value
    return setting_defaults


def settings_seed_apply(value=None):
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
        int: the seed actually applied.
    """
    if value is None:
        # `seed=` on the command line outranks the setting: a soak comparing runs needs to
        # pin the seed per launch, and editing settings.yaml between runs is exactly the
        # kind of shared-state fiddling a launch argument exists to avoid.
        from .command_line import command_line_get
        cli_seed = command_line_get("seed")
        if cli_seed:
            try:
                value = int(str(cli_seed).strip())
            except ValueError:
                _warn(f"seed='{cli_seed}' is not a number - using the setting instead")
                value = None
        if value is None:
            value = settings_get_defaults().get("seed_value", 0)
    value = int(value) if value else random.randrange(1, 2**31)
    random.seed(value)
    return value


def settings_add_defaults(additions):
    """Merge additional keys into the global settings defaults.

    ``additions`` acts as a fallback — existing values from ``settings.yaml``
    or ``setup.json`` take precedence, so this only fills gaps.

    Args:
        additions (dict): Default key-value pairs to add if not already present.
    """
    global setting_defaults
    setting_defaults = settings_get_defaults()
    #
    # Note it is in this order because the json file 
    # has the true values, the additions is jst to make
    # sure the setting has a value
    #
    setting_defaults =   additions | setting_defaults
    # NOTE: Should this return the setting_defaults?




def settings_set_mod_default(key, value):
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
        bool: whether it applied. False means the mission (or the launch) had already set it.
    """
    global setting_defaults
    setting_defaults = settings_get_defaults()
    if key in _explicit_keys:
        return False
    setting_defaults[key] = value
    return True


def settings_playable_races():
    """The races a player ship may be, lowercased, from ``PLAYABLE_RACES``."""
    raw = settings_get_defaults().get("PLAYABLE_RACES") or ""
    if not isinstance(raw, str):
        # A mission may reasonably have written a list instead of a string.
        raw = ",".join(str(x) for x in raw)
    return {r.strip().lower() for r in raw.split(",") if r.strip()}


def settings_race_is_playable(race):
    """Whether a race may be flown as a player ship.

    Used by the ``interiors_*`` addons to skip loading floor plans for a race no player
    can be, since an interior is only ever built for a player ship.

    An EMPTY or missing ``PLAYABLE_RACES`` means "no restriction" rather than "nothing is
    playable" - a mission that clears the setting should get every race, not a game where
    no ship has an interior.
    """
    races = settings_playable_races()
    if not races:
        return True
    return str(race or "").strip().lower() in races


def settings_npc_races():
    """The races that can appear as NPCs, lowercased, from ``NPC_RACES``."""
    raw = settings_get_defaults().get("NPC_RACES") or ""
    if not isinstance(raw, str):
        raw = ",".join(str(x) for x in raw)
    return {r.strip().lower() for r in raw.split(",") if r.strip()}


def settings_race_is_npc(race):
    """Whether a race can appear as an NPC.

    Used by the ``race_*`` addons to skip loading a fleet ladder for a race this mission
    never spawns. As with :func:`settings_race_is_playable`, matching ignores case and
    spacing, and an EMPTY setting means no restriction rather than no races.
    """
    races = settings_npc_races()
    if not races:
        return True
    return str(race or "").strip().lower() in races
