"""First-char set analysis for MAST node regexes (compiler dispatch).

`first_chars_for_pattern(pattern)` returns the set of characters a compiled
regex could match as its first character, or `None` meaning "could start with
anything". The compiler uses this to skip nodes whose rule provably cannot match
the current line, without changing match order.

Safety invariant: never UNDER-claim. If the result omitted a character the regex
can actually start with, the compiler could skip the true winning node and
mis-parse. Therefore every uncertain construct (`.`, `\w` and other categories,
negated sets, anything unrecognized) collapses to `None` (never skip). This is
validated differentially against the real mission corpus.
"""
try:
    from re import _parser as reparser
    from re import _constants as reconst
except ImportError:  # pragma: no cover - very old Pythons
    import sre_parse as reparser
    import sre_constants as reconst

LITERAL = reconst.LITERAL
NOT_LITERAL = reconst.NOT_LITERAL
IN = reconst.IN
BRANCH = reconst.BRANCH
SUBPATTERN = reconst.SUBPATTERN
MAX_REPEAT = reconst.MAX_REPEAT
MIN_REPEAT = reconst.MIN_REPEAT
AT = reconst.AT
ANY = reconst.ANY
RANGE = reconst.RANGE
CATEGORY = reconst.CATEGORY
NEGATE = reconst.NEGATE
POSSESSIVE_REPEAT = getattr(reconst, "POSSESSIVE_REPEAT", None)
ATOMIC_GROUP = getattr(reconst, "ATOMIC_GROUP", None)


def _in_first_chars(items):
    # items: parsed contents of an IN set, e.g. [(LITERAL, code), (RANGE,(lo,hi))]
    chars = set()
    for op, av in items:
        if op is NEGATE:
            return None  # negated set matches a large/unknown range
        elif op is LITERAL:
            chars.add(chr(av))
        elif op is RANGE:
            lo, hi = av
            if hi - lo > 128:
                return None
            for cc in range(lo, hi + 1):
                chars.add(chr(cc))
        else:  # CATEGORY (\w \d \s ...) or anything else -> uncertain
            return None
    return chars


def _first_set(seq, i=0):
    n = len(seq)
    if i >= n:
        # The remaining pattern can match empty here, i.e. zero-width at this
        # point -> it could "start" with any character -> give up (None).
        return None
    op, av = seq[i]
    if op is LITERAL:
        return {chr(av)}
    if op is IN:
        return _in_first_chars(av)
    if op is ANY or op is NOT_LITERAL or op is CATEGORY:
        return None
    if op is AT:
        # zero-width anchor (^, \b, ...) -> look at the next token
        return _first_set(seq, i + 1)
    if op is BRANCH:
        acc = set()
        for b in av[1]:
            s = _first_set(b, 0)
            if s is None:
                return None
            acc |= s
        return acc
    if op is SUBPATTERN:
        # av = (group, add_flags, del_flags, subpattern); subpattern is last
        return _first_set(av[-1], 0)
    if op is MAX_REPEAT or op is MIN_REPEAT or (POSSESSIVE_REPEAT and op is POSSESSIVE_REPEAT):
        mn, mx, item = av
        s = _first_set(item, 0)
        if mn >= 1:
            return s  # required at least once -> first char is the item's
        if s is None:
            return None
        # optional: the element may be skipped, so union with the continuation
        cont = _first_set(seq, i + 1)
        if cont is None:
            return None
        return s | cont
    if ATOMIC_GROUP and op is ATOMIC_GROUP:
        return _first_set(av, 0)
    return None  # unknown construct -> safe (never skip)


def first_chars_for_pattern(pattern):
    """Return a set of possible first chars, or None for 'matches anything'."""
    try:
        parsed = reparser.parse(pattern)
        return _first_set(parsed, 0)
    except Exception:
        return None
