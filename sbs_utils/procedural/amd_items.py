"""Declarative game ITEMS from AMD - author a mission's collectible/usable items (upgrades,
resources, traps) as data instead of hand-writing a `=== prefab_item_<key>` metadata label.

A section authors one heading per item; the heading key is the item key, the display text is
the item name, and the description body is the item's ``desc``:

    ## Items

    # [Secret Codecase](secret_codecase)
    ---
    Type: item/upgrade/comms
    Art: container_1a
    Mode: consumable
    Targets: ship, cockpit
    Consoles: comms
    Duration: 300
    Tier: 3
    Price: 400
    ---
    Arms a one-shot enemy auto-surrender (used from comms).

The fields mirror the ``metadata`` block used by ``LegendaryMissions/items/item_defs.mast``:
``Type`` (``item/<category>/<sub>``), ``Art`` (pickup art_id), ``Mode``
(``consumable`` | ``install`` | ``resource``), ``Targets`` (agent kinds), ``Consoles`` (which
console(s) may activate it), ``Duration`` (seconds), ``Tier`` / ``Price`` (economy hints). All
fields are plain strings/numbers, so an items section parses under the default AMD coercion
(``amd_num`` - ``Tier``/``Price``/``Duration`` come back as ints), or under a mission's
``amd_mission_data``; no dedicated fact handler is needed.

The item registry (``procedural.items``) is simply the set of labels tagged ``type: item/...`` in
the story (``labels_get_type("item/")``): ``item_get(key)`` returns that label, and activation runs
the *same* label's body as the effect (``upgrade_add`` in ``item_activate.mast``). So registering an
item declaratively means applying the AMD data as metadata onto that label.

DECLARATIVE MODIFIER EFFECT (no MAST body). A *simple* upgrade item whose whole effect is applying
stat modifiers can be authored FULLY in AMD - the effect becomes data. Add a ``Modifiers`` field:

    # [Carapaction Coil](carapaction_coil)
    ---
    Type: item/upgrade/defense
    Art: alien_2a
    Mode: consumable
    Duration: 300
    Tier: 2
    Price: 250
    Modifiers: all_shield_upgrade_coeff 2.0
    ---
    Reinforces shields for a time.

``Modifiers`` is a comma-separated list of ``blob_key value`` pairs (one or many):

    Modifiers: impulse_upgrade_coeff 2.0, turn_upgrade_coeff 2.0

Each pair is parsed to ``[blob_key:str, value:float]`` and exposed on the record as
``record.modifiers`` (a list). It is stamped onto the item's label metadata, and on activation the
upgrade path (``Upgrade._apply_declared_modifiers`` in ``procedural.upgrades``) auto-applies each as
``modifier_add(holder, blob_key, value, item_key, duration=item_duration)`` - exactly the call a
hand-written ``prefab_item_<key>`` body would make, so no MAST effect body is needed. The modifier
auto-expires after the item's ``Duration`` and is removed when the upgrade is deactivated.

EFFECT LOGIC BEYOND MODIFIERS STAYS IN MAST. A richer effect (signal_emit, spawns, conditional
logic) still lives in MAST, under the convention that item ``<key>`` maps to the label
``prefab_item_<key>`` (``item_effect_label_name``). ``items_declare_amd`` applies the authored
metadata to that label if the mission already wrote it (mission writes the effect body, AMD supplies
the data); if no such label exists it registers a data-only item (still discoverable/queryable by
the registry). Declared ``Modifiers`` apply IN ADDITION to whatever a body does, so an item may
have both a body AND declared modifiers, and a hand-authored body with no ``Modifiers`` field is
completely unaffected (no regression). Generalises the OU/LM item pattern the same way
``amd_lifeforms`` / ``amd_landmarks`` generalise their spawns.
"""
from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import MastDataObject


def amd_parse_modifiers(spec):
    """Parse a ``Modifiers`` field into a structured ``[[blob_key, value], ...]`` list.

    Accepts the AMD string form ``"key value, key2 value2"`` (comma-separated ``blob_key value``
    pairs) or an already-structured list of pairs. Pairs that don't have a numeric value are
    skipped. Always returns a list (empty for ``None``/blank/unparseable)."""
    out = []
    if not spec:
        return out
    items = spec if isinstance(spec, (list, tuple)) else str(spec).split(",")
    for item in items:
        if isinstance(item, (list, tuple)):
            toks = [str(t) for t in item]
        else:
            toks = str(item).split()
        if len(toks) < 2:
            continue
        try:
            out.append([toks[0], float(toks[1])])
        except (TypeError, ValueError):
            continue
    return out


def amd_item_data(text):
    """Parse one item fence into a data dict (default coercion - Type/Art/Mode/Targets/Consoles
    are strings, Tier/Price/Duration come back as ints via ``amd_num``). Use as the ``data_parser``
    for an items-only .amd; a consolidated mission file uses ``amd_mission_data`` and its item
    fences fall through to the same default coercion."""
    return amd_parse_facts(text)


def items_from_section(section):
    """Item records (MastDataObject) from a section node's children (empty if None)."""
    out = []
    if section is not None:
        for n in section.get("children", []):
            data = {str(k).lower(): v for k, v in (n.get("data") or {}).items()}
            out.append(MastDataObject({
                "key": n.get("key"),
                "name": n.get("display_text"),
                "desc": (n.get("description") or "").strip(),
                "type": data.get("type") or "item/misc",
                "art": data.get("art"),
                "mode": data.get("mode"),
                "targets": data.get("targets"),
                "consoles": data.get("consoles"),
                "duration": data.get("duration"),
                "tier": data.get("tier"),
                "price": data.get("price"),
                "modifiers": amd_parse_modifiers(data.get("modifiers")),  # [[blob_key, value], ...]
                "data": data,   # carry the raw fence for mission-specific extras
            }))
    return out


def item_effect_label_name(key):
    """The effect-label name for an item key, by convention: ``prefab_item_<key>``. The mission
    authors this label's body (the modifier_add / signal_emit effect) in MAST."""
    return "prefab_item_" + str(key)


def _story():
    """Resolve the current story (whose ``labels`` dict is the item registry) the same way
    ``labels_get_type`` does: the executing page's story, else ``FrameContext.mast``."""
    page = FrameContext.page
    story = getattr(page, "story", None) if page is not None else None
    return story or FrameContext.mast


def _item_metadata(record):
    """The metadata dict to stamp on the item's label: the raw fence plus the heading-derived
    key / display_text / type / desc (so ``item_get`` / ``item_meta`` read them)."""
    meta = dict(record.get("data") or {})
    meta["key"] = record.get("key")
    meta["display_text"] = record.get("name")
    meta["type"] = record.get("type") or "item/misc"
    desc = record.get("desc")
    if desc:
        meta["desc"] = desc
    # Stamp the STRUCTURED modifier spec (list of [blob_key, value] pairs), replacing the raw
    # "Modifiers" string from the fence, so the activation path can apply it directly.
    mods = record.get("modifiers")
    if mods:
        meta["modifiers"] = mods
    elif "modifiers" in meta:
        del meta["modifiers"]
    return meta


def item_declare(record):
    """Register one authored item into the story registry, returning its key (or None if it has no
    key, or there is no resolvable story). Applies the record's metadata onto the ``prefab_item_<key>``
    effect label - reusing the mission's label if it exists, else creating a data-only one so the
    item is still discoverable via ``labels_get_type("item/")`` / ``item_get``."""
    key = record.get("key")
    if not key:
        return None
    story = _story()
    labels = getattr(story, "labels", None)
    if labels is None:
        return None
    name = item_effect_label_name(key)
    label = labels.get(name)
    if label is None:
        # Data-only item: no MAST effect body was authored. Register a bare label so the registry
        # (spawn / market / GUI) can still resolve its art/name/economy fields.
        from sbs_utils.mast.core_nodes.label import Label
        label = Label(name)
        labels[name] = label
    label.apply_metadata(_item_metadata(record))
    return key


def items_declare_amd(section):
    """Register every item in a section (applying its AMD data as metadata onto the matching
    ``prefab_item_<key>`` label). Returns the list of registered item keys. Convenience over
    ``items_from_section`` + ``item_declare``; None-safe (empty list for a missing section)."""
    out = []
    for rec in items_from_section(section):
        key = item_declare(rec)
        if key is not None:
            out.append(key)
    return out
