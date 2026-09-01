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
       pull` or a re-extract owns. Equally full featured: an `addons:`/`media:` selection
       resolves through `__lib__`, which is shared, so "the Artemis 2.8 skies in whatever
       I am running tonight" is one file rather than one per mission.

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
        # A shared profile is a FULL profile, `addons:`/`media:` included. Those resolve
        # globally, not per mission: `addons: include:` falls back to __lib__ (see
        # Mast.addon_include_path) and a media pack matches the shared packs there, so
        # "the Artemis 2.8 skies in whatever I am running" is exactly the case this tier
        # is for. Only `exclude:` names something the mission itself declared, and an
        # exclude that matches nothing is a no-op filter rather than an error.
        extra = " (selects content)" if ("addons" in data or "media" in data) else ""
        _log(f"profile='{name}' came from common_data/profiles - shared across "
             f"missions{extra}")
        return data

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
        # Let a mission or mod declare extra hulls. OFF, because the answer depends on
        # the INSTALL: the engine only grew a working extra-ship-data path in v1.3.7,
        # and on v1.3.4 a declared hull never registers - then spawning one dies inside
        # the engine as `bad allocation`, minutes later, against unrelated code. A
        # mission that knows its engine sets this true, usually in a profile.
        "EXTRA_SHIP_DATA": False,
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
        # Which crew roster staffs consoles nobody named - a roster key, its display name,
        # "random" to pick from every declared one, or "" for none.
        #
        # It lives HERE, in the library built-ins, for the same reason MUSIC_SELECT does: a
        # key present in a mission's settings.yaml is EXPLICIT and outranks a mod, so writing
        # CREW_SELECT into LegendaryMissions would stop the TNG mod - the case in hand - from
        # ever claiming it with settings_set_mod_default.
        #
        # The default is "" and NOT "random", which is the backward-compatibility guarantee:
        # with nothing selected the resolution chain stops before it can invent anybody, so a
        # mission that does none of this behaves exactly as it always has. Defaulting to
        # "random" would silently rename every unmanned console in every existing mission,
        # and a Director rundown nobody touched would change on air.
        "CREW_SELECT": "",
        # Whether a console nobody named gets a name anyway - a random one, different from
        # every other console in the run.
        #
        # ON, because the crew name existed for years and almost nobody typed one, so every
        # seat on air read "unmanned". Turning it on is what makes the Director's bridge wall
        # and the Gamemaster's message list read like a crewed ship out of the box.
        #
        # It is the one part of the crew system that changes what an EXISTING mission shows.
        # Set false for a mission that wants a seat nobody claimed to read as empty.
        "CREW_AUTONAME": True,
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
        # ART ONLY. Maps a mission's own faction to the shipData faction its hulls should be
        # DRAWN from, leaving the side a ship actually spawns on - and therefore diplomacy,
        # comms and contact colour - completely alone.
        #
        # WHY IT HAS TO BE SEPARATE FROM THE SIDE. shipData `side` is a LOOKUP field ("what
        # kind of ship is this"), while the side passed to npc_spawn is the diplomatic
        # faction. A prefab already keeps them apart as `origin` vs `side_value`; this is
        # the knob that lets a mod move the first without touching the second.
        #
        # WHY A MOD NEEDS IT AT ALL: overriding a STOCK ship key with mod art works on the
        # server and NEVER on a client. A client resolves a key it already knows against its
        # own data/shipData.yaml, so its stock artfileroot wins and the override never
        # crosses the wire. Pointing the lookup at the mod's OWN keys is what reaches
        # clients, because the client has no local record for those and uses what the server
        # sends. Empty here, so nothing changes unless a mission or profile sets it.
        "RACE_ART": {},
        # ART ONLY, same reasoning, for the OTHER way a hull gets chosen: by explicit KEY
        # rather than by faction. Keyed by the stock key being replaced. Covers stations,
        # and fleet ladders - which name their hulls outright and so never reach RACE_ART.
        "ART_KEYS": {},
        # ART ONLY, third of the set, for FACES. Maps a mission's own race/side to the face
        # race a crew portrait should be drawn from.
        #
        # IT NEEDS ITS OWN MAP because face races are SPECIES and ship sides are FACTIONS -
        # they do not spell the same. A mod's Federation ships are crewed by `human`, not by
        # `federation`, and a faction can have ships and no faces at all (Cosmos-TNG-Mod
        # fields Breen hulls and registers no Breen portraits). Reusing RACE_ART here would
        # silently fall back to terran faces for every one of those.
        #
        # Consulted inside random_face(), so every caller gets it - a name with no entry
        # passes through unchanged, which is why this is safe to leave empty.
        "RACE_FACES": {},
        # Which declared THEATER is active - the enemy roster a mission fights. Empty
        # means "no theater", and every consumer then keeps its own literal list, so a
        # stock mission is untouched. Resolvable per map (`Defaults: THEATER: x` in the
        # @map metadata), per profile, or with `var.THEATER=` on the command line.
        "THEATER": "",
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


def _settings_add_races(key, races):
    """Append ``races`` to the comma-separated setting ``key``, keeping what is there.

    Shared by :func:`settings_add_playable_races` and :func:`settings_add_npc_races`.
    """
    flat = []
    for r in races:
        if r is None:
            continue
        if isinstance(r, str):
            flat += [p for p in r.split(",")]
        else:
            # A list/tuple/set passed as one argument, rather than as *args.
            flat += [str(p) for p in r]
    flat = [r.strip() for r in flat if str(r).strip()]

    settings = settings_get_defaults()
    raw = settings.get(key) or ""
    if not isinstance(raw, str):
        raw = ",".join(str(x) for x in raw)
    have = {r.strip().lower() for r in raw.split(",") if r.strip()}

    added = []
    for r in flat:
        if r.lower() in have:
            continue
        have.add(r.lower())          # dedupe WITHIN this call too, not just against `have`
        added.append(r)
    if added:
        settings[key] = (raw + ", " if raw.strip() else "") + ", ".join(added)
    return added


def settings_add_playable_races(*races):
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
        list: the names actually added, in order. Empty when every one was already listed.
    """
    return _settings_add_races("PLAYABLE_RACES", races)


def settings_add_npc_races(*races):
    """Add races to ``NPC_RACES``, keeping whatever is already listed.

    The NPC twin of :func:`settings_add_playable_races` - same semantics, same ordering
    caveat. Separate from the playable list on purpose: the races a player may BE and the
    races that raid them are different questions.

    Args:
        *races: race names, as separate arguments, a comma-separated string, or a list.

    Returns:
        list: the names actually added, in order.
    """
    return _settings_add_races("NPC_RACES", races)
