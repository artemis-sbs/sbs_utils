"""Declarative faction SIDES from AMD - author a mission's sides as data instead of a block
of prefab_side_generic / side_set_relations calls.

One heading per side; the fence carries its identity and diplomacy:

    # [TSN](tsn)
    ---
    Color: #07F
    Enemies: raider
    ---
    The Terran Stellar Navy.

`Color` / `Icon index` / `Races` configure the side; `Enemies` / `Allies` (comma lists) set
diplomacy. The heading display is the name, the body prose the description. Built on the
shared Python side_create (the port of the prefab_side_generic prefab), so no mast prefab is
needed. sides_declare is TWO-PASS - every side is created first, then relations are applied -
so a side may name an enemy/ally defined later in the file.
"""
from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.procedural.sides import side_create, side_set_relations, _side_csv_list
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import MastDataObject


def amd_side_facts():
    """amd_parse_facts handler for a side fence: name/desc/color/races/allies/enemies (text),
    icon_index (number). Unknown labels return None (chain / default coercion)."""
    def handler(data, label, value):
        if label in ("name", "desc", "color", "races", "allies", "enemies", "neutral"):
            data[label] = str(value).strip()
        elif label in ("icon_index", "icon"):
            data["icon_index"] = value
        else:
            return None
        return True
    return handler


def amd_side_data(text):
    """Parse one side fence into a data dict."""
    return amd_parse_facts(text, amd_side_facts())


def sides_from_section(node):
    """Side records (MastDataObject) from a node whose children are the side headings - the
    document itself (a flat sides file) or a `## [Sides]` section."""
    out = []
    if node is not None:
        for n in node.get("children", []):
            data = n.get("data") or {}
            out.append(MastDataObject({
                "key": n.get("key"),
                "name": data.get("name") or n.get("display_text"),
                "desc": data.get("desc") or ((n.get("description") or "").strip() or None),
                "color": data.get("color"),
                "icon_index": data.get("icon_index"),
                "races": data.get("races"),
                "allies": data.get("allies"),
                "enemies": data.get("enemies"),
                "neutral": data.get("neutral"),
            }))
    return out


def sides_declare(records):
    """Create every side from records, then apply diplomacy (two-pass, so relations resolve
    regardless of authoring order). Returns {key: side_id}."""
    ids = {}
    for r in records:
        ids[r.get("key")] = side_create(
            r.get("key"), r.get("name"), r.get("desc"), r.get("color"),
            r.get("icon_index"), r.get("races"))   # relations applied in pass 2
    sbs = FrameContext.context.sbs
    if sbs is not None:
        for r in records:
            key = r.get("key")
            for a in _side_csv_list(r.get("allies")):
                side_set_relations(key, a, sbs.DIPLOMACY.ALLIED)
            for e in _side_csv_list(r.get("enemies")):
                side_set_relations(key, e, sbs.DIPLOMACY.HOSTILE)
            for nn in _side_csv_list(r.get("neutral")):
                side_set_relations(key, nn, sbs.DIPLOMACY.NEUTRAL)
    return ids


def sides_declare_amd(node):
    """Declare all sides authored under an AMD node (flat sides doc or a Sides section)."""
    return sides_declare(sides_from_section(node))
