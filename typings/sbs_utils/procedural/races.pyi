from sbs_utils.mast.mast_node import MastDataObject
def _entries ():
    """Every ship-table entry, or [] when no table is loaded.
    
    Deliberately does NOT force the load. `get_ship_data()` caches on first call, so asking
    it here would make merely COUNTING a race's hulls flip `ship_data_is_loaded()` to true
    for everything downstream - and that probe is what the depth guard uses to tell "this
    roster is too thin" from "I cannot judge yet". Answering "nothing known" is correct
    before the table exists; manufacturing a load to answer is not."""
def _is_station (entry):
    """Whether an entry is a station, by its ROLES string.
    
    Matches `_side_split`'s rule deliberately, and for its reason: a ``role="ship"`` filter
    silently skips hulls that do not carry one - `arvonian_fighter` is `cockpit,fighter` -
    which shows up as "most of the faction converted and a few ships are still stock"."""
def _norm (value):
    """A race key, lowercased and stripped. Empty string for nothing."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x000002741D0E0540>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def amd_race_data (text):
    """Parse one race fence into a data dict."""
def amd_race_facts ():
    """amd_parse_facts handler for a race fence."""
def amd_read_text (path):
    """The text of one .amd (or any AMD-adjacent source), decoded the same way a
    mastlib read decodes it.
    
    UTF-8 first (with a BOM tolerated, since editors add one), falling back to
    cp1252 for a legacy file that predates that convention, and finally to a
    replacing UTF-8 decode - because a file that cannot be decoded should still
    parse into something an author can look at and fix, not vanish."""
def race_call_sign (race):
    """The prefix letters this race's NPC call signs are drawn from, or None.
    
    None means "no opinion", and `name_random_hostile` then keeps its historical default."""
def race_declare (records):
    """Register every race override record. Returns {key: record}.
    
    A later declaration of the same key REPLACES the earlier one, matching `side_create` and
    `theater_declare`, so a mission can override what an addon shipped."""
def race_declare_amd (doc):
    """Declare every race in a parsed AMD document."""
def race_declare_text (content):
    """Declare races from AMD text already in hand.
    
    The call an ADDON wants: pair it with `media_read_relative_file`, which reads from inside
    a packaged `.mastlib` where `get_mission_dir_filename` cannot reach."""
def race_display_name (race):
    """A race's display name, falling back to its key capitalized."""
def race_exists (race):
    """Whether any hull carries this origin."""
def race_faces (race):
    """The FACE race whose portraits crew this race, defaulting to the race itself.
    
    Different namespaces: a Federation ship is crewed by `human`, not by `federation`, and the
    TNG pack has Breen hulls and no Breen faces. That is why it cannot be inferred."""
def race_fleet_scale (race):
    """How many times the normal fleet count this race spawns. 1.0 unless declared.
    
    Ximni is the case it exists for: LM's maps carry ``if enemy == "Ximni": fleet_count *= 2``
    with the comment "Ximni fleets are typically only one ship". That is a fact about the
    race, not about the map, so all the maps that said it can stop saying it."""
def race_get (race):
    """One race's override record, or None. Derived facts do not live here."""
def race_has_station (race):
    """Whether this race can be spawned as an enemy station.
    
    The eligibility filter for the maps that build enemy starbases. Stated once here instead
    of hand-written as a shortened race list in each of them."""
def race_hull_count (race):
    """How many MOBILE hulls a race fields - the depth-guard input.
    
    A faction with one hull in a heavy weight slot does not error; the same ship simply turns
    up all night, which reads as broken art rather than as a wrong roster."""
def race_hulls (race):
    """A race's MOBILE hull keys, sorted. Stations excluded."""
def race_list ():
    """Every race the loaded ship table knows, sorted. Empty when nothing is loaded.
    
    This is the roster a mod joins by EXISTING. Ship a hull with ``origin: Klingon`` and
    `klingon` is a race here, with no registration call and no settings entry."""
def race_load_amd (file_path):
    """Load a race file relative to the mission folder and declare it.
    
    Bakes in ``data_parser=amd_race_data`` so a caller cannot omit it - the default AMD
    reader is YAML and would read these fields differently."""
def race_npc_list ():
    """The races that can actually raid: in the ship table, enabled, and with a ladder.
    
    Three gates, because three different things can be missing and each is invisible on its
    own - a race with no hulls spawns nothing, a race left out of ``NPC_RACES`` was
    deliberately disabled, and a race with no fleet ladder makes `fleet_create` return None
    after printing. Intersecting them here means a caller gets a list every entry of which
    can actually be spawned."""
def race_station_hull (race):
    """The hull a map should spawn as this race's starbase, or None.
    
    An explicit ``Station Hull:`` override wins; otherwise the race's first station hull.
    ``None`` is a real answer and means "this race has no starbase" - ximni and pirate both
    say it, which is what borderwar's and deepstrike's three-race literals were encoding."""
def race_station_hulls (race):
    """A race's STATION hull keys, sorted. Empty when it has none."""
def race_station_prefix (race):
    """The letters a map names this race's stations with (``KB 1``, ``TB 2``).
    
    Falls back to the race's first two letters upper-cased plus B, so an undeclared race gets
    a usable prefix rather than an empty one - a station called " 1" is worse than "KLB 1"."""
def races_clear ():
    """Drop every declared race override. Called from reset_mission_state()."""
def races_count ():
    """How many race overrides are declared - the reset-ledger probe."""
def races_from_section (node):
    """Race records from a node whose children are the race headings."""
