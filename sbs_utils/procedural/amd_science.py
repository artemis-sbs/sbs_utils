"""Shared AMD science-scan vocabulary.

The declarative fact-sheet grammar for per-role SCIENCE SCANS - the science analogue of
amd_quest. An author writes a heading per role and the tab labels inside a fence:

    # [Poacher](poacher)
    ---
    Scan: Unregistered trawler running dark.
    Bio: Holds contain protected space-life specimens.
    Intel: Falsified transponder. Disable and board - do not destroy.
    ---

Each heading ``# [Name](role)`` becomes ``science_define_scan(role, {tab: text})``. Standard
tabs: ``scan`` / ``status`` / ``intel`` / ``mat`` / ``bio`` (a bare prose body under the fence
is the scan tab when there is no explicit ``Scan:``). Values may carry ``{key}`` placeholders,
filled per object from inventory at scan time (see procedural.science). Generic value coercion
lives in ``amd.py``; this is the science LAYER on top, mirroring ``amd_quest``.
"""
from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.procedural.science import science_define_scan, SCIENCE_SCAN_TABS


def amd_scan_facts():
    """Return an ``amd_parse_facts`` handler mapping the tab labels (Scan / Status / Intel /
    Mat / Bio) to a ``{tab: text}`` dict. Unknown labels return None so a mission can chain
    its own handler (or fall to the default coercion)."""
    def handler(data, label, value):
        if label in SCIENCE_SCAN_TABS:
            data[label] = value
        else:
            return None
        return True
    return handler


def amd_scan_data(text):
    """Parse one scan fact-sheet fence into a ``{tab: text}`` dict."""
    return amd_parse_facts(text, amd_scan_facts())


def science_define_scan_amd(doc):
    """Register per-role scan content from a parsed AMD doc (``document_get_amd_file`` with
    ``data_parser=amd_scan_data``). Each heading ``# [Name](role)`` ->
    ``science_define_scan(role, tabs)``; a prose body under the fence becomes the ``scan`` tab
    when there is no explicit ``Scan:`` label. Idempotent (science_define_scan merges)."""
    if doc is None:
        return
    for n in doc.get("children", []):
        role = n.get("key")
        if not role:
            continue
        data = n.get("data") or {}
        # Only the standard scan tabs (amd_parse_facts' default coercion also captures any
        # stray labels, which we ignore here).
        tabs = {k: data[k] for k in SCIENCE_SCAN_TABS if k in data}
        desc = (n.get("description") or "").strip()
        if desc and "scan" not in tabs:
            tabs["scan"] = desc
        if tabs:
            science_define_scan(role, tabs)
