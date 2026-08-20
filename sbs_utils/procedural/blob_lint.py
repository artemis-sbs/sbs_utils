"""data_set linter: flag a blob read that is compared or `in`-tested without a guard.

The engine returns **None** for a data_set field that was never set. The mock returns a
typed default from its own table instead, so an expression like::

    scan_tabs = sel_so.data_set.get("scan_type_list", 0)
    if "Hold 1" not in scan_tabs and dist <= 600:

runs fine headless for years and raises `TypeError: argument of type 'NoneType' is not
iterable` the first time a real bridge selects something nobody has scanned. Worse, a
failing expression STOPS the command, so a watcher task that hits it ends and never comes
back - the feature just stops working, which nobody reports as a crash.

That is what shipped in Peacetime Remastered (LM `fb_scanning_cargo_containers`), and the
same divergence produced a helm crash before it (`get("energy", 0) < 30`).

One rule, deliberately narrow - ``blob-unguarded-none`` (WARNING) on a blob read with no
coalesce that is then:

- used in ``< <= > >=`` or as the right-hand side of ``in`` / ``not in``, with no None
  check at the point of use; or
- used arithmetically ON ITS OWN LINE, or handed straight to ``int()`` / ``float()`` -
  ``newCount = get_data_set_value(...) + count`` raises before any later use exists.

Reads through an ALIAS count (``blob = obj.data_set`` then ``blob.get(...)``) - LM's
docking route is written that way and an unguarded ``torp_now < torp_max`` hid behind it.

**Equality is deliberately NOT flagged.** ``x == "docked"`` on None is simply False, which
is the correct answer, and that shape is everywhere in the missions - flagging it would
bury the cases that actually raise. Staying high-signal matters more than completeness,
for the reason signal_lint gives: a linter that flags correct code teaches people to stop
reading it.

Reuses amd_lint's AmdFinding so `sbs lint` prints these uniformly.
"""
import re

from .amd_lint import AmdFinding, WARNING, _source_lines

def _read_re(aliases=()):
    """A variable assigned from a blob read. Both spellings - the raw engine blob API and
    the procedural wrapper (whose third argument is an INDEX, not a default, which is the
    confusion feeding this bug) - plus any blob ALIAS bound earlier in this label."""
    alt = r"\.data_set\.get\s*\(|\bget_data_set_value\s*\("
    for a in aliases:
        alt += r"|\b" + re.escape(a) + r"\.get\s*\("
    return re.compile(r"^(?P<indent>\s*)(?P<var>[A-Za-z_]\w*)\s*=\s*(?P<rhs>.*?"
                      r"(?:" + alt + r").*)$")


_READ = _read_re()

#: A coalesce on the assignment - `... or 0`, `... or ""`. That IS the fix, so a read
#: carrying one is done.
_COALESCED = re.compile(r"\bor\b")

#: The read used AT the assignment - arithmetic on it, or handed to int()/float()/round().
#: `newCount = get_data_set_value(id, f"{type}_NUM", 0) + count` raises on the read's own
#: line, so there is no later use for the walk below to catch; LM's gamemaster torpedo
#: control had exactly this and was only found because a later `< 0` happened to exist.
_USED_IN_PLACE = re.compile(
    r"(?:\.data_set\.get\s*\([^)]*\)|get_data_set_value\s*\([^)]*\))\s*[-+*/%]"
    r"|\b(?:int|float|round|abs|len)\s*\(\s*(?:\w+\.)*data_set\.get\s*\("
    r"|\b(?:int|float|round|abs|len)\s*\(\s*get_data_set_value\s*\(")

#: A column-0 structural line: a new label/route, so task variables start over.
_STRUCT = re.compile(r"^(//|=|@|-{3,})")

#: `player_blob = DOCKING_PLAYER.data_set` - an ALIAS. LM's docking route does exactly
#: this and then reads through it, which hid an unguarded `torp_now < torp_max` from the
#: first cut of this rule. Aliases are tracked per label alongside the reads themselves.
_ALIAS = re.compile(r"^\s*(?P<var>[A-Za-z_]\w*)\s*=\s*(?:[\w.]+\.data_set\s*$"
                    r"|to_blob\s*\()")

#: `# lint: allow [code ...]` on the line ABOVE excuses the next line - same convention as
#: signal_lint, for the same reason (a trailing `#` on a MAST call is not reliably a
#: comment).
_ALLOW = re.compile(r"^#\s*lint:\s*allow(?P<codes>.*)$", re.I)

CODE = "blob-unguarded-none"


def _uses(var):
    """Patterns that RAISE on None.

    All four shapes come from real LM code: an ordering comparison (`torp_now <
    torp_max`), iteration or containment (`for t in _torp_types`, `"Hold 1" not in
    scan_tabs`), an augmented assignment a line after the read (`shield_rate *=
    coeff`), and the read handed to a numeric builtin (`range(sCount)`).
    """
    v = re.escape(var)
    return re.compile(
        r"\b" + v + r"\s*(?:<=|>=|<(?!=)|>(?!=))"           # var < x
        r"|(?:<=|>=|<(?!=)|>(?!=))\s*" + v + r"\b"          # x < var
        r"|\bin\s+" + v + r"\b"                             # "y" in var / for y in var
        r"|\b" + v + r"\s*(?:\+=|-=|\*=|/=|//=|%=)"         # var *= coeff
        r"|\b" + v + r"\s*[-+*/%](?![=>])"                  # var * 2 - None raises too
        r"|[-+*/%]\s*" + v + r"\b"                          # 2 * var
        r"|\b(?:range|int|float|abs|round|len)\s*\(\s*" + v + r"\s*[,)]")


def _guarded(line, var):
    """Whether this line CHECKS the variable rather than using it.

    Three idioms, all of them already in the missions, and each one a false positive the
    first cut produced:

    * `length is not None and length < 0.01`     (ai/grid_brains.mast)
    * `if not shield_strength:` -> `->END`       (collisions/collision.mast)
    * `if not isinstance(avail, str):`           (hangar/hangar_loadout.mast)

    A guard clears the variable from the watch list: whatever the author does with it
    afterwards, they have established it is there.
    """
    v = re.escape(var)
    return (re.search(r"\b" + v + r"\s+is\s+(?:not\s+)?None", line) is not None
            or re.search(r"\bnot\s+" + v + r"\b", line) is not None
            or re.search(r"\bisinstance\s*\(\s*" + v + r"\b", line) is not None
            or re.search(r"^\s*(?:if|elif)\s+" + v + r"\s*(?::|\band\b|\bor\b)", line) is not None)


def blob_lint(file_path=None, content=None):
    """Return [AmdFinding] (all WARNING) for unguarded blob reads in one .mast source.

    Anchored at the ASSIGNMENT, not at the line that raises: the fix is a coalesce on the
    read, and the raising line is often several lines away (and there may be four of them,
    as in the Florbin case).
    """
    lines = _source_lines(file_path, content)
    findings = []
    pending = {}     # var -> (assign_line, key_text)
    aliases = set()  # names bound to a `.data_set`, so `<alias>.get(...)` is a read too
    read_re = _READ
    allow = None     # codes a `# lint: allow` comment excuses on the NEXT line
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            m = _ALLOW.match(stripped)
            if m:
                allow = {c.strip() for c in m.group("codes").replace(",", " ").split()}
            continue
        code_only = line.split("#", 1)[0]

        # A new label/route: task variables do not survive it, so neither do we.
        if not line[:1].isspace() and _STRUCT.match(stripped):
            pending.clear()
            aliases.clear()
            read_re = _READ
            allow = None
            continue

        # `blob = obj.data_set` - remember it, so reads through it count from here on.
        alias = _ALIAS.match(code_only)
        if alias:
            aliases.add(alias.group("var"))
            read_re = _read_re(aliases)
            allow = None
            continue

        # A use of something we are watching. Report once, then stop watching it - the
        # author fixes the read, and a second finding for the same read is noise.
        for var in list(pending):
            if _uses(var).search(code_only) and not _guarded(code_only, var):
                assign_line, key = pending.pop(var)
                findings.append(AmdFinding(
                    assign_line, WARNING, CODE,
                    "\"" + var + "\" is read from the data_set" + key + " and used at line "
                    + str(i) + " without a guard. The ENGINE returns None for a field that "
                    "was never set (the mock returns a default, so this runs clean "
                    "headless and raises on a real bridge) - and a failing expression "
                    "STOPS the command, so a watcher task hitting it ends silently. "
                    "Coalesce the read: `... or 0` / `or \"\"`, or pass default= to "
                    "get_data_set_value."))
            elif _guarded(code_only, var):
                pending.pop(var, None)

        m = read_re.match(code_only)
        if m:
            var = m.group("var")
            excused = allow is not None and (not allow or CODE in allow)
            if _COALESCED.search(m.group("rhs")) or excused:
                pending.pop(var, None)          # already handled, or the author said so
            elif _USED_IN_PLACE.search(m.group("rhs")):
                # Raises on this very line - report here and do not watch for a later use.
                pending.pop(var, None)
                findings.append(AmdFinding(
                    i, WARNING, CODE,
                    "the data_set read" + _key_of(m.group("rhs")) + " assigned to \"" + var
                    + "\" is used arithmetically on this line. The ENGINE returns None for "
                    "a field that was never set (the mock returns a default, so this runs "
                    "clean headless and raises on a real bridge). Coalesce it: "
                    "`(... or 0) + x`, or pass default= to get_data_set_value."))
            else:
                key = _key_of(m.group("rhs"))
                pending[var] = (i, key)
        allow = None        # a directive excuses exactly one line
    return findings


def _key_of(rhs):
    """` ("scan_type_list")` for the message, or "" when the key is not a literal."""
    m = re.search(r"""get\s*\(\s*["']([A-Za-z_0-9]+)["']""", rhs)
    return " (\"" + m.group(1) + "\")" if m else ""
