"""Implicit line-joining for bracket-continued MAST source.

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
    if src is None or _needs_join(src) is False:
        return src

    n = len(src)
    i = 0
    out = []
    depth = 0            # bracket depth on the current CODE logical line
    pending = 0          # collapsed newlines to re-emit at logical-line end
    state = "N"          # N=normal  T=triple-string  Z=~~fence  F=```fence
    triple = ""          # active triple delimiter while state == "T"
    line_is_code = None  # None => not yet seen first non-ws char of this line

    while i < n:
        c = src[i]

        # inside a multi-line construct: copy verbatim until its closer
        if state == "T":
            if src.startswith(triple, i):
                out.append(triple); i += 3; state = "N"
            else:
                out.append(c); i += 1
            continue
        if state == "Z":
            if src.startswith("~~", i):
                out.append("~~"); i += 2; state = "N"
            else:
                out.append(c); i += 1
            continue
        if state == "F":
            if src.startswith("```", i):
                out.append("```"); i += 3; state = "N"
            else:
                out.append(c); i += 1
            continue

        # newline: collapse (in-bracket) or real logical-line boundary
        if c == "\n":
            if out and out[-1] == "\r":
                out.pop()  # normalize \r\n on the collapsed line
            if depth > 0 and line_is_code:
                out.append(" ")       # continuation
                pending += 1
                # same logical line: keep line_is_code
            else:
                out.append("\n")
                if pending:
                    out.append("\n" * pending)  # give the scanner its line count
                    pending = 0
                depth = 0
                line_is_code = None   # real boundary: reclassify next line
            i += 1
            continue

        # first non-ws char of a logical line decides code vs prose
        if line_is_code is None:
            if c in " \t\r":
                out.append(c); i += 1
                continue
            line_is_code = c.isalpha() or c == "_"

        # multi-line openers honored regardless of code/prose
        if src.startswith('"""', i) or src.startswith("'''", i):
            triple = src[i:i + 3]; out.append(triple); i += 3; state = "T"
            continue
        if src.startswith("~~", i):
            out.append("~~"); i += 2; state = "Z"
            continue
        if src.startswith("```", i):
            out.append("```"); i += 3; state = "F"
            continue

        # comment to end of line
        if c == "#":
            j = i
            while j < n and src[j] != "\n":
                j += 1
            if depth > 0 and line_is_code:
                pass  # drop: collapsing would let it eat the rest of the joined line
            else:
                out.append(src[i:j])
            i = j
            continue

        # single/double string, code lines only (prose apostrophes!)
        if line_is_code and (c == '"' or c == "'"):
            q = c; out.append(c); i += 1
            while i < n and src[i] != "\n":
                if src[i] == "\\" and i + 1 < n:
                    out.append(src[i:i + 2]); i += 2; continue
                out.append(src[i])
                if src[i] == q:
                    i += 1; break
                i += 1
            continue

        # brackets (code lines only)
        if line_is_code and c in "([{":
            depth += 1; out.append(c); i += 1
            continue
        if line_is_code and c in ")]}":
            depth = max(0, depth - 1); out.append(c); i += 1
            continue

        out.append(c); i += 1

    if pending:
        out.append("\n" * pending)
    return "".join(out)
