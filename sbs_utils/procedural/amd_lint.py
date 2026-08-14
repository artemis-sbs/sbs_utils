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
import os
import re
from sbs_utils.procedural.amd import amd_read_text, RE_HEADING

ERROR = "error"
WARNING = "warning"

# Mirror the parser's own patterns (procedural/quest.py `_document_get_amd_file`)
# so the linter agrees with it exactly on what IS a heading / a fence.
# THE PARSER'S rule, not a copy of it. This used to be a lookalike with greedy
# `.*` groups and no end anchor, which made it MORE permissive than the reader:
# a `#` line the parser drops into body text matched HERE as a valid heading, so
# the linter stayed quiet about the exact `broken-heading` it exists to catch.
_RE_SECTION = RE_HEADING
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
        content = amd_read_text(file_path)
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
    "quest_succeeded", "quest_failed_done", "quest_started",
    "game_over", "game_started", "show_game_results",
    "universe_arrived", "item_collected", "item_changed", "ship_docked",
    "quest_engage", "create_player_ships",
})


# --- Phase 2: reference integrity (model-level, exact spans) -----------------
def _item_universe_known(doc, items):
    """True when SOMETHING in reach declares items - MAST `type: item/` labels, or item
    records in this document. False means the checker cannot see what an item is, and a
    drop key must be given the benefit of the doubt."""
    if items:
        return True
    return any(getattr(n, "kind", None) == "item" for n in doc.nodes)


def _resolves(doc, value, known_keys):
    """A bare key or `a/b/c` path resolves inside this doc, or (cross-file) its
    key/leaf is a known symbol elsewhere in the mission (another .amd node or a
    MAST label). Cross-file structure can't be verified from one file, so the leaf
    check is intentionally soft.

    A key that names SEVERAL nodes still counts as resolving here - it exists, it is
    just under-specified - so it is reported once by `amd_lint_keys` as ambiguous
    rather than twice, and never as "points at nothing"."""
    if "/" in value:
        # A slashed value may be a literal KEY (an AMD heading `](arc/step)`, which is how
        # a nested quest is authored) as well as a heading PATH. Check the key first, or
        # every nested reference reads as dangling.
        return (value in doc.keys or doc.path_resolves(value)
                or value.split("/")[-1] in known_keys)
    # `Aka:` names count as resolving - that is the entire point of declaring one.
    return (value in doc.keys or value in known_keys
            or _aka_hit(doc, value))


def _aka_hit(doc, value):
    """True when `value` is an `Aka:` name some record in this doc answers to."""
    from sbs_utils.procedural.amd import amd_norm
    aliases = getattr(doc, "aliases", None)
    return bool(aliases) and amd_norm(value) in aliases


def amd_lint_fence(doc):
    """Surface what the fence READER already noticed.

    The reader collects its complaints in a writer's terms rather than raising, so a
    typo can never take a mission down - but until this pass nothing ever asked for
    them, so every one of those messages was thrown away. ERROR: each is a line the
    parser could not use."""
    return [AmdFinding(line, ERROR, "fence-syntax", message)
            for line, message in getattr(doc, "errors", ())]


def amd_lint_unknown_fields(doc):
    """Flag a field no archetype declares.

    Growth rule 1: an unknown field is kept and never fatal, so a newer mission still
    loads on an older library. But silence is how `Disposition:` typos survived - the
    author gets told, and the fix is either a spelling or one line of
    `amd_register_fields`. WARNING, and only where the record's kind is KNOWN: with no
    archetype there is nothing to be unknown against."""
    from sbs_utils.procedural.amd_schema import (amd_is_declared, template_fields,
                                                 amd_traits_of)
    findings = []
    for node in doc.nodes:
        if not node.kind:
            continue
        # A record's `Also:` traits lend it their fields - that is the whole point of a
        # trait. Without them a worldlet saying `Also: economy` was still told `Yields:`
        # and `Reserve:` are unknown, which is the trait mechanism working everywhere
        # except in the tool that reports on it.
        traits = amd_traits_of(node.data)
        for lineno, raw, label, _value in _fence_fields(node):
            # Only TOP-LEVEL labels are fields. An indented line is inside a nested
            # block (a recipe's Properties/Defaults, a chatter Lines list) whose inner
            # names the mission owns - the registry has no opinion on those.
            if raw[:1] in (" ", "\t"):
                continue
            if amd_is_declared(label, node.kind, traits):
                continue
            known = ", ".join(sorted(template_fields(node.kind))[:6])
            col = 0 if ":" not in raw else len(raw) - len(raw.lstrip())
            findings.append(AmdFinding(
                lineno, WARNING, "unknown-field",
                f"`{label}` is not a known {node.kind} field - check the spelling, or "
                f"declare it with amd_register_fields. Known: {known}...", col=col))
    return findings


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
        # SIBLINGS only. A record is addressed by PATH, so two cousins may share a leaf
        # name - `job_sweep/recover` and `job_cache/recover` are two different steps and
        # reading them as short names scoped to their job is the point, which this rule's
        # own docstring says. Warning on every duplicate contradicted that: peacetime's
        # three `scan` steps and three `recover` steps were flagged forever with nothing
        # to fix, because renaming them would make the file worse and every reference to
        # them already writes the path (`ambiguous-reference` below fires on the ones that
        # do not, and fires zero times there).
        #
        # Two SIBLINGS sharing a key is the real defect: no path can tell them apart, so
        # one of them is unreachable however it is referenced.
        by_parent = {}
        for n in nodes:
            by_parent.setdefault(id(n.parent), []).append(n)
        for clash in by_parent.values():
            if len(clash) < 2:
                continue
            where = ", ".join(path_of(n) for n in clash)
            for n in clash[1:]:
                findings.append(AmdFinding.at(
                    n.key_span or n.span, WARNING, "duplicate-key",
                    f"`{key}` names {len(clash)} records under the same parent ({where}) "
                    f"- no path can tell them apart, so rename one"))
    for ref in doc.refs:
        if ref.kind in ("scene", "parent", "reveal", "choice") and doc.is_ambiguous(ref.value):
            owner = doc.by_key.get(ref.owner)
            if doc.resolve_target(ref.value, from_node=owner) is None:
                paths = ", ".join(path_of(n) for n in doc.nodes_for(str(ref.value)))
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "ambiguous-reference",
                    f"`{ref.value}` could mean {paths} - say which by writing the path"))
    return findings


def amd_lint_references(doc, known_keys=frozenset(), items=None):
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
        elif ref.kind == "cue":
            # A cue names who SPEAKS. The cast usually lives in another file (a
            # `Characters` section loaded alongside), so `known_keys` carries most of
            # the real answers and this only fires on a name nothing defines.
            if not _resolves(doc, ref.value, known_keys):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-speaker",
                    f"`{ref.owner}` gives a line to `{ref.value}`, who is not in the cast"))
        elif ref.kind == "speaker":
            # The FIELD form of the same question a cue asks, so it answers to the same
            # code: a tool filtering `dangling-speaker` keeps working, and an author sees
            # one diagnostic for "this voice is nobody" however they wrote it.
            if not _resolves(doc, ref.value, known_keys):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-speaker",
                    f"`{ref.owner}` gives its voice to `{ref.value}`, who is not in the cast"))
        elif ref.kind == "drop":
            # A drop key that names no item is a table that yields nothing - the silent
            # failure the feature was asked for.
            #
            # But an item is usually a `type: item/` MAST label, and its KEY is not its
            # label name - so checking against nodes and labels alone called every
            # shipped trade good dangling (`salvage`, `contraband`). The item universe is
            # scanned separately, and when it is EMPTY this check does not run at all:
            # a mission whose items all live in an addon we cannot see has not told us
            # what an item key looks like, and guessing there is how a linter teaches
            # authors to ignore it.
            if not _item_universe_known(doc, items):
                continue
            if ref.value in (items or ()):
                continue
            if not _resolves(doc, ref.value, known_keys):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-drop",
                    f"`{ref.owner}` drops `{ref.value}`, which is not a defined item"))
        elif ref.kind == "item":
            # A relic part's `Item:`. Same reasoning as `drop` above, including the
            # refusal to guess when nothing in reach declares any items at all.
            if not _item_universe_known(doc, items):
                continue
            if ref.value in (items or ()):
                continue
            if not _resolves(doc, ref.value, known_keys):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "relic-unknown-item",
                    f"`{ref.owner}` holds `{ref.value}`, which is not a defined item"))
        elif ref.kind == "link":
            # A `[[link]]` to something unwritten is a NOTE TO SELF, not a mistake -
            # drafting a mission as prose and letting the linter list what is still
            # missing is a supported way to work (`sbs lint --missing`). So the
            # wording asks rather than accuses, and the severity stays WARNING.
            if not _resolves(doc, ref.value, known_keys):
                findings.append(AmdFinding.at(
                    ref.span, WARNING, "dangling-link",
                    f"`{ref.owner}` links to `{ref.value}`, which is not written yet"))
    return findings


def amd_lint_callouts(doc):
    """An unknown callout kind (`> [!MYSTERY]`) - renders as a plain quote. WARNING.

    Never an error: a document written against a newer build, or against an addon
    that is not loaded right now, must stay readable."""
    from sbs_utils.procedural.amd_callout import amd_callout_blocks, amd_callout_kinds
    findings = []
    for node in doc.nodes:
        body = [raw for _ln, raw in (node.body_lines or ())]
        if not body:
            continue
        first_line = node.body_lines[0][0]
        for block in amd_callout_blocks("\n".join(body)):
            if block["known"]:
                continue
            findings.append(AmdFinding(
                first_line + block["start"], WARNING, "unknown-callout",
                f"`{block['kind']}` is not a callout kind this build knows "
                f"(one of: {', '.join(amd_callout_kinds())}) - it will read as a quote"))
    return findings


def amd_lint_missing(doc, known_keys=frozenset()):
    """Every reference in `doc` that resolves to nothing, grouped by target.

    Obsidian's unresolved-links pane: the same facts `amd_lint_references` reports as
    diagnostics, turned into a WORK LIST - `{target: [(kind, owner, span), ...]}`.
    Powers `sbs lint --missing` and the editor's Missing panel, so a writer can draft
    the whole story in prose with `[[links]]` and be handed what to write next."""
    out = {}
    for ref in doc.refs:
        if ref.kind not in ("scene", "parent", "reveal", "choice", "link", "cue"):
            continue
        target = str(ref.value or "")
        if not target or target.startswith("//"):
            continue
        if _resolves(doc, target, known_keys):
            continue
        out.setdefault(target, []).append((ref.kind, ref.owner, ref.span))
    return out


# --- Phase 3: cross-file (signals vs routes, reach vs landmark) --------------
def _mast_routes(mast_sources):
    """Set of declared signal-route names across the given .mast sources.

    BOTH forms count. `//shared/signal/X` handles signal X exactly as `//signal/X` does -
    it is the SERVER-only variant, and SIGNAL_ROUTING.md recommends it for anything that
    spawns, saves, rewards or counts. Matching only the per-console form meant the linter
    reported "no route was found" for the routing style the project tells authors to
    prefer: every one of Storm's Beacon's shared routes was flagged despite existing.
    """
    routes = set()
    rx = re.compile(r"^//(?:shared/)?signal/(?P<name>\S+)")
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
            "labels": mast_labels(mast_sources),
            "items": mast_item_keys(mast_sources)}


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


def _action_blocks(node):
    """(lineno, text) for every stage-direction line in this record's `Action:` field.

    The directions are LIST ITEMS, so `_fence_fields` never sees them - it keeps only
    lines carrying a colon. Walk the raw fence instead: the `Action:` label opens the
    block, indented / `-` lines continue it, and the next unindented `Label:` closes it.
    The inline single-line form (`Action: X becomes a pirate`) is one direction on the
    label line itself.
    """
    out = []
    inside = False
    for lineno, raw in (getattr(node, "fence_lines", None) or []):
        stripped = raw.strip()
        if not stripped or stripped.startswith("//"):
            continue
        label = raw.split(":", 1)[0].strip().lower() if ":" in raw else None
        indented = raw[:1] in (" ", "\t")
        if label == "action" and not indented:
            inside = True
            value = raw.split(":", 1)[1].strip()
            if value:                       # inline form
                out.append((lineno, value))
            continue
        if inside and (indented or stripped.startswith("-")):
            out.append((lineno, stripped))
            continue
        if not indented and label:
            inside = False                  # a new field closes the block
    return out


def amd_lint_actions(doc, known_keys=frozenset()):
    """Flag a stage direction that will silently do nothing - an unknown verb, a
    direction with no actor, a missing/extra operand, or an operand that names a record
    nothing declares. WARNING.

    The check is the runtime parser itself (`amd_action_parse`), which is pure and
    engine-free precisely so the linter and the runtime can never disagree about what a
    line means.

    A verb registered with `operand_ref="node"` says its operand is an AMD record key -
    `DS1 hails ds1_brief` names a dialogue scene - so a typo there can be caught the
    same way `Then: reveal` and every other reference is. The verb declares this; the
    linter does not know about any particular verb.

    Deliberately NOT checked: whether the ACTOR exists. An actor resolves to a declared
    landmark key or to a ROLE, and roles are minted in MAST (`add_role`), in spawn CSVs
    and by shipData - none of which this pass can see. Guessing would flag correct files,
    which is how authors learn to ignore a linter.
    """
    from sbs_utils.procedural.amd_action import amd_action_parse
    findings = []
    for node in doc.nodes:
        for lineno, text in _action_blocks(node):
            for act in amd_action_parse(text):
                if act.get("error"):
                    code = "unknown-action-verb" if act.get("verb") is None else "bad-action"
                    findings.append(AmdFinding(lineno, WARNING, code, act["error"]))
                    continue
                operand = str(act.get("operand") or "").strip()
                if act.get("operand_ref") != "node" or not operand:
                    continue
                if not _resolves(doc, operand, known_keys):
                    findings.append(AmdFinding(
                        lineno, WARNING, "dangling-action-ref",
                        f"`{act['verb']} {operand}` names `{operand}`, which no record "
                        f"in this document declares."))
    return findings


def _urge_nodes(doc):
    """(node, {label_lower: (lineno, value)}) for every record declared an Urge."""
    out = []
    for node in doc.nodes:
        fields = {}
        for lineno, raw, label, value in _fence_fields(node):
            if raw[:1] not in (" ", "\t"):
                fields[label.strip().lower()] = (lineno, value)
        if str(getattr(node, "kind", "") or "").strip().lower() == "urge":
            out.append((node, fields))
    return out



def _relic_nodes(doc):
    """(node, {label_lower: (lineno, value)}) for every record in a relic section."""
    out = []
    for node in doc.nodes:
        fields = {}
        for lineno, raw, label, value in _fence_fields(node):
            if raw[:1] not in (" ", "	"):
                fields[label.strip().lower()] = (lineno, value)
        if str(getattr(node, "kind", "") or "").strip().lower() == "relic":
            out.append((node, fields))
    return out


def _relic_nums(value):
    out = []
    for part in str(value).replace(",", " ").split():
        try:
            out.append(float(part))
        except ValueError:
            pass
    return out


def _relic_dist3(a, b):
    return sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)) ** 0.5


def _relic_solid_holds(kind, nums, p):
    """Is point `p` inside this solid? The shapes `Solid:` accepts, and nothing else."""
    if kind == "sphere" and len(nums) >= 4:
        return _relic_dist3(p, nums[0:3]) < nums[3]
    if kind == "box" and len(nums) >= 6:
        return all(abs(float(p[i]) - nums[i]) < nums[3 + i] for i in range(3))
    if kind == "capsule" and len(nums) >= 7:
        return _relic_seg_dist(p, nums[0:3], nums[3:6]) < nums[6]
    return False


def _relic_seg_dist(p, a, b):
    """Distance from a point to a segment - what a capsule measures against."""
    ax, ay, az = (float(v) for v in a[:3])
    bx, by, bz = (float(v) for v in b[:3])
    dx, dy, dz = bx - ax, by - ay, bz - az
    dd = dx * dx + dy * dy + dz * dz
    if dd <= 0:
        return _relic_dist3(p, (ax, ay, az))
    t = ((float(p[0]) - ax) * dx + (float(p[1]) - ay) * dy + (float(p[2]) - az) * dz) / dd
    t = max(0.0, min(1.0, t))
    return _relic_dist3(p, (ax + dx * t, ay + dy * t, az + dz * t))


def amd_lint_relics(doc):
    """Flag a relic layout that will build into something other than it reads as. WARNING.

    Six things go wrong silently, and none of them raises:

    * a ``Passage to:`` naming a chamber no record declares - the corridor simply is not
      built, so the relic has an unreachable wing and looks like a pathfinding bug;
    * a part naming a relic that does not exist - the whole part is dropped;
    * a non-positive radius or half-extent, which builds a chamber enclosing nothing or a
      passage nothing can fly down; and
    * too few numbers on a ``Chamber:`` / ``Box:`` / ``Solid:`` / ``Point:``, where the part
      is skipped
      rather than half-built;
    * a Starts when: phrase the relic watcher cannot evaluate, so authored contents
      never appear; and
    * a Qty:/Starts when: with nothing to apply to.

    Deliberately NOT checked here: whether the relic fits inside one nebula. That is a
    judgement about atmosphere cost, not a correctness claim, and the number depends on
    the shader - a linter asserting it would go stale.
    """
    findings = []
    relic_keys = set()
    chamber_names = {}          # relic key -> {part names}
    parts = []
    for node, fields in _relic_nodes(doc):
        key = str(getattr(node, "key", "") or "")
        owner = fields.get("relic")
        if owner is None:
            relic_keys.add(key)
            chamber_names.setdefault(key, set())
        else:
            parts.append((node, fields, str(owner[1]).strip()))
    for node, fields, owner in parts:
        name = str(getattr(node, "key", "") or "")
        if "chamber" in fields or "box" in fields:
            chamber_names.setdefault(owner, set()).add(name)
    # A NAMED PLACE INSIDE A SUBTRACTED MASS. `Point:` is where a mission puts something -
    # an item, a spawn, a quest target, the marker `reach <role>` measures against - so a
    # point buried in rock is a thing no ship can ever get to, and nothing says so: the
    # relic builds, the item spawns inside the mass, and the objective simply never
    # completes.
    #
    # This is the most repeated mistake in authoring a relic. It is easy to make because
    # the obvious place for a marker is the middle of a room, and the obvious place for a
    # pillar is also the middle of a room. It is invisible in the plan view, where a solid
    # is drawn as a hole rather than as a wall.
    #
    # NOT flagged: a solid over a chamber's CENTRE. That is the suspended-core pattern -
    # a mass hanging in a room you fly around - and it is correct.
    solids = []           # (relic, kind, numbers)
    for node, fields, owner in parts:
        if "solid" in fields:
            value = fields["solid"][1]
            words = [w for w in str(value).replace(",", " ").split() if not _relic_nums(w)]
            solids.append((owner, (words[0].lower() if words else "sphere"),
                           _relic_nums(value)))
    for node, fields, owner in parts:
        if "point" not in fields:
            continue
        ln, value = fields["point"]
        pt = _relic_nums(value)
        if len(pt) < 3:
            continue
        for sowner, kind, nums in solids:
            if sowner != owner or not _relic_solid_holds(kind, nums, pt):
                continue
            findings.append(AmdFinding(
                ln, "warning", "relic-point-in-solid",
                f"this point is inside a subtracted mass - no ship can reach it, so "
                f"anything placed here is unreachable and a `reach` trigger on it never "
                f"fires. Move it off the mass"))
            break

    for node, fields, owner in parts:
        lineno = fields["relic"][0]
        if owner not in relic_keys:
            findings.append(AmdFinding(
                lineno, "warning", "relic-dangling-parent",
                f"'{owner}' is not a relic in this file, so this part is dropped"))
            continue
        if "point" in fields:
            ln, value = fields["point"]
            nums = _relic_nums(value)
            if len(nums) < 3:
                findings.append(AmdFinding(
                    ln, "warning", "relic-short-point",
                    f"'point' needs 3 numbers, got {len(nums)} - "
                    f"the part is skipped rather than half-placed"))
        for label, need in (("chamber", 4), ("box", 6)):
            if label in fields:
                ln, value = fields[label]
                nums = _relic_nums(value)
                if len(nums) < need:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-short-part",
                        f"'{label}' needs {need} numbers, got {len(nums)}"))
                elif label == "chamber" and nums[3] <= 0:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-bad-radius",
                        "a chamber radius must be positive or it encloses nothing"))
                elif label == "box" and min(nums[3:6]) <= 0:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-bad-radius",
                        "box half-extents must be positive"))
        # CONTENTS. An item is a ref, so the resolver already catches a typo in the key -
        # what it cannot catch is a `Starts when:` phrase that PARSES but that the relic
        # watcher does not evaluate. That failure is the worst kind: the file reads
        # correctly, lint is clean, and the beacon simply never appears.
        if "starts when" in fields or "when" in fields:
            ln, value = fields.get("starts when") or fields["when"]
            if "item" not in fields and "spawn" not in fields:
                findings.append(AmdFinding(
                    ln, "warning", "relic-when-without-contents",
                    "'starts when' with no 'item' or 'spawn' has nothing to trigger"))
            else:
                from .amd_relics import relic_contents_can_trigger, RELIC_TRIGGERS
                if not relic_contents_can_trigger(str(value)):
                    findings.append(AmdFinding(
                        ln, "warning", "relic-when-unwatchable",
                        f"a relic cannot watch for '{value}' - it understands "
                        f"reach, signal and a delay ({', '.join(RELIC_TRIGGERS)}); "
                        f"contents with this phrase would never appear"))
        if "qty" in fields and "item" not in fields:
            findings.append(AmdFinding(
                fields["qty"][0], "warning", "relic-qty-without-item",
                "'qty' says how many of an 'item', and there is no item here"))
        if "passage to" in fields:
            ln, value = fields["passage to"]
            for group in str(value).split(","):
                words = [w for w in group.replace(",", " ").split()
                         if not _relic_nums(w)]
                if not words:
                    continue
                target = words[0]
                known = chamber_names.get(owner, set())
                if target not in known:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-dangling-passage",
                        f"'{target}' is not a chamber of '{owner}' - "
                        f"this passage is not built"))
                nums = _relic_nums(group)
                if nums and nums[0] <= 0:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-bad-radius",
                        "a passage radius must be positive or nothing can fly down it"))
    # THE LOOK. Both of these fail silently and visibly - the relic builds, the mission
    # runs, and what you fly into is wrong. An unknown art key does not raise: the engine
    # falls back to the `unknown` mesh, so a typo is a ruin built out of question marks.
    # An unknown `Walls:` value falls back to plain rock, so a plated hall quietly is not.
    known_art = _relic_known_art()
    for node, fields in _relic_nodes(doc):
        if "art" in fields and known_art:
            ln, value = fields["art"]
            for key in [k.strip() for k in str(value).split(",") if k.strip()]:
                if key not in known_art:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-unknown-art",
                        f"'{key}' is not a shipData key - it renders as the `unknown` "
                        f"question-mark mesh rather than failing"))
        # ATMOSPHERE. Same silent fallback as the two above, and it cost a look: an
        # unknown colour is not an error, it quietly becomes YELLOW - so a ruin authored
        # `violet` filled with a dirty yellow haze and nothing said why.
        if "atmosphere" in fields:
            ln, value = fields["atmosphere"]
            want = str(value).strip().lower()
            if want and want not in ("none", "no", "off"):
                try:
                    from .terrain import _neb_colors
                    known = tuple(sorted(_neb_colors.keys()))
                except Exception:                       # noqa: BLE001
                    known = ()
                if known and want not in known:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-unknown-atmosphere",
                        f"'{value}' is not a nebula colour ({', '.join(known)}) - "
                        f"it falls back to yellow rather than failing"))
        if "walls" in fields:
            ln, value = fields["walls"]
            style = str(value).strip().lower()
            try:
                from .volume_dress import volume_style_names
                styles = volume_style_names()
            except Exception:                           # noqa: BLE001
                styles = ()
            if styles and style and style not in styles:
                findings.append(AmdFinding(
                    ln, "warning", "relic-unknown-walls",
                    f"'{value}' is not a wall style ({', '.join(styles)}) - "
                    f"this part falls back to plain rock"))
    return findings


def _relic_known_art():
    """Every shipData key, or an empty set when there is no shipData to ask.

    Empty means SAY NOTHING. `sbs lint` runs outside the game, where the art catalog may
    not be reachable at all, and a linter that reports every key as unknown because it
    could not find the file is worse than one that stays quiet.
    """
    try:
        from .ship_data import get_ship_index
        return set((get_ship_index() or {}).keys())
    except Exception:                                   # noqa: BLE001
        return set()


def amd_lint_urges(doc):
    """Flag an urge that will never speak, or will speak wrongly. WARNING.

    Four things go silently wrong with an urge, and none of them raises at runtime:

    * an unknown ``Whenever:`` / ``Until:`` phrase evaluates FALSE, so the urge simply
      never fires - and a condition that is never true looks exactly like a character
      with nothing to say;
    * a bound quest key that no record declares - the same typo, one layer along;
    * no lines and no ``Action:``, which burns a turn every pass to do nothing; and
    * an ``Every:`` shorter than the global speech floor, which is not an error but IS
      a lie: the urge cannot possibly fire that often, so the number misleads whoever
      tunes it next.

    The condition check calls the RUNTIME registry (``urge_conditions``) rather than a
    copy, so the linter and the game cannot disagree about what a phrase means - the
    same rule ``amd_lint_actions`` follows for verbs.
    """
    try:
        from sbs_utils.procedural.urge import urge_conditions, URGE_GLOBAL_FLOOR
        from sbs_utils.procedural.amd_urge import _every
    except Exception:
        return []                      # engine-free environments skip this pass
    from sbs_utils.procedural.amd import amd_duration_seconds
    known = urge_conditions()
    findings = []

    def _phrase_ok(text):
        line = " ".join(str(text).strip().lower().split())
        if line.startswith("not "):
            line = line[4:]
        return any(line == p or line.startswith(p + " ") for p in known)

    for node, fields in _urge_nodes(doc):
        for label in ("whenever", "until"):
            if label not in fields:
                continue
            lineno, value = fields[label]
            if not value:
                continue
            if not _phrase_ok(value):
                findings.append(AmdFinding(
                    lineno, WARNING, "unknown-urge-condition",
                    f"`{label.title()}: {value}` starts with no known condition - it "
                    f"will always be false, so this urge never fires. Known: "
                    f"{', '.join(known)}"))
        # Deliberately NOT checked: whether the bound QUEST exists. A quest id is
        # routinely built at runtime (`"waiting_" + key`), so no scan of the file - or
        # of the MAST sources - can see it, and checking flagged correct shipped
        # content on the first run. Same call `amd_lint_actions` makes about an actor,
        # for the same reason: guessing flags good files, and that is how authors learn
        # to ignore a linter.
        # Nothing to say and nothing to do. The lint model calls the body `body_lines`
        # (the runtime reader calls it `description`) - reading the runtime's name here
        # made every well-formed urge look empty.
        body = [l for _n, l in (getattr(node, "body_lines", None) or [])
                if l.strip() and not l.strip().startswith("//")]
        if not body and "action" not in fields:
            findings.append(AmdFinding(
                getattr(node, "body_start", 0) or 0, WARNING, "empty-urge",
                f"urge `{node.key}` has no lines and no `Action:` - it would take its "
                f"turn every pass and do nothing"))
        # A cadence the speech budget cannot honor.
        if "every" in fields:
            lineno, value = fields["every"]
            secs = _every(value)
            low = min(secs) if isinstance(secs, tuple) else secs
            if low is not None and 0 < low < URGE_GLOBAL_FLOOR:
                findings.append(AmdFinding(
                    lineno, WARNING, "urge-too-eager",
                    f"`Every: {value}` is under the {URGE_GLOBAL_FLOOR}s global speech "
                    f"floor, so it cannot fire that often - the number will mislead "
                    f"whoever tunes this next"))
    return findings


def _png_size(path):
    """(width, height) from a PNG header, or (None, None). Read here rather than through
    the image atlas so the linter needs no engine paths and no image library."""
    import struct
    try:
        with open(path, "rb") as f:
            head = f.read(26)
        return struct.unpack(">LL", head[16:24])
    except Exception:
        return (None, None)


def _sheet_resolver(file_path):
    """A `sheet -> (exists, size)` lookup rooted at the FILE being linted.

    The runtime resolves art through the engine's mission paths, which a static linter
    does not have - so it looks where the author would put it: the mission's `media/`,
    the mission root, the .amd's own folder, and each unpacked shared pack beside the
    libraries. Returns (None, False) when even the mission root cannot be found, so the
    caller reports what it knows instead of calling every sheet missing.
    """
    import glob
    if not file_path:
        return None, False
    here = os.path.dirname(os.path.abspath(file_path))
    root = here
    while True:
        if os.path.exists(os.path.join(root, "story.json")):
            break
        parent = os.path.dirname(root)
        if parent == root:
            return None, False              # not inside a mission - cannot check
        root = parent
    roots = [os.path.join(root, "media"), root, here]
    roots += sorted(glob.glob(os.path.join(os.path.dirname(root), "__lib__", "media", "*")))

    def resolve(sheet):
        for base in roots:
            candidate = os.path.join(base, str(sheet).replace("/", os.sep))
            if os.path.exists(candidate + ".png"):
                return True, _png_size(candidate + ".png")
        return False, (None, None)

    return resolve, True


def _hail_nodes(doc):
    """(node, {label_lower: lineno}) for every dialogue scene, so a finding can point
    at the offending fence line rather than the heading."""
    out = []
    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").strip().lower() != "dialogue":
            continue
        lines = {}
        for lineno, raw, label, _value in _fence_fields(node):
            if raw[:1] not in (" ", "	"):
                lines[label.strip().lower()] = lineno
        out.append((node, lines))
    return out


def amd_lint_hails(doc):
    """Flag an incoming hail (`When: hail`) that cannot draw or cannot be answered.

    A hail is PRESENTED - it takes over a screen - so the ways it fails are the ways a
    blank screen happens, and none of them raises at runtime:

    * `Presentation: orbit` with no `Subject:` - the shot has nothing to film, so the
      main screen goes black with the conversation drawn over nothing. ERROR.
    * `Presentation: still` with no `Backdrop:` - the same hole, one form along. ERROR.
    * more than `HAIL_MAX_CHOICES` UNGUARDED choices - the answer strip is 1-4 buttons,
      so a fifth ungated choice can never be pressed by anyone. Guarded choices are the
      author's business (that is what a guard is for) and are not counted. WARNING.
    * a hail with no lines AND no choices - it opens and instantly closes. A hail with
      lines but no choices is deliberately fine: that is a one-way message. WARNING.

    Two checks deliberately absent. `Audio:` file existence is NOT checked - the engine
    resolves audio names loosely (shipped missions pass extension-less paths) and a
    check that fires on a valid file is worse than no check. Reachability of a scene
    carrying `Presentation:` is NOT checked either - `hail_offer(scene=...)` lets MAST
    enter any scene directly, so "unreferenced in this document" does not mean dead.

    The choice pattern is imported from the runtime parser rather than copied, so the
    linter and the game cannot disagree about what a choice is - the same rule
    `amd_lint_actions` and `amd_lint_urges` follow for verbs and conditions.
    """
    from sbs_utils.procedural.amd_dialogue import _CHOICE, _dlg_parse_choice
    from sbs_utils.procedural.amd import RE_CUE, RE_DIRECTION
    try:
        from sbs_utils.procedural.hail import HAIL_MAX_CHOICES
    except Exception:
        HAIL_MAX_CHOICES = 4          # the strip is 1-4 buttons

    findings = []
    for node, at in _hail_nodes(doc):
        data = node.data or {}
        presentation = str(data.get("presentation") or "").strip().lower()
        is_hail = str(data.get("when") or "").strip().lower() == "hail"

        if presentation == "orbit" and not str(data.get("subject") or "").strip():
            findings.append(AmdFinding(
                at.get("presentation", node.span.line), ERROR, "hail-missing-subject",
                f"`{node.key}` is `Presentation: orbit` but names no `Subject:` - an "
                f"orbit shot with nothing to film renders a black screen."))
        if presentation == "still" and not str(data.get("backdrop") or "").strip():
            findings.append(AmdFinding(
                at.get("presentation", node.span.line), ERROR, "hail-missing-backdrop",
                f"`{node.key}` is `Presentation: still` but names no `Backdrop:` - "
                f"there is no image to draw."))

        if not is_hail:
            continue

        spoken = 0
        unguarded = []
        for lineno, text in (node.body_lines or []):
            line = text.strip()
            if not line or line.startswith("//"):
                continue
            if line.startswith("-") and "](" in line:
                ch = _dlg_parse_choice(line)
                if ch is not None and not ch.get("guard"):
                    unguarded.append(lineno)
                continue
            if RE_CUE.match(line) or RE_DIRECTION.match(line):
                continue
            spoken += 1

        if len(unguarded) > HAIL_MAX_CHOICES:
            findings.append(AmdFinding(
                unguarded[HAIL_MAX_CHOICES], WARNING, "hail-too-many-choices",
                f"`{node.key}` offers {len(unguarded)} unguarded choices but the answer "
                f"strip shows at most {HAIL_MAX_CHOICES} - this one can never be pressed. "
                f"Gate it with `if ...`, or move it behind another scene."))

        if not spoken and not unguarded:
            findings.append(AmdFinding(
                node.span.line, WARNING, "hail-empty",
                f"`{node.key}` is `When: hail` but has no lines and no choices - it "
                f"opens and closes again with nothing shown."))
    return findings + _lint_hails_verb(doc)


def amd_lint_dialogue_outcomes(doc):
    """Flag a choice outcome (`; <verb> ...`) no handler answers to. WARNING.

    An unregistered verb is applied by nobody: `dialogue_apply` walks past it and the
    choice does everything except the thing the author wrote after the semicolon. There
    is no error and no log line, because nothing looked.

    The known set is the RUNTIME registry, so a mission's own word (`costs`, `earns`)
    counts as soon as its module is loaded - which is what `amd_lint_mission` does
    before linting. A bare-file lint that has not loaded a mission cannot know those
    words, so this pass runs only when a registry beyond the built-in exists; a lint
    that flags correct files is how authors learn to ignore a linter.
    """
    try:
        from sbs_utils.procedural.amd_dialogue import (dialogue_outcome_verbs,
                                                       _dlg_parse_choice)
    except Exception:
        return []
    known = set(dialogue_outcome_verbs())
    if known <= {"signal"}:
        return []                 # nothing but the built-in is loaded: cannot judge
    findings = []
    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").strip().lower() != "dialogue":
            continue
        for lineno, text in (node.body_lines or []):
            line = text.strip()
            if not (line.startswith("-") and "](" in line):
                continue
            ch = _dlg_parse_choice(line)
            for outcome in (ch or {}).get("outcomes") or []:
                verb = str(outcome[0]).lower()
                if verb in known:
                    continue
                findings.append(AmdFinding(
                    lineno, WARNING, "unknown-outcome-verb",
                    f"`{verb}` is not an outcome verb, so nothing applies it - the "
                    f"choice does everything except this. Known: "
                    f"{', '.join(sorted(known))}."))
    return findings


def amd_lint_then(doc):
    """Flag a `Then:` whose first word is not a verb it knows. WARNING.

    `Then:` takes `reveal <key>` or `signal <name>`, and ANYTHING else falls through to
    "reveal a quest with this whole line as its key". So `Then: hail brief` parses,
    lints clean, and silently means nothing - which is exactly the failure mode the AMD
    tooling exists to end. This finding is what makes keeping `Then:` a closed set safe:
    the author is told rather than left guessing.
    """
    from sbs_utils.procedural.amd_quest import THEN_VERBS
    findings = []
    for node in doc.nodes:
        for lineno, raw, label, value in _fence_fields(node):
            if label.strip().lower() != "then":
                continue
            toks = str(value).split()
            if len(toks) < 2 or toks[0].lower() in THEN_VERBS:
                continue
            findings.append(AmdFinding(
                lineno, WARNING, "unknown-then-verb",
                f"`Then: {value}` - `{toks[0]}` is not a `Then:` verb, so this reads as "
                f"`reveal {value}` and will look for a record by that whole name. "
                f"`Then:` takes {' or '.join(THEN_VERBS)}."))
    return findings


def _lint_hails_verb(doc):
    """Check every `Action: <actor> hails <scene>` against the scenes in the document.

    `dangling-action-ref` already catches an operand naming NOTHING. These are the
    three ways it can name something real and still be wrong, all of which end in a
    call that never goes out:

    * the key names a record that is not a dialogue scene at all (a quest, a lifeform);
    * the bare form is written for a speaker who declares no `When: hail` scene, so
      there is nothing to open;
    * the named scene belongs to a different speaker than the actor, or is on the
      `comms` door rather than the `hail` one. Both still run - the scene names its own
      voice and the verb honours it - but they are almost always a copy-paste, so they
      are warnings rather than errors.
    """
    from sbs_utils.procedural.amd_action import amd_action_parse
    from sbs_utils.procedural.amd_dialogue import _dlg_norm

    scenes = {}
    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").strip().lower() == "dialogue":
            scenes[str(node.key).strip().lower()] = node
    if not scenes:
        return []                 # a document with no scenes cannot be judged here

    hail_entries = {}
    for key, node in scenes.items():
        data = node.data or {}
        if str(data.get("when") or "").strip().lower() == "hail":
            hail_entries.setdefault(_dlg_norm(data.get("speaker")), key)

    findings = []
    for node in doc.nodes:
        for lineno, text in _action_blocks(node):
            for act in amd_action_parse(text):
                if act.get("verb") != "hails" or act.get("error"):
                    continue
                actor = _dlg_norm(act.get("actor"))
                operand = str(act.get("operand") or "").strip().lower()
                if not operand:
                    if actor not in hail_entries:
                        findings.append(AmdFinding(
                            lineno, ERROR, "hail-no-entry",
                            f"`{act['actor']} hails` with nothing after it opens that "
                            f"speaker's `When: hail` scene, and none is declared for "
                            f"`{actor}`."))
                    continue
                scene = scenes.get(operand)
                if scene is None:
                    if operand in doc.keys:
                        findings.append(AmdFinding(
                            lineno, ERROR, "hail-unknown-scene",
                            f"`{operand}` is not a dialogue scene, so there is nothing "
                            f"for `{act['actor']}` to say."))
                    continue          # unknown entirely -> dangling-action-ref said so
                data = scene.data or {}
                voice = _dlg_norm(data.get("speaker"))
                if voice and actor and voice != actor:
                    findings.append(AmdFinding(
                        lineno, WARNING, "hail-speaker-mismatch",
                        f"`{act['actor']} hails {operand}` but `{operand}` is spoken by "
                        f"`{data.get('speaker')}` - the scene names the voice, so the "
                        f"call goes out as `{data.get('speaker')}`."))
                if str(data.get("when") or "").strip().lower() != "hail":
                    findings.append(AmdFinding(
                        lineno, WARNING, "hail-not-a-hail",
                        f"`{operand}` is not marked `When: hail` - it reads as a comms "
                        f"scene the player opens, and this pushes it at them instead."))
    return findings


def amd_lint_images(doc, file_path=None):
    """Flag an atlas entry that cannot draw: no sheet, a sheet that is not on disk, an
    `At:` with nothing to measure a cell against, or a cell off the edge of the sheet.

    All four render as a BLANK WIDGET today, with no error anywhere - the failure mode
    the whole AMD validator exists to remove. ERROR, except off-the-edge (WARNING: a
    sheet may legitimately be about to grow)."""
    from sbs_utils.procedural.amd_images import images_from_core, images_validate
    resolve, check_files = _sheet_resolver(file_path)
    findings = []
    for node in doc.nodes:
        if node.kind != "image":
            continue
        if getattr(node.parent, "kind", None) == "image":
            continue                        # an entry; handled with its section
        for child, record in images_from_core(node):
            for _key, severity, code, message in images_validate([record], resolve,
                                                                 check_files):
                findings.append(AmdFinding.at(
                    child.span, ERROR if severity == "error" else WARNING, code, message))
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


def mast_item_keys(mast_sources):
    """Every ITEM key the given MAST sources declare.

    An item is a prefab label whose metadata says `type: item/...` and names itself with
    `key: <k>` - that `key` is the word a `Drops:` table, a `Reward:` and a `collect`
    trigger all write. It is NOT the label name (`prefab_trade_ore` declares `ore`), so
    the label table cannot answer this and a drop key checked against labels alone reads
    as dangling for every item the game actually ships.
    """
    keys = set()
    rx_type = re.compile(r"^\s*type\s*:\s*item/", re.I)
    rx_key = re.compile(r"^\s*key\s*:\s*(?P<k>[\w.\-]+)")
    for src in mast_sources or []:
        in_item = False
        pending = None
        for line in src.splitlines():
            stripped = line.strip()
            # A metadata fence closes the block; a new label starts another one.
            if stripped.startswith("```") or stripped.startswith("=="):
                if in_item and pending:
                    keys.add(pending)
                in_item, pending = False, None
                continue
            if rx_type.match(line):
                in_item = True
                if pending:
                    keys.add(pending)
                    pending = None
                continue
            m = rx_key.match(line)
            if m:
                # `key:` may be written above or below `type:`, so hold it until the
                # block ends and only keep it if the block turned out to be an item.
                if in_item:
                    keys.add(m.group("k"))
                else:
                    pending = m.group("k")
    return keys


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
            content = amd_read_text(file_path)
        except Exception:
            content = ""

    try:
        from sbs_utils.procedural.amd_core import parse
        doc = parse(content)
        keys = set(known_keys) if known_keys else set()
        if source_index is not None:
            keys |= source_index["labels"]  # MAST labels are valid targets too
        findings += amd_lint_fence(doc)
        findings += amd_lint_references(
            doc, keys, items=(source_index or {}).get("items"))
        findings += amd_lint_keys(doc)
        findings += amd_lint_unknown_fields(doc)
        findings += amd_lint_field_values(doc)
        findings += amd_lint_actions(doc, keys)
        findings += amd_lint_urges(doc)
        findings += amd_lint_relics(doc)
        findings += amd_lint_hails(doc)
        findings += amd_lint_then(doc)
        findings += amd_lint_dialogue_outcomes(doc)
        findings += amd_lint_callouts(doc)
        findings += amd_lint_images(doc, file_path)
        if cross_file is not False:
            findings += amd_lint_cross_file(doc, mast_sources, source_index)
    except Exception as e:
        findings.append(AmdFinding(0, WARNING, "parse-skipped",
                                   f"reference checks skipped - parse failed: {e}"))

    findings.sort(key=lambda f: (f.line, 0 if f.is_error() else 1,
                                 f.col if f.col is not None else -1))
    return findings


def amd_lint_mission(mission_root, cross_file=False, use_stamp=True):
    """Lint every .amd a mission ships. Returns [(path, finding)].

    The pre-flight gate. `sbs lint` is the same passes wrapped in a CLI with the
    signal and namespace checks on top; this is the part a headless `--test` can
    run before the sim starts, so a mission that cannot possibly work does not
    burn a test window proving it.

    Loads the mission's own vocabulary FIRST -- that step is what makes the result
    trustworthy rather than noise. Without it the shipped corpus reports 174
    `unknown-field` warnings instead of 2.

    `cross_file` defaults OFF: that pass needs the mastlib signal scan only the CLI
    assembles, and the findings that should stop a run are the ERROR-class
    structural ones anyway.

    `use_stamp` skips a file whose bytes a mastlib already recorded as clean (see
    amd_stamp). A mission-folder file has no stamp, so the file an author is
    actually editing is always linted.
    """
    from sbs_utils.procedural.amd_vocab import load_mission_vocabulary
    from sbs_utils.procedural.amd_schema import (amd_vocabulary_snapshot,
                                                 amd_vocabulary_restore)

    root = os.path.abspath(mission_root)
    # BORROW the mission's vocabulary; do not keep it. This runs in the same process
    # that is about to run the mission, and pre-registering its fields changes the
    # ORDER they are declared in - which is enough to turn a passing mission into a
    # startup ValueError. See amd_vocabulary_snapshot.
    _snap = amd_vocabulary_snapshot()
    try:
        try:
            load_mission_vocabulary(root)
        except Exception:
            pass      # a mission whose module needs the engine still lints
        return _amd_lint_mission_inner(root, cross_file, use_stamp)
    finally:
        amd_vocabulary_restore(_snap)


def _amd_lint_mission_inner(root, cross_file, use_stamp):
    """The pass itself, with the mission's vocabulary loaded around it."""
    import glob as _glob
    from sbs_utils.procedural.amd import amd_read_text
    from sbs_utils.procedural.amd_core import parse as _core_parse
    from sbs_utils.procedural.amd_vocab import declared_addon_paths

    clean = set()
    if use_stamp:
        try:
            from sbs_utils.procedural.amd_stamp import amd_clean_digests, amd_digest
            clean = amd_clean_digests(declared_addon_paths(root))
        except Exception:
            clean = set()

    paths = sorted(_glob.glob(os.path.join(root, "**", "*.amd"), recursive=True))
    sources = {}
    for path in paths:
        try:
            sources[path] = amd_read_text(path)
        except Exception as e:
            sources[path] = e

    # The MISSION-WIDE symbol table, built before anything is linted. A reference
    # is only dangling if NO file in the mission defines it, and linting a file
    # alone cannot know that: without this, OpenUniverse reports 35 findings
    # instead of 2, and 33 of them point at records that do exist next door.
    known_keys = set()
    for text in sources.values():
        if isinstance(text, str):
            try:
                known_keys |= _core_parse(text).keys
            except Exception:
                pass

    out = []
    for path in paths:
        text = sources.get(path)
        if not isinstance(text, str):
            out.append((path, AmdFinding(0, ERROR, "unreadable", f"cannot read: {text}")))
            continue
        if clean:
            from sbs_utils.procedural.amd_stamp import amd_digest
            if amd_digest(text) in clean:
                continue
        for f in amd_lint(file_path=path, content=text, cross_file=cross_file,
                          known_keys=known_keys):
            out.append((path, f))
    return out


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
