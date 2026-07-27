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


def amd_signal_name(value):
    """A signal name, lowercased with spaces -> underscores (matched exactly).

    Lives here, not in a caller, because it IS the matching contract: the quest driver
    matches on it at runtime and the editor's signal join matches on it statically. Two
    copies held in agreement by a comment would silently stop agreeing the first time
    the rule widened."""
    return str(value).strip().lower().replace(" ", "_")


def amd_duration_parts(value):
    """`6 minutes` -> `(6, "minutes")`, `90 seconds` -> `(90, "seconds")`, `2` ->
    `(2, "minutes")`. `(None, unit)` when there's no number.

    The unit is MINUTES unless the text says "second" - the rule `Fail after:` and
    `Complete after:` have always used. Shared so a view can't disagree with the clock
    the engine actually runs. Returns the AUTHORED unit (not just seconds) because the
    quest data keeps what was written."""
    num = next((int(t) for t in str(value).split() if t.isdigit()), None)
    unit = "seconds" if "second" in str(value).lower() else "minutes"
    return num, unit


def amd_duration_seconds(value):
    """`amd_duration_parts` collapsed to seconds, or None if there's no number."""
    num, unit = amd_duration_parts(value)
    return None if num is None else (num if unit == "seconds" else num * 60)


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


def amd_counted(s):
    """'bio_sample x1, salvage x5' -> {'bio_sample': 1, 'salvage': 5}; a bare key -> 1.

    The shopping-list shape an author writes for costs and contents. Promoted here from
    LegendaryMissions' `recipes.py:_parse_inputs` so the fabrication recipe fence reads
    through the SAME declared type as everything else, instead of a private loader."""
    out = {}
    for part in amd_list(s):
        bits = part.split()
        count = 1
        if len(bits) > 1:
            c = bits[-1].lstrip("xX")
            if c.isdigit():
                count = int(c)
        out[bits[0]] = count
    return out


def amd_kv(s):
    """'kind=bio, range=medium' -> {'kind': 'bio', 'range': 'medium'}.

    Promoted from `recipes.py:_parse_program`. Parts without an `=` are skipped."""
    out = {}
    for part in amd_list(s):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    return out


# --- fence parsing ----------------------------------------------------------
# ONE reader. Before this there were four - the default `load_yaml_string`, this
# friendly sheet, a whole-fence YAML flip triggered by a `{` ANYWHERE in the block,
# and domain loaders that bypassed all of it - so the linter and the runtime could
# read the same bytes differently. The grammar:
#
#     Characters                 first meaningful line, no colon: WHAT THESE ARE
#     Color: #3399ff             a field
#     Citation: a long line      non-empty value -> indented lines CONTINUE it
#       that wraps
#     Properties:                EMPTY value -> indented lines NEST
#       Monster: 'gui_...'
#     Lines:                     ...or become a list
#       - "First bark."
#     Modifiers: {speed: 2}      value starting { or [ is flow (that value only)
#     // a comment
#
# One rule separates continuation from nesting: an inline value means indented
# lines continue it; an empty value means they nest. That resolves every shape in
# the corpus without asking the author to learn a second sigil.

KIND_KEY = "__kind__"     # reserved: where the bare-noun kind line is stored


def amd_is_yaml_flow(text):
    """True when a VALUE should be parsed as YAML flow - it starts with `{` or `[`.

    This used to scan the whole fence, so one prose value carrying a brace
    (`Intel: Captain {name}`) silently reparsed every other line under YAML rules,
    where `Color: #07F` becomes None and `Reveals: Survey logged: 3` raises. The
    flip is now per-value, which is strictly more permissive: nothing that parsed
    before stops parsing, and `#` colours survive in the same fence as a flow value."""
    s = str(text).lstrip()
    return s.startswith("{") or s.startswith("[")


def amd_fact_lines(text):
    """Yield (label, value) per `Label: value` line - label lowercased, both
    stripped. Skips blanks, `//` comments, and lines without a colon.

    Kept for callers that want the flat view; `amd_parse_facts` no longer uses it."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or ":" not in line:
            continue
        label, value = line.split(":", 1)
        yield label.strip().lower(), value.strip()


def _meaningful(text):
    """[(lineno, raw)] with blanks and `//` comments dropped, 1-based line numbers."""
    out = []
    for i, raw in enumerate(str(text).splitlines(), start=1):
        s = raw.strip()
        if s and not s.startswith("//"):
            out.append((i, raw.rstrip()))
    return out


def _indent(raw):
    return len(raw) - len(raw.lstrip())


def _flow(value, lineno, errors):
    """Parse a `{...}` / `[...]` value. On a syntax slip, say so in the author's
    terms and keep the raw text rather than losing the line."""
    try:
        parsed = load_yaml_string(value)
    except Exception:
        parsed = None
    if parsed is None:
        _err(errors, lineno, f'could not read {value.lstrip()[:1]}...{value.rstrip()[-1:]} '
                             f'- check the brackets match and quote any value with a colon in it')
        return value
    return parsed


def _err(errors, lineno, message):
    if errors is not None:
        errors.append(f"line {lineno}: {message}")


def _group(entries):
    """Split [(lineno, raw)] into [(lineno, raw, children)] by indentation - each
    entry owns the more-indented lines that follow it."""
    out = []
    if not entries:
        return out
    base = min(_indent(r) for _, r in entries)
    i = 0
    while i < len(entries):
        lineno, raw = entries[i]
        j = i + 1
        while j < len(entries) and _indent(entries[j][1]) > base:
            j += 1
        out.append((lineno, raw, entries[i + 1:j]))
        i = j
    return out


def _parse_entries(entries, errors):
    """The recursive body: grouped lines -> a dict (or a list, for `- item` form).

    SYNTAX ONLY. Leaves come back as the author's raw string, so the caller's handler
    still gets first refusal on the text before any type touches it - a domain rule
    like landmarks' "Loc needs three numbers" has to be able to see `1, 2` and reject
    it. Flow values ARE parsed here, because a bracket is syntax, not meaning."""
    grouped = _group(entries)
    if grouped and all(g[1].lstrip().startswith("- ") or g[1].strip() == "-" for g in grouped):
        return [_scalar(g[1].lstrip()[1:].strip(), g[0], errors) for g in grouped]

    data = {}
    for lineno, raw, children in grouped:
        line = raw.strip()
        if line.startswith("- "):
            _err(errors, lineno, "a list item here needs a `Label:` above it to belong to")
            continue
        if ":" not in line:
            if len(line.split()) == 1:
                _err(errors, lineno, f'"{line}" looks like a kind, but a kind has to be '
                                     f'the first line of the fence')
            else:
                _err(errors, lineno, 'expected "Label: value" - did you mean to put this '
                                     'line in the body, below the --- ?')
            continue
        label, value = line.split(":", 1)
        label, value = label.strip(), value.strip()
        if value and children:
            # non-empty value + indented lines = a value that WRAPS
            value = " ".join([value] + [c[1].strip() for c in children])
        elif children:
            # empty value + indented lines = a nested block or a list
            data[label] = _parse_entries(children, errors)
            continue
        data[label] = _flow(value, lineno, errors) if amd_is_yaml_flow(value) else value
    return data


def _coerce_nested(value, default):
    """Apply `default` to every leaf of a nested block or list, so `Inner: 3` reads
    as 3 wherever it sits. Inner KEYS keep the author's exact spelling - mission code
    reads a Properties/Defaults block by the names it wrote."""
    if isinstance(value, dict):
        return {k: _coerce_nested(v, default) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_nested(v, default) for v in value]
    return default(value) if isinstance(value, str) else value


def _scalar(value, lineno, errors):
    """A bare list item: flow if it opens with a bracket, else text with quotes shed."""
    if amd_is_yaml_flow(value):
        return _flow(value, lineno, errors)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def amd_chain(*handlers):
    """Compose several `amd_parse_facts` handlers into one. Each label is offered to the
    handlers in order; the first that consumes it (returns truthy) wins, otherwise it falls
    through to the default coercion. Lets a single parser understand SEVERAL vocabularies at
    once - e.g. quests + science scans + landmarks - so a mission can author all its content
    sections in ONE .amd file (parsed by document_get_amd_file with the chained parser) and
    hand each section to its own loader. Ordering matters only where two handlers claim the
    same label; keep the most specific first."""
    def handler(data, label, value):
        for fn in handlers:
            if fn is not None and fn(data, label, value):
                return True
        return None
    return handler


def amd_kind_line(text):
    """The fence's bare-noun kind line (`Characters`) if it has one, else None.

    Must be the FIRST meaningful line - blanks and `//` comments may precede it, so a
    section can be commented without breaking. Singular or plural both work; the caller
    resolves the noun against the section-name table."""
    lines = _meaningful(text)
    if not lines:
        return None
    first = lines[0][1].strip()
    if ":" in first or first.startswith("-") or _indent(lines[0][1]):
        return None
    # A kind is ONE word. `Colour red` is a mistyped field, not a kind - without this
    # a forgotten colon on the first line would be silently swallowed as a kind.
    # (`These are: characters` is the long form and carries a colon, so it arrives
    # here as an ordinary field; this is the bare-noun short form only.)
    return first if len(first.split()) == 1 else None


def amd_parse_facts(text, handler=None, default=amd_num, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.

    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.

    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
    from sbs_utils.procedural.amd_schema import amd_is_declared, amd_read_field

    lines = _meaningful(text)
    kind = amd_kind_line(text)
    if kind is not None:
        lines = lines[1:]

    raw_data = _parse_entries(lines, errors)
    if not isinstance(raw_data, dict):
        return raw_data

    data = {}
    for label, value in raw_data.items():
        # 1. the caller's handler, on the AUTHOR'S TEXT, before any type touches it.
        #    The label reaches it exactly as `amd_fact_lines` used to yield it -
        #    lowercased with SPACES INTACT - because handlers match spaced labels
        #    (`"scan text"`, `"fail on signal"`).
        if handler is not None and isinstance(value, str) \
                and handler(data, label.strip().lower(), value):
            continue
        # 2. the field registry, when this field is declared for this kind of record
        if amd_is_declared(label, archetype):
            key, parsed = amd_read_field(label, value, archetype)
            data[key] = parsed if isinstance(value, str) else value
            continue
        # 3. otherwise exactly what it does today
        data[amd_norm(label)] = _coerce_nested(value, default)
    if kind is not None:
        data[KIND_KEY] = amd_norm(kind)
    return data
