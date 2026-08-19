"""Declarative faction SIDES from AMD - author a mission's sides as data instead of a block
of prefab_side_generic / side_set_relations calls.

One heading per side; the fence carries its identity and diplomacy:

    # [TSN](tsn)
    ---
    Color: #07F
    Enemies: raider
    ---
    The Terran Stellar Navy.

`Color` / `Icon index` / `Races` configure the side; `Enemies` / `Allies` / `Neutral` (comma
lists) set diplomacy. The heading display is the name, the body prose the description. Built
on the shared Python side_create (the port of the prefab_side_generic prefab), so no mast
prefab is needed. sides_declare is TWO-PASS - every side is created first, then relations are
applied - so a side may name an enemy/ally defined later in the file.

`*` MEANS EVERY OTHER SIDE IN THE DOCUMENT, and explicit names beat it::

    # [Dominion](dominion)
    ---
    Allies: cardassian, breen
    Enemies: *
    ---

That is allied with those two and hostile to everything else authored alongside it. Reach
for it whenever factions are mutually hostile: relations only exist where they are declared,
so a set of factions that each name one enemy produces a STAR - one side hostile to all, and
every other pair NEUTRAL - which is invisible headlessly, because what breaks is the
shooting rather than the script.
"""
from sbs_utils.procedural.amd import amd_parse_facts, amd_read_text
from sbs_utils.procedural.sides import side_create, side_set_relations, _side_csv_list
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_node import MastDataObject


def amd_side_facts():
    """amd_parse_facts handler for a side fence: name/desc/color/races/allies/enemies (text),
    icon_index (number), civilian (flag). Unknown labels return None (chain / default
    coercion)."""
    def handler(data, label, value):
        if label in ("name", "desc", "color", "races", "allies", "enemies", "neutral"):
            data[label] = str(value).strip()
        elif label in ("icon_index", "icon"):
            data["icon_index"] = value
        elif label == "civilian":
            data["civilian"] = str(value).strip().lower() in ("true", "yes", "1", "on")
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
            # Lower-case fence keys so the read is robust to casing/parser: a mission authors
            # `Color:`/`Enemies:` (natural case), and while amd_side_data's friendly path
            # lowercases, the default reader keeps case - normalize here like amd_records does.
            data = {str(k).lower(): v for k, v in (n.get("data") or {}).items()}
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
                "civilian": data.get("civilian"),
            }))
    return out


SIDE_EVERYONE = ("*", "all", "everyone")
SIDE_PLAYERS = ("players", "player")
SIDE_CIVILIANS = ("civilians", "civilian", "civs")
SIDE_TOKENS = SIDE_EVERYONE + SIDE_PLAYERS + SIDE_CIVILIANS

# CROSS-DOCUMENT, per-mission state, so it is on the reset ledger (see handlerhooks).
#
# `_civilian_sides` is every side that declared `Civilian: true`, whichever addon declared
# it; `_audience_rules` is every token rule seen, kept so sides_apply_audiences() can
# re-run them once the roster is real.
_civilian_sides = set()
_audience_rules = []


def amd_sides_clear():
    """Drop the cross-document side registries - the per-mission reset."""
    _civilian_sides.clear()
    del _audience_rules[:]


def amd_sides_audience_count():
    """Reset-ledger probe: how many token rules are held."""
    return len(_audience_rules) + len(_civilian_sides)


def side_player_sides():
    """Every side the crew may be on, as a set of keys.

    TWO SOURCES, deliberately unioned. `PLAYER_LIST` (settings, profile-merged) is the
    roster and is known before any ship exists, which is what lets a side document resolve
    `players` at declare time. Live `role("__player__")` ships cover a mission that moves a
    crew to another side afterwards.

    NOTE `PLAYER_LIST` is an OVERLOADED NAME: the setting is a list of dicts carrying
    `side`, but `LegendaryMissions/consoles/common_console_select.mast` rebinds a MAST
    variable of the same name to live player OBJECTS. This reads the SETTING.
    """
    keys = set()
    try:
        from sbs_utils.procedural.settings import settings_get_defaults
        for entry in (settings_get_defaults() or {}).get("PLAYER_LIST") or []:
            if isinstance(entry, dict):
                key = entry.get("side")
                if key:
                    keys.add(str(key).strip().lower())
    except Exception:
        pass
    try:
        from sbs_utils.procedural.query import to_object_list
        from sbs_utils.procedural.roles import role
        for p in to_object_list(role("__player__")):
            key = getattr(p, "side", None)
            if key:
                keys.add(str(key).strip().lower())
    except Exception:
        pass
    return keys


def side_civilian_sides():
    """Every side declared `Civilian: true`, across every document loaded this mission."""
    return set(_civilian_sides)


def _side_expand(items, all_keys, self_key, claimed):
    """Expand a `*` in one relation list to every OTHER side in the document.

    Returns `items` UNCHANGED when there is no wildcard, so a document that never uses one
    emits exactly the relations it always did.

    `claimed` is every side named explicitly across this side's three lists, so an explicit
    entry always beats the wildcard: `Allies: breen` + `Enemies: *` means breen is an ally
    and everything else is hostile, whichever list the wildcard sits in.

    Scope is THIS DOCUMENT. A wildcard reaches the sides authored alongside it and no
    others - so an addon declaring its own factions cannot silently redefine a relation
    with a side some other addon declared.
    """
    lowered = [str(i).strip().lower() for i in items]
    if not any(t in SIDE_TOKENS for t in lowered):
        return items
    named = [i for i in items if str(i).strip().lower() not in SIDE_TOKENS]
    out = list(named)

    def _add(keys):
        for k in keys:
            if k and k != self_key and k not in claimed and k not in out:
                out.append(k)

    # `players` and `civilians` reach ACROSS documents - that is the whole point, since a
    # mod cannot name another mod's sides. `*` stays inside this document, so an addon
    # cannot silently redefine a relation with a side it has never heard of.
    if any(t in SIDE_PLAYERS for t in lowered):
        _add(sorted(side_player_sides()))
    if any(t in SIDE_CIVILIANS for t in lowered):
        _add(sorted(side_civilian_sides()))
    if any(t in SIDE_EVERYONE for t in lowered):
        _add([k for k in all_keys])
    return out


def sides_declare(records):
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
    not - the new side is hostile to the others without editing seven other fences.
    """
    ids = {}
    for r in records:
        ids[r.get("key")] = side_create(
            r.get("key"), r.get("name"), r.get("desc"), r.get("color"),
            r.get("icon_index"), r.get("races"))   # relations applied in pass 2
        # Registered BEFORE pass 2 so a `civilians` token in this same document already
        # sees them, and kept across documents so another addon's raiders do too.
        if r.get("civilian"):
            _civilian_sides.add(str(r.get("key")).strip().lower())
    sbs = FrameContext.context.sbs
    if sbs is not None:
        all_keys = [r.get("key") for r in records]
        for r in records:
            key = r.get("key")
            allies = _side_csv_list(r.get("allies"))
            enemies = _side_csv_list(r.get("enemies"))
            neutral = _side_csv_list(r.get("neutral"))
            # Everything named by hand, so a token only fills what is left over.
            claimed = set()
            for lst in (allies, enemies, neutral):
                for i in lst:
                    if str(i).strip().lower() not in SIDE_TOKENS:
                        claimed.add(i)
            for a in _side_expand(allies, all_keys, key, claimed):
                side_set_relations(key, a, sbs.DIPLOMACY.ALLIED)
            for e in _side_expand(enemies, all_keys, key, claimed):
                side_set_relations(key, e, sbs.DIPLOMACY.HOSTILE)
            for nn in _side_expand(neutral, all_keys, key, claimed):
                side_set_relations(key, nn, sbs.DIPLOMACY.NEUTRAL)

            # Remember the token rules. `players` resolves against the ROSTER, which a
            # mission may change after the sides are declared (a trial that seats its crew
            # on another side), and `civilians` against a registry another addon may still
            # be adding to. sides_apply_audiences() replays these once everything is real.
            for lst, rel in ((allies, sbs.DIPLOMACY.ALLIED),
                             (enemies, sbs.DIPLOMACY.HOSTILE),
                             (neutral, sbs.DIPLOMACY.NEUTRAL)):
                if any(str(i).strip().lower() in SIDE_TOKENS for i in lst):
                    _audience_rules.append((key, tuple(lst), tuple(all_keys),
                                            frozenset(claimed), int(rel)))
    return ids


def sides_apply_audiences():
    """Re-apply every token rule seen this mission. Returns how many were replayed.

    Declaration happens at `create_sides`, BEFORE any player ship exists, so `players`
    resolves from `PLAYER_LIST` alone at that point. Call this once the crew is real - or
    after a mission moves a crew onto another side - and the same rules resolve against the
    live roster too.

    Safe to call repeatedly: `side_set_relations` replaces a pair's relation rather than
    accumulating, and explicit names still beat the tokens because `claimed` was captured
    with the rule.
    """
    sbs = FrameContext.context.sbs
    if sbs is None:
        return 0
    n = 0
    for key, lst, all_keys, claimed, rel in _audience_rules:
        for other in _side_expand(list(lst), list(all_keys), key, set(claimed)):
            side_set_relations(key, other, rel)
        n += 1
    return n


def sides_declare_amd(node):
    """Declare all sides authored under an AMD node (flat sides doc or a Sides section)."""
    return sides_declare(sides_from_section(node))


def sides_load_amd(file_path):
    """Load a sides file relative to the mission folder and declare every side in it - the
    one-call path a mission should use. Bakes in ``data_parser=amd_side_data`` so a caller
    can't accidentally omit it: the default AMD reader is YAML, which would silently drop a
    ``Color: #07F`` value (``#`` starts a YAML comment). Returns {key: side_id}."""
    from sbs_utils.procedural.amd_doc import amd_document
    from sbs_utils.fs import get_mission_dir_filename
    content = amd_read_text(get_mission_dir_filename(file_path))
    return sides_declare_amd(amd_document(content, data_parser=amd_side_data))
