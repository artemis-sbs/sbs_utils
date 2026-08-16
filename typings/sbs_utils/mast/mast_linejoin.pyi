def _needs_join (src):
    """Cheap gate: could ANY physical line leave a bracket group open?
    
    Per line, count openers vs closers with C-level ``str.count`` -- no per-char
    loop, no string parsing. The opening line of every real multiline group has
    ``opens > closes``, so this never MISSES a real continuation. It over-fires
    (an unmatched ``(`` in prose, or a lone ``[`` in a format string trips it),
    but that only costs a scan that changes nothing.
    
    One documented pathological miss: an opening line whose string literal
    contains a closer that exactly cancels the real opener, e.g. ``foo(")",`` --
    vanishingly rare, and not worth a string-aware gate that would cost as much
    as the scan it avoids."""
def join_bracket_continuations (src):
    """Merge bracket-continued physical lines into one logical line.
    
    Slice-copying scanner: the state machine below only ever stops at a character
    that can change state (``_NEXT``), at a verbatim region's closer (``str.find``),
    or at a string's escape/closer (``_IN_STR``). Every inert run between two stops
    is appended as ONE slice. The previous character-at-a-time version appended one
    element per byte and re-probed ``startswith`` at every position, which made this
    pre-pass the single largest cost in compiling a big story (measured: 232ms of
    LegendaryMissions' ~1s compile, 57 of its 171 files). Output is byte-identical."""
