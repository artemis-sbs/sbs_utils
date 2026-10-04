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
        if value in doc.keys or doc.path_resolves(value):
            return True
        # THE ARC IS IN THIS FILE, so the step has to be under it. The soft check below
        # asks only whether the LEAF exists somewhere, which is right for a path into
        # another file and wrong here: `Then: reveal salvage/home` was "resolved" by a
        # `home` typed under the wrong heading, the reveal found nothing, the arc was
        # left with one nested step - and the game was won when that one step finished.
        if value.split("/")[0] in doc.keys:
            return False
        return value.split("/")[-1] in known_keys
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
            "items": mast_item_keys(mast_sources),
            "quoted_words": _quoted_words(mast_sources)}


#: A string literal on one line. Roles are always written inside one ("tsn, station",
#: add_role(id, "lens")), so words found here are the mission's role vocabulary - and
#: code words (`len(`) are not, which is what keeps the plural check below honest.
_QUOTED = re.compile(r"\"([^\"\n]*)\"|'([^'\n]*)'")


def _quoted_words(mast_sources):
    """Lower-case words that appear inside string literals in the mission's sources."""
    words = set()
    for src in mast_sources or []:
        for m in _QUOTED.finditer(src):
            words.update(re.findall(r"[a-z][a-z0-9_]*", (m.group(1) or m.group(2) or "").lower()))
    return words


def _relic_waits(doc):
    """Signals a relic's `Starts when:` / `Opens when:` phrases wait on."""
    out = set()
    try:
        nodes = _relic_nodes(doc)
    except Exception:                                    # noqa: BLE001
        return out
    for _node, fields in nodes:
        for label in ("starts when", "starts_when", "when", "opens when", "opens_when"):
            if label in fields:
                words = str(fields[label][1]).replace(",", " ").split()
                if len(words) >= 2 and words[0].lower() == "signal":
                    out.add(words[1].strip().lower())
    return out


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

    # A signal something in the AMD WAITS on is handled, route or no route: a quest's
    # `Done when: signal X`, or a relic part's `Starts when:` / `Opens when:`. Flagging
    # those told an author to write an empty route for a signal that already did its job.
    waited = {r.value for r in doc.refs if r.kind == "wait_signal"} | _relic_waits(doc)
    for ref in doc.refs:
        if ref.kind == "signal" and source_index is not None:
            if ref.value in routes or ref.value in DRIVER_SIGNALS or ref.value in waited:
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


#: Trigger fields whose target word is singularized into a role (normalized label).
_TRIGGER_FIELDS = ("done_when", "starts_when", "fails_when", "goal", "when",
                   "fail_on_all_dead")

#: Plurals no suffix rule gets right. `_singular` strips the `s` (or does nothing), so
#: the role it looks for is never the one the author meant.
_IRREGULAR_PLURALS = {
    "mice": "mouse", "lice": "louse", "men": "man", "women": "woman",
    "people": "person", "children": "child", "geese": "goose", "feet": "foot",
    "teeth": "tooth", "oxen": "ox", "dice": "die", "cacti": "cactus",
    "fungi": "fungus", "nuclei": "nucleus", "radii": "radius", "alumni": "alumnus",
    "criteria": "criterion", "phenomena": "phenomenon", "vertices": "vertex",
    "indices": "index", "matrices": "matrix", "crises": "crisis", "analyses": "analysis",
    "theses": "thesis",
}


def _trigger_target(value):
    """The words a trigger singularizes into a role, lower-cased, or None.

    Mirrors `amd_trigger`'s token handling: drop the verb (or `all dead`), a leading
    count, and trailing numbers (a `reach <role> <radius>` radius)."""
    toks = str(value).replace(",", " ").split()
    if not toks:
        return None
    if len(toks) > 2 and toks[0].lower() == "all" and toks[1].lower() == "dead":
        toks = toks[2:]
    else:
        toks = toks[1:]
    if toks and toks[0].isdigit():
        toks = toks[1:]
    while toks and toks[-1].lstrip("-").isdigit():
        toks = toks[:-1]
    target = " ".join(toks).strip().lower()
    return target or None


def amd_lint_trigger_roles(doc, source_index=None):
    """Flag a trigger target the role singularizer gets wrong. WARNING.

    `_singular` only knows suffix rules, so an irregular plural (`destroy 2 mice` looks
    for the role `mice`, not `mouse`) or a `-ves` plural (`wolves` -> `wolve`) never
    names the real role. And a SINGULAR ending in
    `s` can be read as a plural (`scan 1 lens` -> `len`). Either way the trigger
    compiles, and never fires.

    The irregular and `-ves` cases are flagged always. The mangled-singular case needs
    evidence, since `guns` and `cameras` are fine: it is flagged only when the
    mission's string literals use the word AS WRITTEN and never the singularized form
    (needs `source_index`)."""
    from sbs_utils.procedural.amd_quest import amd_trigger, _resolve_role
    findings = []
    quoted = (source_index or {}).get("quoted_words")
    for node in doc.nodes:
        for lineno, raw, label, value in _fence_fields(node):
            field = label.lower().replace(" ", "_")
            if field not in _TRIGGER_FIELDS:
                continue
            if field == "fail_on_all_dead":
                # The whole value is the role here - no verb, no count.
                target = str(value).strip().lower() or None
                role = _resolve_role(target) if target else None
            else:
                parsed = amd_trigger(value)
                target = _trigger_target(value)
                role = parsed[1].get("role") if parsed else None
            if not target or not role:
                continue
            last = target.split()[-1]
            message = None
            if last in _IRREGULAR_PLURALS:
                message = (f"`{target}` is an irregular plural, so this trigger looks for "
                           f"the role `{role}` - write the role's singular "
                           f"(`{_IRREGULAR_PLURALS[last]}`) instead")
            elif last.endswith("ves") and len(last) > 4:
                message = (f"`{target}` becomes the role `{role}` (only the `s` is "
                           f"dropped) - write the role's singular instead, e.g. "
                           f"`{last[:-3]}f` / `{last[:-3]}fe`")
            elif (quoted is not None and role != target and target in quoted
                  and role not in quoted):
                message = (f"this trigger looks for the role `{role}` (`{target}` read as "
                           f"a plural), but the mission only ever uses `{target}` - a "
                           f"singular ending in `s` is not safe here. Name the role "
                           f"differently (e.g. `{target}_target`)")
            if message:
                col = len(raw.split(":", 1)[0]) + 1
                col += len(raw[col:]) - len(raw[col:].lstrip())
                findings.append(AmdFinding(lineno, WARNING, "trigger-role-plural", message,
                                           col=col, end_line=lineno,
                                           end_col=col + len(str(value))))
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
        # WHAT THE RECORD IS, when the parser already worked that out. A roster says
        # `crew` on its fence and its section is keyed whatever the author liked, so
        # guessing from the section name and the labels found nothing - and a closed enum
        # on a kind-line record (`Names: lokced`) was never checked at all.
        arch = node.kind or infer_archetype([lab for _l, _r, lab, _v in fields],
                                            _section_key(node))
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


#: Fields that make a record a PART of a relic - a room, a place, a thing in the way.
_RELIC_PART_FIELDS = ("chamber", "box", "solid", "point", "barrier", "prop", "passage to")


def _relic_section_above(node):
    """(section, depth) - the top-level relic section this node is under and how many
    levels down it sits (1 = directly under it, where the game reads). (None, 0) when no
    ancestor is one."""
    from sbs_utils.procedural.amd_schema import archetype_for_section
    depth = 0
    n = node
    while n is not None and n.parent is not None:
        depth += 1
        p = n.parent
        # A SECTION is a child of the document's own heading, which in turn hangs off the
        # parser's unnamed root.
        top = p.parent
        is_section = (top is not None and top.parent is not None
                      and top.parent.parent is None)
        if is_section and archetype_for_section(str(p.key)) == "relic":
            return p, depth
        n = p
    return None, 0


def amd_lint_relic_structure(doc):
    """Flag a relic record the GAME will not read, though every tool draws it. WARNING.

    The game reads a relic file one way: a top-level section of relics, and directly
    under it the relic and each of its parts, all at the same heading level, each part
    naming its relic. The plan view and the rest of this linter are more forgiving - they
    find a relic record wherever it is - so each of these was clean, was drawn, and built
    nothing:

    * a room with one hash too many (it becomes a child of the room above it), or one too
      few (it leaves the section, and takes every room after it along);
    * a room with no `Relic:` line - read as a second, empty relic;
    * a relic outside any relics section.
    """
    findings = []
    typed = {id(node): fields for node, fields in _relic_nodes(doc)}
    for node in doc.nodes:
        fields = typed.get(id(node))
        if fields is None:
            # NOT typed as a relic record - which is exactly what happens to a room that
            # has fallen out of its section: with one hash too few it IS a section, and
            # everything after it is its child. It still says what it was meant to be.
            fields = {}
            for lineno, raw_line, label, value in _fence_fields(node):
                if raw_line[:1] not in (" ", "	"):
                    fields[label.strip().lower()] = (lineno, value)
            if not ("relic" in fields
                    and any(f in fields for f in _RELIC_PART_FIELDS)):
                continue
        if not fields:
            continue
        is_part = "relic" in fields
        has_shape = [f for f in _RELIC_PART_FIELDS if f in fields]
        where = node.display_span or node.span
        section, depth = _relic_section_above(node)
        if section is None:
            if is_part or has_shape:
                findings.append(AmdFinding.at(
                    where, WARNING, "relic-outside-section",
                    f"`{node.display}` is not inside a relics section, so the game does "
                    f"not read it. Check the number of hashes on its heading: a relic "
                    f"and its rooms all sit one level below `## [Relics](relics)`"))
            continue
        if depth > 1:
            findings.append(AmdFinding.at(
                where, WARNING, "relic-part-level",
                f"`{node.display}` is nested under `{node.parent.display}`, and the game "
                f"reads a relic and its rooms only from directly under "
                f"`{section.display}`. Give this heading {section.level + 1} hashes, the "
                f"same as the relic itself"))
            continue
        if not is_part and "loc" in fields:
            ln, value = fields["loc"]
            got = len(_relic_nums(value))
            if got < 3:
                findings.append(AmdFinding(
                    ln, WARNING, "relic-bad-loc",
                    f"`Loc:` needs 3 numbers - across, height, along - and has {got}, "
                    f"so it is not read and `{node.display}` is built at 0, 0, 0"))
        if has_shape and not is_part:
            findings.append(AmdFinding.at(
                where, WARNING, "relic-part-no-owner",
                f"`{node.display}` has a `{has_shape[0].capitalize()}:` line and no "
                f"`Relic:` line, so it is read as a relic of its own with no rooms. Add "
                f"`Relic: <the relic's key>` to its fence"))
    return findings


#: Fields that belong to the RUIN, and do nothing written on one of its parts.
_RELIC_ONLY_FIELDS = ("seed", "debris", "gaps", "plate", "atmosphere", "loc", "containment")
_YES_NO = ("yes", "no", "true", "false", "on", "off", "1", "0")


_FIELD_SHAPED = re.compile(r"^([A-Z][A-Za-z]*(?: [A-Za-z]+){0,2}):\s+\S")


def amd_lint_fields_below_fence(doc):
    """Flag a FIELD written below the closing `---`, where it is only prose. WARNING.

        ### [The Way In](way_in)
        ---
        Relic: hollow
        Point: 0, 0, -700
        ---
        Roles: entrance            <- below the fence: part of the note, not a field

    A writer told to "add a line" adds it at the end. The record parses, lint was clean,
    and the line does nothing - here the ruin's name stays off the map. Only the lines
    that open the body are judged, and only a label that IS a field of this kind of
    record: prose that happens to contain a colon further down is left alone, and so is
    dialogue, whose body is speech.
    """
    try:
        from sbs_utils.procedural.amd_schema import amd_is_declared
    except Exception:                                   # noqa: BLE001
        return []
    findings = []
    for node in doc.nodes:
        kind = str(getattr(node, "kind", "") or "").strip().lower()
        if not kind or kind == "dialogue" or not node.fence_lines:
            continue
        for lineno, raw in (node.body_lines or []):
            line = raw.strip()
            if not line:
                continue
            m = _FIELD_SHAPED.match(line)
            if m is None:
                break                            # prose has begun: stop looking
            label = m.group(1)
            try:
                declared = amd_is_declared(label.lower(), kind)
            except Exception:                           # noqa: BLE001
                declared = False
            if not declared:
                break
            findings.append(AmdFinding(
                lineno, WARNING, "field-below-fence",
                f"`{label}:` is a field, and this line is BELOW the closing `---`, so it "
                f"is read as part of the note and does nothing. Move it up, between the "
                f"two `---` lines"))
    return findings


_START_ONLY_STATES = ("at_once", "accepted", "revealed")
_FINISH_FIELDS = ("done when", "goal", "complete after", "done_when", "complete_after")


def amd_lint_start_only(doc):
    """Flag a quest that a trigger STARTS and nothing can FINISH. WARNING.

    `When:` is short for `Starts when:`. It used to be the trigger that completed a step,
    and a chain written the old way still reads like one:

        #### [Storm's First Lead](ep1_go)
        ---
        State: secret
        When: reach 2, -1
        Then: reveal beacon_arc/ep1_approach
        ---

    The ship arrives, the step STARTS, and that is all: with no `Done when:` it stays
    active for good, its `Then:` never happens and its reward is never paid. Nothing is
    logged, because nothing went wrong that the game can see.

    A quest with steps of its own is left alone - it finishes when they do.
    """
    try:
        from sbs_utils.procedural.amd_quest import amd_trigger
    except Exception:                                   # noqa: BLE001
        return []
    findings = []
    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").lower() != "quest" or not node.fence_lines:
            continue
        if any(str(getattr(c, "kind", "") or "").lower() == "quest" for c in node.children):
            continue
        fields = _plain_fields(node)
        if any(f in fields for f in _FINISH_FIELDS):
            continue
        for label in ("when", "starts when"):
            for lineno, value in fields.get(label, []):
                try:
                    trig = amd_trigger(value)
                except Exception:                        # noqa: BLE001
                    trig = None
                if trig is None or trig[0] in _START_ONLY_STATES:
                    continue
                word = "When" if label == "when" else "Starts when"
                lost = [w for w, f in (("its `Then:` never happens", "then"),
                                       ("its reward is never paid", "reward"),
                                       ("its reward is never paid", "pays"))
                        if f in fields]
                findings.append(AmdFinding(
                    lineno, WARNING, "quest-never-finishes",
                    f"`{word}: {value}` STARTS `{node.display}`"
                    + (" (`When:` is short for `Starts when:`)" if label == "when" else "")
                    + ", and nothing here finishes it: it stays active for good"
                    + ("; " + " and ".join(dict.fromkeys(lost)) if lost else "")
                    + f". If this is what finishes it, write `Done when: {value}`"))
    return findings


_SIDE_STOCK_WORDS = frozenset(("*", "all", "everyone", "players", "player", "civilians",
                               "civilian", "civs"))


def amd_lint_sides(doc, keys=None, mast_sources=None):
    """Flag a side key that names no side. WARNING.

    A side is named by its KEY - the word in round brackets on its heading - in three
    places: another side's `Enemies:` / `Allies:` / `Neutral:` line, and `Side:` on a
    landmark. A key nothing declares is not an error anywhere: the relation is not made,
    the landmark is on no side, and the crew sees a contact that is `unknown` for good.

        Enemies: tsm                 a typo
        Enemies: tsn guild           no comma: one side called "tsn guild"
        Side: braker                 on a landmark

    Judged only in a file that declares sides, and against every key in the mission plus
    every quoted word in its MAST (a side made by `prefab_side_generic` there counts).
    """
    sides = [n for n in doc.nodes
             if str(getattr(n, "kind", "") or "").lower() == "side" and n.fence_lines]
    if not sides:
        return []
    known = {str(n.key).strip().lower() for n in sides} | set(_SIDE_STOCK_WORDS)
    known |= {str(k).strip().lower() for k in (keys or ())}
    known |= {w.lower() for w in re.findall(r"[\"']([A-Za-z_][\w]*)[\"']",
                                            "\n".join(mast_sources or []))}
    declared = ", ".join(sorted(str(n.key) for n in sides))
    findings = []

    def judge(lineno, label, value):
        for word in [w.strip() for w in str(value).split(",") if w.strip()]:
            if word.lower() in known:
                continue
            why = ("has a space in it, so it is read as ONE side called all of that. Put "
                   "a comma between sides" if " " in word else
                   "is not a side in this mission")
            findings.append(AmdFinding(
                lineno, WARNING, "dangling-side",
                f"`{label}: {word}` - `{word}` {why}. A side is named by its key, the "
                f"word in round brackets on its heading. Declared here: {declared}"))

    side_ids = {id(n) for n in sides}
    for node in doc.nodes:
        fields = _plain_fields(node)
        if id(node) in side_ids:
            for label in ("enemies", "allies", "neutral"):
                for lineno, value in fields.get(label, []):
                    judge(lineno, label.capitalize(), value)
        elif str(getattr(node, "kind", "") or "").lower() == "landmark":
            for lineno, value in fields.get("side", []):
                judge(lineno, "Side", value)
    return findings


_QUEST_SHAPE_FIELDS = ("done when", "starts when", "fails when", "then", "objective")


def amd_lint_relic_strays(doc):
    """Flag a scene or a quest written inside a relic section. WARNING.

    The natural place to write what a place says is right under the place. But the relic
    reader takes EVERY record in its section for a ruin or a part of one: a record with no
    `Relic:` line is a ruin with no rooms - "it was not built" in the log - and the scene
    or the quest in it is never read by the loader it was written for.
    """
    try:
        from sbs_utils.procedural.amd_schema import archetype_for_section
    except Exception:                                   # noqa: BLE001
        return []
    findings = []
    for node in doc.nodes:
        parent = node.parent
        if parent is None or parent.key == "__root__":
            continue
        if archetype_for_section(str(parent.key or "").strip().lower()) != "relic":
            continue
        fields = _plain_fields(node)
        if "relic" in fields or "loc" in fields or any(f in fields for f in _RELIC_PART_FIELDS):
            continue                                     # a ruin, or a part of one
        speaks = any(l.strip().startswith("%") or (l.strip().startswith("-") and "](" in l)
                     for _n, l in (node.body_lines or []))
        asks = (str(getattr(node, "kind", "") or "").lower() == "quest"
                or any(f in fields for f in _QUEST_SHAPE_FIELDS))
        if not (speaks or asks):
            continue
        what, where = (("a scene", "Dialogue") if speaks and not asks else
                       ("a quest", "Quests"))
        findings.append(AmdFinding.at(
            node.display_span or node.span, WARNING, "relic-section-stray",
            f"`{node.display}` is {what}, and it is written in `{parent.display}`, where "
            f"every record is read as a ruin or a part of one: the game takes it for a "
            f"ruin with no rooms, and never reads it as {what}. Move it to the {where} "
            f"section"))
    return findings


def amd_lint_relic_dressing(doc):
    """Flag how a ruin is DRESSED where the game will quietly do something else. WARNING.

    Dressing is the part of a ruin an author looks at, and every one of these built a
    ruin, ran with an empty log, and looked wrong (or looked like nothing):

    * `Walls: plats` / `Walls: torgoth.zip, plates` - a style that is nearly one of the
      built-in five, or a file name;
    * `Seed: abc`, `Debris: lots`, `Gaps: 20%`, `Gaps: 2`, `Plate: 20` - a dial the game
      cannot read, or reads as something absurd (a 20-unit plate was 20,000 objects);
    * `Gaps:` on a room, `Walls:` on a point - a field on a record it does nothing on;
    * `Dress: generic-torus.obj 4`, `Dress:` on a room, a `Prop:` with no `Dress:` - a
      set piece that is never placed;
    * `Hidden: maybe`, two `Roles: entrance` points, `Roles: entrence`.
    """
    import difflib
    findings = []
    try:
        from .volume_dress import volume_style_names
        styles = tuple(volume_style_names())
    except Exception:                                   # noqa: BLE001
        styles = ()
    try:
        from .amd_relics import RELIC_PLATE_MIN, RELIC_PLATE_MAX
    except Exception:                                   # noqa: BLE001
        RELIC_PLATE_MIN, RELIC_PLATE_MAX = 150.0, 2000.0
    known_art = None
    entrances = {}                                       # relic key -> [(line, name)]
    part_keys = {}                                       # relic key -> {keys of its parts}
    for node, fields in _relic_nodes(doc):
        if "relic" in fields:
            part_keys.setdefault(str(fields["relic"][1]).strip(), set()).add(str(node.key))
    for node, fields in _relic_nodes(doc):
        is_part = "relic" in fields
        owner = str(fields["relic"][1]).strip() if is_part else str(node.key)
        is_room = "chamber" in fields or "box" in fields

        # --- which way a set piece looks ----------------------------------------------
        if "facing" in fields:
            ln, value = fields["facing"]
            text = str(value).strip()
            if text and len(_relic_nums(text)) < 3 and text not in part_keys.get(owner, ()):
                findings.append(AmdFinding(
                    ln, WARNING, "relic-facing-unknown",
                    f"`Facing: {text}` names no room, place or set piece of `{owner}`, so "
                    f"the piece looks at the middle of its own room as if the line were "
                    f"not there. Write a part's key, or a direction as three numbers"))

        # --- a style that is nearly a style -------------------------------------------
        if "walls" in fields and styles:
            ln, value = fields["walls"]
            for word in [w.strip().lower() for w in str(value).split(",") if w.strip()]:
                if word in styles:
                    continue
                if "." in word:
                    findings.append(AmdFinding(
                        ln, WARNING, "relic-walls-word",
                        f"`{word}` looks like a file name. `Walls:` takes the NAME of a "
                        f"style or a wall kit - one word, no extension"))
                    continue
                near = difflib.get_close_matches(word, styles, n=1, cutoff=0.7)
                if near:
                    findings.append(AmdFinding(
                        ln, WARNING, "relic-walls-word",
                        f"`{word}` is not a wall style. Did you mean `{near[0]}`? The "
                        f"styles are {', '.join(styles)}"))

        # --- the dials ---------------------------------------------------------------
        if not is_part:
            for label, kind in (("seed", "int"), ("debris", "count"), ("gaps", "fraction"),
                                ("plate", "plate")):
                if label not in fields:
                    continue
                ln, value = fields[label]
                text = str(value).strip()
                try:
                    number = float(text)
                except ValueError:
                    number = None
                bad = None
                if number is None:
                    bad = "is not a number, so the game uses its own"
                elif kind in ("int", "count") and number != int(number):
                    bad = "has to be a whole number"
                elif kind == "count" and number < 0:
                    bad = "cannot be less than 0"
                elif kind == "fraction" and not 0.0 <= number <= 1.0:
                    bad = ("is a fraction from 0 to 1 - 0.2 leaves out one plate in "
                           "five, 1 leaves out all of them")
                elif kind == "plate" and number != 0 and not (
                        RELIC_PLATE_MIN <= number <= RELIC_PLATE_MAX):
                    bad = (f"is a plate size in units, from {RELIC_PLATE_MIN:g} to "
                           f"{RELIC_PLATE_MAX:g}; the game uses the nearest of the two")
                if bad:
                    findings.append(AmdFinding(
                        ln, WARNING, "relic-dial-range",
                        f"`{label.capitalize()}: {text}` {bad}"))

        # --- a field on the wrong record --------------------------------------------
        if is_part:
            for label in _RELIC_ONLY_FIELDS:
                if label in fields:
                    findings.append(AmdFinding(
                        fields[label][0], WARNING, "relic-field-wrong-record",
                        f"`{label.capitalize()}:` belongs on the ruin itself, not on one "
                        f"of its parts - here it does nothing. Move it to `{owner}`"))
            if not is_room and "solid" not in fields:
                for label in ("walls", "art"):
                    if label in fields:
                        findings.append(AmdFinding(
                            fields[label][0], WARNING, "relic-field-wrong-record",
                            f"`{label.capitalize()}:` dresses a room, and this record is "
                            f"not a room - here it does nothing. What a place or a set "
                            f"piece looks like is `Dress:`"))

        # --- what a place says ----------------------------------------------------------
        # A scene opens when someone ARRIVES, and a route only ever ends at a `Point:`.
        # On a room, a prop or the ruin itself it is read, kept, and never opened.
        if "scene" in fields and "point" not in fields:
            findings.append(AmdFinding(
                fields["scene"][0], WARNING, "relic-field-wrong-record",
                "`Scene:` is what a PLACE says when someone arrives at it, and this record "
                "is not a place: nobody can be sent to a room, a set piece or the ruin "
                "itself, so the scene never opens. Put the line on a `Point:` record"))

        # --- set pieces ---------------------------------------------------------------
        if "prop" in fields:
            ln, value = fields["prop"]
            if len(_relic_nums(value)) < 3:
                findings.append(AmdFinding(
                    ln, WARNING, "relic-short-part",
                    f"'prop' needs 3 numbers, got {len(_relic_nums(value))} - nothing is "
                    f"placed"))
            if "dress" not in fields:
                findings.append(AmdFinding(
                    ln, WARNING, "relic-prop-no-dress",
                    "a `Prop:` is a place for a set piece, and with no `Dress:` line "
                    "there is nothing to put there"))
        if "dress" in fields:
            ln, value = fields["dress"]
            if is_room:
                findings.append(AmdFinding(
                    ln, WARNING, "relic-dress-on-room",
                    "`Dress:` places ONE set piece at a `Prop:`, a `Point:` or a "
                    "`Solid:`. On a room it places nothing - a room's look is `Walls:` "
                    "and `Art:`"))
            keys = []
            for entry in [e.strip() for e in str(value).split(",") if e.strip()]:
                word = entry.split()[0]
                keys.append(word)
                if "." in word:
                    findings.append(AmdFinding(
                        ln, WARNING, "relic-unknown-dress",
                        f"`{word}` looks like a file name. `Dress:` takes an art KEY, "
                        f"with no extension: `{word.rsplit('.', 1)[0]}`"))
            if known_art is None:
                known_art = _relic_known_art()
            plain = [k for k in keys if "." not in k]
            if known_art and plain and not any(k in known_art for k in plain):
                findings.append(AmdFinding(
                    ln, WARNING, "relic-unknown-dress",
                    f"`{', '.join(plain)}` names no art the game has, so nothing is "
                    f"placed here. (A wall kit is a `Walls:` style, not a set piece.)"))

        # --- places -------------------------------------------------------------------
        if "hidden" in fields:
            ln, value = fields["hidden"]
            if str(value).strip().lower() not in _YES_NO:
                findings.append(AmdFinding(
                    ln, WARNING, "relic-hidden-value",
                    f"`Hidden: {value}` is read as NOT hidden. Write `Hidden: yes`"))
        if "point" in fields and "roles" in fields:
            ln, value = fields["roles"]
            for word in [w.strip().lower() for w in str(value).split(",") if w.strip()]:
                if word == "entrance":
                    entrances.setdefault(owner, []).append((ln, str(node.display)))
                elif difflib.get_close_matches(word, ["entrance"], n=1, cutoff=0.8):
                    findings.append(AmdFinding(
                        ln, WARNING, "relic-role-near-entrance",
                        f"`{word}` is nearly `entrance`, the one role the game itself "
                        f"reads: it is where the ruin's name goes on the map. As "
                        f"written the marker stays at the ruin's `Loc:`"))
    for owner, found in entrances.items():
        for ln, name in found[1:]:
            findings.append(AmdFinding(
                ln, WARNING, "relic-two-entrances",
                f"`{name}` is a second `entrance` in `{owner}`: the map marker goes to "
                f"the first one in the file (`{found[0][1]}`), and this one is not "
                f"marked"))
    return findings


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
                        f"'{target}' is not a room of '{owner}' - a passage has to end "
                        f"on a room's key, and with this one going nowhere the game "
                        f"does not build '{owner}' at all"))
                nums = _relic_nums(group)
                if nums and nums[0] <= 0:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-bad-radius",
                        "a passage radius must be positive or nothing can fly down it"))
    # THE LOOK. Both of these fail silently and visibly - the relic builds, the mission
    # runs, and what you fly into is wrong. An unknown art key does not raise: the engine
    # falls back to the `unknown` mesh, so a typo is a ruin built out of question marks.
    # An unknown `Walls:` value falls back to plain rock, so a plated hall quietly is not.
    # Asked for only when a relic actually names art. Asking up front meant EVERY lint of
    # every mission went looking for the catalog - and where it cannot be found, said so
    # in the first line of the output, to a writer whose file had no relic in it.
    known_art = None
    for node, fields in _relic_nodes(doc):
        if "art" in fields and known_art is None:
            known_art = _relic_known_art()
        if "art" in fields and known_art:
            ln, value = fields["art"]
            for key in [k.strip() for k in str(value).split(",") if k.strip()]:
                if key not in known_art:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-unknown-art",
                        f"'{key}' is not an art key the game has, so it is dropped and "
                        f"the room is dressed in the ruin's ordinary look instead"))
        # ATMOSPHERE. A word that is not a color used to be handed to the nebula spawner,
        # which picks one at random for a word it does not know - so a ruin authored
        # `violet` was a different color on every run. It now gets no cloud at all, and
        # the game says so; this is the same sentence before the game is started.
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
                        f"'{value}' is not a nebula color ({', '.join(known)}), so the "
                        f"ruin gets no cloud at all"))
        if "walls" in fields:
            ln, value = fields["walls"]
            # A LIST IS A FALLBACK CHAIN - `Walls: torgoth, plates` wears the art pack's
            # kit when the mission has it and plates when it does not. Kits come from a
            # pack lint cannot see, so only a chain with NO built-in style in it is one
            # that can end in plain rock.
            chain = [w.strip().lower() for w in str(value).split(",") if w.strip()]
            try:
                from .volume_dress import volume_style_names
                styles = volume_style_names()
            except Exception:                           # noqa: BLE001
                styles = ()
            if styles and chain and not any(w in styles for w in chain):
                findings.append(AmdFinding(
                    ln, "warning", "relic-unknown-walls",
                    f"'{value}' names no built-in wall style ({', '.join(styles)}) - "
                    f"without the art pack it names, this part falls back to plain rock. "
                    f"End the list with one: `{value}, plates`"))
        # HOW A SUIT OPENS IT. An unknown word is a tool nobody holds, so the barrier
        # reads as clearable to `relic-barrier-seals` and is not.
        if "clear with" in fields:
            ln, value = fields["clear with"]
            for entry in [e.strip() for e in str(value).split(",") if e.strip()]:
                bits = entry.split()
                word = bits[0].lower()
                if word in ("beam", "tether"):
                    continue
                if word == "check" and len(bits) >= 3 and _relic_nums(bits[2]):
                    continue
                findings.append(AmdFinding(
                    ln, "warning", "relic-unknown-clear",
                    f"'{entry}' is not a way to clear a barrier - use beam, tether, or "
                    f"check <skill> <dc>"))
    findings.extend(_lint_relic_web(doc))
    return findings


def _relic_layouts(doc):
    """Each relic in the document as plain geometry, read from the RAW fields.

    Not `relics_from_section`: that reads the parsed fence DATA, and the fence is only
    parsed into numbers when the document was loaded with the relic handler wired in. The
    linter loads documents generically, so `Chamber: 0, 0, 0, 900` is still a string here.
    Every other relic rule in this file reads the raw text for the same reason.
    """
    layouts = {}
    parts = []
    for node, fields in _relic_nodes(doc):
        key = str(getattr(node, "key", "") or "")
        if "relic" not in fields:
            layouts[key] = {"key": key,
                            "line": getattr(getattr(node, "span", None), "line", 1) or 1,
                            "chambers": {}, "boxes": {}, "solids": [], "passages": [],
                            "points": {}, "barriers": {}, "point_lines": {}}
        else:
            parts.append((node, fields, str(fields["relic"][1]).strip()))
    for node, fields, owner in parts:
        rec = layouts.get(owner)
        if rec is None:
            continue                       # dangling - relic-dangling-parent says so
        name = str(getattr(node, "key", "") or "")
        if "chamber" in fields:
            n = _relic_nums(fields["chamber"][1])
            if len(n) >= 4:
                rec["chambers"][name] = n[:4]
        if "box" in fields:
            n = _relic_nums(fields["box"][1])
            if len(n) >= 6:
                rec["boxes"][name] = n[:6]
        if "solid" in fields:
            value = str(fields["solid"][1])
            words = [w for w in value.replace(",", " ").split() if not _relic_nums(w)]
            rec["solids"].append([(words[0].lower() if words else "sphere")]
                                 + _relic_nums(value))
        if "point" in fields:
            n = _relic_nums(fields["point"][1])
            if len(n) >= 3:
                roles = [r.strip().lower()
                         for r in str(fields.get("roles", (0, ""))[1]).split(",")
                         if r.strip()]
                hidden = str(fields.get("hidden", (0, ""))[1]).strip().lower() in (
                    "yes", "true", "on", "1")
                rec["points"][name] = [n[0], n[1], n[2], roles, name, hidden]
                rec["point_lines"][name] = fields["point"][0]
        if "barrier" in fields:
            n = _relic_nums(fields["barrier"][1])
            if len(n) >= 4:
                opens = fields.get("opens when", fields.get("opens_when", (0, "")))[1]
                clears = fields.get("clear with", fields.get("clear_with", (0, "")))[1]
                rec["barriers"][name] = [n[0], n[1], n[2], n[3],
                                         str(opens).strip(), str(clears).strip(), name]
        if "passage to" in fields:
            for group in str(fields["passage to"][1]).split(","):
                words = [w for w in group.replace(",", " ").split()
                         if not _relic_nums(w)]
                if not words:
                    continue
                nums = _relic_nums(group)
                rec["passages"].append([name, words[0], nums[0] if nums else 200.0])
    return list(layouts.values())


def _lint_relic_web(doc):
    """Build each relic's RAIL WEB and ask it what is unreachable. WARNING.

    THIS IS THE RULE WORTH HAVING. Every other rule in this file reads the text; this one
    solves the ruin the way the game will and reports what came out - so "part of this
    relic cannot be flown to" stops being something found by flying and becomes a line
    number.

    Three things it can say, and each has cost somebody a run:

    * **the web is in pieces** - a room that does not overlap anything, or abuts it with
      zero thickness. `sink`'s inlet ended at x=-2400 and its basin BEGAN at x=-2400: a
      containment test calls that one connected space, because a point on that plane is
      inside both, so the relic read as flyable while its only way in was sealed;
    * **a named place cannot be reached** from the entrance - the same fault, localised
      to the part an author can fix;
    * **a barrier seals the ruin** - it is shut, there is no way round, and nothing opens
      it. A hard lock is a legitimate thing to author, so this is a warning and says so.

    Quiet when the geometry cannot be built at all: the structural rules above already
    reported that, and a second complaint about the same line helps nobody.
    """
    findings = []
    try:
        from .rails import (rail_barrier, rail_build, rail_nodes, rail_reachable,
                            rail_remove)
        from .volume import volume_define, volume_remove
    except Exception:                                   # noqa: BLE001
        return findings

    for rec in _relic_layouts(doc):
        key, ln = rec["key"], rec["line"]
        if not (rec["chambers"] or rec["boxes"]):
            continue                                    # nothing to solve
        name = "__lint__%s" % key
        try:
            volume_define(name, chambers=rec["chambers"], passages=rec["passages"],
                          boxes=rec["boxes"], solids=rec["solids"])
        except Exception:                               # noqa: BLE001
            continue                                    # already reported structurally
        try:
            # A PLACE OUTSIDE EVERY ROOM. A point is where a mission puts something and
            # where a crew is sent; one written outside the open space is in the rock,
            # and nothing said so - it got its marker post there and simply could not be
            # reached.
            #
            # WELL outside, not on the line: a way in is authored AT a room's wall, where
            # the depth is exactly zero, and that is the right place for it.
            from .volume import volume_depth, volume_get
            built = volume_get(name)
            #
            # AND NEVER AN ENTRANCE. The way in is where a ship ARRIVES, and every shipped
            # ruin puts it outside the mouth, in open space, so science has a bearing
            # to call before anyone is inside.
            for pname, pv in rec["points"].items():
                if "entrance" in (pv[3] or ()):
                    continue
                if built is not None and volume_depth(built, (pv[0], pv[1], pv[2])) > 50.0:
                    findings.append(AmdFinding(
                        rec["point_lines"].get(pname, ln), "warning", "relic-point-outside",
                        "'%s' is not inside any room or passage of '%s' - it is in the "
                        "rock, where nothing can reach it. Its numbers are measured "
                        "from the ruin's `Loc:`, the same as a room's" % (pname, key)))
            places = {p: {"pos": (v[0], v[1], v[2]), "hidden": v[5]}
                      for p, v in rec["points"].items()}
            stats = rail_build(name, places=places)
            if stats is None:
                continue
            if stats["components"] > 1:
                findings.append(AmdFinding(
                    ln, "warning", "relic-disconnected",
                    "'%s' solves into %d separate pieces - part of it cannot be flown "
                    "to from the rest. Rooms must OVERLAP, not abut: a zero-thickness "
                    "join reads as connected and is not"
                    % (key, stats["components"])))
            for oname in stats.get("orphans") or ():
                findings.append(AmdFinding(
                    ln, "warning", "relic-unreachable-node",
                    "'%s' is in '%s' but nothing can see it - no route will ever end "
                    "there" % (oname, key)))
            # A SECRET NOBODY CAN EVER FIND. `Hidden:` takes a place off the crew's list
            # until they have been near it, and "been near it" is measured against the
            # role MARKER the point gets - so a hidden point carrying no `Roles:` gets no
            # marker, is never revealed, and is a destination that does not exist.
            #
            # It fails in complete silence: the relic builds, the place is on the web, a
            # route will even pass through it, and it is simply never offered. Measured
            # 2026-09-17 - with `Roles:` the place appears the moment a suit comes within
            # 1200 units; without, it never appears at all.
            for pname, pv in rec["points"].items():
                if pv[5] and not pv[3]:
                    findings.append(AmdFinding(
                        rec["point_lines"].get(pname, ln), "warning",
                        "relic-hidden-unreachable",
                        "'%s' is `Hidden:` but carries no `Roles:` - nothing marks it, so "
                        "nothing can ever reveal it and the crew will never be offered it"
                        % pname))
            entrance = _relic_entrance(rec)
            if entrance is None or entrance not in dict(rail_nodes(name)):
                continue
            reach = rail_reachable(name, entrance, open_only=False)
            for pname, _prec in rail_nodes(name, listed=True):
                if pname not in reach:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-unreachable-node",
                        "'%s' cannot be reached from '%s' in '%s'"
                        % (pname, entrance, key)))
            for bname, b in rec["barriers"].items():
                rail_barrier(name, bname, (b[0], b[1], b[2]), b[3])
            hard = [n for n, b in rec["barriers"].items() if not b[4] and not b[5]]
            if hard:
                shut = rail_reachable(name, entrance, open_only=True)
                lost = [p for p, _r in rail_nodes(name, listed=True)
                        if p in reach and p not in shut]
                if lost:
                    findings.append(AmdFinding(
                        ln, "warning", "relic-barrier-seals",
                        "'%s' shuts %d place(s) off (%s) behind %s, which has neither "
                        "`Opens when:` nor `Clear with:` - nothing can ever open it"
                        % (key, len(lost), ", ".join(sorted(lost)[:3]),
                           ", ".join(sorted(hard)))))
        finally:
            rail_remove(name)
            volume_remove(name)
    return findings


def _relic_entrance(rec):
    """The point a crew arrives at: one carrying the `entrance` role, else the first."""
    points = rec.get("points") or {}
    for pname, pt in points.items():
        roles = pt[3] if len(pt) > 3 else []
        if "entrance" in [str(r).lower() for r in (roles or [])]:
            return pname
    return next(iter(points), None)





def _relic_known_art():
    """Every shipData key, or an empty set when there is no shipData to ask.

    Empty means SAY NOTHING. `sbs lint` runs outside the game, where the art catalog may
    not be reachable at all, and a linter that reports every key as unknown because it
    could not find the file is worse than one that stays quiet.

    SAY NOTHING includes not ASKING. `get_ship_data` treats a missing catalog as an
    install fault - it logs "could not read ship data ... Check the Artemis install path"
    and caches an empty ship table for the rest of the process. Both are right inside the
    game and wrong here: under the CLI `exe_dir` is the Python program's folder, so the
    file is simply not where the library looks. Look first, and only load what is there.
    """
    try:
        from . import ship_data
        if ship_data.ship_data_cache is None:
            from ..fs import get_artemis_data_dir
            base = os.path.join(get_artemis_data_dir(), "shipData")
            # The same three spellings `load_data` tries, in its order.
            if not any(os.path.exists(base + ext) for ext in (".yaml", ".yml", ".json")):
                return set()
        return set((ship_data.get_ship_index() or {}).keys())
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
    # THE LIBRARY'S OWN VERBS. `give`, `take`, `open`, `reveal`, `check` and the combat
    # words are registered by the boarding modules as they import - which a mission that
    # never imported them by the time lint ran had not done, so a correct relic or away
    # scene lit up with "`check` is not an outcome verb". They are the library's, so the
    # library loads them before it judges.
    # AND THE QUEST VERBS. `accepts`, `completes` and `fails` are registered by
    # `quest_driver` as it imports. Loading the boarding modules above made the registry
    # non-trivial, so the "nothing but the built-in is loaded" guard below stopped
    # tripping - and a plain mission with no vocabulary file of its own was told that
    # `; completes my_quest` in a hail does nothing, which is exactly what it does do.
    for _mod in ("boarding_props", "boarding_checks", "boarding_combat", "quest_driver"):
        try:
            __import__("sbs_utils.procedural." + _mod)
        except Exception:                                # noqa: BLE001
            pass
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
                if verb == "learn" and len(outcome) < 2:
                    # `_boarding_learn_outcome` returns without recording anything, so
                    # the reading the choice exists to give is never counted.
                    findings.append(AmdFinding(
                        lineno, WARNING, "learn-nothing",
                        "`learn` names no fact, so nothing is recorded and `learned` "
                        "does not go up. Write `; learn <name>`."))
                    continue
                if verb in known:
                    continue
                findings.append(AmdFinding(
                    lineno, WARNING, "unknown-outcome-verb",
                    f"`{verb}` is not an outcome verb, so nothing applies it - the "
                    f"choice does everything except this. Known: "
                    f"{', '.join(sorted(known))}."))
    return findings


def amd_lint_guards(doc):
    """Flag a condition the game cannot read, on a choice or on a `%{...}` line. WARNING.

    A guard is a name, or `name op number` - nothing else (`dialogue_guard_ok`). Anything
    that is neither is answered False, every time, with no error: the choice is never
    offered and the line is never spoken. To the author that is a choice that vanished,
    and the file looks right because it very nearly is:

        - [Answer the log](last_entry) if learned => 2      the operator is backwards
        - [Read the tags](suits) if medical, learn suits    a comma where the `;` goes
        - [Read the tags](suits) ; learn suits if medical   the condition after the `;`

    The third parses differently and fails differently - the `if` is swallowed into the
    outcome, so the choice is offered to EVERYBODY and records a fact named
    `suits if medical` - but it is the same slip, so it is reported here too
    (`guard-after-outcome`).

    Only the SHAPE is judged. Whether `medcal` is a word anything answers to depends on
    the mission's resolver, which a linter does not run.
    """
    try:
        from sbs_utils.procedural.amd import amd_body_variant
        from sbs_utils.procedural.amd_dialogue import (_dlg_parse_choice, _GUARD,
                                                       _BARE_GUARD)
    except Exception:
        return []

    def readable(guard):
        text = str(guard).strip()
        return bool(_BARE_GUARD.match(text) or _GUARD.match(text))

    how = "Write a name (`if medical`) or `name >= number` - the operators are >= <= == != > <."
    findings = []
    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").strip().lower() != "dialogue":
            continue
        for lineno, text in (node.body_lines or []):
            line = text.strip()
            if not line or line.startswith("//"):
                continue
            if line.startswith("-") and "](" in line:
                ch = _dlg_parse_choice(line) or {}
                guard = ch.get("guard")
                if guard and not readable(guard):
                    findings.append(AmdFinding(
                        lineno, WARNING, "unreadable-guard",
                        f"`if {guard}` is not a condition the game can read, so this "
                        f"choice is never offered. {how} An outcome goes after a `;`, "
                        f"not a comma."))
                for outcome in ch.get("outcomes") or []:
                    if "if" in [str(t).lower() for t in outcome[1:]]:
                        findings.append(AmdFinding(
                            lineno, WARNING, "guard-after-outcome",
                            f"the `if` is after the `;`, so it is read as part of "
                            f"`{outcome[0]}` and the choice is offered to everybody. "
                            f"Put the condition first: `- [..](..) if <condition> ; "
                            f"{outcome[0]} ...`."))
                continue
            if not (line.startswith("%") or line.startswith("{")):
                continue
            _text, gate = amd_body_variant(line)
            if gate and not readable(gate):
                findings.append(AmdFinding(
                    lineno, WARNING, "unreadable-guard",
                    f"`{{{gate}}}` is not a condition the game can read, so this line "
                    f"is never spoken. {how}"))
    return findings


_ANSWER_SHAPED = re.compile(r"^\s*(?:[-*]\s*\[|\[[^\]]*\]\s*\(|;)")
_QUEST_OUTCOMES = ("accepts", "completes", "fails")


def amd_lint_choices(doc, keys=None):
    """Flag an answer the game reads as something else, or sends at nothing. WARNING.

    A choice is exactly `- [words](target) if <condition> ; <outcomes>`. Near it are
    several shapes that parse - as a SPOKEN LINE, or as a choice with part of it thrown
    away - and say nothing:

        - [Not now, DS 1.]                       no round brackets: she SAYS this line
        * [We will tag her.](quill_offer)        a star for the dash: spoken
        ; accepts tag_hulk                       an outcome on a line of its own: spoken
        - [We will tag her.]() accepts tag_hulk  no `;`: the outcome is ignored
        - [We will.]() ; accepts tag_hulkk       no such quest: the answer does nothing
        - [We will.]() ; completes study         a step needs its arc: `first_contact/study`
        - [We will.]() ; reveal tag_hulk         `reveal` is for `Then:`; here it is `accepts`
        #### [The Offer](quill_offer)            a scene nested under a scene removes the
                                                 scene ABOVE it from the game
    """
    try:
        from sbs_utils.procedural.amd import RE_CHOICE
        from sbs_utils.procedural.amd_dialogue import _dlg_parse_choice
    except Exception:                                   # noqa: BLE001
        return []
    findings = []
    # Quests in THIS file, by the id the game files them under and by leaf key.
    paths, leaves, by_path = set(), {}, {}
    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").lower() != "quest" or not node.fence_lines:
            continue
        path = _quest_path(node)
        if path:
            paths.add(path)
            by_path[path] = node
            leaves.setdefault(str(node.key), set()).add(path)
    known = set(keys or ()) | set(doc.keys)

    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").strip().lower() != "dialogue":
            continue
        # A SECTION is not a scene, whatever notes its author wrote under its heading:
        # `## [Dialogue](dialogue)` with a paragraph of intent is the normal shape.
        top = node.parent
        is_section = (top is None or top.key == "__root__" or top.parent is None
                      or top.parent.key == "__root__")
        is_scene = (not is_section) and any(
            t.strip() and not t.strip().startswith("//")
            for _n, t in (node.body_lines or []))
        if is_scene:
            for child in node.children:
                if str(getattr(child, "kind", "") or "").lower() == "dialogue":
                    findings.append(AmdFinding.at(
                        child.display_span or child.span, WARNING, "scene-nested",
                        f"`{child.display}` is nested under the scene `{node.display}`, "
                        f"and a scene with a scene under it is read as a heading, not "
                        f"as a scene: `{node.display}` disappears from the game. Give "
                        f"this heading {node.level} hashes, the same as the scene above"))
        for lineno, text in (node.body_lines or []):
            line = text.strip()
            if not line or line.startswith("//"):
                continue
            m = RE_CHOICE.match(line)
            if m is None:
                if _ANSWER_SHAPED.match(line):
                    findings.append(AmdFinding(
                        lineno, WARNING, "choice-shape",
                        "this looks like an answer and is read as a SPOKEN line. An "
                        "answer is a dash, the words in square brackets, then round "
                        "brackets with nothing between them: `- [words](key)`. Outcomes "
                        "go on the same line, after a `;`"))
                continue
            rest = m.group("rest").split(";", 1)[0].strip()
            if rest and not rest.lower().startswith("if "):
                findings.append(AmdFinding(
                    lineno, WARNING, "choice-tail-ignored",
                    f"`{rest}` after the round brackets is neither a condition (`if "
                    f"...`) nor an outcome (after a `;`), so it is ignored. Put a `;` in "
                    f"front of an outcome"))
            ch = _dlg_parse_choice(line) or {}
            for outcome in ch.get("outcomes") or []:
                verb = str(outcome[0]).lower()
                toks = [str(t) for t in outcome[1:]]
                if verb == "reveal" and len(toks) == 1 and (toks[0] in paths
                                                            or toks[0] in leaves):
                    findings.append(AmdFinding(
                        lineno, WARNING, "outcome-quest-verb",
                        f"`; reveal {toks[0]}` does nothing to a quest: `reveal` is "
                        f"what `Then:` says. From an answer, write `; accepts "
                        f"{toks[0]}`"))
                if verb not in _QUEST_OUTCOMES:
                    continue
                if len(toks) != 1:
                    findings.append(AmdFinding(
                        lineno, WARNING, "outcome-quest-missing",
                        f"`; {verb}` needs ONE quest key after it"
                        + (f", and `{' '.join(toks)}` is {len(toks)} words. Use the "
                           f"key in round brackets on the quest's heading, not its name"
                           if toks else "")))
                    continue
                want = toks[0]
                if want in paths:
                    # AN ENDING THAT IS ALREADY RUNNING. The way to give a scene two
                    # endings is an answer that starts a hidden quest; written `at once`
                    # the quest was running from the first second, and was paid whichever
                    # way the scene went.
                    starts = [v.lower() for _l, v in
                              _plain_fields(by_path[want]).get("starts when", [])]
                    if verb == "accepts" and any(
                            v in ("at once", "immediately", "now", "start", "at start")
                            for v in starts):
                        findings.append(AmdFinding(
                            lineno, WARNING, "outcome-accepts-running",
                            f"`; accepts {want}` - that quest says `Starts when: "
                            f"{starts[0]}`, so it is running before anyone gives this "
                            f"answer, and it finishes whichever answer is given. A quest "
                            f"an answer starts says `Starts when: revealed`"))
                    continue
                nested = [p for p in leaves.get(want, ()) if p != want]
                if nested:
                    findings.append(AmdFinding(
                        lineno, WARNING, "outcome-quest-path",
                        f"`; {verb} {want}` - that quest is `{sorted(nested)[0]}` to "
                        f"the game, which looks for the exact path. Write `; {verb} "
                        f"{sorted(nested)[0]}`"))
                elif want.split("/")[0] not in known:
                    findings.append(AmdFinding(
                        lineno, WARNING, "outcome-quest-missing",
                        f"`; {verb} {want}` - no quest has the key `{want}`, so this "
                        f"answer does nothing. Check the spelling against the quest's "
                        f"heading"))
    return findings


_AMD_SECTION_CALL = re.compile(r"amd_section\(\s*[^,()]+,\s*[\"']([\w -]+)[\"']\s*\)")
_RELIC_FILE_SECTIONS = ("items", "dialogue", "cutscenes", "side_stories")
_TRIGGER_LABELS_SPACED = ("done when", "starts when", "fails when", "goal", "when")


#: Roles the engine and the library hand out themselves - never written in a mission's
#: own strings, so their absence from them proves nothing.
_STOCK_ROLES = frozenset((
    "station", "ship", "npc", "player", "terrain", "asteroid", "nebula", "mine",
    "pickup", "upgrade", "wreck", "friendly", "enemy", "raider", "civ", "civilian",
    "monster", "typhon", "black_hole", "cockpit", "fighter", "shuttle", "elite",
    "__player__", "__npc__", "__terrain__", "__space_object__"))


def amd_lint_mission_reads(doc, file_path=None, mast_sources=None, source_index=None):
    """Flag content the mission will never load, and a pointer at a key where the game
    wants a role. WARNING. Needs the mission's MAST, so it runs in a whole-mission lint.

    A mission's `story.mast` reads its `.amd` one section at a time, by key:
    `landmarks_spawn(amd_section(MISSION_DOC, "landmarks"))`. A section nothing asks for
    is not an error anywhere - its records are parsed, typed, linted clean and never
    used:

    * `## [Places](places)` where the story asks for `landmarks`      section-not-loaded
    * a landmark with no `Art:` (not placed), no `Loc:` (placed at the origin, inside
      whatever stands there), no `Kind:` (made as a station, and wearing that role)
    * `Done when: reach lifeboat 500` / `Scan of: lifeboat` where `lifeboat` is the
      landmark's KEY and it has no `Roles: lifeboat` - quests and scans look for a
      ROLE, so the step never finishes and the scan text never shows     role-is-a-key

    Silent for a file the mission's own MAST does not name (an addon reads those its own
    way), and whenever a section is read through a name lint cannot see.
    """
    findings = []
    text = "\n".join(mast_sources or [])
    name = os.path.basename(file_path) if file_path else ""
    if not text or not name or name not in text:
        return findings

    # --- sections nothing reads ------------------------------------------------------
    literal = set(m.group(1).strip().lower() for m in _AMD_SECTION_CALL.finditer(text))
    every_call_is_literal = text.count("amd_section(") == len(_AMD_SECTION_CALL.findall(text))
    reads_crew = "crew_load_amd(" in text or "crew_declare_amd(" in text
    reads_relics = any(w in text for w in ("relics_spawn(", "relics_load(", "relics_build("))
    if literal and every_call_is_literal:
        from sbs_utils.procedural.amd_crew import CREW_KINDS
        from sbs_utils.procedural.amd_schema import archetype_for_section
        for node in doc.nodes:
            top = node.parent
            if top is None or top.key == "__root__":
                continue
            if not (top.parent is None or top.parent.key == "__root__"):
                continue                                   # not a top-level section
            key = str(node.key or "").strip().lower()
            if key in literal:
                continue
            if not node.children:
                # No records under it. Either an empty section (nothing lost), or a
                # RECORD written with one hash too few - which is now a section of its
                # own that nothing reads, and everything it said is lost.
                if any(":" in l for _n, l in (node.fence_lines or [])):
                    findings.append(AmdFinding.at(
                        node.display_span or node.span, WARNING, "section-not-loaded",
                        f"`{node.display}` has {node.level} hashes, which makes it a "
                        f"section of its own, and nothing in this mission reads a "
                        f"section keyed `{node.key}`. If it is a record, give its "
                        f"heading {node.level + 1} hashes so it sits inside the "
                        f"section above it"))
                continue
            if any(l.strip().lower().startswith(("file:", "files:"))
                   for _n, l in (node.fence_lines or [])):
                continue                                   # a table of contents
            if reads_crew and (_own_kind_word(node) in CREW_KINDS or key in CREW_KINDS):
                continue
            if any("for" in _plain_fields(c) for c in node.children):
                continue             # personal quests: `stories-not-handed-out` says how
            if reads_relics and (archetype_for_section(key) == "relic"
                                 or key in _RELIC_FILE_SECTIONS):
                continue
            findings.append(AmdFinding.at(
                node.display_span or node.span, WARNING, "section-not-loaded",
                f"nothing in this mission reads a section keyed `{node.key}`, so its "
                f"records are never loaded. The story asks this file for: "
                f"{', '.join(sorted(literal))}. Change the key in round brackets to one "
                f"of those, or add the line that reads it"))

    # --- landmarks the bulk spawner will not place as written --------------------------
    landmarks = [n for n in doc.nodes
                 if str(getattr(n, "kind", "") or "").lower() == "landmark" and n.fence_lines]
    by_key = {}
    roles_seen = set()
    for node in doc.nodes:
        for _ln, value in _plain_fields(node).get("roles", []):
            roles_seen.update(w.strip().lower() for w in value.split(",") if w.strip())
    # Only where the WHOLE section is placed by the library's bulk spawner. A mission that
    # places chosen records itself (`landmark_spawn(rec)`) or has its own builder (Open
    # Universe) is free to keep a landmark that is only a position or a key.
    spawned = "landmarks_spawn(" in text
    for node in landmarks:
        fields = _plain_fields(node)
        if not spawned:
            continue
        by_key[str(node.key).strip().lower()] = node
        parent = node.parent
        if parent is not None and parent.fence_lines                 and str(getattr(parent, "kind", "") or "").lower() == "landmark":
            findings.append(AmdFinding.at(
                node.display_span or node.span, WARNING, "landmark-record-level",
                f"`{node.display}` is nested under the landmark `{parent.display}`, so "
                f"it is not placed. Give this heading {parent.level} hashes, the same "
                f"as the landmark above it"))
            continue
        if any(v.strip().lower() == "point" for _l, v in fields.get("kind", [])):
            continue                 # a ZONE: a position the mission reads, not an object
        where = node.display_span or node.span
        if "art" not in fields:
            findings.append(AmdFinding.at(
                where, WARNING, "landmark-no-art",
                f"`{node.display}` has no `Art:` line, so it is not placed in the game "
                f"at all"))
        if "loc" in fields:
            ln, value = fields["loc"][0]
            got = len(_relic_nums(value))
            if got < 3:
                findings.append(AmdFinding(
                    ln, WARNING, "landmark-bad-loc",
                    f"`Loc:` needs 3 numbers - across, height, along - and has {got}, "
                    f"so it is not read and `{node.display}` is placed at 0, 0, 0"))
        elif "system" not in fields:
            findings.append(AmdFinding.at(
                where, WARNING, "landmark-no-loc",
                f"`{node.display}` has no `Loc:` line, so it is placed at 0, 0, 0 - "
                f"inside whatever stands there"))
        if "kind" not in fields:
            findings.append(AmdFinding.at(
                where, WARNING, "landmark-no-kind",
                f"`{node.display}` has no `Kind:` line, so it is made as a station and "
                f"wears the role `station` - a step that says `reach station` finishes "
                f"at it. Say what it is: `Kind: wreck`, `Kind: station`, `Kind: ship`"))

    # --- a key where the game wants a role ---------------------------------------------
    def points_at(lineno, word, what):
        word = word.strip().lower()
        node = by_key.get(word)
        if node is None or word in roles_seen:
            return
        findings.append(AmdFinding(
            lineno, WARNING, "role-is-a-key",
            f"`{word}` is the KEY of the landmark `{node.display}`, and {what} looks "
            f"for a ROLE. Nothing wears a role called `{word}`, so this matches "
            f"nothing. Add `Roles: {word}` to that landmark's fence"))

    # --- a role nothing wears ----------------------------------------------------------
    # The mission's role vocabulary: every word in a string literal in its own MAST, every
    # `Roles:` in this file, and the roles the engine hands out. A trigger or a scan that
    # names a word outside it matches nothing, ever - `reach lifebaot 500` is a step that
    # cannot finish, `Scan of: derelect` is a tab that never appears.
    #
    # Only in a mission built the template's way (its story places the Landmarks section
    # itself). A mission on an addon's world - Open Universe - gets its roles from relic
    # points, captains and sites in OTHER files, which this cannot see.
    vocabulary = None
    if spawned and source_index is not None and source_index.get("quoted_words"):
        vocabulary = set(source_index["quoted_words"]) | roles_seen | set(_STOCK_ROLES)
        vocabulary |= set(by_key)                # a key is reported by role-is-a-key

    def worn(lineno, word, what, exact=False):
        if vocabulary is None:
            return
        low = word.strip().lower()
        if not re.match(r"^[a-z_][a-z0-9_]*$", low):
            return
        forms = {low}
        if not exact:
            # A quest trigger makes its role singular before it looks; `Scan of:` is
            # read as written, so `derelicts` there is a role nothing wears.
            try:
                from sbs_utils.procedural.amd_quest import _singular
                forms.add(_singular(low))
            except Exception:                           # noqa: BLE001
                pass
        if forms & vocabulary:
            return
        findings.append(AmdFinding(
            lineno, WARNING, "role-nothing-wears",
            f"nothing in this mission wears a role called `{low}`, so {what} matches "
            f"nothing. Check the spelling against the `Roles:` line of the thing you "
            f"mean, or the roles in `story.mast`"))

    seen_scans = {}
    for node in doc.nodes:
        fields = _plain_fields(node)
        for lineno, value in fields.get("scan of", []):
            parts = [w.strip() for w in value.split(",") if w.strip()]
            if len(parts) != 1 or len(parts[0].split()) != 1:
                findings.append(AmdFinding(
                    lineno, WARNING, "scan-of-many",
                    f"`Scan of:` takes ONE role - one word - and `{value}` is read as "
                    f"a single role by that whole name, which nothing wears. Write one "
                    f"record for each role"))
                continue
            worn(lineno, parts[0], "this scan text", exact=True)
            tab = (fields.get("tab", [(0, "scan")])[0][1] or "scan").strip().lower()
            first = seen_scans.setdefault((parts[0].lower(), tab), lineno)
            if first != lineno:
                findings.append(AmdFinding(
                    lineno, WARNING, "duplicate-scan",
                    f"this is a second record for role `{parts[0]}` on the `{tab}` "
                    f"tab (the first is at line {first}), and the later one replaces "
                    f"the earlier. A record with no `Tab:` line is the `scan` tab. "
                    f"Put every reading for one tab in one record"))
            # A READING CANNOT WRAP. Each line of a scan record is one reading, so the
            # second half of a long sentence is offered to the crew as a reading of its
            # own - and half the time the first half is.
            previous = None
            for body_line, raw in (node.body_lines or []):
                line = raw.strip()
                if not line or line.startswith("//"):
                    previous = None
                    continue
                if previous == "%" and not line.startswith("%"):
                    findings.append(AmdFinding(
                        body_line, WARNING, "reading-wrapped",
                        "a reading has to stay on one line: this line is read as a "
                        "separate reading, so the crew may be shown half a sentence. "
                        "Join it to the line above, however long that gets"))
                previous = "%" if line.startswith("%") else "text"
            if "scan of" in _plain_fields(node.parent) if node.parent is not None else False:
                findings.append(AmdFinding.at(
                    node.display_span or node.span, WARNING, "scan-record-level",
                    f"`{node.display}` is nested under the scan record "
                    f"`{node.parent.display}`, so it is not read. Give it the same "
                    f"number of hashes"))
        for label in _TRIGGER_LABELS_SPACED:
            for lineno, value in fields.get(label, []):
                words = value.replace(",", " ").split()
                if len(words) < 2 or words[0].lower() not in (
                        "reach", "travel", "destroy", "kill", "scan", "survey", "dock",
                        "recover", "collect", "gather", "tow", "haul"):
                    continue
                for w in words[1:]:
                    if not re.match(r"^-?\d+(\.\d+)?%?$", w):
                        if w.lower() not in by_key:
                            worn(lineno, w, f"`{words[0]}`")
                        break

    if by_key:
        for node in doc.nodes:
            fields = _plain_fields(node)
            for label in _TRIGGER_LABELS_SPACED:
                for lineno, value in fields.get(label, []):
                    words = value.replace(",", " ").split()
                    if len(words) < 2:
                        continue
                    for w in words[1:]:
                        if not re.match(r"^-?\d+(\.\d+)?%?$", w):
                            points_at(lineno, w, f"`{words[0]}`")
                            break
            for lineno, value in fields.get("scan of", []):
                for w in value.split(","):
                    if w.strip():
                        points_at(lineno, w, "`Scan of:`")
    return findings


def amd_lint_kind_lines(doc):
    """Flag a bare word on a fence's first line that is not a kind of record. WARNING.

    One word alone on the first line of a fence says what KIND the record is (`Arc`,
    `Boss`, `crew`). Any single word is taken that way, known or not - so a value written
    without its label is swallowed as a kind nobody has heard of:

        ### [The Lifeboat](lifeboat)
        ---
        wreck                  meant `Kind: wreck`. Read as a kind line; the landmark
        Art: wreck             has no Kind, and is made as a station.
        ---
    """
    from sbs_utils.procedural.amd_schema import _kind_to_archetype, amd_known_kinds
    findings = []
    for node in doc.nodes:
        for lineno, raw in (node.fence_lines or []):
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            if ":" in line or len(line.split()) != 1:
                break
            if _kind_to_archetype(line) is None:
                near = ", ".join(sorted(amd_known_kinds())[:6])
                findings.append(AmdFinding(
                    lineno, WARNING, "unknown-kind-line",
                    f"`{line}` alone on the first line of a fence says what KIND of "
                    f"record this is, and it is not a kind the game knows. If it is a "
                    f"value, give it its label (`Kind: {line}`); a kind is a word like "
                    f"{near}..."))
            break
    return findings


_SKILL_ENTRY = re.compile(r"^[A-Za-z_][A-Za-z_ ]*\s+-?\d+$")

#: Words a guard reads as a JOB when no roster says otherwise - `boarding._STOCK_JOBS`.
_STOCK_JOB_WORDS = ("medical", "engineering", "security", "science", "helm", "weapons",
                    "comms", "captain", "command", "pilot", "doctor", "tactical",
                    "operations")


def _crew_rosters(doc):
    """The roster sections of a document: a `crew` kind line, else a crew section key."""
    from sbs_utils.procedural.amd_crew import CREW_KINDS
    declared = [n for n in doc.nodes if _own_kind_word(n) in CREW_KINDS]
    if declared:
        return declared
    return [n for n in doc.nodes if str(n.key or "").strip().lower() in CREW_KINDS]


def _plain_fields(node):
    """{label_lower: [(lineno, value), ...]} for a node's fence, every line kept."""
    out = {}
    for lineno, raw, label, value in _fence_fields(node):
        out.setdefault(label.strip().lower(), []).append((lineno, str(value).strip()))
    return out


def amd_lint_skills(doc):
    """Flag a skill number, a skill gate or a skill check the game cannot act on. WARNING.

    A crew roster says how good each person is (`Skills: engineering 4, science 1`), a
    boarding room gates a choice on it (`if skill science >= 3`) and rolls against it
    (`; check engineering 9 else core_dead`). Every one of these has a near miss that is
    read as something else, with no error:

    * `Skills: medical 4 science 3` is ONE skill called "medical 4 science"; `medical: 4`,
      `4 medical` and `science three` are dropped; a second `Skills:` line replaces the
      first; `Skills:` on the roster itself is nobody's.
    * `if skill sience >= 3`, `if skill science 3`, `if skills science >= 3` and
      `if science >= 3` (a JOB is 1 or 0) are never true, so the choice is never offered.
    * `check engineering nine`, `check zero g 9`, `check engineering >= 9` roll nothing and
      always succeed; `check enginering 9` rolls with 0; `else core_ded` sends a failed
      roll to a room that is not there, and the visit ends.
    * a crew member with one hash too many or too few is not on the roster at all.

    Skill WORDS are judged only against a roster in the same file - a mission that keeps
    its crew elsewhere is not second-guessed.
    """
    try:
        from sbs_utils.procedural.amd import amd_body_variant
        from sbs_utils.procedural.amd_dialogue import (_dlg_parse_choice, _GUARD,
                                                       _BARE_GUARD)
    except Exception:                                   # noqa: BLE001
        return []
    findings = []

    # --- the roster ----------------------------------------------------------------
    rosters = _crew_rosters(doc)
    roster_ids = {id(n) for n in rosters}
    skills, jobs = set(), set(_STOCK_JOB_WORDS)
    have_skills = False
    for roster in rosters:
        fields = _plain_fields(roster)
        for lineno, _value in fields.get("skills", []):
            findings.append(AmdFinding(
                lineno, WARNING, "skills-on-roster",
                "`Skills:` here is on the roster, not on a person, so nobody has them. "
                "Put the line in each crew member's own fence"))
        for member in roster.children:
            mf = _plain_fields(member)
            for _ln, value in mf.get("roles", []):
                jobs.update(w.strip().lower() for w in value.split(",") if w.strip())
            for _ln, value in mf.get("console", []):
                if value:
                    jobs.add(value.lower())
            lines = mf.get("skills", [])
            for lineno, _value in lines[1:]:
                findings.append(AmdFinding(
                    lineno, WARNING, "repeated-skills",
                    "`Skills:` is written twice on this person, and only the last line "
                    "counts. Put every skill on one line, with commas between"))
            for lineno, value in lines:
                have_skills = True
                for part in [p.strip() for p in value.split(",") if p.strip()]:
                    if not _SKILL_ENTRY.match(part):
                        findings.append(AmdFinding(
                            lineno, WARNING, "skills-shape",
                            f"`{part}` is not a skill and a number, so it is dropped. "
                            f"Write `Skills: engineering 4, science 1` - a name, a "
                            f"space, digits, and a comma between each"))
                        continue
                    skills.add(" ".join(part.split()[:-1]).lower())
    # A person who is not directly under a roster is not on it.
    if rosters:
        for node in doc.nodes:
            if id(node) in roster_ids or id(node.parent) in roster_ids:
                continue
            mf = _plain_fields(node)
            if "console" in mf and ("roles" in mf or "skills" in mf or "face" in mf):
                roster = rosters[0]
                findings.append(AmdFinding.at(
                    node.display_span or node.span, WARNING, "crew-member-level",
                    f"`{node.display}` reads like a crew member and is not directly "
                    f"under the roster `{roster.display}`, so that seat gets an "
                    f"automatic name instead. Give this heading {roster.level + 1} "
                    f"hashes"))
    known = skills | jobs

    def unknown(word):
        return have_skills and word.lower() not in known

    # --- the rooms -----------------------------------------------------------------
    # What the party can LEARN here, and who is on the roster: the two things a writer
    # reaches for in a condition that a condition cannot ask about.
    facts = set()
    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").strip().lower() != "dialogue":
            continue
        for _ln, body in (node.body_lines or []):
            body = body.strip()
            if body.startswith("-") and "](" in body:
                for outcome in (_dlg_parse_choice(body) or {}).get("outcomes") or []:
                    if str(outcome[0]).lower() == "learn" and len(outcome) > 1:
                        facts.add(" ".join(str(t) for t in outcome[1:]).strip().lower())
    people = _roster_words(doc)[0] - jobs

    def read_as_a_name(lineno, text, name, what):
        """A condition that is one long NAME nobody answers to. True when reported.

        A condition is a name, or `name op number`, and nothing else - so every one of
        these is read as a job nobody holds, is false for everyone, and says nothing:

            if medical and learned >= 2      two conditions joined
            if medical or engineering        the same
            if not medical                   there is no `not`
            if learned alive / if learned 3  `learned` only counts
            if alive                         a fact the party learns, asked for by name
            if hale / if Dr Hale             a person; `if` takes a job
        """
        parts = name.split()
        code = how = None
        if parts and (parts[0] == "not" or any(w in ("and", "or") for w in parts[1:])):
            code = "guard-joined"
            how = ("is more than one condition, and a condition is ONE name: `and`, `or` "
                   "and `not` are read as part of the name. Write one condition per "
                   "choice; a choice for two jobs is two choices that lead to one room")
        elif parts and parts[0] == "learned" and len(parts) > 1:
            code = "guard-learned-shape"
            how = ("is not how `learned` works: it only COUNTS what the party knows. "
                   "Write `if learned >= 3`")
        elif name in facts and name not in jobs:
            code = "guard-names-a-fact"
            how = (f"asks for `{name}`, which is something the party LEARNS, and a "
                   f"condition cannot ask for one fact by name - it is read as a job. "
                   f"Count them: `if learned >= 2`")
        elif name in people:
            code = "guard-names-a-person"
            how = (f"names a person. `if` takes a JOB from a `Roles:` line; `For:` on a "
                   f"quest is the one place a person's key or name goes")
        if code is None:
            return False
        findings.append(AmdFinding(lineno, WARNING, code,
                                   f"`if {text}` {how}. As written {what}"))
        return True

    def gate(lineno, guard, what):
        text = " ".join(str(guard).split())
        low = text.lower()
        m = _GUARD.match(text)
        if read_as_a_name(
                lineno, text,
                " ".join(m.group("lhs").split()).lower() if m is not None else low, what):
            return
        if m is None:
            if _BARE_GUARD.match(text) and (low.startswith("skill ") or low.startswith("skills ")
                                           or low in ("skill", "skills")):
                findings.append(AmdFinding(
                    lineno, WARNING, "skill-gate-shape",
                    f"`if {text}` has no sign and number, so it is read as a name "
                    f"nobody has and {what}. Write `if skill science >= 3`"))
            return
        lhs = " ".join(m.group("lhs").split()).lower()
        op, num = m.group("op"), int(m.group("num"))
        if lhs in ("skill", "skills") or lhs.startswith("skills "):
            findings.append(AmdFinding(
                lineno, WARNING, "skill-gate-shape",
                f"`if {text}` is not a skill gate, so {what}. The word is `skill`, then "
                f"which one: `if skill science >= 3`"))
        elif lhs.startswith("skill "):
            word = lhs[6:].strip()
            if unknown(word):
                findings.append(AmdFinding(
                    lineno, WARNING, "unknown-skill",
                    f"nobody on the roster has a skill or a job called `{word}`, so "
                    f"this is 0 for everyone. Check the spelling against the `Skills:` "
                    f"lines"))
        elif lhs in jobs:
            never = ((op == ">=" and num > 1) or (op == ">" and num >= 1)
                     or (op == "==" and num > 1))
            if never:
                findings.append(AmdFinding(
                    lineno, WARNING, "job-gate-never",
                    f"`{lhs}` on its own is a JOB, which is 1 or 0, so `if {text}` is "
                    f"never true and {what}. For how good someone is, write "
                    f"`if skill {lhs} {op} {num}`"))

    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").strip().lower() != "dialogue":
            continue
        previous = None
        for lineno, text in (node.body_lines or []):
            line = text.strip()
            if not line or line.startswith("//"):
                previous = None
                continue
            # A LINE CANNOT WRAP. Each `%` line is one thing the room may say, and the
            # second half of a long sentence, typed on the next line, is another: the
            # party is shown one half or the other.
            if previous == "%" and (line[0].isalnum() or line[0] in "\"'"):
                findings.append(AmdFinding(
                    lineno, WARNING, "line-wrapped",
                    "a `%` line has to stay on one line: this is read as a second line "
                    "of its own, so the party is shown one half of the sentence or the "
                    "other. Join it to the line above, however long that gets"))
            previous = "%" if line.startswith("%") else "other"
            if line.startswith("-") and "](" in line:
                ch = _dlg_parse_choice(line) or {}
                if ch.get("guard"):
                    gate(lineno, ch["guard"], "this choice is never offered")
                for outcome in ch.get("outcomes") or []:
                    if str(outcome[0]).lower() != "check":
                        continue
                    toks = [str(t) for t in outcome[1:]]
                    shape = (len(toks) in (2, 4) and re.match(r"^-?\d+$", toks[1])
                             and (len(toks) == 2 or toks[2].lower() == "else"))
                    if not shape:
                        findings.append(AmdFinding(
                            lineno, WARNING, "check-shape",
                            f"`check {' '.join(toks)}` is not `check <skill> <number>` "
                            f"or `check <skill> <number> else <room>`, so nothing is "
                            f"rolled and the choice always works. A skill is one word "
                            f"and the number is written in digits"))
                        continue
                    if unknown(toks[0]):
                        findings.append(AmdFinding(
                            lineno, WARNING, "unknown-skill",
                            f"nobody on the roster has a skill or a job called "
                            f"`{toks[0]}`, so everyone rolls this check with 0. Check "
                            f"the spelling against the `Skills:` lines"))
                    if len(toks) == 4 and toks[3] not in doc.keys:
                        findings.append(AmdFinding(
                            lineno, WARNING, "check-else-missing",
                            f"a failed roll goes to `{toks[3]}`, and no room here has "
                            f"that key - the party would be left nowhere and the visit "
                            f"would end. It only shows when a roll fails"))
                continue
            if line.startswith("%") or line.startswith("{"):
                _text, g = amd_body_variant(line)
                if g:
                    gate(lineno, g, "this line is never spoken")
    return findings


_TRIGGER_LABELS = {
    "done when": "done", "done_when": "done", "goal": "done",
    "fails when": "fails", "fails_when": "fails",
    "starts when": "starts", "starts_when": "starts",
}

#: What `Fails when:` has a watcher for. Anything else parses and is then dropped.
_FAIL_TRIGGERS = ("on_signal", "all_dead", "after")


def amd_lint_quest_triggers(doc):
    """Flag a `Starts when:` / `Done when:` / `Fails when:` the game cannot watch for.

    All three take one small grammar, and a value outside it is not an error anywhere:
    the line is dropped and the quest simply has no such trigger. So `Done when: ten
    minutes` is a quest with no way to finish, `Fails when: reach station 1000` is a
    quest that cannot fail that way, and `Starts when: reveal` (for `revealed`) is a
    quest left on the board - each with lint clean, each found by playing. WARNING.

    Also `Then:` written twice: the fence keeps one value per label, so the second
    replaces the first and a quest meant to reveal two steps reveals one.
    """
    try:
        from sbs_utils.procedural.amd_quest import amd_trigger
    except Exception:
        return []
    findings = []
    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").strip().lower() != "quest":
            continue
        # A REQUIRED STEP THAT CAN FAIL, AND WHOSE FAILURE ENDS NOTHING. The story waits
        # for every required step to COMPLETE; a failed one never will, and unless the
        # step is `Fatal:` its failure does not fail the story either. So the story can
        # no longer be won or lost - it just stops, with a quest list that looks alive.
        # Quiet when the story has a clock of its own: then it does end, at the deadline.
        own = _plain_fields(node)

        def _yes(label):
            return any(v.strip().lower() in ("true", "yes", "on", "1")
                       for _l, v in own.get(label, []))

        if (_yes("required") and "fails when" in own
                and not (_yes("fatal") or _yes("critical"))):
            parent = node.parent
            parent_fields = _plain_fields(parent) if parent is not None else {}
            if "fails when" not in parent_fields:
                findings.append(AmdFinding(
                    own["fails when"][0][0], WARNING, "required-step-dead-end",
                    f"`{node.display}` is required and can fail, and its failure ends "
                    f"nothing: the story it is part of can then never be finished and "
                    f"never fails. Add `Fatal: true` so failing it fails the story, give "
                    f"the story a `Fails when:` of its own, or take `Required:` off"))
        thens = []
        for lineno, _raw, label, value in _fence_fields(node):
            name = " ".join(label.strip().lower().split())
            if name == "then":
                thens.append(lineno)
                continue
            which = _TRIGGER_LABELS.get(name)
            if which is None or not value:
                continue
            try:
                trig = amd_trigger(value)
            except Exception:
                trig = None
            if trig is None:
                if which == "starts":
                    say = ("is not a way a quest starts, so it is left waiting on the "
                           "board. Write `at once`, `accepted`, `revealed`, or a trigger")
                elif which == "fails":
                    say = ("is not something the game can watch for, so this quest "
                           "cannot fail this way. `Fails when:` takes `signal <name>`, "
                           "a time, or `all dead <role>`")
                else:
                    say = ("is not something the game can watch for, so this quest has "
                           "no way to finish. Start with destroy, scan, dock, reach, "
                           "recover, tow or signal - or write a time")
                findings.append(AmdFinding(
                    lineno, WARNING, "unknown-trigger",
                    f"`{value}` {say}. A time is a number and a unit: `10 minutes`, "
                    f"`90 seconds`, `1 hour`."))
            elif which == "fails" and trig[0] not in _FAIL_TRIGGERS:
                findings.append(AmdFinding(
                    lineno, WARNING, "unsupported-fail-trigger",
                    f"`Fails when: {value}` is never checked - nothing watches for it - "
                    f"so this quest cannot fail this way. `Fails when:` takes `signal "
                    f"<name>`, a time, or `all dead <role>`."))
        for lineno in thens[1:]:
            findings.append(AmdFinding(
                lineno, WARNING, "repeated-then",
                "`Then:` is written more than once in this record, and only the last "
                "one counts - the earlier reveal or signal is lost."))
    return findings


def _quest_path(node):
    """The path the game files this quest under: its own key below each quest it is
    nested in - `salvage/approach/home`. None when any key on the way is already a
    slashed literal, which this cannot second-guess.

    An ancestor counts only when it is plainly a QUEST: typed as one AND carrying fields
    of its own. A `## [Quests](quests)` section is typed quest by its name and is a
    container, not a step on the path; so is a heading whose fence is a kind line and
    nothing else, which cannot be told from a section. Stopping there can only make the
    answer too SHORT, and the caller reports only an answer that is LONGER than what
    was written - so a doubtful ancestor costs a missed warning, never a false one.
    """
    if "/" in str(node.key):
        return None
    keys = [str(node.key)]
    n = node.parent
    while (n is not None and str(getattr(n, "kind", "") or "").lower() == "quest"
           and _fence_fields(n)):
        if "/" in str(n.key):
            return None
        keys.append(str(n.key))
        n = n.parent
    return "/".join(reversed(keys))


def amd_lint_reveal_paths(doc):
    """Flag a `Then: reveal` that finds its step in the FILE and not in the GAME.

    The game looks a revealed step up by its exact path, `arc/step`. Lint is more
    forgiving: a bare key resolves anywhere in the document, and a path may skip levels.
    So two ways of writing it were clean here and did nothing there:

        Then: reveal home              the step is `salvage/home`
        Then: reveal salvage/home      the step has five hashes: `salvage/approach/home`

    Nothing is revealed, the story cannot be finished - or, when the missing step was
    the only one left, the arc completes without it and the game is WON at once. WARNING.
    """
    findings = []
    by_key = getattr(doc, "_by_key_all", None)
    if by_key is None:
        return findings
    owners = {n.key: n for n in doc.nodes}
    for ref in doc.refs:
        if ref.kind != "reveal":
            continue
        owner = owners.get(ref.owner)
        if owner is None or str(getattr(owner, "kind", "") or "").lower() != "quest":
            continue
        value = str(ref.value).strip()
        if not value or value in doc.keys and "/" in value:
            continue                               # a literal slashed key: not ours
        if "/" in value:
            target = doc._match_path([s for s in value.split("/") if s])
        else:
            nodes = by_key.get(value) or ()
            target = nodes[0] if len(nodes) == 1 else None
        if target is None:
            continue                               # dangling or ambiguous: said elsewhere
        if str(getattr(target, "kind", "") or "").lower() != "quest":
            continue
        want = _quest_path(target)
        if want is None or want == value or want.count("/") <= value.count("/"):
            continue
        findings.append(AmdFinding.at(
            ref.span, WARNING, "reveal-path",
            f"`Then: reveal {value}` - that step is `{want}` to the game, which looks "
            f"for the exact path. Nothing will be revealed. Write `Then: reveal {want}`"
            + (", or check the number of hashes on the step's heading."
               if "/" in value else ".")))
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


def amd_lint_named_hulls(doc):
    """Flag a `Name hull_key` entry that will not make the ship the author meant.

    `Named: Iron Duke kralien_dreadnought` is a ship named `Iron` on a hull called `Duke`:
    the reader takes the first two words and drops the rest. Nothing fails - the flagship
    just never turns up. Applies to any field declared `named_hulls()`. WARNING.

    The hull is checked against shipData only when there is a catalog to ask; with none
    this says nothing rather than report every key as unknown."""
    from sbs_utils.procedural.amd_schema import field_schema, amd_traits_of
    findings = []
    known = None
    for node in doc.nodes:
        if not node.kind:
            continue
        traits = amd_traits_of(node.data)
        for lineno, raw, label, _value in _fence_fields(node):
            if raw[:1] in (" ", "\t"):
                continue                       # inside a nested block, not a field
            if field_schema(label, node.kind, traits).get("items") != "named_hull":
                continue
            offset = len(raw.split(":", 1)[0]) + 1
            for piece in raw[offset:].split(","):
                item = piece.strip()
                col = offset + (len(piece) - len(piece.lstrip()))
                offset += len(piece) + 1
                if not item:
                    continue
                words = item.split()
                if len(words) == 1:
                    findings.append(AmdFinding(
                        lineno, WARNING, "hull-name-shape",
                        f"`{item}` needs a name AND a hull - write `Name hull_key`",
                        col=col, end_line=lineno, end_col=col + len(item)))
                    continue
                if len(words) > 2:
                    fixed = "_".join(words[:-1]) + " " + words[-1]
                    findings.append(AmdFinding(
                        lineno, WARNING, "hull-name-shape",
                        f"`{item}` reads as a ship named `{words[0]}` on a hull called "
                        f"`{words[1]}` - a name is ONE word here. Write `{fixed}`",
                        col=col, end_line=lineno, end_col=col + len(item)))
                    continue
                if known is None:
                    known = {str(k).lower() for k in _relic_known_art()}
                if known and words[1].lower() not in known:
                    findings.append(AmdFinding(
                        lineno, WARNING, "unknown-hull",
                        f"`{words[1]}` is not a hull in shipData, so `{words[0]}` has "
                        f"nothing to fly",
                        col=col, end_line=lineno, end_col=col + len(item)))
    return findings


_STORIES_CALLS = ("stories=", "boarding_quests_grant(", "boarding_quests_open_unclaimed(")
_QUEST_START_FIELDS = ("starts when", "when", "state", "at start")
_QUEST_ASLEEP = ("accepted", "on accept", "when accepted", "offered", "idle")
_RUNNING_KIND_WORDS = ("objective", "beat", "cue")


def _roster_words(doc):
    """Every word a `For:` can name on this file's rosters, and the rosters' titles.

    What `boarding_quests._matches` answers to: a job (the member's `Roles:`, or their seat
    when the roster gave them none), the member's key, their name, and any tail of the name
    (`Dr Ines Hale` is also `Ines Hale` and `Hale`).
    """
    words, titles = set(), []
    for roster in _crew_rosters(doc):
        titles.append(str(roster.display or roster.key))
        for member in roster.children:
            mf = _plain_fields(member)
            roles = [w.strip().lower() for _ln, v in mf.get("roles", [])
                     for w in v.split(",") if w.strip()]
            if not roles:
                roles = [v.lower() for _ln, v in mf.get("console", []) if v]
            words.update(roles)
            if member.key:
                words.add(str(member.key).strip().lower())
            parts = str(member.display or "").lower().split()
            for i in range(len(parts)):
                words.add(" ".join(parts[i:]))
    return words, titles


def amd_lint_personal_quests(doc, file_path=None, mast_sources=None):
    """Flag a quest for one person that reaches nobody, and two outcomes run together.
    WARNING.

    A quest that says `For: medical` is handed to the one person aboard who answers to
    that word. Every near miss is silent - the file is clean, the run passes, the log is
    empty, and nobody has the quest:

        ; learn suits signal names_read     no comma: one fact with a long name, and the
                                            signal that finishes the quest is never sent
        For: medcal                         nobody answers to it
        For: medical, engineering           ONE word; this is a job called both
        Scope: shared  +  For:              the shared story holds it, and `For:` is ignored
        (no `Starts when:`)                 handed over asleep, with no Accept anywhere
        (no `Done when:`)                   nothing can finish it
        #### under another `For:` quest     handed to the person of the quest ABOVE it
        (no `For:` in a section of them)    handed to nobody
        the section is never handed out     `boarding_visit(..., stories=...)` is missing,
                                            or it is the section `quest_grant_amd` reads

    `For:` words are judged only against a roster in the same file - a mission that keeps
    its crew elsewhere is not second-guessed. The last check needs the mission's MAST.
    """
    findings = []
    try:
        from sbs_utils.procedural.amd_dialogue import (_dlg_parse_choice,
                                                       dialogue_outcome_verbs)
    except Exception:                                   # noqa: BLE001
        return findings

    # --- two outcomes with nothing between them -----------------------------------------
    verbs = {str(v).lower() for v in dialogue_outcome_verbs()} | {"signal", "learn"}
    for node in doc.nodes:
        if str(getattr(node, "kind", "") or "").strip().lower() != "dialogue":
            continue
        for lineno, text in (node.body_lines or []):
            line = text.strip()
            if not (line.startswith("-") and "](" in line):
                continue
            ch = _dlg_parse_choice(line) or {}
            for outcome in ch.get("outcomes") or []:
                toks = [str(tok) for tok in outcome]
                low = [tok.lower() for tok in toks]
                if "if" in low or low[0] == "check":
                    continue             # `guard-after-outcome` / `check-shape` say it
                for i in range(2, len(toks) - 1):
                    if low[i] != "and" and low[i] not in verbs:
                        continue
                    lost = " ".join(toks[i + 1:] if low[i] == "and" else toks[i:])
                    findings.append(AmdFinding(
                        lineno, WARNING, "outcome-run-together",
                        f"`{lost}` is read as part of `{' '.join(toks[:i])}`, so it never "
                        f"happens. Outcomes are separated by a comma: `; "
                        f"{' '.join(toks[:i])}, {lost}`"))
                    break

    # --- quests that say `For:` ---------------------------------------------------------
    people, rosters = _roster_words(doc)
    text = "\n".join(mast_sources or [])
    name = os.path.basename(file_path) if file_path else ""
    in_mission = bool(text and name and name in text)
    sections = {}                                        # id(section) -> (section, [quests])
    lost = set()                                         # quests written as sections
    for node in doc.nodes:
        fields = _plain_fields(node)
        if "for" not in fields or str(getattr(node, "kind", "") or "").lower() != "quest":
            continue
        lineno, want = fields["for"][0]
        parent = node.parent
        # ONE HASH TOO FEW. The quest is then a SECTION beside its own section, with the
        # sections of the file for brothers - and everything below would be said about
        # the wrong heading (the whole file "is not handed out", the roster "has no
        # `For:`"). Told apart from a real section of quests by those brothers: a quest
        # has steps or nothing under it, a section has records.
        top = parent is not None and (parent.parent is None
                                      or parent.parent.key == "__root__")
        if top and sum(1 for c in parent.children
                       if c is not node and c.children
                       and "for" not in _plain_fields(c)) >= 2:
            lost.add(id(node))
            findings.append(AmdFinding.at(
                node.display_span or node.span, WARNING, "for-section-level",
                f"`{node.display}` has {node.level} hashes, which makes it a section of "
                f"its own and not a quest in a section, so it is handed to nobody. Give "
                f"its heading {node.level + 1} hashes"))
            continue
        if parent is not None and id(parent) in lost:
            continue                     # under a heading already reported: fix that one
        if parent is not None and "for" in _plain_fields(parent):
            findings.append(AmdFinding.at(
                node.display_span or node.span, WARNING, "for-nested",
                f"`{node.display}` is nested under `{parent.display}`, so it is handed to "
                f"THAT quest's person as a step of it, and its own `For:` is ignored. Give "
                f"this heading {parent.level} hashes to make it a quest of its own"))
            continue
        section = parent if parent is not None and parent.key != "__root__" else None
        if section is not None:
            sections.setdefault(id(section), (section, []))[1].append(node)

        if people and want.lower() not in people:
            how = ("`For:` takes ONE word, so this is a job called all of that"
                   if "," in want or " and " in want.lower() else
                   "nobody on the roster answers to it")
            findings.append(AmdFinding(
                lineno, WARNING, "for-nobody",
                f"`For: {want}` - {how}, and this quest is handed to nobody. Write a job "
                f"from a crew member's `Roles:` line, their key, or their name. On "
                f"`{rosters[0]}`: {', '.join(sorted(people))}"))
        if any(v.lower() == "shared" for _ln, v in fields.get("scope", [])):
            findings.append(AmdFinding(
                fields["scope"][0][0], WARNING, "for-shared",
                "`Scope: shared` and `For:` on one quest: the shared story holds it, and "
                "nobody gets it as their own. Take out the `Scope:` line"))
        starts = [v.lower() for f in _QUEST_START_FIELDS for _ln, v in fields.get(f, [])]
        if _own_kind_word(node) not in _RUNNING_KIND_WORDS and (
                not starts or all(v in _QUEST_ASLEEP for v in starts)):
            findings.append(AmdFinding.at(
                node.display_span or node.span, WARNING, "for-not-started",
                f"`{node.display}` is handed to its person asleep: "
                + ("it has no `Starts when:`" if not starts else
                   f"it starts `{starts[0]}`")
                + ", and a quest for one person has no Accept button on any screen. "
                  "Write `Starts when: at once`"))
        if not node.children and not any(
                f in fields for f in ("done when", "goal", "fails when")):
            findings.append(AmdFinding.at(
                node.display_span or node.span, WARNING, "for-no-end",
                f"`{node.display}` has no `Done when:`, so nothing finishes it. To finish "
                f"it from a choice, write `Done when: signal <name>` here and `; signal "
                f"<name>` on the choice"))

    for section, quests in sections.values():
        key = str(section.key or "").strip()
        quoted = ('"' + key + '"') in text or ("'" + key + "'") in text
        granted = in_mission and any(
            ("quest_grant_amd(" in line or "quest_add_amd(" in line)
            and (('"' + key + '"') in line or ("'" + key + "'") in line)
            for line in text.splitlines())
        # A quest with no `For:` among them - but only where the section IS one of personal
        # quests. One `For:` typed under the ship's Quests is the stray there, and it is
        # reported as that (below); its neighbors are the ship's and are fine.
        others = [c for c in section.children
                  if c not in quests and "for" not in _plain_fields(c) and c.fence_lines
                  and not any(l.strip().lower().startswith("for:")
                              for _n, l in (c.body_lines or []))]
        if not granted and len(quests) >= len(others):
            for child in others:
                findings.append(AmdFinding.at(
                    child.display_span or child.span, WARNING, "story-no-for",
                    f"`{child.display}` is in a section of quests that each belong to one "
                    f"person, and has no `For:`, so it is handed to nobody. Add `For: "
                    f"<job>`"))
        if not in_mission:
            continue
        if granted:
            findings.append(AmdFinding.at(
                section.display_span or section.span, WARNING, "for-in-quests",
                f"`{section.display}` is the section the story gives to `quest_grant_amd`, "
                f"which hands every quest in it to the SHIP: `For:` on "
                f"`{quests[0].display}` is ignored. Move the quests that are for one "
                f"person into a section of their own (`## [Side Stories](side_stories)`) "
                f"and give that to `boarding_visit(..., stories=...)`"))
        elif not (quoted and any(call in text for call in _STORIES_CALLS)):
            findings.append(AmdFinding.at(
                section.display_span or section.span, WARNING, "stories-not-handed-out",
                f"nothing in this mission hands out `{section.display}`, so nobody gets "
                f"the quests in it. Give it to the visit: `boarding_visit(..., "
                f"stories=amd_section(MISSION_DOC, \"{key}\"))`"))
    return findings


def _own_kind_word(node):
    """A record's OWN kind line - the bare first word of its fence - lower-cased, else ''."""
    for _lineno, raw in (getattr(node, "fence_lines", None) or []):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        return line.lower() if (":" not in line and len(line.split()) == 1) else ""
    return ""


def _boss_names(doc):
    return [n for n in doc.nodes if n.level == 1 and _own_kind_word(n) == "boss"]


def amd_lint_boss_names(doc, file_path=None):
    """Flag a `Boss` whose name another boss file in the same folder already uses.

    A boss list offers bosses BY NAME, so two files that both say `# [Warlord](...)` put
    one entry in it - and which file that entry runs is whichever was read last. Copying
    a boss file and forgetting to rename the heading is the first thing a new author
    does, and nothing said so: the copy linted clean and simply was not there. WARNING.

    Needs the file's own path to find its neighbors, so a caller that lints bare text
    (the language server) does not get this one."""
    if not file_path:
        return []
    mine = _boss_names(doc)
    if not mine:
        return []
    import glob as _glob
    from sbs_utils.procedural.amd_core import parse as _core_parse
    here = os.path.abspath(file_path)
    taken = {}
    # The folder this file is in - and the folder read TOGETHER with it, when the mission
    # keeps an author's own files apart from its shipped ones (`common_data/bosses` beside
    # `maps/bosses`). One list is offered from both, so a name taken in either is taken.
    folders = [os.path.dirname(here)]
    try:
        from sbs_utils.procedural.amd_vocab import shared_neighbor_folders
        folders += shared_neighbor_folders(here)
    except Exception:                                   # noqa: BLE001
        pass
    others = []
    for folder in folders:
        others += sorted(_glob.glob(os.path.join(folder, "*.amd")))
    for other in others:
        if os.path.abspath(other) == here:
            continue
        try:
            theirs = _boss_names(_core_parse(amd_read_text(other)))
        except Exception:                               # noqa: BLE001
            continue        # a neighbor that cannot be read is its own finding, not ours
        for node in theirs:
            taken.setdefault(str(node.display).strip(), os.path.basename(other))
    findings = []
    for node in mine:
        other = taken.get(str(node.display).strip())
        if other:
            findings.append(AmdFinding.at(
                node.display_span or node.span, WARNING, "duplicate-boss-name",
                f"`{node.display}` is also the name of the boss in `{other}`. A boss "
                f"list offers bosses by name, so only one of the two can appear - give "
                f"this one a name of its own"))
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

    # A `Properties:` block's var= names are seeded into the task scope through
    # set_variable, so one named after a MAST global (var="range") kills that global for
    # the whole task. Imported locally: namespace_lint imports AmdFinding from here.
    try:
        from sbs_utils.procedural.namespace_lint import namespace_lint_var_bindings
        findings += namespace_lint_var_bindings(content)
    except Exception:
        pass   # a linter pass must never take the rest of the run down with it

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
        findings += amd_lint_relic_structure(doc)
        findings += amd_lint_relic_dressing(doc)
        findings += amd_lint_relic_strays(doc)
        findings += amd_lint_sides(doc, keys, mast_sources)
        findings += amd_lint_start_only(doc)
        findings += amd_lint_fields_below_fence(doc)
        findings += amd_lint_hails(doc)
        findings += amd_lint_then(doc)
        findings += amd_lint_quest_triggers(doc)
        findings += amd_lint_reveal_paths(doc)
        findings += amd_lint_dialogue_outcomes(doc)
        findings += amd_lint_guards(doc)
        findings += amd_lint_choices(doc, keys)
        findings += amd_lint_skills(doc)
        findings += amd_lint_personal_quests(doc, file_path, mast_sources)
        findings += amd_lint_kind_lines(doc)
        findings += amd_lint_mission_reads(doc, file_path, mast_sources, source_index)
        findings += amd_lint_callouts(doc)
        findings += amd_lint_images(doc, file_path)
        findings += amd_lint_named_hulls(doc)
        findings += amd_lint_boss_names(doc, file_path)
        findings += amd_lint_trigger_roles(doc, source_index)
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
