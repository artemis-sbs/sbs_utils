"""Friendly AMD fact-sheet fence reader.

A companion `data_parser` for `procedural.quest.document_get_amd_file` (which
already parses the `#`/`##` headings and `---` fences): this turns a single
`Label: value` fenced block into a dict, with light value coercion - comma lists,
"name N" weights, "name N%" makeup, coord pairs, percentages. A block that uses
YAML flow (`{` or `[`) is parsed as YAML instead, so YAML fences keep working
through the same reader.

Domain label->key interpretation (what "flies" or "yields" means) is the CALLER's
job, supplied via a `handler` callback - see the Open Universe's `universe_amd.py`
for a worked example. This module stays content-agnostic: just parsing + coercion.

Dependency-light (only `load_yaml_string`) so it imports cleanly and is
unit-testable outside the engine.
"""
from sbs_utils.fs import load_yaml_string


# --- value-coercion primitives ---------------------------------------------
def amd_norm(name):
    """Canonicalize a token: lowercase, hyphens/spaces -> underscores."""
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def amd_num(s):
    """int -> float -> the trimmed string, whichever parses first."""
    s = str(s).strip()
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def amd_pct(s):
    """'40%' -> 0.4; '0.4' -> 0.4; a bare number -> float; else the string."""
    s = str(s).strip()
    if s.endswith("%"):
        s = s[:-1].strip()
        try:
            return float(s) / 100.0
        except ValueError:
            return s
    try:
        return float(s)
    except ValueError:
        return s


def amd_list(s):
    """Comma-split, trimmed, empties dropped."""
    return [x.strip() for x in str(s).split(",") if x.strip()]


def amd_weighted(s):
    """'by-the-book 40, fearsome 30' -> {by_the_book: 40, fearsome: 30}
    (trailing integer is the weight; a bare name gets weight 0)."""
    out = {}
    for item in amd_list(s):
        toks = item.split()
        if len(toks) >= 2 and toks[-1].lstrip("+-").isdigit():
            out[amd_norm(" ".join(toks[:-1]))] = int(toks[-1])
        elif toks:
            out[amd_norm(item)] = 0
    return out


def amd_makeup(s):
    """'60% X, 40% Y' -> {X:60, Y:40}; 'X, Y' -> list; 'X' -> str.
    (Three shapes; the percent form keeps the original display casing of the key.)"""
    items = amd_list(s)
    if any("%" in it for it in items):
        out = {}
        for it in items:
            toks = it.replace("%", " ").split()
            if toks and toks[0].isdigit():
                out[" ".join(toks[1:])] = int(toks[0])
            elif len(toks) >= 2 and toks[-1].isdigit():
                out[" ".join(toks[:-1])] = int(toks[-1])
        return out
    return items[0] if len(items) == 1 else items


def amd_coords(s, n=2):
    """'6, 4' -> [6, 4] (the first `n` signed-integer tokens)."""
    return [int(x) for x in str(s).replace(",", " ").split()
            if x.lstrip("-").isdigit()][:n]


# --- fence parsing ----------------------------------------------------------
def amd_is_yaml_flow(text):
    """True when the fence should be parsed as YAML (contains '{' or '[')."""
    return "{" in text or "[" in text


def amd_fact_lines(text):
    """Yield (label, value) per `Label: value` line - label lowercased, both
    stripped. Skips blanks, `//` comments, and lines without a colon."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or ":" not in line:
            continue
        label, value = line.split(":", 1)
        yield label.strip().lower(), value.strip()


def amd_parse_facts(text, handler=None, default=amd_num):
    """Parse a friendly fact-sheet fence into a dict.

    If `amd_is_yaml_flow(text)`, delegate to `load_yaml_string`. Otherwise, for
    each (label, value): call `handler(data, label, value)` when given, and if it
    returns a truthy value the label is consumed; otherwise fall back to
    `data[amd_norm(label)] = default(value)`. The handler receives the mutable
    `data` dict so it can setdefault / nest / append freely. Returns `data`."""
    if amd_is_yaml_flow(text):
        y = load_yaml_string(text)
        # Normalize TOP-LEVEL keys the same way the friendly path does (amd_norm), so a fence
        # parses to the SAME keys whether it took the friendly path or YAML flow. A stray
        # `{`/`[` (e.g. an `Intel: Captain {name}` value, or a `reputation: {...}` block)
        # flips the whole fence to YAML, which otherwise preserves label CASE - the historical
        # source of capitalized-vs-lowercase key drift. Nested structure is left as authored
        # (mission code reads those inner keys by their exact names).
        if isinstance(y, dict):
            return {amd_norm(k): v for k, v in y.items()}
        return y
    data = {}
    for label, value in amd_fact_lines(text):
        if handler is not None and handler(data, label, value):
            continue
        data[amd_norm(label)] = default(value)
    return data
