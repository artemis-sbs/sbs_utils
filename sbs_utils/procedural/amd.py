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
import re

from sbs_utils.fs import load_yaml_string


# --- document line grammar (ONE definition, shared by every AMD reader) ------
# `amd_core` (the linter/LSP model) and `quest._document_get_amd_file` (the runtime)
# each used to carry their own copy of these rules. Two copies of a grammar is how
# the tooling and the game came to disagree about the same file, so they live here
# once and both import them.

# `\r` is in the trailing class on purpose. A line fed here still carries its ending
# (`splitlines(True)` / `readlines()`), and `$` matches before a final `\n` but NOT
# before `\r\n`. A file with CRLF therefore matched no heading at all - every heading
# became body text and the whole document collapsed into its root.
#
# Why it depended on WHERE the file was read from, which is the part worth remembering:
# on Windows `core.autocrlf=true` means the .amd is CRLF ON DISK. Reading it from a
# folder goes through `open(path, 'r')`, and Python's text mode translates `\r\n` to
# `\n` - so the folder path silently repaired it. Reading it out of a MASTLIB decodes
# the zip's BYTES, where no such translation happens, so the CRLF survives. One file,
# two readers, two different documents.
# RE_FENCE never had the bug because `\s` already includes `\r`.
RE_HEADING = re.compile(r"(?P<hashes>#+)[ \t]+\[(?P<display>[^\]]*)\]"
                        r"\((?P<urn>[^)]*)\)[ \t\r]*$")
RE_FENCE = re.compile(r"\s*-{3,}\s*$")

# --- body-line grammar -------------------------------------------------------
# The rule that keeps this format growable: **a body line the grammar does not
# claim is prose, forever.** Every pattern below claims a line only on an
# unmistakable leading sigil, so adding one can never change what an existing
# sentence means. (Strictness is the FENCE's job, where a dropped line silently
# loses authored data; a body is a writer's paragraph and must stay one.)

# `= ` opens an author-only synopsis, never rendered to a player. The space is
# REQUIRED: `=$name font:...;color:...` is the line-style declaration (14 uses in
# the corpus), and `=` immediately followed by `$` must keep meaning that. No line
# in the corpus matches `^=\s`, so this costs no migration.
RE_SYNOPSIS = re.compile(r"^[ \t]*=(?=[ \t])[ \t]*(?P<text>.*?)[ \t\r]*$")

# `[[key]]` / `[[key|words]]` - an inline reference inside prose. Non-greedy and
# newline-free so an unclosed `[[` cannot swallow the rest of the document.
# The leading `!` (Obsidian's embed) is NOT consumed here: `RE_TRANSCLUDE` claims
# those first, and the negative lookbehind keeps this from also matching them.
RE_WIKILINK = re.compile(r"(?<!!)\[\[[ \t]*(?P<target>[^\]|\r\n]+?)[ \t]*"
                         r"(?:\|[ \t]*(?P<alias>[^\]\r\n]*?)[ \t]*)?\]\]")

# `![[key]]` on its own line - pull that record's body in here. A whole line by
# itself, deliberately: a transclusion is a BLOCK, and allowing it mid-sentence
# would mean splicing paragraphs into the middle of one.
RE_TRANSCLUDE = re.compile(r"^[ \t]*!\[\[[ \t]*(?P<target>[^\]|\r\n]+?)[ \t]*\]\][ \t\r]*$")


def amd_body_transclude(line):
    """The record a `![[key]]` line pulls in, or None."""
    m = RE_TRANSCLUDE.match(line or "")
    return m.group("target").strip() if m is not None else None

# A line-leading `//` comment. Shared so both readers agree on what a comment is.
RE_COMMENT = re.compile(r"^[ \t]*//")

# `@Ashfang` / `@Ashfang (comms)` - a character cue, Fountain's idea with an
# explicit sigil. Fountain detects a cue by ALL CAPS, which it can afford because
# screenplay prose is stylized; AMD bodies are arbitrary sci-fi prose and 12 record
# bodies already open with a field-shaped line (`COMMS: hail the freighter.`), so
# the cue is always `@`. It reads as mention syntax, which every writer knows.
RE_CUE = re.compile(r"^[ \t]*@(?P<key>[\w.\-]+)[ \t]*"
                    r"(?:\((?P<ext>[^)\r\n]*)\))?[ \t\r]*$")

# `(shaken)` on its own line - a delivery direction for the line beneath it.
RE_DIRECTION = re.compile(r"^[ \t]*\((?P<text>[^)\r\n]*)\)[ \t\r]*$")

# `> CUT TO:` - Fountain's transition, with its forcing character. A callout
# (`> [!NOTE]`) also opens with `>`, so a transition is `>` NOT followed by `[`.
RE_TRANSITION = re.compile(r"^[ \t]*>[ \t]*(?!\[)(?P<text>\S[^\r\n]*?)[ \t\r]*$")

# The bare forms a screenwriter writes without thinking about markup. A CLOSED set,
# checked by exact match - deliberately not an all-caps heuristic, which is the same
# trap that made ALL-CAPS character cues unusable here (`Cutscene: intro` is a fence
# line, `SCIENCE: scan her.` is prose, and neither may become structure by accident).
_BARE_TRANSITIONS = {
    "FADE IN:", "FADE OUT.", "FADE OUT:", "FADE TO BLACK.", "CUT TO:",
    "SMASH CUT TO:", "MATCH CUT TO:", "DISSOLVE TO:", "CUT TO BLACK.", "THE END",
}

# `> [!NOTE] Title` - an Obsidian callout, for in-fiction documents that want
# in-fiction document formatting.
RE_CALLOUT = re.compile(r"^[ \t]*>[ \t]*\[!(?P<kind>[A-Za-z]+)\][ \t]*"
                        r"(?P<title>[^\r\n]*?)[ \t\r]*$")
# A continuation line of a callout block: `>` and the rest of the paragraph.
RE_CALLOUT_BODY = re.compile(r"^[ \t]*>[ \t]?(?P<text>[^\r\n]*?)[ \t\r]*$")


def amd_body_transition(line):
    """The transition a body line names (`CUT TO:`), or None.

    Either Fountain's forced form (`> CUT TO:`) or one of the bare spellings every
    screenwriter already types. Returned uppercase so a renderer never has to care
    which was written."""
    text = (line or "").strip()
    if text.upper() in _BARE_TRANSITIONS:
        return text.upper()
    if RE_CALLOUT.match(line or ""):
        return None
    m = RE_TRANSITION.match(line or "")
    return m.group("text").strip().upper() if m is not None else None


def amd_body_synopsis(line):
    """The text of a `= ` synopsis line, or None when this is not one."""
    m = RE_SYNOPSIS.match(line or "")
    return m.group("text") if m is not None else None


def amd_wikilinks(line):
    """Every `[[target]]` / `[[target|words]]` in `line` as `(target, alias, start, end)`.

    Columns are 0-based into `line` and cover the whole `[[...]]` token, so a caller
    can both point at it (spans, diagnostics) and replace it (rendering)."""
    out = []
    for m in RE_WIKILINK.finditer(line or ""):
        target = (m.group("target") or "").strip()
        if target:
            out.append((target, (m.group("alias") or "").strip() or None,
                        m.start(), m.end()))
    return out


def amd_render_wikilinks(text, display_of=None):
    """Replace every `[[key]]` / `[[key|words]]` with what a PLAYER should read.

    `[[key|words]]` renders `words`. A bare `[[key]]` renders the target record's
    display text when `display_of(key)` finds one, and otherwise the key itself - so
    a draft that links ahead to a scene nobody has written yet still reads as a
    sentence instead of showing brackets. The linter reports the same unresolved
    target as `dangling-link`; rendering never fails on it."""
    def sub(m):
        target = (m.group("target") or "").strip()
        if not target:
            return m.group(0)
        alias = (m.group("alias") or "").strip()
        if alias:
            return alias
        if display_of is not None:
            shown = display_of(target)
            if shown:
                return str(shown)
        return target
    return RE_WIKILINK.sub(sub, text or "")


class BoneyardScanner:
    """Tracks `/* ... */` cut text - Fountain's boneyard.

    A writer cuts a scene far more often than a line, and wants it back next week.
    `//` handles a line; this handles a block, and it works INSIDE a fence as well
    as in a body because a cut scene usually takes its data with it - so it runs as
    a pre-pass, before the fence scanner sees anything.

    The opener must start a line (indent allowed) so a `/*` inside a sentence is
    still a sentence. Nothing is silently eaten: text after the closing `*/` on the
    same line is handed back as the surviving line, and an unclosed block at EOF is
    reported rather than swallowing the rest of the file."""

    def __init__(self):
        self.in_boneyard = False
        self.open_line = 0
        self.unterminated = False

    def feed(self, line, lineno=0):
        """Classify one raw line -> `(dropped, surviving_text)`.

        `dropped` True means the line is entirely commented out. Otherwise
        `surviving_text` is the line to go on processing - normally the line
        itself, or its tail when a `*/` ended a block partway through."""
        if self.in_boneyard:
            pos = line.find("*/")
            if pos < 0:
                return True, None
            self.in_boneyard = False
            rest = line[pos + 2:]
            return (True, None) if not rest.strip() else (False, rest)
        if not line.lstrip().startswith("/*"):
            return False, line
        pos = line.find("*/", line.find("/*") + 2)
        if pos < 0:
            self.in_boneyard = True
            self.open_line = lineno
            return True, None
        rest = line[pos + 2:]
        return (True, None) if not rest.strip() else (False, rest)

    def finish(self):
        """Call at EOF. True when a block was left open."""
        self.unterminated = self.in_boneyard
        return self.unterminated


class FenceScanner:
    """Tracks whether we are inside a `---` data block, WITHOUT toggling.

    A `---` used to flip a boolean, so one stray rule inverted data-and-body for the
    rest of the file. The rules now:

      * `---` OPENS only immediately after a heading (or at the very top of the file,
        which is the document-level fence)
      * `---` CLOSES only while a block is open
      * a heading always closes an open block
      * anywhere else `---` is just prose

    `unterminated` reports a block still open at EOF, so the caller can say so."""

    def __init__(self):
        self.in_data = False
        self._can_open = True      # doc start: a leading fence is front matter
        self.unterminated = False
        self.open_line = 0

    def feed(self, line, lineno=0):
        """Classify one line: 'open' | 'close' | 'data' | 'heading' | 'body'."""
        if RE_FENCE.match(line):
            if self.in_data:
                self.in_data = False
                self._can_open = False
                return "close"
            if self._can_open:
                self.in_data = True
                self.open_line = lineno
                return "open"
            return "body"          # a horizontal rule in prose
        if self.in_data:
            return "data"
        if RE_HEADING.match(line):
            self._can_open = True
            return "heading"
        # A comment or an author-only synopsis may sit between a heading and its
        # fence without closing the window - both are things a writer puts THERE,
        # right under the title, and neither is content. Nothing else survives:
        # one line of real prose still means the `---` below it is a rule, not a
        # fence. (Zero files in the corpus put either between a heading and a
        # fence today, so this opens a door without moving anything through it.)
        if line.strip() and not RE_COMMENT.match(line) and RE_SYNOPSIS.match(line) is None:
            self._can_open = False
        return "body"

    def finish(self):
        """Call at EOF. True when a block was left open."""
        self.unterminated = self.in_data
        return self.unterminated


# --- value-coercion primitives ---------------------------------------------
# Every collection grammar below starts with `str(s)`, so handing one its OWN output
# is silent corruption rather than an error: `amd_counted({'salvage': 5})` stringifies
# the dict and comma-splits it back into `{"{'salvage':": 1}` -- a plausible-looking
# dict of garbage keys. That is easy to hit now that a declared field type (amd_schema's
# `counted`/`kv`/...) already coerces on the way out of the reader, so a loader that
# also parses is parsing twice. Each grammar passes an already-parsed value through.
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


_COMPACT_DURATION = re.compile(r"^(\d+)\s*([a-zA-Z]*)$")


def amd_duration_parts(value):
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
    unrecognized suffix still falls through to minutes, as before.
    """
    text = str(value)
    num = next((int(t) for t in text.split() if t.isdigit()), None)
    unit = "seconds" if "second" in text.lower() else "minutes"
    if num is not None:
        return num, unit
    for token in text.split():
        m = _COMPACT_DURATION.match(token)
        if m is None:
            continue
        num = int(m.group(1))
        suffix = m.group(2).lower()
        if suffix.startswith("s"):
            unit = "seconds"
        elif suffix.startswith("h"):
            num *= 60           # hours are minutes; `2h` must not read as 2 minutes
            unit = "minutes"
        return num, unit
    return None, unit


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
    if isinstance(s, (list, tuple)):
        return [str(x).strip() for x in s if str(x).strip()]
    return [x.strip() for x in str(s).split(",") if x.strip()]


def amd_weighted(s):
    """'by-the-book 40, fearsome 30' -> {by_the_book: 40, fearsome: 30}
    (trailing integer is the weight; a bare name gets weight 0)."""
    if isinstance(s, dict):
        return dict(s)
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
    if isinstance(s, dict):
        return dict(s)
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
    if isinstance(s, (list, tuple)):
        return [int(x) for x in s][:n]
    return [int(x) for x in str(s).replace(",", " ").split()
            if x.lstrip("-").isdigit()][:n]


def amd_counted(s):
    """'bio_sample x1, salvage x5' -> {'bio_sample': 1, 'salvage': 5}; a bare key -> 1.

    The shopping-list shape an author writes for costs and contents. Promoted here from
    LegendaryMissions' `recipes.py:_parse_inputs` so the fabrication recipe fence reads
    through the SAME declared type as everything else, instead of a private loader."""
    if isinstance(s, dict):
        return dict(s)
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


def amd_drop_table(s):
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
    parsing twice is harmless.
    """
    if isinstance(s, (list, tuple)) and all(isinstance(e, dict) for e in s):
        return [dict(e) for e in s]
    text = str(s or "").strip()
    if not text or text.lower() in ("none", "nothing", "-"):
        return []
    out = []
    for part in amd_list(text):
        key = None
        low = high = 1
        chance = 1.0
        for tok in part.split():
            if tok.endswith("%"):
                try:
                    chance = max(0.0, min(1.0, float(tok[:-1]) / 100.0))
                except ValueError:
                    pass
            elif tok.lower().startswith("x") and len(tok) > 1:
                span = tok[1:]
                lo, _, hi = span.partition("-")
                try:
                    low = int(lo)
                    high = int(hi) if hi else low
                except ValueError:
                    low = high = 1
            elif key is None:
                key = tok
        if key:
            out.append({"key": key, "low": min(low, high), "high": max(low, high),
                        "chance": chance})
    return out


def amd_drop_keys(s):
    """Just the item keys a drop table names, in written order - what a reference
    extractor and a linter need, without the counts."""
    return [e["key"] for e in amd_drop_table(s)]


def amd_kv(s):
    """'kind=bio, range=medium' -> {'kind': 'bio', 'range': 'medium'}.

    Promoted from `recipes.py:_parse_program`. Parts without an `=` are skipped."""
    if isinstance(s, dict):
        return dict(s)
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
    """Record a parse problem in a WRITER's terms.

    `errors` may be a plain list (messages, for a caller that just wants to print
    them) or an `AmdErrors` (which also keeps the line, so the linter and the editor
    can put a squiggle on it)."""
    if errors is None:
        return
    if isinstance(errors, AmdErrors):
        errors.add(lineno, message)
    else:
        errors.append(f"line {lineno}: {message}")


class AmdErrors(list):
    """Collected parse problems that remember WHERE they were.

    Behaves as a list of `"line N: message"` strings (so existing callers are
    unaffected), while `.items` keeps `(line, message)` pairs. `line_offset` maps
    the fence-relative line the parser sees onto the real file line - without it a
    diagnostic would point at line 3 of the block instead of line 147 of the file."""

    def __init__(self, line_offset=0):
        super().__init__()
        self.items = []
        self.line_offset = line_offset

    def add(self, lineno, message):
        line = lineno + self.line_offset
        self.items.append((line, message))
        self.append(f"line {line}: {message}")


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
