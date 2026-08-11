"""Shared AMD science-scan vocabulary - the science analogue of amd_quest, authored the
same way OU authors dialogue.

One heading per (role, tab); the fence binds it via ``Scan of:`` (the role, like dialogue's
``Speaker:``) and ``Tab:`` (which tab, like ``When:``; default ``scan``), and the BODY holds
the ``%`` random variant lines (like dialogue's spoken lines, one picked at random per scan):

    # [Derelict Hull](derelict_scan)
    ---
    Scan of: universe_derelict
    Tab: scan
    ---
    % Gutted, battle-scarred wreckage of a starship.
    % Hulk of a destroyed ship, still smoking.

Standard tabs: ``scan`` / ``status`` / ``intel`` / ``mat`` / ``bio``. Any line may carry
``{key}`` placeholders, filled per object from inventory at scan time (see procedural.science)
AFTER the random pick, so a ``{captain}`` line resolves per object. Because the text lives in
the BODY (not a fence value), it never trips the YAML-flow path, so ``{placeholder}`` and
colon-heavy prose are safe there. Generic value coercion lives in ``amd.py``; this is the
science LAYER on top, mirroring ``amd_quest``.

(A flat ``Scan: <text>`` / ``Bio: <text>`` fence form was retired on v1.4.0_dev in favour of
this single dialogue-native form; ``science_define_scan`` is the underlying registry API.)
"""
from sbs_utils.procedural.amd import amd_parse_facts, amd_variant_pool
from sbs_utils.procedural.science import science_define_scan


def amd_scan_data(text):
    """Parse one scan fence into a data dict (``Scan of:`` -> ``scan_of``, ``Tab:`` -> ``tab``,
    via the default value coercion). Use as the ``data_parser`` for a scan-only .amd file; a
    consolidated mission file uses ``amd_mission_data`` instead. The scan TEXT is read from the
    fence body by ``science_define_scan_amd``, not from here."""
    return amd_parse_facts(text)


# Body prose -> list of scan variants. One line -> one fixed variant; several ->
# pick-one-at-random at scan time (science_scan_tab). One owner: the rule was
# copied byte for byte into amd_chatter and inlined a third time in amd_lsp.
_scan_body_lines = amd_variant_pool


def science_define_scan_amd(doc):
    """Register per-role scan content from a parsed AMD doc (``document_get_amd_file`` with
    ``data_parser=amd_scan_data`` or a mission's ``amd_mission_data``). Per heading: a
    ``Scan of: <role>`` fence (+ optional ``Tab:``, default ``scan``); the BODY's ``%`` lines
    are that tab's random variants (a single line -> one fixed variant). Multiple headings for
    the same role compose - ``science_define_scan`` merges their tabs."""
    if doc is None:
        return
    for n in doc.get("children", []):
        # amd_norm already lowercases keys during parsing; lower() again is belt-and-suspenders
        # so a hand-built data dict (e.g. in tests) resolves the same way.
        data = {str(k).lower(): v for k, v in (n.get("data") or {}).items()}
        role_of = data.get("scan of") or data.get("scan_of")
        if not role_of:
            continue
        tab = str(data.get("tab", "scan")).strip().lower()
        lines = _scan_body_lines(n.get("description") or "")
        if lines:
            science_define_scan(role_of, {tab: lines if len(lines) > 1 else lines[0]})
