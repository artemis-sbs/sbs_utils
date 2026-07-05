def amd_coords (s, n=2):
    """'6, 4' -> [6, 4] (the first `n` signed-integer tokens)."""
def amd_fact_lines (text):
    """Yield (label, value) per `Label: value` line - label lowercased, both
    stripped. Skips blanks, `//` comments, and lines without a colon."""
def amd_is_yaml_flow (text):
    """True when the fence should be parsed as YAML (contains '{' or '[')."""
def amd_list (s):
    """Comma-split, trimmed, empties dropped."""
def amd_makeup (s):
    """'60% X, 40% Y' -> {X:60, Y:40}; 'X, Y' -> list; 'X' -> str.
    (Three shapes; the percent form keeps the original display casing of the key.)"""
def amd_norm (name):
    """Canonicalize a token: lowercase, hyphens/spaces -> underscores."""
def amd_num (s):
    """int -> float -> the trimmed string, whichever parses first."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x000001F842814D60>):
    """Parse a friendly fact-sheet fence into a dict.
    
    If `amd_is_yaml_flow(text)`, delegate to `load_yaml_string`. Otherwise, for
    each (label, value): call `handler(data, label, value)` when given, and if it
    returns a truthy value the label is consumed; otherwise fall back to
    `data[amd_norm(label)] = default(value)`. The handler receives the mutable
    `data` dict so it can setdefault / nest / append freely. Returns `data`."""
def amd_pct (s):
    """'40%' -> 0.4; '0.4' -> 0.4; a bare number -> float; else the string."""
def amd_weighted (s):
    """'by-the-book 40, fearsome 30' -> {by_the_book: 40, fearsome: 30}
    (trailing integer is the weight; a bare name gets weight 0)."""
def load_yaml_string (s):
    """Parse a YAML string.
    
    Attempts to parse using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
    Args:
        s (str): YAML content as a string.
    
    Returns:
        dict or None: Parsed YAML data, or None if parsing fails."""
