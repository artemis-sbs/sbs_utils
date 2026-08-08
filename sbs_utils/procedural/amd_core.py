"""A position-tracking AMD parser - the shared model behind AMD tooling.

`procedural.quest._document_get_amd_file` builds the runtime quest tree but throws
away source positions, so downstream tools (the linter, and a future language
server / formatter) can't point at *where* something is. `amd_core.parse` is a
backward-compatible superset: it produces the same heading tree plus a **span**
`(line, col)-(line, col)` for every node and every reference it carries, and a
flat reference list ready for resolution.

Positions are 1-based line, 0-based column (character offset), end-exclusive -
the shape editors and LSP want (subtract 1 from the line for LSP).

Dependency-light: `re` + `load_yaml_string` (for `---` fences). Content-agnostic -
it knows the generic AMD grammar (headings, fences, choices, the reference-bearing
metadata verbs) but not what any domain *means*; callers resolve keys/signals.
"""
import re

from sbs_utils.procedural.amd import (amd_parse_facts, amd_kind_line, KIND_KEY,
                                      FenceScanner, RE_HEADING, RE_FENCE, AmdErrors,
                                      BoneyardScanner, amd_body_synopsis, amd_wikilinks,
                                      RE_CUE, RE_DIRECTION, amd_norm)

# Grammar - ONE definition, imported from `amd` and shared with the runtime reader
# in quest.py. These aliases keep the existing local names working.
_RE_SECTION = RE_HEADING
_RE_DATA_FENCE = RE_FENCE
_RE_CHOICE = re.compile(r"^(?P<pre>\s*-\s*\[(?P<label>[^\]]*)\]\()(?P<target>[^)]*)\)(?P<rest>.*)$")
_RE_SIGNAL = re.compile(r"\bsignal\s+(?P<name>[A-Za-z0-9_]+)")

# Reference-bearing metadata verbs, keyed by the fence label they live under.
_REF_KINDS = ("scene", "parent", "reveal", "signal", "reach", "at")


class Span:
    """A source range: 1-based lines, 0-based columns, end-exclusive."""
    __slots__ = ("line", "col", "end_line", "end_col")

    def __init__(self, line, col, end_line=None, end_col=None):
        self.line = line
        self.col = col
        self.end_line = end_line if end_line is not None else line
        self.end_col = end_col if end_col is not None else col

    def __repr__(self):
        return f"Span({self.line}:{self.col}-{self.end_line}:{self.end_col})"


class AmdRef:
    """A reference occurrence: `kind` names what it points at; `value` is the raw
    target; `span` locates the target token; `owner` is the enclosing node key."""
    __slots__ = ("kind", "value", "span", "owner")

    def __init__(self, kind, value, span, owner):
        self.kind = kind
        self.value = value
        self.span = span
        self.owner = owner

    def __repr__(self):
        return f"AmdRef({self.kind!r}, {self.value!r}, {self.span}, owner={self.owner!r})"


class AmdNode:
    """A heading and its contents. `span` covers the heading line; `data` is the
    merged `---` fence dict; `refs` are references sourced from this node."""
    __slots__ = ("key", "display", "level", "span", "key_span", "display_span",
                 "query", "data", "children", "parent", "refs", "summary",
                 "fence_lines", "body_lines", "body_start", "kind", "synopsis",
                 "synopsis_span")

    def __init__(self, key, display, level, span=None, parent=None):
        self.key = key
        self.display = display
        self.level = level
        self.span = span            # the whole heading line
        self.key_span = None        # just the `key` token inside `](key)`
        self.display_span = None    # just the display text inside `[...]`
        self.query = {}
        self.data = {}
        self.children = []
        self.parent = parent
        self.refs = []
        self.summary = ""           # first prose body line, for hover
        self.fence_lines = []       # (lineno, raw) of the `---` metadata content
        self.body_lines = []        # (lineno, raw) of the prose/choice body
        self.body_start = 0         # 0-based line where the body begins
        self.kind = None            # resolved archetype (own kind line, else inherited)
        self.synopsis = ""          # `= ` author-only note; NEVER shown to a player
        self.synopsis_span = None


class AmdDocument:
    """Parsed model + the index the reference passes need."""
    def __init__(self, root, nodes, refs, line_count=0):
        self.root = root
        self.nodes = nodes            # every node except the synthetic root
        self.refs = refs              # every AmdRef, document order
        self.line_count = line_count  # source line count (for end-of-file inserts)
        self.keys = {n.key for n in nodes}
        # `by_key` keeps ONE node per key, for the many callers that just want a
        # lookup. It is lossy when a key repeats - use `nodes_for` / `by_path` when
        # that matters, and `duplicates` to find out whether it does.
        self.by_key = {n.key: n for n in nodes}
        self._by_key_all = {}
        for n in nodes:
            self._by_key_all.setdefault(n.key, []).append(n)
        self.duplicates = {k: v for k, v in self._by_key_all.items() if len(v) > 1}
        self.by_path = {path_of(n): n for n in nodes}
        # Kept for compatibility. It is FLAT and therefore last-wins when a key
        # repeats, which is exactly why path resolution no longer consults it.
        self.parent_of = {n.key: (n.parent.key if n.parent and n.parent.key != "__root__" else None)
                          for n in nodes}
        # `Aka:` - other names a record answers to. Indexed beside the real keys so
        # a reference written before a rename still finds its target, and an
        # a2x-generated key can be given a human name without breaking anything that
        # already points at it. A real key ALWAYS wins: an alias is a fallback, never
        # a way to shadow another record.
        self.aliases = {}
        for n in nodes:
            for alias in _node_aliases(n):
                if alias and alias not in self.keys:
                    self.aliases.setdefault(alias, []).append(n)
        self.landmark_cells = {r.value for r in refs if r.kind == "at"}
        self.errors = []      # (line, message) fence parse problems

    def nodes_for(self, key):
        """Every node carrying `key` - 40 of the corpus's 374 keys repeat, and three
        of those repeat WITHIN one file."""
        return list(self._by_key_all.get(key, ()))

    def path_resolves(self, path):
        """True when `path` names a real chain in the tree.

        Walks actual parent pointers. It used to consult the flat `parent_of` map,
        which keeps only the LAST node for a repeated key - so the correctly-written
        `florbin/recover` in peacetime_remastered.amd resolved to nothing, and it was
        the only reference `sbs lint` complained about in the whole file."""
        return self._match_path([s for s in str(path).split("/") if s]) is not None

    def _match_path(self, segs):
        """The node a segment chain names, or None. Ambiguity is impossible here:
        a full chain of keys is unique even when the leaf key is not."""
        if not segs:
            return None
        found = []
        for node in self._by_key_all.get(segs[-1], ()):
            n, ok = node, True
            for want in reversed(segs[:-1]):
                n = n.parent
                while n is not None and n.key != want and n.key != "__root__":
                    n = n.parent           # allow skipping intermediate levels
                if n is None or n.key != want:
                    ok = False
                    break
            if ok:
                found.append(node)
        return found[0] if len(found) == 1 else None

    def resolve_target(self, value, from_node=None):
        """The node a reference points at, or None.

        A slash path names a chain. A BARE key resolves RELATIVELY when `from_node`
        is given - nearest scope first: the referring node's own subtree, then each
        ancestor's, then the document. That matches what authors already write
        (`recover` and `scan` are step names reused inside several jobs) and mirrors
        MAST's `---inline` label scoping. Without `from_node` it is a document-wide
        lookup, which returns None rather than guessing when the key is ambiguous."""
        segs = [s for s in str(value).split("/") if s]
        if not segs:
            return None
        if len(segs) > 1:
            return self._match_path(segs)
        key = segs[0]
        candidates = self._by_key_all.get(key, ())
        if not candidates:
            # Only now consider `Aka:` names, so a real key can never be shadowed.
            candidates = self.aliases.get(amd_norm(key), ())
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        if from_node is not None:
            scope = from_node
            while scope is not None:
                inside = [c for c in candidates if _is_within(c, scope)]
                if len(inside) == 1:
                    return inside[0]
                if len(inside) > 1:
                    return None            # ambiguous even in the nearest scope
                scope = scope.parent
        return None                        # ambiguous document-wide: say so, don't guess

    def is_ambiguous(self, value):
        """True when a BARE key names more than one node (a path never is)."""
        segs = [s for s in str(value).split("/") if s]
        return len(segs) == 1 and len(self._by_key_all.get(segs[0], ())) > 1


# --- shared queries over the parsed tree ------------------------------------
def span_range(span):
    """An amd_core Span -> an LSP Range dict (0-based lines, end-exclusive).

    Lives with `Span` so the one place that defines the 1-based convention also
    defines the conversion off it - the language server and the story-flow analysis
    both emit this shape into the same payloads."""
    return {"start": {"line": span.line - 1, "character": span.col},
            "end": {"line": span.end_line - 1, "character": span.end_col}}


def path_of(node):
    """A node's full slash path from the document root (`florbin/recover`).

    This is the unambiguous name for a record. Bare keys are not unique - 40 of the
    corpus's 374 keys repeat - so anything that needs to identify a node exactly
    (an index, a rename, a cross-file reference) should use the path."""
    parts = []
    n = node
    while n is not None and n.key and n.key != "__root__":
        parts.append(n.key)
        n = n.parent
    return "/".join(reversed(parts))


def _node_aliases(node):
    """The `Aka:` names a node answers to, normalized. Tolerant of the shape the
    fence reader produced - a csv field may arrive as a list or as one string."""
    raw = (node.data or {}).get("aka")
    if not raw:
        return ()
    parts = raw if isinstance(raw, (list, tuple)) else str(raw).split(",")
    return tuple(amd_norm(p) for p in parts if str(p).strip())


def _is_within(node, scope):
    """True when `node` is `scope` or sits underneath it."""
    n = node
    while n is not None:
        if n is scope:
            return True
        n = n.parent
    return False


def section_of(node):
    """The `##` section group a record lives under.

    A pure walk over the parent pointers this module builds, so it belongs here rather
    than being re-derived by each consumer - the language server, the linter and the
    story-flow analysis all group by it and must agree."""
    n = node
    while n.parent is not None and n.parent.key != "__root__" and n.level > 2:
        n = n.parent
    return n.key


# --- helpers ----------------------------------------------------------------
def _di(data, *names):
    """First-present fetch from a fence data dict, tolerant of the fact reader's
    key normalization (lowercase, spaces -> underscores)."""
    lower = {str(k).lower(): v for k, v in data.items()}
    for n in names:
        key = n.lower()
        if key in lower:
            return lower[key]
        if key.replace(" ", "_") in lower:
            return lower[key.replace(" ", "_")]
    return None


def _coords(value, n=2):
    """The first `n` integers of a cell reference.

    Accepts the AUTHORED text (`6, 4`) or an already-typed sequence - the field
    registry now coerces `At:`/`Center:` to a list of ints before this sees them, and
    `str([6, 4])` does not re-parse (the brackets stop the digit test)."""
    if isinstance(value, (list, tuple)):
        toks = [int(t) for t in value if isinstance(t, int) or str(t).lstrip("-").isdigit()]
    else:
        toks = [int(t) for t in str(value).replace(",", " ").split()
                if t.lstrip("-").isdigit()]
    return tuple(toks[:n]) if len(toks) >= n else None


def _kv_value_col(raw, key):
    """0-based column where `key:`'s value begins on line `raw`, or None."""
    p = raw.lower().find(key.lower() + ":")
    if p < 0:
        return None
    c = p + len(key) + 1
    while c < len(raw) and raw[c] in " \t":
        c += 1
    return c


def _token_span(fence_lines, key, token, owner_key, kind):
    """Locate `token` on the `key:` line within a fence block; return an AmdRef."""
    for lineno, raw in fence_lines:
        base = _kv_value_col(raw, key)
        if base is None:
            continue
        col = raw.find(token, base)
        if col < 0:
            col = base
        return AmdRef(kind, token, Span(lineno, col, lineno, col + len(str(token))), owner_key)
    return None


def _token_spans(fence_lines, key, tokens, owner_key, kind):
    """Locate every token in order on the `key:` line; one AmdRef each.

    A cursor walks forward so a word written twice (`salvage x1, salvage 10%`) lands on
    its own occurrence instead of every ref pointing at the first one."""
    out = []
    for lineno, raw in fence_lines:
        base = _kv_value_col(raw, key)
        if base is None:
            continue
        cursor = base
        for token in tokens:
            col = raw.find(token, cursor)
            if col < 0:
                col = base
            else:
                cursor = col + len(token)
            out.append(AmdRef(kind, token, Span(lineno, col, lineno, col + len(token)),
                              owner_key))
        return out
    return out


def _extract_data_refs(node, fence_lines):
    """Pull reference-bearing verbs out of a node's fence block (with spans)."""
    data = node.data
    key = node.key

    scene = _di(data, "Scene")
    if scene:
        r = _token_span(fence_lines, "Scene", str(scene).strip(), key, "scene")
        if r:
            node.refs.append(r)

    parent = _di(data, "Parent")
    if parent:
        r = _token_span(fence_lines, "Parent", str(parent).strip(), key, "parent")
        if r:
            node.refs.append(r)

    then = _di(data, "Then")
    if then:
        toks = str(then).split()
        verb = toks[0].lower() if toks else ""
        if verb == "reveal" and len(toks) >= 2:
            r = _token_span(fence_lines, "Then", toks[1], key, "reveal")
        elif verb == "signal" and len(toks) >= 2:
            r = _token_span(fence_lines, "Then", toks[1], key, "signal")
        elif verb not in ("reveal", "signal"):
            r = _token_span(fence_lines, "Then", str(then).strip(), key, "reveal")
        else:
            r = None
        if r:
            node.refs.append(r)

    when = _di(data, "When")
    if when:
        toks = str(when).split(None, 1)
        verb = toks[0].lower() if toks else ""
        if verb in ("reach", "travel") and len(toks) > 1:
            cell = _coords(toks[1])
            if cell:
                r = _token_span(fence_lines, "When", toks[1].strip(), key, "reach")
                if r:
                    r.value = cell
                    node.refs.append(r)
        elif verb == "signal" and len(toks) > 1:
            # class-2 quest trigger: waits for a SIGNAL_NAME emit of this name
            r = _token_span(fence_lines, "When", toks[1].strip(), key, "wait_signal")
            if r:
                node.refs.append(r)

    # `Goal: signal [N] NAME` is a COMPLETION trigger - semantically the same wait as
    # `When: signal`, so it carries the same ref kind (a goal signal nothing emits is a
    # job that can never be finished, and a job whose goal a MAST route emits is NOT an
    # orphan). The optional count (`signal 5 drone_down`) is stripped exactly as
    # `amd_quest.amd_trigger` strips it, so tooling and the engine read the same name.
    goal = _di(data, "Goal")
    if goal:
        toks = str(goal).split()
        if toks and toks[0].lower() == "signal":
            rest = toks[1:]
            if rest and rest[0].isdigit():
                rest = rest[1:]
            if rest:
                r = _token_span(fence_lines, "Goal", rest[0], key, "wait_signal")
                if r:
                    node.refs.append(r)

    fail = _di(data, "Fail on signal")
    if fail:
        r = _token_span(fence_lines, "Fail on signal", str(fail).strip(), key, "wait_signal")
        if r:
            node.refs.append(r)

    at = _di(data, "At")
    if at:
        cell = _coords(at)
        if cell:
            r = _token_span(fence_lines, "At", str(at).strip(), key, "at")
            if r:
                r.value = cell
                node.refs.append(r)

    # Region geometry - spans so a map view can drag/resize (value carried too).
    center = _di(data, "Center")
    if center is not None and _coords(center):
        r = _token_span(fence_lines, "Center", str(center).strip(), key, "center")
        if r:
            r.value = _coords(center)
            node.refs.append(r)
    radius = _di(data, "Radius")
    if radius is not None:
        r = _token_span(fence_lines, "Radius", str(radius).strip(), key, "radius")
        if r:
            node.refs.append(r)
    kind = _di(data, "Kind")
    if kind:
        r = _token_span(fence_lines, "Kind", str(kind).strip(), key, "kind")
        if r:
            node.refs.append(r)

    # WHO speaks for this record. Dialogue has always had its speaker checked, but only
    # through its cue LINES; the field itself named nobody, so a quest's `Speaker:` - the
    # voice its deadline reminders go out in - resolved to nothing and no tool could say
    # so. Same ref kind for both, because it is the same question.
    speaker = _di(data, "Speaker")
    if speaker:
        r = _token_span(fence_lines, "Speaker", str(speaker).strip(), key, "speaker")
        if r:
            node.refs.append(r)

    # `Drops: salvage x2-4, contraband 20%` - every key in the table names an ITEM. Without
    # refs a misspelled key is a table that silently yields nothing, which is the exact
    # failure `Drops:` exists to make visible. The grammar is shared with the runtime
    # reader (`amd.amd_drop_table`), so the linter and the loot cannot disagree about
    # which words are keys.
    drops = _di(data, "Drops")
    if drops:
        from sbs_utils.procedural.amd import amd_drop_keys
        node.refs.extend(_token_spans(fence_lines, "Drops", amd_drop_keys(drops),
                                      key, "drop"))


def _is_top_level(node):
    """True when nothing but the synthetic root is above this node - the flat-file shape
    (`jobs.amd`), where the record's own key is the only thing that can name its kind."""
    parent = node.parent
    while parent is not None:
        if parent.key and parent.key != "__root__":
            return False
        parent = parent.parent
    return True


def _resolve_node_kind(node, block):
    """The archetype for one node: its own kind line, then the NEAREST ancestor that
    answers, then the discriminating-field fallback.

    "Nearest wins" is the whole point, and it used to be only a promise. Kind lines were
    collected into one list and section names into another, and EVERY ancestor kind was
    tried before ANY section name - so a kind line on the document ROOT reached past every
    section beneath it. `silver_reach.amd` opens with `Universe` (-> map), which typed its
    `## Sides`, `## Regions`, `## Jobs` and `## Narrative` records as maps: 336 bogus
    unknown-field warnings across LM + OU + Storm's Beacon, and - because `node.kind`
    picks the coercion table - wrong VALUES, `Center: 5, -4` parsing as the string
    '5, -4' instead of [5, -4].

    Inheriting a kind downward is right for `## Characters` over its records. It is wrong
    for a root, whose kind line names the FILE and not its contents. So each ancestor is
    asked in turn, closest first, for its kind line OR its section name, and the first
    ancestor that answers wins. An explicit kind still beats a section NAME at the same
    distance - explicit beats convention, but only where it was written.
    """
    from sbs_utils.procedural.amd_schema import amd_resolve_kind_chain
    # One pair per ancestor, NEAREST FIRST, so a kind line and a section name compete at
    # the distance they were actually written at.
    ancestors = []
    parent = node.parent
    while parent is not None:
        key = parent.key if parent.key != "__root__" else None
        ancestors.append((getattr(parent, "kind", None), key))
        parent = parent.parent
    # Read the labels out of the RAW block: this runs BEFORE the fence is parsed
    # (the parse needs the kind to pick a table), so `node.data` is still empty and
    # the discriminating-field fallback would never fire.
    from sbs_utils.procedural.amd import amd_fact_lines
    labels = [lab for lab, _v in amd_fact_lines(block)]
    return amd_resolve_kind_chain(own_kind=amd_kind_line(block), ancestors=ancestors,
                                  field_labels=labels, own_section=node.key)


def _extract_choice_refs(node, lineno, raw):
    """A `- [label](target) ; ... signal X` line -> a choice-target ref plus any
    signal-outcome refs, each with an exact column span."""
    m = _RE_CHOICE.match(raw)
    if not m:
        return
    target = m.group("target").strip()
    if target:
        col = m.start("target")
        node.refs.append(AmdRef("choice", target, Span(lineno, col, lineno, col + len(target)), node.key))
    rest = m.group("rest") or ""
    base = m.start("rest")
    for sm in _RE_SIGNAL.finditer(rest):
        col = base + sm.start("name")
        name = sm.group("name")
        node.refs.append(AmdRef("signal", name, Span(lineno, col, lineno, col + len(name)), node.key))


def _extract_link_refs(node, lineno, raw):
    """`[[key]]` / `[[key|words]]` in prose -> ordinary `link` refs.

    Narrative text could not carry a reference before this: a record reached another
    only through a typed field (`Then: reveal`, `Scene:`, `Parent:`). Because these
    are plain `AmdRef`s, everything already built on refs - find-all-references,
    rename, the story graph, the timeline, the outline - picks them up with no
    further work. The span covers the WHOLE `[[...]]` token so a rename can rewrite
    it and a diagnostic can underline it."""
    for target, _alias, start, end in amd_wikilinks(raw):
        node.refs.append(AmdRef("link", target, Span(lineno, start, lineno, end), node.key))


def _extract_cue_refs(node, lineno, raw):
    """`@Ashfang` -> a `cue` ref pointing at the cast record that voices the line.

    Same treatment as every other reference, so go-to-definition on a cue lands on
    the character, rename follows it, and a cue naming nobody is reported instead of
    silently speaking as an unknown."""
    m = RE_CUE.match(raw)
    if m is None:
        return
    key = m.group("key")
    col = m.start("key")
    # The VALUE normalizes (record keys are slugs, so `@Ashfang` and `@ashfang` are
    # the same cast member) while the SPAN stays on the authored text, so a
    # diagnostic underlines what the writer actually typed.
    node.refs.append(AmdRef("cue", amd_norm(key),
                            Span(lineno, col, lineno, col + len(key)), node.key))


# --- parser -----------------------------------------------------------------
def parse(content, file_path=None):
    """Parse AMD `content` into an `AmdDocument` (tree + spans + references)."""
    if content is None and file_path is not None:
        with open(file_path, "r") as f:
            content = f.read()
    lines = (content or "").splitlines()

    root = AmdNode("__root__", "", 0)
    stack = [root]           # stack[i] == current node at level i
    nodes, refs = [], []

    scanner = FenceScanner()
    boneyard = BoneyardScanner()
    fence_lines = []
    errors = []          # (line, message) - fence problems, in a writer's terms

    for idx, raw in enumerate(lines, start=1):
        # Cut text first, before anything else can see it: `/* ... */` must be able
        # to take a whole record - heading, fence and body - out of the document.
        dropped, raw = boneyard.feed(raw, idx)
        if dropped:
            continue
        action = scanner.feed(raw, idx)
        if action == "open":
            fence_lines = []
            continue
        if action == "data":
            fence_lines.append((idx, raw))
            continue
        if action == "close":
            node = stack[-1]
            block = "\n".join(t for _, t in fence_lines)
            # Resolve WHAT KIND of record this is before reading its fields, so the
            # registry coerces by the right table. Nearest-first ancestors, then the
            # section name, then the discriminating-field fallback.
            node.kind = _resolve_node_kind(node, block)
            # Collect the reader's writer-facing complaints WITH their real file
            # lines, so the linter and the editor can put a squiggle on them. The
            # parser numbers lines within the block, so offset by the line the
            # block's first content sits on.
            block_errors = AmdErrors(line_offset=(fence_lines[0][0] - 1) if fence_lines else 0)
            try:
                parsed = amd_parse_facts(block, archetype=node.kind, errors=block_errors)
            except Exception:
                parsed = None
            errors.extend(block_errors.items)
            if isinstance(parsed, dict):
                node.data.update(parsed)
                _extract_data_refs(node, fence_lines)
            node.fence_lines = list(fence_lines)
            node.body_start = idx           # 0-based line after the closing ---
            fence_lines = []
            continue

        m = _RE_SECTION.match(raw) if action == "heading" else None
        if m:
            level = len(m.group("hashes"))
            urn = m.group("urn").split("?", 1)
            node = AmdNode(urn[0], m.group("display"), level,
                           span=Span(idx, 0, idx, len(raw)))
            ustart = m.start("urn")
            node.key_span = Span(idx, ustart, idx, ustart + len(urn[0]))
            dstart = m.start("display")
            node.display_span = Span(idx, dstart, idx, dstart + len(m.group("display")))
            node.body_start = idx           # 0-based line after the heading
            if len(urn) == 2:
                for kv in urn[1].split("&"):
                    kv = kv.split("=")
                    if len(kv) == 2:
                        node.query[kv[0]] = kv[1]
            while len(stack) > level:
                stack.pop()
            node.parent = stack[-1]
            stack[-1].children.append(node)
            stack.append(node)
            nodes.append(node)
            continue

        if raw.strip().startswith("//"):
            continue

        node = stack[-1]

        # `= ` synopsis: the author's note about what this beat is FOR. It is not
        # body text - keeping it out of `body_lines` is what keeps it out of every
        # renderer, and keeping it out of `summary` is what stops a synopsized
        # record from showing the author's private note as its description.
        syn = amd_body_synopsis(raw)
        if syn is not None:
            if node.synopsis:
                node.synopsis += " " + syn
            else:
                node.synopsis = syn
                col = raw.find("=")
                node.synopsis_span = Span(idx, col, idx, len(raw.rstrip()))
            continue

        # body line of the current node - scan for choice/signal/link references
        node.body_lines.append((idx, raw))
        _extract_choice_refs(node, idx, raw)
        _extract_link_refs(node, idx, raw)
        _extract_cue_refs(node, idx, raw)
        stripped = raw.strip()
        # `summary` is what hover and the outline show, so it wants the first line of
        # PROSE - not the scaffolding around it. A choice, a cue and a direction are
        # all structure, and a scene that opens `@Ashfang` should summarize as what
        # Ashfang says, not as the word "@Ashfang".
        if (stripped and not node.summary and not stripped.startswith("- [")
                and RE_CUE.match(raw) is None and RE_DIRECTION.match(raw) is None):
            node.summary = stripped

    # Collect refs in document order (data refs were attached per-node above).
    for n in nodes:
        refs.extend(n.refs)
    refs.sort(key=lambda r: (r.span.line, r.span.col))
    if scanner.finish():
        errors.append((scanner.open_line,
                       'this --- was never closed, so the rest of the file is being read as data'))
    if boneyard.finish():
        errors.append((boneyard.open_line,
                       'this /* was never closed, so the rest of the file is cut out of the document'))
    doc = AmdDocument(root, nodes, refs, line_count=len(lines))
    doc.errors = errors
    return doc
