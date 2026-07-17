"""Shared AMD science-scan vocabulary - the science analogue of amd_quest, authored the
same way OU authors dialogue.

The preferred (dialogue-native) form: one heading per (role, tab); the fence binds it via
``Scan of:`` (the role, like dialogue's ``Speaker:``) and ``Tab:`` (which tab, like
``When:``), and the BODY holds the ``%`` random variant lines (like dialogue's spoken lines,
one picked at random per scan):

    # [Derelict Hull](derelict_scan)
    ---
    Scan of: universe_derelict
    Tab: scan
    ---
    % Gutted, battle-scarred wreckage of a starship.
    % Hulk of a destroyed ship, still smoking.

A flat form is also accepted (simplest for single-line tabs) - heading key = role, fence tab
labels = one line each:

    # [Poacher](poacher)
    ---
    Scan: Unregistered trawler running dark.
    Bio: Holds contain protected space-life specimens.
    ---

Standard tabs: ``scan`` / ``status`` / ``intel`` / ``mat`` / ``bio``. Any line may carry
``{key}`` placeholders, filled per object from inventory at scan time (see procedural.science).
Because the dialogue-native text lives in the BODY (not a fence value), it never trips the
YAML-flow path, so ``{placeholder}`` and colon-heavy prose are safe there. Generic value
coercion lives in ``amd.py``; this is the science LAYER on top, mirroring ``amd_quest``.
"""
from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.procedural.science import science_define_scan, SCIENCE_SCAN_TABS


def amd_scan_facts():
    """Return an ``amd_parse_facts`` handler mapping the flat tab labels (Scan / Status /
    Intel / Mat / Bio) to a ``{tab: text}`` dict. Unknown labels return None so a mission
    can chain its own handler (or fall to the default coercion)."""
    def handler(data, label, value):
        if label in SCIENCE_SCAN_TABS:
            data[label] = value
        else:
            return None
        return True
    return handler


def amd_scan_data(text):
    """Parse one fence into a data dict. Handles the flat tab labels; the dialogue-native
    ``Scan of:`` / ``Tab:`` labels fall through to default coercion (they're read by
    ``science_define_scan_amd``)."""
    return amd_parse_facts(text, amd_scan_facts())


def _scan_body_lines(desc):
    """Body prose -> list of scan variants. Each non-empty, non-comment line is a variant; a
    leading ``%`` (the random-variant marker, as in dialogue) is stripped. One line -> one
    fixed variant; several -> pick-one-at-random at scan time (science_scan_tab)."""
    out = []
    for raw in (desc or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("%"):
            line = line[1:].strip()
        if line:
            out.append(line)
    return out


def science_define_scan_amd(doc):
    """Register per-role scan content from a parsed AMD doc (``document_get_amd_file`` with
    ``data_parser=amd_scan_data``). Per heading, two authoring forms (they compose -
    science_define_scan merges):

    * Dialogue-native: a ``Scan of: <role>`` fence (+ optional ``Tab:``, default ``scan``);
      the BODY's ``%`` lines are that tab's random variants.
    * Flat: heading key = role; fence scan-tab labels (Scan/Status/Intel/Mat/Bio) are
      single-line tabs; a bare body becomes the ``scan`` tab.
    """
    if doc is None:
        return
    for n in doc.get("children", []):
        # Lowercase keys: a {placeholder} in a FLAT fence value trips YAML mode, which
        # preserves label case; do both so lookups (lowercase) match either way.
        data = {str(k).lower(): v for k, v in (n.get("data") or {}).items()}
        role_of = data.get("scan of") or data.get("scan_of")
        if role_of:
            # Dialogue-native: the body holds this tab's (possibly random) lines.
            tab = str(data.get("tab", "scan")).strip().lower()
            lines = _scan_body_lines(n.get("description") or "")
            if lines:
                science_define_scan(role_of, {tab: lines if len(lines) > 1 else lines[0]})
            continue
        # Flat: heading key = role; fence tab labels = single-line tabs.
        role = n.get("key")
        if not role:
            continue
        tabs = {k: data[k] for k in SCIENCE_SCAN_TABS if k in data}
        desc = (n.get("description") or "").strip()
        if desc and "scan" not in tabs:
            tabs["scan"] = desc
        if tabs:
            science_define_scan(role, tabs)
