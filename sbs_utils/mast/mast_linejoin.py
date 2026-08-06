"""Implicit line-joining for bracket-continued MAST source.

Performance note: this runs over EVERY byte of EVERY .mast file in a story before
the scanner sees it, so it is on the critical path of mission start. It is written
to copy source in SLICES between interesting characters rather than one character
at a time -- see ``join_bracket_continuations``.


MAST's node rules are almost all newline-bounded (``[^\\n\\r\\f]+``), so a Python
expression spanning physical lines inside ``( ) [ ] { }`` breaks every one of them
(Assign, FuncCommand, Await, for, with, match/case, if, yield). Rather than teach
each rule to balance brackets (regex can't), we do ONE O(n) pre-pass that merges
bracket-continued lines into a single logical line before the scanner runs --
exactly CPython's implicit line-joining rule.

Line numbers stay EXACT: a collapsed in-bracket newline becomes a space, and the
same number of ``\\n`` is re-emitted right AFTER the logical line ends (blank lines
the scanner skips), so ``line.count('\\n')`` bookkeeping lands on the right line.
An error *inside* a collapsed expression resolves to that expression's first line
(the whole expression is one logical line); everything after the block is exact.

Prose-safety: dialogue/narration carries unbalanced brackets and apostrophes
(``% You can't win!``, ``% (thinking``). Bracket/quote tracking only engages on
lines whose first non-ws char starts a statement (letter/underscore). Triple-quoted
strings, ``~~ ~~`` and triple-backtick fences are tracked globally (they may span
lines and start with punctuation); single/double quotes are honored only on code
lines, so prose apostrophes are left alone.

Known limitation: a bracket group that itself contains a real-newline triple-quoted
string is not collapsed (the inner newlines are string data and must survive), so
that construct stays unsupported exactly as before. Common scalar dict/list/call
literals collapse fine.
"""


import re

# The ONLY characters that can change state while scanning a normal (non-verbatim)
# region. Everything between two of them is inert and gets copied in one slice, so
# the scan cost tracks the number of interesting characters, not the file size.
_NEXT = re.compile(r"""[\n"'#~`()\[\]{}]""")
# Leading whitespace of a physical line (consumed in bulk before classifying it).
_INDENT = re.compile(r"[ \t\r]*")
# Inside a single/double quoted string only an escape, the closing quote, or a
# newline matter. One pattern per quote type so the closer is baked in.
_IN_STR = {'"': re.compile(r'\\|"|\n'), "'": re.compile(r"\\|'|\n")}
# Closer for each verbatim state, reached with str.find (one C-level scan, one slice).
_VERBATIM_CLOSER = {"Z": "~~", "F": "```"}


def _needs_join(src):
    """Cheap gate: could ANY physical line leave a bracket group open?

    Per line, count openers vs closers with C-level ``str.count`` -- no per-char
    loop, no string parsing. The opening line of every real multiline group has
    ``opens > closes``, so this never MISSES a real continuation. It over-fires
    (an unmatched ``(`` in prose, or a lone ``[`` in a format string trips it),
    but that only costs a scan that changes nothing.

    One documented pathological miss: an opening line whose string literal
    contains a closer that exactly cancels the real opener, e.g. ``foo(")",`` --
    vanishingly rare, and not worth a string-aware gate that would cost as much
    as the scan it avoids.
    """
    for line in src.split("\n"):
        if "(" in line or "[" in line or "{" in line:
            if (line.count("(") + line.count("[") + line.count("{")
                    > line.count(")") + line.count("]") + line.count("}")):
                return True
    return False


def join_bracket_continuations(src):
    """Merge bracket-continued physical lines into one logical line.

    Slice-copying scanner: the state machine below only ever stops at a character
    that can change state (``_NEXT``), at a verbatim region's closer (``str.find``),
    or at a string's escape/closer (``_IN_STR``). Every inert run between two stops
    is appended as ONE slice. The previous character-at-a-time version appended one
    element per byte and re-probed ``startswith`` at every position, which made this
    pre-pass the single largest cost in compiling a big story (measured: 232ms of
    LegendaryMissions' ~1s compile, 57 of its 171 files). Output is byte-identical.
    """
    if src is None or _needs_join(src) is False:
        return src

    n = len(src)
    i = 0
    out = []
    add = out.append
    depth = 0            # bracket depth on the current CODE logical line
    pending = 0          # collapsed newlines to re-emit at logical-line end
    state = "N"          # N=normal  T=triple-string  Z=~~fence  F=```fence
    triple = ""          # active triple delimiter while state == "T"
    line_is_code = None  # None => not yet seen first non-ws char of this line

    while i < n:
        # inside a multi-line construct: copy verbatim through to its closer in one
        # slice. An unterminated construct swallows the rest of the file, as before.
        if state != "N":
            closer = triple if state == "T" else _VERBATIM_CLOSER[state]
            j = src.find(closer, i)
            if j == -1:
                add(src[i:])
                i = n
                break
            add(src[i:j + len(closer)])
            i = j + len(closer)
            state = "N"
            continue

        # first non-ws char of a logical line decides code vs prose. A line that is
        # only whitespace never classifies -- the newline branch below handles it.
        if line_is_code is None:
            end = _INDENT.match(src, i).end()
            if end > i:
                add(src[i:end])
                i = end
            if i >= n:
                break
            c = src[i]
            if c != "\n":
                line_is_code = c.isalpha() or c == "_"

        # copy the inert run up to the next character that can change state
        mo = _NEXT.search(src, i)
        if mo is None:
            add(src[i:])
            i = n
            break
        j = mo.start()
        if j > i:
            add(src[i:j])
            i = j
        c = src[i]

        # newline: collapse (in-bracket) or real logical-line boundary
        if c == "\n":
            if out and out[-1].endswith("\r"):
                # normalize \r\n on the collapsed line (the \r is the tail of
                # whatever slice was emitted last, not its own element)
                tail = out[-1]
                if len(tail) == 1:
                    out.pop()
                else:
                    out[-1] = tail[:-1]
            if depth > 0 and line_is_code:
                add(" ")              # continuation
                pending += 1
                # same logical line: keep line_is_code
            else:
                add("\n")
                if pending:
                    add("\n" * pending)  # give the scanner its line count
                    pending = 0
                depth = 0
                line_is_code = None   # real boundary: reclassify next line
            i += 1
            continue

        # multi-line openers honored regardless of code/prose
        if c == "~":
            if src.startswith("~~", i):
                add("~~"); i += 2; state = "Z"
                continue
            add(c); i += 1
            continue
        if c == "`":
            if src.startswith("```", i):
                add("```"); i += 3; state = "F"
                continue
            add(c); i += 1
            continue

        # comment to end of line
        if c == "#":
            j = src.find("\n", i)
            if j == -1:
                j = n
            if depth > 0 and line_is_code:
                pass  # drop: collapsing would let it eat the rest of the joined line
            else:
                add(src[i:j])
            i = j
            continue

        if c == '"' or c == "'":
            if src.startswith(c * 3, i):
                triple = c * 3
                add(triple); i += 3; state = "T"
                continue
            # single/double string, code lines only (prose apostrophes!)
            if line_is_code:
                pat = _IN_STR[c]
                k = i + 1
                while True:
                    sm = pat.search(src, k)
                    if sm is None:          # unterminated at EOF
                        add(src[i:]); i = n
                        break
                    e = sm.start()
                    ch = src[e]
                    if ch == "\\":
                        if e + 1 < n:       # skip the escaped char, keep scanning
                            k = e + 2
                            continue
                        add(src[i:e + 1]); i = e + 1
                        break
                    if ch == "\n":          # unterminated: leave the \n to the caller
                        add(src[i:e]); i = e
                        break
                    add(src[i:e + 1]); i = e + 1   # the closing quote
                    break
                continue
            add(c); i += 1
            continue

        # brackets (code lines only)
        if line_is_code:
            if c in "([{":
                depth += 1; add(c); i += 1
                continue
            if c in ")]}":
                if depth:
                    depth -= 1
                add(c); i += 1
                continue

        add(c); i += 1

    if pending:
        add("\n" * pending)
    return "".join(out)
