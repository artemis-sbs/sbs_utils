"""AMD validator / linter - makes the silent AMD failure modes loud.

`procedural.quest._document_get_amd_file` builds its tree by treating any line
that is not a link-form heading, a `//` comment, or inside a `---` data fence as
DESCRIPTION text. That is convenient for prose but means a *broken* structural
heading (a typo'd `# [Display](key)`) silently becomes body text - the node it
was meant to create simply vanishes, with no error. This module re-scans the
source and the parsed tree to surface that class of failure, plus dangling
intra-document references, and (via a pluggable schema) cross-file references
such as an emitted `signal X` with no `//signal/X` route.

Layers, cheapest/most-generic first:
  * Phase 1 - structural (source-level, generic): broken headings, unclosed data
    fences, illegal heading-level jumps. See `amd_lint_structural`.
  * Phase 2 - reference integrity (tree-level, generic + schema): choice targets
    and quest `reveal`/`also` paths that resolve to no node. See
    `amd_lint_references`.
  * Phase 3 - cross-file (mission-shaped, schema): emitted signals vs `//signal/`
    routes, `reach i,j` cells vs landmark `At:`. See `amd_lint_cross_file`.

Severity policy (what `--test` should gate on): STRUCTURAL findings are ERRORs
(hard-fail); reference/cross-file findings default to WARNING. Callers decide how
to act on the returned list.

Dependency-light: the structural pass needs only the standard library, so it is
unit-testable outside the engine. The tree passes reuse the same parser the
engine uses (`document_get_amd_file`).
"""
import re

ERROR = "error"
WARNING = "warning"

# Mirror the parser's own patterns (procedural/quest.py `_document_get_amd_file`)
# so the linter agrees with it exactly on what IS a heading / a fence.
_RE_SECTION = re.compile(r"#+[ \t]+\[(?P<display_text>.*)\]\((?P<urn>.*)\)[ \t]*")
_RE_HEADING_ATTEMPT = re.compile(r"#+[ \t]+\S")
_RE_DATA_FENCE = re.compile(r"\s*-{3,}\s*$")


class AmdFinding:
    """One linter result. `line` is 1-based (0 when file-global); `col`/`end_line`/
    `end_col` (0-based columns, end-exclusive) locate a precise range when known."""
    __slots__ = ("line", "severity", "code", "message", "col", "end_line", "end_col")

    def __init__(self, line, severity, code, message, col=None, end_line=None, end_col=None):
        self.line = line
        self.severity = severity
        self.code = code
        self.message = message
        self.col = col
        self.end_line = end_line
        self.end_col = end_col

    @classmethod
    def at(cls, span, severity, code, message):
        """Build a finding anchored to an `amd_core.Span`."""
        return cls(span.line, severity, code, message,
                   col=span.col, end_line=span.end_line, end_col=span.end_col)

    def is_error(self):
        return self.severity == ERROR

    def to_dict(self, file=None):
        """Serializable form (1-based line, 0-based col, end-exclusive). Consumers
        building LSP diagnostics subtract 1 from `line`."""
        d = {"line": self.line, "severity": self.severity,
             "code": self.code, "message": self.message}
        if self.col is not None:
            d["col"] = self.col
        if self.end_line is not None:
            d["endLine"] = self.end_line
        if self.end_col is not None:
            d["endCol"] = self.end_col
        if file is not None:
            d["file"] = file
        return d

    def compact(self, file="<amd>"):
        """`file:line:col: severity: message [code]` - one line, for editor
        problem-matchers (columns emitted 1-based)."""
        col = (self.col + 1) if self.col is not None else 1
        return f"{file}:{self.line}:{col}: {self.severity}: {self.message} [{self.code}]"

    def __repr__(self):
        return f"AmdFinding({self.line}, {self.severity!r}, {self.code!r}, {self.message!r})"

    def __str__(self):
        if not self.line:
            where = "file"
        elif self.col is not None:
            where = f"line {self.line}:{self.col}"
        else:
            where = f"line {self.line}"
        return f"[{self.severity.upper()}] {where}: {self.message} ({self.code})"


def _source_lines(file_path=None, content=None):
    """Return source as a list of lines (no trailing newline), from content or file."""
    if content is None and file_path is not None:
        with open(file_path, "r") as f:
            content = f.read()
    return (content or "").splitlines()


# --- Phase 1: structural (source-level, generic) ----------------------------
def amd_lint_structural(file_path=None, content=None):
    """Scan raw source for the silent structural failures. Returns [AmdFinding].

    Checks:
      * broken structural heading - a `#`-led line carrying a malformed link
        boundary `](` (or bracket pair) that the parser will NOT recognize as a
        heading, so it vanishes into the parent's description. A plain prose
        heading (`## Objective`, no brackets) is NOT flagged.
      * unclosed `---` data fence - an odd number of fence lines leaves the tail
        of the file silently swallowed as (unparsed) data.
      * heading-level jump - a heading that dives more than one level below the
        current depth (the parser raises a bare `Document structure error`; we
        report it with the line and a hint).
    """
    lines = _source_lines(file_path, content)
    findings = []

    in_data = False
    data_open_line = 0
    depth = 0  # current heading depth (root = 0)

    for i, line in enumerate(lines, start=1):
        if _RE_DATA_FENCE.match(line):
            in_data = not in_data
            if in_data:
                data_open_line = i
            continue
        if in_data:
            continue

        if _RE_HEADING_ATTEMPT.match(line):
            if _RE_SECTION.match(line):
                # A valid link-form heading: track depth for jump detection.
                hashes = line.split(None, 1)[0]
                level = len(hashes)
                if level > depth + 1:
                    findings.append(AmdFinding(
                        i, ERROR, "heading-level-jump",
                        f"heading jumps from level {depth} to {level}; add the "
                        f"missing intermediate level(s) or the parser will error"))
                depth = level
                continue
            # A `#`-led line the parser will NOT treat as a heading.
            if "](" in line:
                findings.append(AmdFinding(
                    i, ERROR, "broken-heading",
                    "looks like a link-form heading but the `[Display](key)` is "
                    "malformed; it will silently become body text and the node "
                    "will vanish"))
            elif "[" in line and "]" in line:
                findings.append(AmdFinding(
                    i, WARNING, "suspect-heading",
                    "a `#` heading with brackets but no `(key)` - if this was "
                    "meant to be a structural heading it needs `[Display](key)`; "
                    "if it's prose, ignore"))
            # else: a plain prose/body markdown heading - legitimate, no finding.

    if in_data:
        findings.append(AmdFinding(
            data_open_line, ERROR, "unclosed-data-fence",
            "a `---` data fence was opened but never closed; the rest of the "
            "file is swallowed as unparsed data"))

    return findings


# --- content safety: the engine renders ASCII only --------------------------
_RE_NONASCII = re.compile(r"[^\x00-\x7f]+")


def amd_lint_ascii(file_path=None, content=None):
    """Flag non-ASCII runs in author text - the engine renders ASCII only, so a
    pasted smart-quote / em-dash / emoji misrenders or crashes. `//` comment lines
    are exempt (not rendered). WARNING."""
    findings = []
    for i, line in enumerate(_source_lines(file_path, content), start=1):
        if line.lstrip().startswith("//"):
            continue
        for m in _RE_NONASCII.finditer(line):
            findings.append(AmdFinding(
                i, WARNING, "non-ascii",
                f"non-ASCII text {m.group()!r} - the engine renders ASCII only "
                f"(smart quotes / em-dashes / emoji misrender or crash)",
                col=m.start(), end_line=i, end_col=m.end()))
    return findings


# --- scan vocabulary: a typo'd tab is silently swallowed --------------------
# Standard science-scan tabs (mirror procedural.science SCIENCE_SCAN_TABS - kept local so
# this module stays stdlib-only). Only the dialogue-native `Scan of:` fence is a scan fence;
# there is no longer a flat-tab form to detect heuristically (a lone `Intel:` may be a rumor
# reveal or any other domain key, not a scan - so we never guess).
_SCAN_TABS = frozenset({"scan", "status", "intel", "mat", "bio"})
_RE_FENCE_LABEL = re.compile(r"^[ \t]*([A-Za-z][A-Za-z0-9 _]*?)[ \t]*:")


def _scan_fence_findings(fence):
    """Findings for one `---` fence's (lineno, label, value) list. A scan fence is the
    dialogue-native `Scan of:` form; warn if its `Tab:` value isn't a real scan tab (a typo
    like `Tab: scna` is silently swallowed and that scan never renders)."""
    labels = [lab for _, lab, _ in fence]
    if "scan of" not in labels and "scan_of" not in labels:
        return []   # not a scan fence
    out = []
    for lineno, lab, val in fence:
        if lab == "tab" and val.strip().lower() not in _SCAN_TABS:
            out.append(AmdFinding(
                lineno, WARNING, "unknown-scan-tab",
                f"`Tab: {val}` is not a known scan tab (scan/status/intel/mat/bio); "
                f"that scan will never render - likely a typo"))
    return out


def amd_lint_scan_labels(file_path=None, content=None):
    """In a `Scan of:` fence, warn on a `Tab:` that is not one of scan/status/intel/mat/bio -
    a typo (`Tab: scna`) is silently swallowed and that scan never renders, exactly the silent
    failure class the linter exists to surface. Quest / other fences are left alone."""
    lines = _source_lines(file_path, content)
    findings = []
    fence = None  # collecting (lineno, label, value) between --- fences, or None outside
    for i, line in enumerate(lines, start=1):
        if _RE_DATA_FENCE.match(line):
            if fence is None:
                fence = []
            else:
                findings += _scan_fence_findings(fence)
                fence = None
            continue
        if fence is not None:
            m = _RE_FENCE_LABEL.match(line)
            if m:
                value = line.split(":", 1)[1].strip() if ":" in line else ""
                fence.append((i, m.group(1).strip().lower(), value))
    return findings


# Engine / quest-driver signals that have built-in handlers - never flag these as
# "emitted with no route" (source: schema map, quest_driver.mast + engine routes).
DRIVER_SIGNALS = frozenset({
    "quest_activated", "quest_completed", "quest_failed", "quest_signal",
    "quest_finished", "game_over", "game_started", "show_game_results",
    "universe_arrived", "item_collected", "item_changed", "ship_docked",
    "quest_engage", "create_player_ships",
})


# --- Phase 2: reference integrity (model-level, exact spans) -----------------
def _resolves(doc, value, known_keys):
    """A bare key or `a/b/c` path resolves inside this doc, or (cross-file) its
    key/leaf is a known symbol elsewhere in the mission (another .amd node or a
    MAST label). Cross-file structure can't be verified from one file, so the leaf
    check is intentionally soft.

    A key that names SEVERAL nodes still counts as resolving here - it exists, it is
    just under-specified - so it is reported once by `amd_lint_keys` as ambiguous
    rather than twice, and never as "points at nothing"."""
    if "/" in value:
        return doc.path_resolves(value) or value.split("/")[-1] in known_keys
    return value in doc.keys or value in known_keys


def amd_lint_keys(doc):
    """Flag key collisions and the references made unresolvable by them.

    Nothing checked this before, and it matters: 40 of the corpus's 374 keys repeat,
    three of them WITHIN one file (`recover` x3, `scan` x3 in peacetime_remastered).
    Repeating a key is legitimate - short step names scoped to their job read well -
    so a duplicate is a note, not an error. What IS a problem is a BARE reference to
    a key that names several nodes, because nothing can tell which was meant.
    Answer: write the path (`florbin/recover`). WARNING."""
    from sbs_utils.procedural.amd_core import path_of
    findings = []
    for key, nodes in sorted(doc.duplicates.items()):
        where = ", ".join(path_of(n) for n in nodes)
        for n in nodes[1:]:
            findings.append(AmdFinding.at(
                n.key_span or n.span, WARNING, "duplicate-key",
                f"`{key}` names {len(nodes)} records ({where}) - reference them by "
                f"path, or rename so a bare `{key}` is unambiguous"))
    for ref in doc.refs:
        if ref.kind in ("scene", "parent", "reveal", "choice") and doc.is_ambiguous(ref.value):
            owner = doc.by_key.get(ref.owner)
            if doc.resolve_target(ref.value, from_node=owner) is None:
                paths = ", ".join(path_of(n) for n in doc.nodes_for(str(ref.value)))
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "ambiguous-reference",
                    f"`{ref.value}` could mean {paths} - say which by writing the path"))
    return findings


def amd_lint_references(doc, known_keys=frozenset()):
    """Flag intra-document references that resolve to no node: dialogue/comms choice
    `](target)`, lifeform `Scene:`, quest `Then: reveal <path>`, `Parent:`. Uses the
    `amd_core` model, so each finding carries the target's exact range. `known_keys`
    are symbols defined elsewhere in the mission (sibling .amd nodes + MAST labels),
    so a legitimate cross-file / MAST-label target is not flagged. WARNING."""
    findings = []
    for ref in doc.refs:
        if ref.kind == "scene":
            if not _resolves(doc, ref.value, known_keys):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-scene",
                    f"`{ref.owner}` Scene points at `{ref.value}`, which is not a defined node"))
        elif ref.kind == "parent":
            if not _resolves(doc, ref.value, known_keys):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-parent",
                    f"`{ref.owner}` Parent points at `{ref.value}`, which is not a defined node"))
        elif ref.kind == "reveal":
            if not _resolves(doc, ref.value, known_keys):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-reveal",
                    f"`{ref.owner}` Then reveals `{ref.value}`, which resolves to no node"))
        elif ref.kind == "choice":
            target = ref.value
            if not target or target.startswith("//"):
                continue  # empty (comms back) or a route -> not an intra-doc node
            if not _resolves(doc, target, known_keys):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-choice",
                    f"choice in `{ref.owner}` points at `{target}`, which resolves to no node"))
    return findings


# --- Phase 3: cross-file (signals vs routes, reach vs landmark) --------------
def _mast_routes(mast_sources):
    """Set of declared `//signal/<name>` route names across the given .mast sources."""
    routes = set()
    rx = re.compile(r"^//signal/(?P<name>\S+)")
    for src in mast_sources or []:
        for line in src.splitlines():
            m = rx.match(line.strip())
            if m:
                routes.add(m.group("name").split()[0])  # drop trailing ` if <cond>`
    return routes


# Signal names EMITTED from .mast/.py: literal signal_emit("x"), the quest-signal
# `"SIGNAL_NAME": "x"` plumbing (what a quest `When: signal x` actually waits on), and
# the quest driver's DIRECT advance calls. `quest_credit_signal(ship, "x")` /
# `quest_on_signal("x")` satisfy a quest's `When:`/`Goal: signal x` without ever going
# through signal_emit - miss them and every owner-scoped job reads as "nothing emits
# this" (peacetime credits its jobs entirely this way).
_RE_EMIT = re.compile(r'signal_emit\s*\(\s*["\']([A-Za-z0-9_]+)["\']')
_RE_SIGNAL_NAME = re.compile(r'["\']SIGNAL_NAME["\']\s*:\s*["\']([A-Za-z0-9_]+)["\']')
_RE_CREDIT = re.compile(r'quest_credit_signal\s*\([^,()]*,\s*["\']([A-Za-z0-9_]+)["\']')
_RE_QUEST_ON = re.compile(r'quest_on_signal\s*\(\s*["\']([A-Za-z0-9_]+)["\']')


def _emitted_from_sources(mast_sources):
    """Signal names statically discoverable as emitted in the given source texts."""
    names = set()
    for src in mast_sources or []:
        for rx in (_RE_EMIT, _RE_SIGNAL_NAME, _RE_CREDIT, _RE_QUEST_ON):
            names.update(m.group(1) for m in rx.finditer(src))
    return names


# Optional declarations in a `metadata:` block (MAST or AMD): `emits: [a, b]` names
# signals the label emits (for what static scanning can't see - dynamic/computed
# names); `handles: [c]` names signals it handles (like a `//signal/` route). Both
# are read as a convention - MAST just treats the keys as (unused) task vars.
_RE_DECLARE = re.compile(r'^[ \t]*(emits|handles)[ \t]*:[ \t]*(.+?)[ \t]*$', re.I | re.M)
_RE_NAME = re.compile(r'^[A-Za-z0-9_]+$')


def _declared_from_sources(mast_sources):
    """(emits, handles) name sets declared via `emits:` / `handles:` metadata lines."""
    emits, handles = set(), set()
    for src in mast_sources or []:
        for m in _RE_DECLARE.finditer(src):
            bucket = emits if m.group(1).lower() == "emits" else handles
            for tok in m.group(2).strip().strip("[]").split(","):
                name = tok.strip().strip("'\"")
                if _RE_NAME.match(name):
                    bucket.add(name)
    return emits, handles


def mast_source_index(mast_sources):
    """The source-derived sets the cross-file checks need: `routes`, `emitted` and
    `labels`, scanned out of the mission's .mast/.py once.

    Derived once and reused because these depend only on the SOURCES, not on the .amd
    being linted: a whole-mission lint calls the cross-file phase once per .amd file,
    and re-deriving these each time re-scans every MAST source once per document (on a
    15-file mission with ~1.2 MB of MAST, the same megabyte 15 times over, which
    dominated the language server's per-keystroke cost)."""
    if mast_sources is None:
        return None
    decl_emits, decl_handles = _declared_from_sources(mast_sources)
    return {"routes": _mast_routes(mast_sources) | decl_handles,
            "emitted": _emitted_from_sources(mast_sources) | decl_emits | DRIVER_SIGNALS,
            "labels": mast_labels(mast_sources)}


def amd_lint_cross_file(doc, mast_sources=None, source_index=None):
    """Flag emitted `signal X` with no `//signal/X` route, a quest `When: signal X`
    that nothing emits, and `reach i,j` cells with no landmark `At: i,j`. WARNING.

    The signal checks need `mast_sources` (a list of .mast/.py source strings) to
    know the mission's routes and emits; without it they are skipped. Pass a
    prebuilt `source_index` (`mast_source_index`) to skip re-scanning them."""
    findings = []
    routes = set()

    # The signals this mission actually emits: .amd raw emits + statically-scanned
    # signal_emit()/SIGNAL_NAME + declared `emits:` + the always-present driver
    # signals. Routes = `//signal/` handlers + declared `handles:`.
    emitted = None
    if source_index is None and mast_sources is not None:
        source_index = mast_source_index(mast_sources)
    if source_index is not None:
        routes = source_index["routes"]
        emitted = ({r.value for r in doc.refs if r.kind == "signal"}
                   | source_index["emitted"])

    for ref in doc.refs:
        if ref.kind == "signal" and source_index is not None:
            if ref.value in routes or ref.value in DRIVER_SIGNALS:
                continue
            findings.append(AmdFinding.at(
                ref.span, WARNING, "signal-no-route",
                f"`{ref.owner}` emits signal `{ref.value}` but no `//signal/{ref.value}` "
                f"route was found in the mission's .mast (nor a known driver signal)"))
        elif ref.kind == "wait_signal" and emitted is not None:
            if ref.value not in emitted:
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "unfired-signal",
                    f"`{ref.owner}` waits on signal `{ref.value}` (When/Fail on signal) "
                    f"but nothing in the mission emits it"))
        elif ref.kind == "reach":
            if ref.value not in doc.landmark_cells:
                i, j = ref.value
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "reach-no-landmark",
                    f"`{ref.owner}` sends the player to cell {i},{j} but no landmark has "
                    f"`At: {i}, {j}` - they may jump to an empty cell"))
    return findings


# --- Phase 2b: field values (schema-driven, exact spans) --------------------
def _section_key(node):
    """The `##` section key a node lives under (mirrors amd_lsp._section_of), so a
    conventionally-named section (`## Items`) resolves the record's archetype."""
    n = node
    while n.parent is not None and n.parent.key != "__root__" and n.level > 2:
        n = n.parent
    return n.key


def _fence_fields(node):
    """(lineno, raw, label, value) for each `Label: value` line in a node's fence,
    skipping `//` comments and label-less lines. `label` is trimmed (natural case);
    the archetype resolver lower-cases it."""
    out = []
    for lineno, raw in (getattr(node, "fence_lines", None) or []):
        if ":" not in raw or raw.strip().startswith("//"):
            continue
        label = raw.split(":", 1)[0].strip()
        if label:
            out.append((lineno, raw, label, raw.split(":", 1)[1].strip()))
    return out


def amd_lint_field_values(doc):
    """Flag a closed-enum field carrying a value outside its vocabulary - `State:
    activ` (typo) otherwise does nothing, silently. Resolves each record's archetype
    via `amd_schema` (its `##` section, else its discriminating fields) and checks
    only genuinely closed enums; open enums and booleans are lenient. WARNING."""
    from sbs_utils.procedural.amd_schema import infer_archetype, enum_accepts
    findings = []
    for node in doc.nodes:
        fields = _fence_fields(node)
        arch = infer_archetype([lab for _l, _r, lab, _v in fields], _section_key(node))
        for lineno, raw, label, value in fields:
            # accepts = current values PLUS retired spellings kept alive by `aka`,
            # so a value rename never flags files written before it.
            vals = enum_accepts(label, arch)
            if not vals or set(vals) == {"true", "false"}:
                continue                       # not closed, or a lenient boolean
            if value and value.lower() not in vals:
                prefix = raw.split(":", 1)[0] + ":"
                after = raw[len(prefix):]
                col = len(prefix) + (len(after) - len(after.lstrip()))
                findings.append(AmdFinding(
                    lineno, WARNING, "unknown-enum-value",
                    f"`{label}: {value}` is not a valid {arch} value "
                    f"({'/'.join(vals)}); likely a typo - it will be silently ignored",
                    col=col, end_line=lineno, end_col=col + len(value)))
    return findings


def mast_labels(mast_sources):
    """Top-level MAST label names (`== name ==`) across the given sources - valid
    jump/handler targets an AMD reference may point at."""
    labels = set()
    rx = re.compile(r"^={2,}\s*(?P<name>\w+)")
    for src in mast_sources or []:
        for line in src.splitlines():
            m = rx.match(line.strip())
            if m:
                labels.add(m.group("name"))
    return labels


def amd_lint(file_path=None, content=None, mast_sources=None, cross_file=None,
             known_keys=None, source_index=None):
    """Run all passes and return a combined, position-sorted [AmdFinding].

    Phase 1 (structural, ERROR) always runs. Phases 2/3 run when the model parses.
    `known_keys` are symbols defined elsewhere in the mission (sibling .amd node
    keys + MAST labels) so cross-file / MAST-label references don't false-positive;
    the cross-file signal check additionally needs `mast_sources` (.mast/.py source
    strings). Pass `cross_file=False` to skip Phase 3. A whole-mission run should
    build `source_index` once (`mast_source_index`) and pass it to every call, so the
    MAST sources are scanned once instead of once per .amd. Any parser exception is
    downgraded to a single finding rather than raised."""
    if source_index is None and mast_sources is not None:
        source_index = mast_source_index(mast_sources)
    findings = list(amd_lint_structural(file_path, content))
    findings += amd_lint_ascii(file_path, content)
    findings += amd_lint_scan_labels(file_path, content)

    if content is None and file_path is not None:
        try:
            with open(file_path, "r") as f:
                content = f.read()
        except Exception:
            content = ""

    try:
        from sbs_utils.procedural.amd_core import parse
        doc = parse(content)
        keys = set(known_keys) if known_keys else set()
        if source_index is not None:
            keys |= source_index["labels"]  # MAST labels are valid targets too
        findings += amd_lint_references(doc, keys)
        findings += amd_lint_keys(doc)
        findings += amd_lint_field_values(doc)
        if cross_file is not False:
            findings += amd_lint_cross_file(doc, mast_sources, source_index)
    except Exception as e:
        findings.append(AmdFinding(0, WARNING, "parse-skipped",
                                   f"reference checks skipped - parse failed: {e}"))

    findings.sort(key=lambda f: (f.line, 0 if f.is_error() else 1,
                                 f.col if f.col is not None else -1))
    return findings


def _main(argv):
    """Minimal file linter: `python -m sbs_utils.procedural.amd_lint [--json|--compact]
    <file.amd> ...`. (No cross-file signal check here - use `sbs lint` for a whole
    mission with its .mast.)"""
    fmt = "text"
    if argv and argv[0] in ("--json", "--compact"):
        fmt = argv[0][2:]
        argv = argv[1:]
    if not argv:
        print("usage: python -m sbs_utils.procedural.amd_lint [--json|--compact] <file.amd> ...")
        return 2

    any_error = False
    bundle = []
    for path in argv:
        findings = amd_lint(file_path=path)
        any_error = any_error or any(f.is_error() for f in findings)
        if fmt == "text":
            print(f"== {path} ==")
            print("  clean" if not findings else "", end="" if findings else "\n")
            for f in findings:
                print(f"  {f}")
        elif fmt == "compact":
            for f in findings:
                print(f.compact(path))
        else:  # json
            bundle.extend(f.to_dict(file=path) for f in findings)
    if fmt == "json":
        import json
        print(json.dumps(bundle, indent=2))
    return 1 if any_error else 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
