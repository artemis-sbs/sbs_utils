from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import MastDataObject
def _side_csv_list (value):
    """A comma string OR a list/set -> a stripped list of non-empty items."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000011CF6E5F4C0>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def amd_side_data (text):
    """Parse one side fence into a data dict."""
def amd_side_facts ():
    """amd_parse_facts handler for a side fence: name/desc/color/races/allies/enemies (text),
    icon_index (number). Unknown labels return None (chain / default coercion)."""
def side_create (key, name=None, desc=None, color=None, icon_index=None, races=None, allies=None, enemies=None):
    """Create and configure a faction SIDE from data - the Python port of the
    ``prefab_side_generic`` MAST prefab, so the same setup is callable from Python or a
    declarative loader without the mast prefab.
    
    Sets side_name / side_key / side_desc / side_races inventory, icon color + index, and
    applies ally/enemy diplomacy (plus the self-ally that ``side_ensure`` seeds). Idempotent:
    if the side already exists it is reconfigured in place (``side_ensure`` returns the
    existing id). ``races``/``allies``/``enemies`` accept a comma string or a list.
    
    Returns the side agent id (None if ``key`` is falsy)."""
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
def sides_declare (records):
    """Create every side from records, then apply diplomacy (two-pass, so relations resolve
    regardless of authoring order). Returns {key: side_id}."""
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
