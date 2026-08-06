from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import MastDataObject
def _item_metadata (record):
    """The metadata dict to stamp on the item's label: the raw fence plus the heading-derived
    key / display_text / type / desc (so ``item_get`` / ``item_meta`` read them)."""
def _story ():
    """Resolve the current story (whose ``labels`` dict is the item registry) the same way
    ``labels_get_type`` does: the executing page's story, else ``FrameContext.mast``."""
def amd_item_data (text):
    """Parse one item fence into a data dict (default coercion - Type/Art/Mode/Targets/Consoles
    are strings, Tier/Price/Duration come back as ints via ``amd_num``). Use as the ``data_parser``
    for an items-only .amd; a consolidated mission file uses ``amd_mission_data`` and its item
    fences fall through to the same default coercion."""
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
def amd_parse_modifiers (spec):
    """Parse a ``Modifiers`` field into a structured ``[[blob_key, value], ...]`` list.
    
    Accepts the AMD string form ``"key value, key2 value2"`` (comma-separated ``blob_key value``
    pairs) or an already-structured list of pairs. Pairs that don't have a numeric value are
    skipped. Always returns a list (empty for ``None``/blank/unparseable)."""
def item_declare (record):
    """Register one authored item into the story registry, returning its key (or None if it has no
    key, or there is no resolvable story). Applies the record's metadata onto the ``prefab_item_<key>``
    effect label - reusing the mission's label if it exists, else creating a data-only one so the
    item is still discoverable via ``labels_get_type("item/")`` / ``item_get``."""
def item_effect_label_name (key):
    """The effect-label name for an item key, by convention: ``prefab_item_<key>``. The mission
    authors this label's body (the modifier_add / signal_emit effect) in MAST."""
def items_declare_amd (section):
    """Register every item in a section (applying its AMD data as metadata onto the matching
    ``prefab_item_<key>`` label). Returns the list of registered item keys. Convenience over
    ``items_from_section`` + ``item_declare``; None-safe (empty list for a missing section)."""
def items_from_section (section):
    """Item records (MastDataObject) from a section node's children (empty if None)."""
