"""Namespace linter: flag name collisions in MAST's ONE shared global namespace.

`import file.py` execs every helper into a SINGLE global dict, and
`MastGlobals.register_mission_functions` does an unconditional
`MastGlobals.globals[fname] = func` - no warning, last writer wins. So two addons that
each define `market_sell_price` compile clean and then fail at RUNTIME, in whichever
addon did NOT get overwritten. Addon load order is non-deterministic, so the failure is
intermittent: it works until the two happen to load the other way around.

Four collision classes, in descending severity:

- ``ns-mast-var-collision`` (ERROR) - a .mast HARD-assigns a name that is also a
  function. This is the compile error "Variable assignment to a keyword <x>" and it
  DESYNCS the whole story (labels 0/N, still reporting PASS). `default x = ...` is
  exempt - core_nodes/assign.py allows it deliberately as a "module may not be loaded"
  fallback.
- ``ns-duplicate-function`` (ERROR) - the same function name defined in two addons.
- ``ns-shadows-library`` (ERROR) - a mission function overrides an `sbs_utils.procedural`
  global. Note a Python-level call inside the defining module still resolves to itself,
  so the tell is "works from Python, fails/misbehaves from MAST".
- ``ns-generic-name`` (WARNING) - a bare generic verb (`get_`/`save_`/`build_`) with no
  domain prefix. Advisory: the next addon to invent that name collides. Leading
  underscore does NOT make a helper private - `_dist` is as exported as `dist`.

Reuses amd_lint's AmdFinding so `sbs lint` prints these uniformly.
"""
import re

from .amd_lint import AmdFinding, ERROR, WARNING

# A top-level `def` in a mission helper. Leading underscore included on purpose: an
# underscore helper is registered as a MAST global exactly like a public one.
_DEF = re.compile(r"^def\s+(?P<name>\w+)\s*\(", re.M)

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
                "Prefix it with the addon name (the hangar_/hangar.py convention). A "
                "leading underscore does not make it private: MAST exports it too.")))

    return findings
