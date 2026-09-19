from sbs_utils.mast.mast_node import MastDataObject
def _csv (value):
    """A comma list -> [str], lowercased and stripped, empties dropped."""
def _depth_check (rec, curve):
    """Report a thin faction in a heavy slot ONCE per mission, per theater."""
def _numbers (value):
    """A comma list of numbers -> [float]. Non-numeric entries are dropped."""
def _pairs (value):
    """An ``a=b, c=d`` list -> {a: b}, lowercased. Entries without ``=`` are ignored."""
def _positional_row (factions, curve):
    """Zip a POSITIONAL curve onto a roster, fixing the three ways it used to go wrong.
    
    Measured against the shipped data before this existed:
    
      * ROSTER LONGER THAN THE CURVE silently dropped the tail. borderwar and deepstrike pass
        a 3-long curve, every TNG theater rosters 4, and the fourth race - ximni in all five
        of them - never spawned at all. The last curve weight is now SHARED among the races
        past its end, so nobody gets zero and the head keeps its share.
      * ROSTER SHORTER THAN THE CURVE cycled the roster to fill the slots, which handed the
        first race the surplus: a 3-race roster under ``[70,10,10,10]`` made it 80%, not 70.
        The curve is truncated instead, and the row normalizes by its own sum.
      * NO CURVE AT ALL is uniform, which is correct and unchanged - singlefront passes none.
    
    Returns ``{race: share}``."""
def _weights (value):
    """A weight row: ``{race: share}`` when keyed, ``[share, ...]`` when positional.
    
    KEYED IS THE REAL FORM. ``kralien:70, torgoth:10`` names who gets what, so the row has
    no length and no order to get wrong. The positional form is what the maps used to pass -
    a bare ``70, 10, 10, 10`` zipped against a race list somewhere else - and is still read
    so existing theaters and callers keep working.
    
    Told apart by a colon, because a race name cannot contain one."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000026177D728E0>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def amd_read_text (path):
    """The text of one .amd (or any AMD-adjacent source), decoded the same way a
    mastlib read decodes it.
    
    UTF-8 first (with a BOM tolerated, since editors add one), falling back to
    cp1252 for a legacy file that predates that convention, and finally to a
    replacing UTF-8 decode - because a file that cannot be decoded should still
    parse into something an author can look at and fix, not vanish."""
def amd_theater_clear ():
    """Drop every declared theater. Called from reset_mission_state()."""
def amd_theater_count ():
    """How many theaters are declared - the reset-ledger probe."""
def amd_theater_data (text):
    """Parse one theater fence into a data dict."""
def amd_theater_facts ():
    """amd_parse_facts handler for a theater fence.
    
    ``Factions`` is the roster, dominant first. ``Weights`` is optional and overrides the
    caller's curve. ``Faces`` maps a faction to the FACE RACE its crews are drawn from -
    those are different namespaces (a Federation ship is crewed by `human`, not by
    `federation`), which is exactly why it cannot be inferred."""
def race_hull_count_safe (race):
    """A race's mobile hull count, or 0 when the ship table cannot answer."""
def theater_art (key=None):
    """The active theater's race -> ART FACTION map ({} when unset).
    
    Feeds `RACE_ART`. Separate from the roster because the roster is in the MISSION's
    vocabulary and this is what those races LOOK like."""
def theater_declare (records):
    """Register every theater record. Returns {key: record}.
    
    A later declaration of the same key REPLACES the earlier one, matching `side_create`'s
    idempotence, so a mission can override a theater an addon shipped."""
def theater_declare_amd (doc):
    """Declare every theater in a parsed AMD document."""
def theater_declare_text (content):
    """Declare theaters from AMD text already in hand.
    
    This is the call an ADDON wants: it reads its own file with `media_read_relative_file`,
    which works inside a packaged `.mastlib` where `get_mission_dir_filename` cannot reach."""
def theater_depth_report (weights=None, key=None):
    """Factions given a heavy slot they do not have the hulls to fill.
    
    Returns ``[(faction, hulls, share)]``. Empty is good.
    
    THIS IS THE FAILURE THAT HIDES. Nothing errors when a one-hull faction takes the 70%
    slot; the same ship simply turns up for the rest of the night, and that reads as broken
    art rather than as a wrong roster."""
def theater_display_name (key=None):
    """A theater's display name, falling back to its key. Empty string when unset."""
def theater_faces (key=None):
    """The active theater's faction -> face-race map ({} when unset)."""
def theater_factions (count=None, key=None, eligible=None):
    """The active theater's factions, dominant first, or None when no theater is set.
    
    Returning None rather than [] is the whole backward-compatibility story: a caller reads
    "no theater" and keeps its own literal list, so stock missions are untouched.
    
    A theater with only a ``Weights:`` row and no ``Races:`` line still has a roster - the
    keys of that row - so a keyed theater does not have to say its races twice.
    
    ``eligible`` drops races the caller cannot use (see `theater_pick_race`).
    
    ``count`` TRUNCATES. It used to cycle the roster to fill the caller's slots, which quietly
    gave the first race the surplus weight - a 3-race roster under ``[70,10,10,10]`` made it
    80%, not 70. Nothing in the library asks for a count any more; the argument stays for
    callers that pass one."""
def theater_find (spec):
    """Resolve a KEY or a DISPLAY NAME to a theater key. None when nothing matches.
    
    An operator control shows display names ("Dominion War") while the `THEATER` setting is
    a key (`dominion_war`), so something has to translate. Accepts either, case- and
    space-insensitively, so a profile that already writes the key keeps working and a
    dropdown selection resolves too."""
def theater_get (key=None):
    """One theater record by key, or the ACTIVE one when key is None. None when unset."""
def theater_get_list ():
    """Every declared theater record, in key order.
    
    The list an operator control is built from - the same shape `music_get_list` and
    `crew_get_list` hand the server panel, so a mod that ships theaters shows up in the
    picker without the panel knowing anything about it."""
def theater_hull_counts (key=None):
    """{faction: how many non-station hulls it has}, for the active theater."""
def theater_load_amd (file_path):
    """Load a theater file relative to the mission folder and declare it.
    
    Bakes in ``data_parser=amd_theater_data`` so a caller cannot omit it - the default AMD
    reader is YAML and would read the comma lists differently."""
def theater_music (key=None):
    """The active theater's MUSIC_SELECT, or None."""
def theater_name_list ():
    """Dropdown options string: ``'None, <Display>, ...'``.
    
    Matches the idiom a map's ``Properties:`` block already uses for its own pickers (see
    siege's ``BOSS_LIST``), so a map opts in with two lines and no new concepts::
    
        default shared THEATER      = theater_selected_name()
        default shared THEATER_LIST = theater_name_list()
        ...
        Theater: 'gui_drop_down("$text: {THEATER};list: {THEATER_LIST}", var="THEATER")'
    
    Built from what is DECLARED, so a mod that ships theaters shows up without the map
    knowing about it - and with none declared the list is just "None", which is the honest
    control for "there is nothing to choose"."""
def theater_names ():
    """Every declared theater key."""
def theater_pick_race (weights=None, names=None, key=None, difficulty=None, eligible=None):
    """Pick one race from the active theater. None when no theater is set.
    
    Returns None rather than a default so the caller keeps its own behavior, which is what
    leaves a mission with no theater untouched.
    
    ``difficulty`` selects a ``Weights <n>:`` tier - the ladder that used to be a table of
    positional rows in the map. ``eligible`` is a predicate the map supplies for what the
    race must be able to DO: borderwar and deepstrike pass `race_has_station`, because they
    build enemy starbases and not every race has one. That constraint was previously written
    out by hand as a shortened race list in each of those maps.
    
    ``weights`` is the caller's own row, used only when the theater declares none. A theater
    row REPLACES it unless the theater said ``Weights Add:``, in which case the two merge -
    and merging rescales everyone, because these are relative shares and not percentages.
    
    ``names`` is the caller's spelling of the races it knows. It is NOT a gate: a race the
    theater rosters is returned even when the caller has never heard of it, because the whole
    point is that a roster is no longer limited to what one map hardcoded. It still supplies
    the SPELLING when it has one, so a caller that does compare against its own literals gets
    a match."""
def theater_player_faction (key=None):
    """The shipData faction the CREW's hulls should be drawn from, or None.
    
    Separate from the ``Art:`` map on purpose. That map says how the mission's own races
    are drawn, and `tsn` in it re-skins the friendly NPCs; this says what the PLAYERS fly,
    which is not always the same thing. A theater where the crew are pirates re-skins them
    to Orion while its allied `tsn` NPCs stay Federation.
    
    ART ONLY - it never moves anybody's side. See :func:`theater_player_side_key`.
    
    **The value is a shipData SIDE, and stock data splits the Federation across two of
    them**: `tsn` is the navy, `USFP` is the freighters and starbases. `Player Faction:
    USFP` therefore seats the crew in a science ship and a luxury liner - correct pairing,
    wrong side. Name the side whose WARSHIPS you want; for a mod that keeps its hulls under
    one side (the TNG pack's `Federation`) there is no such split to fall into."""
def theater_player_side (key=None):
    """The COSTUME for the players' existing side: ``{name, color, icon}``, empties dropped.
    
    A re-dress, not a re-faction. The side KEY is untouched, so diplomacy, `side_are_enemies`,
    every `//comms` gate and every station-friendliness lookup keep working exactly as the
    mission wrote them - only what the crew is called and coloured changes. That is what
    makes "the players are pirates tonight" cost nothing."""
def theater_player_side_key (key=None):
    """Always None, and says so out loud when a theater asked for one.
    
    ``Player Side Key:`` would move the crew onto a different DIPLOMATIC side, and the
    missions are not ready for it: LegendaryMissions carries around 45 literal `tsn` sites
    across maps, fleets, consoles and prefabs, and `spawn_players` places crews via
    ``side_members_set(side) & role("station")`` - so a raider crew with no raider station
    is simply never placed, with nothing logged.
    
    Refused rather than half-applied. A theater that moved the key would look like it
    worked right up to the point where the crew spawned nowhere. Use the costume fields
    (:func:`theater_player_side`) for the look; the key waits on the de-hardcoding pass."""
def theater_players (key=None):
    """Explicit per-slot hull keys the theater wants the crew in, or []."""
def theater_selected_name ():
    """The active theater's DISPLAY name, or ``"None"``.
    
    What a map seeds its shared var from. Called before any shared value exists, it falls
    through to the setting - so a profile's ``THEATER: dominion_war`` becomes the dropdown's
    starting selection instead of being overwritten with "None" by the `default`."""
def theater_weights (difficulty=None, key=None):
    """The active theater's weight row as ``{race: share}``, or None.
    
    Reads, strongest first: the tier matching ``difficulty`` (``Weights 5:``), then the
    single ``Weights:`` row, then nothing. A positional row is NOT returned here - it has no
    race names in it, so it cannot answer "what does each race get" on its own; that form is
    handled in :func:`theater_pick_race` against the roster.
    
    ``difficulty`` is the 1-based tier a map reads (LM's DIFFICULTY), clamped into whatever
    tiers the theater actually declared, so a theater that ships fewer than eleven cannot be
    fallen off either end of."""
def theaters_from_section (node):
    """Theater records from a node whose children are the theater headings."""
