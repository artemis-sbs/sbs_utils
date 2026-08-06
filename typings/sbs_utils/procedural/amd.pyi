def _coerce_nested (value, default):
    """Apply `default` to every leaf of a nested block or list, so `Inner: 3` reads
    as 3 wherever it sits. Inner KEYS keep the author's exact spelling - mission code
    reads a Properties/Defaults block by the names it wrote."""
def _err (errors, lineno, message):
    """Record a parse problem in a WRITER's terms.
    
    `errors` may be a plain list (messages, for a caller that just wants to print
    them) or an `AmdErrors` (which also keeps the line, so the linter and the editor
    can put a squiggle on it)."""
def _flow (value, lineno, errors):
    """Parse a `{...}` / `[...]` value. On a syntax slip, say so in the author's
    terms and keep the raw text rather than losing the line."""
def _group (entries):
    """Split [(lineno, raw)] into [(lineno, raw, children)] by indentation - each
    entry owns the more-indented lines that follow it."""
def _indent (raw):
    ...
def _meaningful (text):
    """[(lineno, raw)] with blanks and `//` comments dropped, 1-based line numbers."""
def _parse_entries (entries, errors):
    """The recursive body: grouped lines -> a dict (or a list, for `- item` form).
    
    SYNTAX ONLY. Leaves come back as the author's raw string, so the caller's handler
    still gets first refusal on the text before any type touches it - a domain rule
    like landmarks' "Loc needs three numbers" has to be able to see `1, 2` and reject
    it. Flow values ARE parsed here, because a bracket is syntax, not meaning."""
def _scalar (value, lineno, errors):
    """A bare list item: flow if it opens with a bracket, else text with quotes shed."""
def amd_chain (*handlers):
    """Compose several `amd_parse_facts` handlers into one. Each label is offered to the
    handlers in order; the first that consumes it (returns truthy) wins, otherwise it falls
    through to the default coercion. Lets a single parser understand SEVERAL vocabularies at
    once - e.g. quests + science scans + landmarks - so a mission can author all its content
    sections in ONE .amd file (parsed by document_get_amd_file with the chained parser) and
    hand each section to its own loader. Ordering matters only where two handlers claim the
    same label; keep the most specific first."""
def amd_coords (s, n=2):
    """'6, 4' -> [6, 4] (the first `n` signed-integer tokens)."""
def amd_counted (s):
    """'bio_sample x1, salvage x5' -> {'bio_sample': 1, 'salvage': 5}; a bare key -> 1.
    
    The shopping-list shape an author writes for costs and contents. Promoted here from
    LegendaryMissions' `recipes.py:_parse_inputs` so the fabrication recipe fence reads
    through the SAME declared type as everything else, instead of a private loader."""
def amd_duration_parts (value):
    """`6 minutes` -> `(6, "minutes")`, `90 seconds` -> `(90, "seconds")`, `2` ->
    `(2, "minutes")`. `(None, unit)` when there's no number.
    
    The unit is MINUTES unless the text says "second" - the rule `Fail after:` and
    `Complete after:` have always used. Shared so a view can't disagree with the clock
    the engine actually runs. Returns the AUTHORED unit (not just seconds) because the
    quest data keeps what was written.
    
    The COMPACT form parses too - `20m`, `30s`, `2h`. It reads naturally and everyone
    writes it, but the digit-token scan never saw it: `20m` is not `isdigit()`, so
    `Fails when: after 20m` came back `(None, "minutes")` -> `{minutes: 0}` -> `secs <=
    0` -> the watcher skipped the quest and **the deadline silently never fired**. An
    unrecognized suffix still falls through to minutes, as before."""
def amd_duration_seconds (value):
    """`amd_duration_parts` collapsed to seconds, or None if there's no number."""
def amd_fact_lines (text):
    """Yield (label, value) per `Label: value` line - label lowercased, both
    stripped. Skips blanks, `//` comments, and lines without a colon.
    
    Kept for callers that want the flat view; `amd_parse_facts` no longer uses it."""
def amd_is_yaml_flow (text):
    """True when a VALUE should be parsed as YAML flow - it starts with `{` or `[`.
    
    This used to scan the whole fence, so one prose value carrying a brace
    (`Intel: Captain {name}`) silently reparsed every other line under YAML rules,
    where `Color: #07F` becomes None and `Reveals: Survey logged: 3` raises. The
    flip is now per-value, which is strictly more permissive: nothing that parsed
    before stops parsing, and `#` colours survive in the same fence as a flow value."""
def amd_kind_line (text):
    """The fence's bare-noun kind line (`Characters`) if it has one, else None.
    
    Must be the FIRST meaningful line - blanks and `//` comments may precede it, so a
    section can be commented without breaking. Singular or plural both work; the caller
    resolves the noun against the section-name table."""
def amd_kv (s):
    """'kind=bio, range=medium' -> {'kind': 'bio', 'range': 'medium'}.
    
    Promoted from `recipes.py:_parse_program`. Parts without an `=` are skipped."""
def amd_list (s):
    """Comma-split, trimmed, empties dropped."""
def amd_makeup (s):
    """'60% X, 40% Y' -> {X:60, Y:40}; 'X, Y' -> list; 'X' -> str.
    (Three shapes; the percent form keeps the original display casing of the key.)"""
def amd_norm (name):
    """Canonicalize a token: lowercase, hyphens/spaces -> underscores."""
def amd_num (s):
    """int -> float -> the trimmed string, whichever parses first."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000011CF6E5F4C0>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def amd_pct (s):
    """'40%' -> 0.4; '0.4' -> 0.4; a bare number -> float; else the string."""
def amd_signal_name (value):
    """A signal name, lowercased with spaces -> underscores (matched exactly).
    
    Lives here, not in a caller, because it IS the matching contract: the quest driver
    matches on it at runtime and the editor's signal join matches on it statically. Two
    copies held in agreement by a comment would silently stop agreeing the first time
    the rule widened."""
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
class AmdErrors(list):
    """Collected parse problems that remember WHERE they were.
    
    Behaves as a list of `"line N: message"` strings (so existing callers are
    unaffected), while `.items` keeps `(line, message)` pairs. `line_offset` maps
    the fence-relative line the parser sees onto the real file line - without it a
    diagnostic would point at line 3 of the block instead of line 147 of the file."""
    def __class_getitem__(*argv):
        """See PEP 585"""
    def __init__ (self, line_offset=0):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add (self, lineno, message):
        ...
class FenceScanner(object):
    """Tracks whether we are inside a `---` data block, WITHOUT toggling.
    
    A `---` used to flip a boolean, so one stray rule inverted data-and-body for the
    rest of the file. The rules now:
    
      * `---` OPENS only immediately after a heading (or at the very top of the file,
        which is the document-level fence)
      * `---` CLOSES only while a block is open
      * a heading always closes an open block
      * anywhere else `---` is just prose
    
    `unterminated` reports a block still open at EOF, so the caller can say so."""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def feed (self, line, lineno=0):
        """Classify one line: 'open' | 'close' | 'data' | 'heading' | 'body'."""
    def finish (self):
        """Call at EOF. True when a block was left open."""
