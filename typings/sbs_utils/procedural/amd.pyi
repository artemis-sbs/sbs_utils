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
def amd_body_synopsis (line):
    """The text of a `= ` synopsis line, or None when this is not one."""
def amd_body_transclude (line):
    """The record a `![[key]]` line pulls in, or None."""
def amd_body_transition (line):
    """The transition a body line names (`CUT TO:`), or None.
    
    Either Fountain's forced form (`> CUT TO:`) or one of the bare spellings every
    screenwriter already types. Returned uppercase so a renderer never has to care
    which was written."""
def amd_body_variant (line):
    """A `%` speech-variant line -> `(text, gate)`, or None when it is not one.
    
    `gate` is the condition in `%{...}` / `{...}`, or None. The leading `%` is
    optional in a dialogue body, so this returns a pair for ANY line once the
    caller has decided it is in speech position - it is the shared *stripping and
    gate* rule, not the decision that a line is speech. Callers that require the
    sigil test `line.startswith("%")` themselves."""
def amd_chain (*handlers):
    """Compose several `amd_parse_facts` handlers into one. Each label is offered to the
    handlers in order; the first that consumes it (returns truthy) wins, otherwise it falls
    through to the default coercion. Lets a single parser understand SEVERAL vocabularies at
    once - e.g. quests + science scans + landmarks - so a mission can author all its content
    sections in ONE .amd file (parsed by document_get_amd_file with the chained parser) and
    hand each section to its own loader. Ordering matters only where two handlers claim the
    same label; keep the most specific first."""
def amd_choice (line):
    """A `- [label](target) if guard ; outcomes` line -> dict, or None.
    
    Returns `{"label", "target", "guard", "outcomes"}`. `guard` is None when the
    choice is unconditional; `outcomes` is `amd_outcomes`' list of tuples.
    
    The `; outcomes` tail splits FIRST, before the `if` guard is read, because a
    guard is free text and would otherwise swallow the whole tail - `if standing >
    10 ; earns kind 5` would become the guard `standing > 10 ; earns kind 5`,
    which no evaluator can answer and which loses the outcome without a word."""
def amd_coords (s, n=2):
    """'6, 4' -> [6, 4] (the first `n` signed-integer tokens)."""
def amd_counted (s):
    """'bio_sample x1, salvage x5' -> {'bio_sample': 1, 'salvage': 5}; a bare key -> 1.
    
    The shopping-list shape an author writes for costs and contents. Promoted here from
    LegendaryMissions' `recipes.py:_parse_inputs` so the fabrication recipe fence reads
    through the SAME declared type as everything else, instead of a private loader."""
def amd_drop_keys (s):
    """Just the item keys a drop table names, in written order - what a reference
    extractor and a linter need, without the counts."""
def amd_drop_table (s):
    """'salvage x2-4, contraband 20%' -> [{key, low, high, chance}, ...].
    
    What a kill leaves behind. A richer shopping list than `amd_counted`, because loot
    has a RANGE and a CHANCE as well as a name:
    
        key            one, always
        key xN         N, always
        key xN-M       between N and M
        key P%         one, P of the time
        key xN-M P%    both
        none           nothing at all - an EMPTY table, which is NOT the same as having
                       no table (see `amd_drops.drops_table_for`)
    
    Lives here rather than in `amd_drops` so the stdlib-only half of the toolchain can
    read it too: the parser turns these keys into references and the linter checks them,
    and neither may import the runtime module. An already-parsed list passes through, so
    parsing twice is harmless."""
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
def amd_outcomes (s):
    """`'costs 200 credits, earns vex kind 5, signal paid'` -> `[(verb, *tokens), ...]`.
    
    Tokens are interpreted by the mission's registered outcome handler (only
    `signal` is built in), so the grammar of costs/earns/etc. lives with the
    mission rather than here."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000025CDACFD900>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def amd_parse_url (text):
    """`key?scale=0.5&align=center` -> `{"url": "key", "scale": "0.5", ...}`.
    
    Values stay STRINGS; every caller coerces to what it needs. Malformed pairs
    are skipped rather than raising - a mistyped option should cost the option,
    not the image."""
def amd_pct (s):
    """'40%' -> 0.4; '0.4' -> 0.4; a bare number -> float; else the string."""
def amd_read_text (path):
    """The text of one .amd (or any AMD-adjacent source), decoded the same way a
    mastlib read decodes it.
    
    UTF-8 first (with a BOM tolerated, since editors add one), falling back to
    cp1252 for a legacy file that predates that convention, and finally to a
    replacing UTF-8 decode - because a file that cannot be decoded should still
    parse into something an author can look at and fix, not vanish."""
def amd_render_wikilinks (text, display_of=None):
    """Replace every `[[key]]` / `[[key|words]]` with what a PLAYER should read.
    
    `[[key|words]]` renders `words`. A bare `[[key]]` renders the target record's
    display text when `display_of(key)` finds one, and otherwise the key itself - so
    a draft that links ahead to a scene nobody has written yet still reads as a
    sentence instead of showing brackets. The linter reports the same unresolved
    target as `dangling-link`; rendering never fails on it."""
def amd_signal_name (value):
    """A signal name, lowercased with spaces -> underscores (matched exactly).
    
    Lives here, not in a caller, because it IS the matching contract: the quest driver
    matches on it at runtime and the editor's signal join matches on it statically. Two
    copies held in agreement by a comment would silently stop agreeing the first time
    the rule widened."""
def amd_table_rows (raw_rows):
    """Raw `|a|b|` lines -> `(rows, aligns)`.
    
    `aligns` is one of `l`/`c`/`r` per column, taken from the `|:--|--:|`
    separator row, which is dropped from the data. A table with no separator
    renders all-left with row 0 as the header, so the separator is optional."""
def amd_table_scan (lines, i):
    """A GFM pipe table starting at `lines[i]` -> `(rows, next_index)`, else None.
    
    A table is **2 or more** consecutive lines starting with `|`. The pair is
    required deliberately: a lone `|` line is prose (a table drawn in words, an
    ASCII diagram, a sentence about a pipe) and must stay prose."""
def amd_variant_pool (text):
    """A record body -> its list of ungated variants, one per line.
    
    Each non-empty, non-comment line is one variant with a leading `%` stripped:
    one line is a fixed string, several are pick-one-at-random at use time. This
    is the pool a scan tab, a chatter bark or any other "say one of these" field
    reads, and it is deliberately NOT `amd_body_variant`: there are two variant
    rules in AMD and conflating them would be a silent behavior change.
    
      * this one   - strip the sigil. A `{...}` prefix is ordinary text.
      * `amd_body_variant` - strip the sigil AND read a `%{gate}` condition.
    
    Only DIALOGUE evaluates gates, because only dialogue has a speaker whose
    standing can be tested. A scan line reading `{lifesigns} faint` is a sentence
    about lifesigns, and must stay one.
    
    (`amd_urge` reads a third rule off the same sigil - it COUNTS `%` to number a
    stage, so `%%` is stage 2 - and cannot share this one.)"""
def amd_weighted (s):
    """'by-the-book 40, fearsome 30' -> {by_the_book: 40, fearsome: 30}
    (trailing integer is the weight; a bare name gets weight 0)."""
def amd_wikilinks (line):
    """Every `[[target]]` / `[[target|words]]` in `line` as `(target, alias, start, end)`.
    
    Columns are 0-based into `line` and cover the whole `[[...]]` token, so a caller
    can both point at it (spans, diagnostics) and replace it (rendering)."""
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
    def __init__ (self, line_offset=0):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add (self, lineno, message):
        ...
class BoneyardScanner(object):
    """Tracks `/* ... */` cut text - Fountain's boneyard.
    
    A writer cuts a scene far more often than a line, and wants it back next week.
    `//` handles a line; this handles a block, and it works INSIDE a fence as well
    as in a body because a cut scene usually takes its data with it - so it runs as
    a pre-pass, before the fence scanner sees anything.
    
    The opener must start a line (indent allowed) so a `/*` inside a sentence is
    still a sentence. Nothing is silently eaten: text after the closing `*/` on the
    same line is handed back as the surviving line, and an unclosed block at EOF is
    reported rather than swallowing the rest of the file."""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def feed (self, line, lineno=0):
        """Classify one raw line -> `(dropped, surviving_text)`.
        
        `dropped` True means the line is entirely commented out. Otherwise
        `surviving_text` is the line to go on processing - normally the line
        itself, or its tail when a `*/` ended a block partway through."""
    def finish (self):
        """Call at EOF. True when a block was left open."""
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
