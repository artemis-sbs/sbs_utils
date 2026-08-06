"""Which ships make up a race's raiding fleet, by difficulty.

WHY THIS IS A REGISTRY AND NOT A TABLE IN A MISSION. The composition ladders used to be
six `siege_<race>_fleet` literals in `LegendaryMissions/fleets/map_common.py` - roughly 420
lines - reached through a seven-branch `if race == "..."` chain, with the roster of
factions that can raid at all written as a `random.choice([...])` literal beside it.
Adding a race meant editing a mission library, and no mod could add one at all.

Now a race declares its own ladder and registers it. The `if` chain becomes a lookup, and
`"random"` picks from what is actually registered rather than from a hardcoded list - so a
new race joins the rotation by existing.

It lives in `sbs_utils` rather than in LegendaryMissions because MAST addons load in a
NON-DETERMINISTIC order. A race addon calling a function defined in the `fleets` addon
would work or not depending on which happened to compile first. The library is always
there.

THE SHAPE. Eleven difficulty tiers, each offering five variants, each variant a list of
ship keys::

    race: kralien
    fleets:
      - [[kralien_cruiser], [kralien_cruiser, kralien_cruiser], ...]   # difficulty 0
      - ...                                                            # difficulty 1

Difficulty is an INDEX, clamped by the caller. Five variants per tier is what the shipped
data uses; a race may supply fewer and they are simply chosen among.
"""

from ..helpers import FrameContext

_TABLES = {}
_MODS = {}


def fleet_table_register(race, table, mod=None):
    """Register a race's fleet ladder.

    Args:
        race (str): Race name; matched case-insensitively.
        table (list): List of difficulty tiers, each a list of variants, each a list of
            ship keys.
        mod (str, optional): Who supplied it, for collision reporting.
    """
    if not race or not table:
        return None
    key = str(race).strip().lower()
    previous = _MODS.get(key)
    if previous is not None and mod is not None and previous != mod:
        from .execution import log
        log(f"fleet table collision: '{key}' is supplied by both '{previous}' and "
            f"'{mod}' - '{mod}' wins.", "fleets", "warning")
    _TABLES[key] = table
    if mod is not None:
        _MODS[key] = mod
    return table


def fleet_table_load_yaml(content, mod=None):
    """Register a ladder from YAML text, as shipped beside a race addon.

    Pair with ``media_read_relative_file`` so it works from a packaged ``.mastlib``::

        fleet_table_load_yaml(media_read_relative_file("fleets.yaml"), "race_kralien")

    A file that will not parse is logged and skipped rather than raised: one bad race
    should not take a mission down, and the caller gets ``None``.
    """
    if not content:
        return None
    from ..fs import load_yaml_string
    try:
        data = load_yaml_string(content)
    except Exception as e:
        from .execution import log
        log(f"fleet table not loaded: {e}", "fleets", "warning")
        return None
    if not isinstance(data, dict):
        return None
    race = data.get("race")
    table = data.get("fleets")
    if not race or not isinstance(table, list):
        from .execution import log
        log("fleet table needs a 'race' and a 'fleets' list", "fleets", "warning")
        return None
    return fleet_table_register(race, table, mod)


def fleet_table_has(race):
    """Whether a race has a registered ladder."""
    return str(race or "").strip().lower() in _TABLES


def fleet_table_races():
    """Every race with a registered ladder, sorted.

    This is the roster of factions that can raid. It used to be a literal.
    """
    return sorted(_TABLES)


def fleet_table_get(race, difficulty, variant=None):
    """One fleet: a list of ship keys, or ``[]`` when the race has no ladder.

    Args:
        race (str): Race name, or ``"random"`` to pick among registered races.
        difficulty (int): Tier index. Clamped into range, so a caller cannot fall off
            either end of a ladder that is shorter than it expects.
        variant (int, optional): Which of the tier's variants. Random when omitted.
    """
    key = str(race or "").strip().lower()
    if key == "random":
        races = fleet_table_races()
        if not races:
            return []
        key = _rand_choice(races)
    table = _TABLES.get(key)
    if not table:
        return []
    tier = table[max(0, min(len(table) - 1, int(difficulty)))]
    if not tier:
        return []
    if variant is None:
        variant = _rand_range(len(tier))
    return list(tier[max(0, min(len(tier) - 1, int(variant)))])


def fleet_table_pick_race(exclude=None):
    """A registered race at random, honoring the mission seed."""
    races = [r for r in fleet_table_races() if r != str(exclude or "").strip().lower()]
    return _rand_choice(races) if races else None


def _rand_choice(seq):
    import random
    return random.choice(seq)


def _rand_range(n):
    import random
    return random.randrange(n) if n > 0 else 0


def fleet_tables_reset():
    """Drop every registered ladder at a mission boundary.

    Per-mission state: the next mission has its own enabled races, and inheriting these
    would let it spawn fleets for a race it never enabled.
    """
    _TABLES.clear()
    _MODS.clear()


def fleet_tables_count():
    """Reset-ledger probe."""
    return len(_TABLES)
