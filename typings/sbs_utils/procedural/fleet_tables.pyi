from sbs_utils.helpers import FrameContext
def _rand_choice (seq):
    ...
def _rand_range (n):
    ...
def fleet_table_get (race, difficulty, variant=None):
    """One fleet: a list of ship keys, or ``[]`` when the race has no ladder.
    
    Args:
        race (str): Race name, or ``"random"`` to pick among registered races.
        difficulty (int): Tier index. Clamped into range, so a caller cannot fall off
            either end of a ladder that is shorter than it expects.
        variant (int, optional): Which of the tier's variants. Random when omitted."""
def fleet_table_has (race):
    """Whether a race has a registered ladder."""
def fleet_table_load_yaml (content, mod=None):
    """Register a ladder from YAML text, as shipped beside a race addon.
    
    Pair with ``media_read_relative_file`` so it works from a packaged ``.mastlib``::
    
        fleet_table_load_yaml(media_read_relative_file("fleets.yaml"), "race_kralien")
    
    A file that will not parse is logged and skipped rather than raised: one bad race
    should not take a mission down, and the caller gets ``None``."""
def fleet_table_pick_race (exclude=None):
    """A registered race at random, honoring the mission seed."""
def fleet_table_races ():
    """Every race with a registered ladder, sorted.
    
    This is the roster of factions that can raid. It used to be a literal."""
def fleet_table_register (race, table, mod=None):
    """Register a race's fleet ladder.
    
    Args:
        race (str): Race name; matched case-insensitively.
        table (list): List of difficulty tiers, each a list of variants, each a list of
            ship keys.
        mod (str, optional): Who supplied it, for collision reporting."""
def fleet_tables_count ():
    """Reset-ledger probe."""
def fleet_tables_reset ():
    """Drop every registered ladder at a mission boundary.
    
    Per-mission state: the next mission has its own enabled races, and inheriting these
    would let it spawn fleets for a race it never enabled."""
