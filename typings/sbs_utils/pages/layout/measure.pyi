from sbs_utils.helpers import FrameContext
def _fits (font, text, box_w, box_h):
    """Does `text` fit `box_w` x `box_h` pixels in `font`?"""
def _font (font):
    """Normalise to a font tag the engine will accept.
    
    Two engine behaviours make this load-bearing:
    
      * the Pybind signature is (fontTag: str, ...) and REJECTS None outright
      * an unrecognised tag does not raise -- it returns -1
    
    A style written `font: gui-3` stores " gui-3" WITH THE LEADING SPACE, and
    the engine does not recognise that, so it measured -1, which became a
    negative column width and an inverted rect: the text simply vanished. The
    mock never reproduced it because its lookup falls back to a gui-3 bucket
    for anything unknown and returns a positive number."""
def _measure_props_uncached (props, mode, avail_px, font, ar):
    """Natural size of a widget whose text lives in a props string.
    
    The shared body of Column.measure for every text-bearing widget (Text,
    Button, Checkbox, TextInput, ...), so they cannot drift apart on how text
    is extracted, which font wins, or how wrapping is asked for.
    
    Returns (width_pct, height_pct), or None if it cannot be measured."""
def _sbs ():
    """The live sbs module, or None if there is no frame context.
    
    No context means we cannot ask the engine, which means the thing is
    genuinely unmeasurable. Callers treat None as "unmeasurable" and fall back
    to flex sizing -- we do not invent a number."""
def _store (cache, key, value):
    ...
def apply_overflow (props, bounds, policy, cascade_font=None):
    """Adjust a props string so it honours `policy` inside `bounds`.
    
    Returns (props, draw). `draw` is False only for `hide`, when the text
    genuinely does not fit.
    
    Called at PRESENT time, because that is the first moment the final rect is
    known. Everything it does is expressible through send_gui_*: change the
    font, change the string, or do not send. It cannot ask the engine to clip,
    because the engine has no such thing."""
def backdrop_props (image, color, layer=None):
    """Props for a background / border fill.
    
    `layer` None keeps the historic 1000, which is UNDER content -- so a
    backdrop cannot hide a neighbour's spill unless the author raises it."""
def measure_block_height (font, text, px_width):
    """Height in PIXELS of `text` wrapped to `px_width`, or None.
    
    Wrapping is the ENGINE's, not ours. We ask rather than compute a line count
    -- computing it is exactly how the mock's wrap and the mock's measure became
    the same code, which is why the mock cannot detect its own wrap error."""
def measure_cache_clear ():
    """Drop every cached measurement and reset the counters. For tests/bench."""
def measure_cache_stats ():
    """Engine-call counts + hits, as a copy. The bench's primary metric."""
def measure_line_height (font, text):
    """Height in PIXELS one line OCCUPIES, or None if unmeasurable.
    
    This deliberately does NOT call sbs.get_text_line_height. That function
    returns the INK EXTENT -- how tall the glyphs themselves are -- not how much
    vertical space a line consumes. For gui-2 it reports 13px where a drawn line
    actually occupies 24px, so every row sized from it came out ~45% short.
    Because the engine does not clip, short rows do not truncate, they overdraw
    whatever is beneath them.
    
    Measured in the engine with missions/layout_probe -> "Wrap Ruler": the same
    sentence at shrinking widths drew 2/3/4 lines in exactly 48/72/96px, so the
    advance is exactly block_height / lines with no constant term. Asking for a
    single unwrapped line therefore gives the true advance, and it agrees with
    the nominal _FONT_SIZES table for every font -- which is the second,
    independent confirmation that that table is real line occupancy.
    
    `text` stays part of the key on purpose: the engine may vary line height
    with the glyphs present, and encoding the mock's belief that it does not
    would bake a mock assumption into the library."""
def measure_line_width (font, text):
    """Width in PIXELS of one unwrapped line, or None if unmeasurable."""
def measure_min_word_width (font, text):
    """Width in PIXELS of the widest unbreakable token -- CSS `min-content`.
    
    The narrowest the text can be laid out without a word spilling past its
    box. Because the engine does not clip, going below this makes glyphs bleed
    over the neighbouring column, so it is the floor the layout shrinks to."""
def measure_props (props, mode, avail_px, font, ar):
    """Cached front end for the per-widget natural size. See
    _measure_props_uncached for the real work and the reasoning."""
def pct_to_px_x (pct, ar):
    """Percent of region width -> pixels, for this client's aspect ratio."""
def px_to_pct_x (px, ar):
    """Pixels -> percent of region width, for this client's aspect ratio."""
def px_to_pct_y (px, ar):
    """Pixels -> percent of region height, for this client's aspect ratio."""
def shrink_font_to_fit (font, text, box_w, box_h):
    """The largest ladder font at or below `font` that fits, or None.
    
    Returns the ORIGINAL font when it already fits, so a caller can tell
    "nothing to do" from "shrank". None means even the smallest font overflows,
    which is a real answer -- the caller then falls back to spilling rather
    than pretending."""
def truncate_to_fit (font, text, box_w):
    """Longest prefix of `text` plus "..." that fits `box_w` pixels.
    
    Returns text unchanged when it already fits, or None if not even the
    ellipsis fits -- at which point truncating would show "..." and no content,
    which is worse than spilling."""
def wrap_to_width (font, text, px_width):
    """Break `text` into lines that each MEASURE within `px_width`.
    
    Two invariants, both learned the hard way:
    
    1. EVERY RETURNED LINE FITS. A line that comes back wider than px_width gets
       wrapped AGAIN by the engine, into a box sized for the line count we
       returned -- and since the engine does not clip, the extra line is drawn on
       top of its neighbour. This is the whole reason the function exists.
    2. NO WORD IS LOST. Obvious, but a greedy version of this that "gave back"
       an over-long word by popping it silently deleted it from the document.
       Hence the index walk below: a word is only consumed by being placed.
    
    On the "ask, never model" rule: measurement still asks the engine. But a
    TextArea has to know where the breaks fall, because it keeps a record per
    display line (styles, links, line-indexed scrolling). It used to guess from
    an AVERAGE glyph width and a character count -- wrong in both directions,
    early on narrow glyphs and late on wide ones. Summed word widths are not
    enough either: a joined string does not measure as the sum of its parts, so
    the candidate itself has to be measured.
    
    Fidelity, from the engine capture (missions/font_measure): line counts agree
    with the engine at >=600px, drift ~6% at 300px, and badly below that -- so a
    very narrow column is still worth confirming in a real session.
    
    Words wider than a whole line are broken MID-WORD, as the engine does."""
