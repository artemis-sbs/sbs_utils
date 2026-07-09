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

from sbs_utils.procedural.amd import amd_parse_facts

# Grammar - kept in agreement with quest.py `_document_get_amd_file`.
_RE_SECTION = re.compile(r"(?P<hashes>#+)[ \t]+\[(?P<display>.*)\]\((?P<urn>.*)\)[ \t]*")
_RE_DATA_FENCE = re.compile(r"\s*-{3,}\s*$")
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
    __slots__ = ("key", "display", "level", "span", "key_span", "query", "data",
                 "children", "parent", "refs", "summary")

    def __init__(self, key, display, level, span=None, parent=None):
        self.key = key
        self.display = display
        self.level = level
        self.span = span            # the whole heading line
        self.key_span = None        # just the `key` token inside `](key)`
        self.query = {}
        self.data = {}
        self.children = []
        self.parent = parent
        self.refs = []
        self.summary = ""      # first prose body line, for hover


class AmdDocument:
    """Parsed model + the index the reference passes need."""
    def __init__(self, root, nodes, refs, line_count=0):
        self.root = root
        self.nodes = nodes            # every node except the synthetic root
        self.refs = refs              # every AmdRef, document order
        self.line_count = line_count  # source line count (for end-of-file inserts)
        self.keys = {n.key for n in nodes}
        self.by_key = {n.key: n for n in nodes}
        self.parent_of = {n.key: (n.parent.key if n.parent and n.parent.key != "__root__" else None)
                          for n in nodes}
        self.landmark_cells = {r.value for r in refs if r.kind == "at"}

    def path_resolves(self, path):
        """A slash path resolves iff every segment is a known key and each
        segment's parent is the preceding segment; a bare key iff it exists."""
        segs = [s for s in str(path).split("/") if s]
        if not segs:
            return True
        if any(s not in self.keys for s in segs):
            return False
        return all(self.parent_of.get(b) == a for a, b in zip(segs, segs[1:]))

    def resolve_target(self, value):
        """The AmdNode a reference points at (bare key or `a/b/c` path), or None."""
        segs = [s for s in str(value).split("/") if s]
        if not segs:
            return None
        if len(segs) == 1:
            return self.by_key.get(segs[0])
        return self.by_key.get(segs[-1]) if self.path_resolves(value) else None


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
    toks = [int(t) for t in str(value).replace(",", " ").split() if t.lstrip("-").isdigit()]
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

    in_data = False
    fence_lines = []

    for idx, raw in enumerate(lines, start=1):
        if _RE_DATA_FENCE.match(raw):
            if in_data:
                block = "\n".join(t for _, t in fence_lines)
                try:
                    # The friendly AMD fact reader: YAML for flow (`{`/`[`), else a
                    # `Label: value` sheet - so `Color: #86c` keeps its value (raw
                    # YAML would read `#86c` as a comment).
                    parsed = amd_parse_facts(block)
                except Exception:
                    parsed = None
                if isinstance(parsed, dict):
                    stack[-1].data.update(parsed)
                    _extract_data_refs(stack[-1], fence_lines)
                in_data = False
                fence_lines = []
            else:
                in_data = True
                fence_lines = []
            continue
        if in_data:
            fence_lines.append((idx, raw))
            continue

        m = _RE_SECTION.match(raw)
        if m:
            level = len(m.group("hashes"))
            urn = m.group("urn").split("?", 1)
            node = AmdNode(urn[0], m.group("display"), level,
                           span=Span(idx, 0, idx, len(raw)))
            ustart = m.start("urn")
            node.key_span = Span(idx, ustart, idx, ustart + len(urn[0]))
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

        # body line of the current node - scan for choice/signal references
        node = stack[-1]
        _extract_choice_refs(node, idx, raw)
        stripped = raw.strip()
        if stripped and not node.summary and not stripped.startswith("- ["):
            node.summary = stripped

    # Collect refs in document order (data refs were attached per-node above).
    for n in nodes:
        refs.extend(n.refs)
    refs.sort(key=lambda r: (r.span.line, r.span.col))
    return AmdDocument(root, nodes, refs, line_count=len(lines))
