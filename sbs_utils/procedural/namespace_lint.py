"""Namespace linter: flag name collisions in MAST's ONE shared global namespace.

`import file.py` execs every helper into a SINGLE global dict, and
`MastGlobals.register_mission_functions` does an unconditional
`MastGlobals.globals[fname] = func` - no warning, last writer wins. So two addons that
each define `market_sell_price` compile clean and then fail at RUNTIME, in whichever
addon did NOT get overwritten. Addon load order is non-deterministic, so the failure is
intermittent: it works until the two happen to load the other way around.

Five collision classes, in descending severity:

- ``ns-mast-var-collision`` (ERROR) - a .mast HARD-assigns a name that is also a
  function. This is the compile error "Variable assignment to a keyword <x>" and it
  DESYNCS the whole story (labels 0/N, still reporting PASS). `default x = ...` is
  exempt - core_nodes/assign.py allows it deliberately as a "module may not be loaded"
  fallback.
- ``ns-label-collision`` (ERROR) - a .mast HARD-assigns a name that is also a top-level
  `== label ==`. The label is then hidden for the rest of that task, so
  `task_schedule(<x>)` is handed the value and dies in do_jump with
  `AttributeError: 'int' object has no attribute 'name'` - pointing at neither the label
  nor the assignment (LM #544). The compiler catches this too, once the whole story is
  in; this catches it in the editor, per file. Inline `--- labels` are NOT included:
  they live in their parent label's own table and were never in the namespace.
- ``ns-duplicate-function`` (ERROR) - the same function name defined in two addons.
- ``ns-shadows-library`` (ERROR) - a mission function overrides an `sbs_utils.procedural`
  global. Note a Python-level call inside the defining module still resolves to itself,
  so the tell is "works from Python, fails/misbehaves from MAST".
- ``ns-generic-name`` (WARNING) - a bare generic verb (`get_`/`save_`/`build_`) with no
  domain prefix. Advisory: the next addon to invent that name collides.
- ``ns-metadata-shadows-builtin`` (WARNING) - a `metadata:` key named after one of MAST's
  own globals (`range`, `random`, `sim`, ...). Metadata values are injected as task
  variables, so the key hides that global for the label's WHOLE body: `range: close or
  far` on the cloak ability is why `for i in range(6)` stopped working inside it (LM
  #657), and the error named the loop rather than the metadata.

Underscore-prefixed defs are NOT checked: since 2026-08-16 both registration paths skip
them, so `_dist` really is private and cannot collide with anything. Flagging it would be
telling authors to prefix a name that is already unreachable.

Reuses amd_lint's AmdFinding so `sbs lint` prints these uniformly.
"""
import re

from .amd_lint import AmdFinding, ERROR, WARNING

# A top-level `def` in a mission helper - PUBLIC ones only. An underscore def is no longer
# registered as a MAST global (mast_globals.register_mission_functions skips it, as
# import_python_module already did), so it cannot shadow a library global, cannot be
# duplicated across addons in any way that matters, and cannot collide with a .mast
# variable. It was that last one - A28's `_mine` against autoplay's `_mine = ...` - that
# made this rule worth having, and the fix removed the reason to lint for it.
_DEF = re.compile(r"^def\s+(?!_)(?P<name>\w+)\s*\(", re.M)

# A .mast assignment. `default` (and `default shared`) are EXEMPT - assign.py permits a
# default onto an existing global. Plain `shared x =` is a hard assign and is not.
_MAST_ASSIGN = re.compile(
    r"^(?P<indent>\s*)(?P<kw>default\s+shared|default|shared|assigned|client|temp)?\s*"
    r"(?P<name>[A-Za-z_]\w*)\s*=(?!=)")

# Generic leading tokens that claim a name no single addon should own.
_GENERIC = frozenset("""
get set load save make build draw render update init add remove clear find calc format
parse to is has do run show handle apply create new list count pick choose reset start
stop next prev main map test check send open close read write on fmt pct num val sum all
any first last name text side
""".split())

_ALLOW = re.compile(r"#\s*lint:\s*allow\s+(?P<codes>[\w\-, ]+)", re.I)

# A `metadata:` fenced block, and the top-level keys in it. Keys are at column 0 by the
# parser's own rule (an indented fence is "Unrecognized syntax"), which is also what keeps
# this from reading nested YAML - only the injected top-level names can shadow anything.
_METADATA_BLOCK = re.compile(r"^metadata:\s*`{3}[^\n]*\n(?P<body>.*?)^`{3}", re.S | re.M)
_METADATA_KEY = re.compile(r"^(?P<name>[A-Za-z_]\w*)\s*:", re.M)

# What a metadata key can actually shadow. NOT the Python builtins: MAST replaces
# __builtins__ with MastGlobals.globals (mast.py: {"__builtins__": _MG.globals}), so this
# table IS the whole vocabulary an expression can reach. That cuts both ways - `sum`,
# `float`, `id` and `type` are absent from it, so a key by those names shadows nothing and
# flagging one would be a false alarm; `random`, `math` and `sim` ARE in it, and a key
# named `sim` would take the simulation handle away from every line in the label.
#
# Kept to that table rather than widened to every library global. Measured against LM:
# metadata keys collide with the 1279 procedural globals in 3 places (`color`, `duration`,
# `face`), none of which call the function they hide - so widening buys ~10 warnings
# nobody can act on, which is how a rule stops being read.
_MAST_BUILTINS = frozenset("""
math json faces scatter random print dir itertools next len reversed int str hex
min max abs sim map filter list set dict tuple zip enumerate iter sorted range isinstance
""".split())


def _allowed(line, code):
    """True when the source line carries `# lint: allow <code>`."""
    m = _ALLOW.search(line or "")
    return bool(m) and code in [c.strip() for c in m.group("codes").replace(",", " ").split()]


def _def_sites(content):
    """[(name, line)] for every top-level def in one .py source."""
    out = []
    for m in _DEF.finditer(content):
        out.append((m.group("name"), content.count("\n", 0, m.start()) + 1))
    return out


def _hard_assigns(content):
    """[(name, line)] for .mast assignments that are NOT `default` (which is exempt)."""
    out = []
    for i, ln in enumerate(content.splitlines(), 1):
        m = _MAST_ASSIGN.match(ln)
        if not m or (m.group("kw") or "").startswith("default"):
            continue
        out.append((m.group("name"), i))
    return out


# A top-level label. Deliberately NOT `---` / `+++`: an inline label lives in its parent
# label's own dict (core_nodes/inline_label.py) and never enters the namespace, so
# flagging it would be a false positive. Route and `@` decorator labels are registered
# under mangled names carrying `/` and an id, which no assignment target can spell.
_MAST_LABEL = re.compile(r"^={2,}\s*(?P<name>[A-Za-z_]\w*)")


def _label_sites(content):
    """[(name, line)] for every top-level `== label ==` in one .mast source."""
    out = []
    for i, ln in enumerate(content.splitlines(), 1):
        m = _MAST_LABEL.match(ln)
        if m:
            out.append((m.group("name"), i))
    return out


def namespace_lint_project(py_sources, mast_sources=(), lib_globals=()):
    """Whole-mission namespace collisions - no single file can see these.

    Args:
        py_sources: iterable of ``(path, content)`` for addon-imported `.py` helpers.
            Path should be mission-relative so the first segment names the addon.
        mast_sources: iterable of ``(path, content)`` for the mission's `.mast`.
        lib_globals: iterable of `sbs_utils.procedural` function names (MAST globals).
            Pass the live set when available; empty disables the shadow check.

    Returns:
        list: ``(path, AmdFinding)`` pairs, anchored at each defining site.
    """
    lib = set(lib_globals or ())
    defs = {}          # name -> [(path, line)]
    lines_by_path = {}
    for path, content in py_sources:
        lines_by_path[path] = content.splitlines()
        for name, line in _def_sites(content):
            defs.setdefault(name, []).append((path, line))

    def _src_line(path, line):
        rows = lines_by_path.get(path) or []
        return rows[line - 1] if 0 < line <= len(rows) else ""

    mast_lines = {p: c.splitlines() for p, c in mast_sources}

    def _mast_line(path, line):
        rows = mast_lines.get(path) or []
        return rows[line - 1] if 0 < line <= len(rows) else ""

    def _addon(path):
        return str(path).replace("\\", "/").split("/")[0]

    findings = []

    # --- a .mast hard-assigns a function name -> compile error, story desyncs ---
    for path, content in mast_sources:
        for name, line in _hard_assigns(content):
            if name not in defs:
                continue
            where = ", ".join(p + ":" + str(ln) for p, ln in defs[name])
            findings.append((path, AmdFinding(
                line, ERROR, "ns-mast-var-collision",
                "\"" + name + "\" is a function (" + where + "), so assigning it here is "
                "the compile error \"Variable assignment to a keyword " + name + "\" - it "
                "desyncs the whole story (labels 0/N, still reporting PASS). Rename the "
                "variable, or use `default " + name + " = ...` if this is a "
                "module-may-not-be-loaded fallback.")))

    # --- a .mast hard-assigns a LABEL name -> the label is hidden for that task ---
    #
    # Whole-mission, like every rule here: the label may be in a different file or a
    # different addon from the assignment, which is exactly why a per-file check cannot
    # see it.
    labels = {}
    for path, content in mast_sources:
        for name, line in _label_sites(content):
            labels.setdefault(name, []).append((path, line))
    for path, content in mast_sources:
        for name, line in _hard_assigns(content):
            if name not in labels:
                continue
            if _allowed(_mast_line(path, line), "ns-label-collision"):
                continue
            where = ", ".join(p + ":" + str(ln) for p, ln in labels[name])
            findings.append((path, AmdFinding(
                line, ERROR, "ns-label-collision",
                "\"" + name + "\" is a label (" + where + "), so assigning it here hides "
                "the label for the rest of this task - `task_schedule(" + name + ")` "
                "would be handed the value instead. Rename the variable, or use "
                "`default " + name + " = ...` if this is a deliberate fallback.")))

    for name in sorted(defs):
        sites = defs[name]

        # --- same name in two addons -> last loaded wins, intermittently ---
        addons = sorted({_addon(p) for p, _ in sites})
        duplicated = len(addons) > 1
        if duplicated:
            where = ", ".join(p + ":" + str(ln) for p, ln in sites)
            for path, line in sites:
                if _allowed(_src_line(path, line), "ns-duplicate-function"):
                    continue
                findings.append((path, AmdFinding(
                    line, ERROR, "ns-duplicate-function",
                    "\"" + name + "\" is defined in " + str(len(addons)) + " addons ("
                    + where + "). MAST merges every addon into one global namespace, so "
                    "the last one loaded wins and the other addon's callers get the wrong "
                    "function - intermittently, since load order is not deterministic. "
                    "Prefix each with its addon name.")))

        # --- overrides a library global ---
        if name in lib:
            for path, line in sites:
                if _allowed(_src_line(path, line), "ns-shadows-library"):
                    continue
                findings.append((path, AmdFinding(
                    line, ERROR, "ns-shadows-library",
                    "\"" + name + "\" overrides the sbs_utils.procedural global of the "
                    "same name for every .mast in this mission. A Python call inside this "
                    "module still resolves to itself, so the symptom is \"works from "
                    "Python, wrong from MAST\". Prefix it, or delete it and import the "
                    "library one (an imported name is not re-registered as a MAST "
                    "global).")))
            continue  # the shadow is the actionable finding; don't also nag about style

        # --- bare generic name: nothing collides YET ---
        # A name already reported as a duplicate has its actionable finding; the style
        # nag on top of it is noise (one finding per name, as with the shadow above).
        token = name.lstrip("_").split("_")[0]
        if token in _GENERIC and not duplicated:
            path, line = sites[0]
            if _allowed(_src_line(path, line), "ns-generic-name"):
                continue
            findings.append((path, AmdFinding(
                line, WARNING, "ns-generic-name",
                "\"" + name + "\" starts with the generic \"" + token + "\" and claims "
                "that name for the WHOLE mission - the next addon to invent it collides. "
                "Prefix it with the addon name (the hangar_/hangar.py convention), or make "
                "it private with a leading underscore - those are not exported.")))

    # --- a metadata key shadows a builtin for its label's whole body ---
    #
    # Not a namespace collision like the rest of this file - it is scoped to one label -
    # but it is the same shape of bug and it fails the same way: the code reads correctly,
    # the name resolves to something else, and the error names a line that is not the
    # cause. It lives here because this is where `sbs lint` already walks the .mast.
    for path, content in mast_sources:
        for block in _METADATA_BLOCK.finditer(content):
            base = content[:block.start("body")].count("\n") + 1
            for key in _METADATA_KEY.finditer(block.group("body")):
                name = key.group("name")
                if name not in _MAST_BUILTINS:
                    continue
                line = base + block.group("body")[:key.start()].count("\n")
                if _allowed(_mast_line(path, line), "ns-metadata-shadows-builtin"):
                    continue
                findings.append((path, AmdFinding(
                    line, WARNING, "ns-metadata-shadows-builtin",
                    "metadata key \"" + name + "\" is one of MAST's own globals, and "
                    "metadata values are injected as task variables - so " + name + " is "
                    "no longer reachable anywhere in this label's body, and the error "
                    "lands on the line that USES it, not on this one. Rename the key "
                    "(ability_range, acquire_range) and update the body that reads it.")))

    return findings
