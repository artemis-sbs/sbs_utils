"""Declarative chatter line-pools from AMD - author a mission's radio / dispatch / news barks as
data instead of hardcoded line dicts, the way Open Universe authors its fleet chatter. A section
holds one heading per event key; the heading's BODY lines are that key's pool (one is picked at
random per call), and ``{field}`` placeholders are filled from the caller's keyword fields:

    ## [Fleet Chatter](chatter)

    # [Order: Strike](ack_strike)
    Weapons free. Moving to engage.
    Guns hot, Admiral - closing now.

    # [Salvage Haul](salvage_haul)
    Wreck stripped: +{ore} ore, +{gas} gas in the hold.
    Good pickings off that hull - {ore} ore and {gas} gas the richer.

No ``---`` fence is needed - the pool lives in the BODY, so ``{placeholder}`` and colon-heavy prose
are safe (they never trip the YAML-flow path). A leading ``%`` (the dialogue random-variant marker)
is stripped if present, and ``//`` comment lines are ignored. Generalised from OU's
``fleet_chatter_configure`` / ``fleet_line`` - the OU built-in default lines and console targeting
stay in OU; this loader is content-agnostic.
"""
import random
import re
from sbs_utils.procedural.amd import amd_parse_facts, amd_variant_pool

# {field} placeholder, matched only for python-identifier field names (a stray brace passes through).
_CHATTER_INTERP = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def amd_chatter_data(text):
    """Parse one chatter fence into a data dict (default coercion - all fields are strings). Use as
    the ``data_parser`` for a chatter-only .amd; a consolidated mission file uses ``amd_mission_data``
    and its chatter headings' bodies fall through the same way. Most chatter needs no fence at all -
    the pool is the heading BODY, not fence values."""
    return amd_parse_facts(text)


# Body prose -> list of chatter lines. One line -> one fixed bark; several ->
# pick-one-at-random per call (chatter_line). Same rule as a scan's variant pool,
# and now the same code: one owner in `amd`.
_chatter_body_lines = amd_variant_pool


def chatter_scenes(section):
    """``{key: [lines]}`` pools from a section node's children (empty dict if None). Each
    ``# [Display](key)`` heading's BODY lines become that key's pool; a heading with an empty body
    is skipped. ``section`` is the parsed AMD section (as from ``document_get_amd_file`` /
    ``universe_section``)."""
    out = {}
    if section is not None:
        for n in section.get("children", []):
            key = n.get("key")
            pool = _chatter_body_lines(n.get("description") or "")
            if key and pool:
                out[key] = pool
    return out


def _fill(line, fields):
    """Fill ``{field}`` placeholders from ``fields``; an unknown field is left LITERAL (so a stray
    ``{x}`` never crashes and never silently vanishes)."""
    if not line or "{" not in line:
        return line
    def repl(m):
        name = m.group(1)
        return str(fields[name]) if name in fields else m.group(0)
    return _CHATTER_INTERP.sub(repl, line)


def chatter_line(scenes, key, **fields):
    """A line for an event key: a random candidate from ``scenes[key]``, with ``{field}``
    placeholders filled from the keyword fields (missing fields are left literal, never a crash).
    Returns ``""`` if the key/pool is missing (or ``scenes`` is None)."""
    pool = (scenes or {}).get(key)
    if not pool:
        return ""
    return _fill(random.choice(pool), fields)
