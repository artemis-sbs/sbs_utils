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
    """One linter result. `line` is 1-based (0 when file-global)."""
    __slots__ = ("line", "severity", "code", "message")

    def __init__(self, line, severity, code, message):
        self.line = line
        self.severity = severity
        self.code = code
        self.message = message

    def is_error(self):
        return self.severity == ERROR

    def __repr__(self):
        return f"AmdFinding({self.line}, {self.severity!r}, {self.code!r}, {self.message!r})"

    def __str__(self):
        where = f"line {self.line}" if self.line else "file"
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


# --- reference extraction helpers (shared by Phase 2 & 3) -------------------
# A dialogue/comms choice line: `- [label](target) <rest>` (rest = guard/outcomes).
_RE_CHOICE = re.compile(r"^\s*-\s*\[(?P<label>[^\]]*)\]\((?P<target>[^)]*)\)(?P<rest>.*)$")
# A `signal <name>` outcome token (dialogue outcome or quest Then:/When:).
_RE_SIGNAL = re.compile(r"\bsignal\s+(?P<name>[A-Za-z0-9_]+)")

# Engine / quest-driver signals that have built-in handlers - never flag these as
# "emitted with no route" (source: schema map, quest_driver.mast + engine routes).
DRIVER_SIGNALS = frozenset({
    "quest_activated", "quest_completed", "quest_failed", "quest_signal",
    "quest_finished", "game_over", "game_started", "show_game_results",
    "universe_arrived", "item_collected", "item_changed", "ship_docked",
    "quest_engage", "create_player_ships",
})


def _coords(value, n=2):
    """First `n` signed-int tokens of a coord string ('2, -1' -> (2, -1)); else None."""
    toks = [int(t) for t in str(value).replace(",", " ").split() if t.lstrip("-").isdigit()]
    return tuple(toks[:n]) if len(toks) >= n else None


def _locate(source_lines, needle, used):
    """1-based line of the first occurrence of `needle` not already claimed in `used`
    (so repeated tokens map to distinct lines); 0 if not found."""
    for i, line in enumerate(source_lines, start=1):
        if i in used:
            continue
        if needle and needle in line:
            used.add(i)
            return i
    return 0


def _index_tree(toc):
    """Walk the parsed tree once. Returns dicts the reference passes need:
      keys           - set of every node key
      parent_of      - key -> parent key (for path shape checks)
      nodes          - list of (key, data, description) for every non-root node
    """
    keys, parent_of, nodes = set(), {}, []

    def walk(node, parent_key):
        key = node.get("key")
        if key and key != "__root__":
            keys.add(key)
            parent_of[key] = parent_key
            nodes.append((key, node.get("data") or {}, node.get("description") or ""))
        for child in node.get("children", []) or []:
            walk(child, key)

    walk(toc, None)
    return {"keys": keys, "parent_of": parent_of, "nodes": nodes}


def _path_resolves(path, keys, parent_of):
    """A slash path (`beacon_arc/ep1_scan`) resolves iff every segment is a known
    key AND each segment's parent is the preceding segment. A bare key resolves iff
    it exists. Mirrors the quest-driver's `<parent>/<child>` grant paths."""
    segs = [s for s in str(path).split("/") if s]
    if not segs:
        return True
    if any(s not in keys for s in segs):
        return False
    for a, b in zip(segs, segs[1:]):
        if parent_of.get(b) != a:
            return False
    return True


def _di(data, *names):
    """Case-insensitive fetch of the first present key from a node's data dict."""
    lower = {str(k).lower(): v for k, v in data.items()}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    return None


# --- Phase 2: reference integrity (tree-level) ------------------------------
def amd_lint_references(toc, source=""):
    """Flag intra-document references that resolve to no node: dialogue/comms choice
    `](target)`, lifeform `Scene:`, quest `Then: reveal <path>`, `Parent:`. All
    WARNING (per the structural-fail / refs-warn policy)."""
    idx = _index_tree(toc)
    keys, parent_of = idx["keys"], idx["parent_of"]
    lines = source.splitlines() if source else []
    used = set()
    findings = []

    def warn(needle, code, msg):
        findings.append(AmdFinding(_locate(lines, needle, used), WARNING, code, msg))

    for key, data, desc in idx["nodes"]:
        # Lifeform Scene: -> a dialogue scene key
        scene = _di(data, "Scene")
        if scene and scene not in keys:
            warn(f"Scene: {scene}", "dangling-scene",
                 f"`{key}` Scene points at `{scene}`, which is not a defined node")

        # Parent: -> a quest key in the same doc
        parent = _di(data, "Parent")
        if parent and parent not in keys:
            warn(f"Parent: {parent}", "dangling-parent",
                 f"`{key}` Parent points at `{parent}`, which is not a defined node")

        # Then: reveal <path> / a bare Then: label -> resolvable node path
        then = _di(data, "Then")
        if then:
            toks = str(then).split()
            verb = toks[0].lower() if toks else ""
            if verb == "reveal" and len(toks) >= 2:
                if not _path_resolves(toks[1], keys, parent_of):
                    warn(f"reveal {toks[1]}", "dangling-reveal",
                         f"`{key}` Then reveals `{toks[1]}`, which resolves to no node")
            elif verb not in ("reveal", "signal"):
                # bare `Then: <label>` is treated as a reveal target by the driver
                if not _path_resolves(then, keys, parent_of):
                    warn(f"{then}", "dangling-reveal",
                         f"`{key}` Then: `{then}` resolves to no node")

        # Choice targets in the description: `- [label](target)`
        for cl in desc.splitlines():
            m = _RE_CHOICE.match(cl)
            if not m:
                continue
            target = m.group("target").strip()
            if not target or target.startswith("//"):
                continue  # empty (comms back) or a route -> not an intra-doc node
            if "/" in target:
                if not _path_resolves(target, keys, parent_of):
                    warn(f"]({target})", "dangling-choice",
                         f"choice in `{key}` points at `{target}`, which resolves to no node")
            elif target not in keys:
                warn(f"]({target})", "dangling-choice",
                     f"choice in `{key}` points at `{target}`, which is not a defined node")

    return findings


# --- Phase 3: cross-file (signals vs routes, reach vs landmark) --------------
def _emitted_signals(idx):
    """Yield (signal_name, key, needle) for every raw signal EMITTED in the doc:
    dialogue-choice `; ... signal X` outcomes and quest `Then: signal X`."""
    for key, data, desc in idx["nodes"]:
        then = _di(data, "Then")
        if then:
            m = _RE_SIGNAL.match(str(then).strip()) or _RE_SIGNAL.search(str(then))
            if str(then).strip().lower().startswith("signal") and m:
                yield m.group("name"), key, f"signal {m.group('name')}"
        for cl in desc.splitlines():
            mc = _RE_CHOICE.match(cl)
            rest = mc.group("rest") if mc else (cl if cl.strip().startswith("%") else "")
            for sm in _RE_SIGNAL.finditer(rest or ""):
                yield sm.group("name"), key, f"signal {sm.group('name')}"


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


def amd_lint_cross_file(toc, source="", mast_sources=None):
    """Flag emitted `signal X` with no `//signal/X` route (and not a known driver
    signal), and `When: reach i,j` cells with no landmark `At: i,j`. WARNING."""
    idx = _index_tree(toc)
    lines = source.splitlines() if source else []
    used = set()
    findings = []
    routes = _mast_routes(mast_sources)

    # Signals -> routes (only when we were given mast to check against)
    if mast_sources is not None:
        for name, key, needle in _emitted_signals(idx):
            if name in routes or name in DRIVER_SIGNALS:
                continue
            ln = _locate(lines, needle, used)
            findings.append(AmdFinding(
                ln, WARNING, "signal-no-route",
                f"`{key}` emits signal `{name}` but no `//signal/{name}` route was "
                f"found in the mission's .mast (nor a known driver signal)"))

    # reach cells -> landmark At cells
    landmark_cells = set()
    reach_refs = []
    for key, data, desc in idx["nodes"]:
        at = _coords(_di(data, "At") or "")
        if at:
            landmark_cells.add(at)
        when = _di(data, "When")
        if when:
            toks = str(when).split(None, 1)
            if toks and toks[0].lower() in ("reach", "travel") and len(toks) > 1:
                cell = _coords(toks[1])
                if cell:
                    reach_refs.append((cell, key, str(when).strip()))
    for cell, key, when in reach_refs:
        if cell not in landmark_cells:
            ln = _locate(lines, when, used)
            findings.append(AmdFinding(
                ln, WARNING, "reach-no-landmark",
                f"`{key}` sends the player to cell {cell[0]},{cell[1]} but no landmark "
                f"has `At: {cell[0]}, {cell[1]}` - they may jump to an empty cell"))

    return findings


def amd_lint(file_path=None, content=None, mast_sources=None, cross_file=None):
    """Run all passes and return a combined, line-sorted [AmdFinding].

    Phase 1 (structural, ERROR) always runs. Phases 2/3 run when the tree parses;
    the cross-file signal check additionally needs `mast_sources` (a list of .mast
    source strings). Pass `cross_file=False` to skip Phase 3. Any exception from the
    tree parser is downgraded to a single finding rather than raised."""
    findings = list(amd_lint_structural(file_path, content))

    if content is None and file_path is not None:
        try:
            with open(file_path, "r") as f:
                content = f.read()
        except Exception:
            content = ""

    try:
        from sbs_utils.procedural.quest import document_get_amd_file
        toc = document_get_amd_file(None, content=content)
        findings += amd_lint_references(toc, content or "")
        if cross_file is not False:
            findings += amd_lint_cross_file(toc, content or "", mast_sources)
    except Exception as e:
        findings.append(AmdFinding(0, WARNING, "parse-skipped",
                                   f"reference checks skipped - tree parse failed: {e}"))

    findings.sort(key=lambda f: (f.line, 0 if f.is_error() else 1))
    return findings


def _main(argv):
    import sys
    if not argv:
        print("usage: python -m sbs_utils.procedural.amd_lint <file.amd> ...")
        return 2
    any_error = False
    for path in argv:
        findings = amd_lint(file_path=path)
        print(f"== {path} ==")
        if not findings:
            print("  clean")
        for f in findings:
            print(f"  {f}")
            any_error = any_error or f.is_error()
    return 1 if any_error else 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
