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


# Engine / quest-driver signals that have built-in handlers - never flag these as
# "emitted with no route" (source: schema map, quest_driver.mast + engine routes).
DRIVER_SIGNALS = frozenset({
    "quest_activated", "quest_completed", "quest_failed", "quest_signal",
    "quest_finished", "game_over", "game_started", "show_game_results",
    "universe_arrived", "item_collected", "item_changed", "ship_docked",
    "quest_engage", "create_player_ships",
})


# --- Phase 2: reference integrity (model-level, exact spans) -----------------
def amd_lint_references(doc):
    """Flag intra-document references that resolve to no node: dialogue/comms choice
    `](target)`, lifeform `Scene:`, quest `Then: reveal <path>`, `Parent:`. Uses the
    `amd_core` model, so each finding carries the target's exact range. WARNING."""
    findings = []
    for ref in doc.refs:
        if ref.kind == "scene":
            if ref.value not in doc.keys:
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-scene",
                    f"`{ref.owner}` Scene points at `{ref.value}`, which is not a defined node"))
        elif ref.kind == "parent":
            if ref.value not in doc.keys:
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-parent",
                    f"`{ref.owner}` Parent points at `{ref.value}`, which is not a defined node"))
        elif ref.kind == "reveal":
            if not doc.path_resolves(ref.value):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-reveal",
                    f"`{ref.owner}` Then reveals `{ref.value}`, which resolves to no node"))
        elif ref.kind == "choice":
            target = ref.value
            if not target or target.startswith("//"):
                continue  # empty (comms back) or a route -> not an intra-doc node
            ok = doc.path_resolves(target) if "/" in target else target in doc.keys
            if not ok:
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


def amd_lint_cross_file(doc, mast_sources=None):
    """Flag emitted `signal X` with no `//signal/X` route (and not a known driver
    signal), and `reach i,j` cells with no landmark `At: i,j`. WARNING."""
    findings = []
    routes = _mast_routes(mast_sources)

    for ref in doc.refs:
        if ref.kind == "signal" and mast_sources is not None:
            if ref.value in routes or ref.value in DRIVER_SIGNALS:
                continue
            findings.append(AmdFinding.at(
                ref.span, WARNING, "signal-no-route",
                f"`{ref.owner}` emits signal `{ref.value}` but no `//signal/{ref.value}` "
                f"route was found in the mission's .mast (nor a known driver signal)"))
        elif ref.kind == "reach":
            if ref.value not in doc.landmark_cells:
                i, j = ref.value
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "reach-no-landmark",
                    f"`{ref.owner}` sends the player to cell {i},{j} but no landmark has "
                    f"`At: {i}, {j}` - they may jump to an empty cell"))
    return findings


def amd_lint(file_path=None, content=None, mast_sources=None, cross_file=None):
    """Run all passes and return a combined, position-sorted [AmdFinding].

    Phase 1 (structural, ERROR) always runs. Phases 2/3 run when the model parses;
    the cross-file signal check additionally needs `mast_sources` (a list of .mast
    source strings). Pass `cross_file=False` to skip Phase 3. Any exception from the
    parser is downgraded to a single finding rather than raised."""
    findings = list(amd_lint_structural(file_path, content))

    if content is None and file_path is not None:
        try:
            with open(file_path, "r") as f:
                content = f.read()
        except Exception:
            content = ""

    try:
        from sbs_utils.procedural.amd_core import parse
        doc = parse(content)
        findings += amd_lint_references(doc)
        if cross_file is not False:
            findings += amd_lint_cross_file(doc, mast_sources)
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
