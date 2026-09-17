from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import MastDataObject
def _side_csv_list (value):
    """A comma string OR a list/set -> a stripped list of non-empty items."""
def _side_expand (items, all_keys, self_key, claimed):
    """Expand a `*` in one relation list to every OTHER side in the document.
    
    Returns `items` UNCHANGED when there is no wildcard, so a document that never uses one
    emits exactly the relations it always did.
    
    `claimed` is every side named explicitly across this side's three lists, so an explicit
    entry always beats the wildcard: `Allies: breen` + `Enemies: *` means breen is an ally
    and everything else is hostile, whichever list the wildcard sits in.
    
    Scope is THIS DOCUMENT. A wildcard reaches the sides authored alongside it and no
    others - so an addon declaring its own factions cannot silently redefine a relation
    with a side some other addon declared."""
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
def amd_read_text (path):
    """The text of one .amd (or any AMD-adjacent source), decoded the same way a
    mastlib read decodes it.
    
    UTF-8 first (with a BOM tolerated, since editors add one), falling back to
    cp1252 for a legacy file that predates that convention, and finally to a
    replacing UTF-8 decode - because a file that cannot be decoded should still
    parse into something an author can look at and fix, not vanish."""
def amd_side_data (text):
    """Parse one side fence into a data dict."""
def amd_side_facts ():
    """amd_parse_facts handler for a side fence: name/desc/color/races/allies/enemies (text),
    icon_index (number), civilian (flag). Unknown labels return None (chain / default
    coercion)."""
def amd_sides_audience_count ():
    """Reset-ledger probe: how many token rules are held."""
def amd_sides_clear ():
    """Drop the cross-document side registries - the per-mission reset."""
def side_civilian_sides ():
    """Every side declared `Civilian: true`, across every document loaded this mission."""
def side_create (key, name=None, desc=None, color=None, icon_index=None, races=None, allies=None, enemies=None):
    """Create and configure a faction SIDE from data - the Python port of the
    ``prefab_side_generic`` MAST prefab, so the same setup is callable from Python or a
    declarative loader without the mast prefab.
    
    Sets side_name / side_key / side_desc / side_races inventory, icon color + index, and
    applies ally/enemy diplomacy (plus the self-ally that ``side_ensure`` seeds). Idempotent:
    if the side already exists it is reconfigured in place (``side_ensure`` returns the
    existing id). ``races``/``allies``/``enemies`` accept a comma string or a list.
    
    Returns the side agent id (None if ``key`` is falsy)."""
def side_player_sides ():
    """Every side the crew may be on, as a set of keys.
    
    TWO SOURCES, deliberately unioned. `PLAYER_LIST` (settings, profile-merged) is the
    roster and is known before any ship exists, which is what lets a side document resolve
    `players` at declare time. Live `role("__player__")` ships cover a mission that moves a
    crew to another side afterwards.
    
    NOTE `PLAYER_LIST` is an OVERLOADED NAME: the setting is a list of dicts carrying
    `side`, but `LegendaryMissions/consoles/common_console_select.mast` rebinds a MAST
    variable of the same name to live player OBJECTS. This reads the SETTING."""
def side_set_relations (side1, side2, relation):
    """Set the diplomatic relationship between two sides.
    
    Updates both the link-based relationship used by the scripting API and the
    engine's own side relationship table for 2D map rendering. Emits the
    ``side_relations_updated`` signal.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
        relation (sbs.DIPLOMACY): New relationship value. Use
            ``sbs.DIPLOMACY.ALLIED``, ``HOSTILE``, ``NEUTRAL``, or
            ``UNKNOWN``."""
def sides_apply_audiences ():
    """Re-apply every token rule seen this mission. Returns how many were replayed.
    
    Declaration happens at `create_sides`, BEFORE any player ship exists, so `players`
    resolves from `PLAYER_LIST` alone at that point. Call this once the crew is real - or
    after a mission moves a crew onto another side - and the same rules resolve against the
    live roster too.
    
    Safe to call repeatedly: `side_set_relations` replaces a pair's relation rather than
    accumulating, and explicit names still beat the tokens because `claimed` was captured
    with the rule."""
def sides_declare (records):
    """Create every side from records, then apply diplomacy (two-pass, so relations resolve
    regardless of authoring order). Returns {key: side_id}.
    
    `Enemies: *` means "hostile to every other side in this document". WHY IT EXISTS: with
    only explicit lists, a set of mutually hostile factions has to name every pair, and the
    failure when you don't is invisible. The TNG mod shipped eight factions each naming only
    `federation`, which made the matrix a STAR - Federation hostile to all seven, and every
    other pair (klingon/dominion, cardassian/klingon) NEUTRAL. Missions crewing a
    non-Federation side against a non-Federation enemy were silently passive: nothing shot
    at anybody, and no headless test can see it, because what breaks is the shooting rather
    than the script.
    
    A wildcard also stays correct when a faction is ADDED, which a hand-listed matrix does
    not - the new side is hostile to the others without editing seven other fences."""
def sides_declare_amd (node):
    """Declare all sides authored under an AMD node (flat sides doc or a Sides section)."""
def sides_from_section (node):
    """Side records (MastDataObject) from a node whose children are the side headings - the
    document itself (a flat sides file) or a `## [Sides]` section."""
def sides_load_amd (file_path):
    """Load a sides file relative to the mission folder and declare every side in it - the
    one-call path a mission should use. Bakes in ``data_parser=amd_side_data`` so a caller
    can't accidentally omit it: the default AMD reader is YAML, which would silently drop a
    ``Color: #07F`` value (``#`` starts a YAML comment). Returns {key: side_id}."""
