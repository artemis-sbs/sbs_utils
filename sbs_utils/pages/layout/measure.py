"""Memoized text measurement.

This module is **a memo in front of the engine's text metrics and nothing
more**. It deliberately does NOT model text: no char-width table, no wrapping,
no assumption that line height is independent of the string. Every number comes
from `sbs.get_text_line_width` / `get_text_line_height` / `get_text_block_height`
-- whatever `sbs` happens to be (the real Pybind module in Cosmos, the mock
headless). The engine is the source of truth; the mock is a dev convenience.

Why a memo at all: sbs_utils had no measurement cache whatsoever, so every
measurement was a fresh engine call -- including genuinely constant ones like
`get_text_line_width(BODY_FONT, "MM")`, re-measured on every TableLine
construction. Content-based layout sizing multiplies that traffic, so the cache
is what keeps it affordable.

Why the cache never needs invalidating: it is keyed and stored in **pixel**
space. Pixel metrics depend only on (font, text) -- not on the client's aspect
ratio or window size. Callers convert px -> percent themselves, at the point of
use, with that client's aspect ratio. So a resolution change invalidates
nothing here.

Note on units: `get_font_size` in layout.py is a *nominal* table used for `em`
arithmetic. It is not a measurement and must never be used as one -- it agrees
with neither the engine nor the mock. Keep the two separate.
"""

from ...helpers import FrameContext


# (font, text) -> px
_line_w = {}
_line_h = {}
# (font, text, px_width) -> px
_block_h = {}

# A plain size cap with clear-on-overflow. No LRU machinery: this is embedded
# Python 3.11 with no pip, where the allocation budget matters more than
# eviction quality, and the working set (a console's visible strings) is small
# and highly repetitive.
CACHE_CAP = 4096

# Engine-call counters. The bench uses these -- call counts are the metric that
# actually moves, since wall time in the mock is noisy.
_stats = {"line_w": 0, "line_h": 0, "block_h": 0, "hits": 0}


# Font used when a widget declares none and nothing cascades one.
#
# This is NOT cosmetic: the engine's get_text_line_width is a Pybind function
# typed (fontTag: str, textToMeasure: str), and it REJECTS None outright --
#
#     TypeError: Invoked with: None, 'Select a mission. 8 types.'
#
# The mock accepts None via .get(fontTag, default), so this could never be
# caught headlessly; it only appears in the engine, and only once measurement
# runs on widgets that declare no font.
#
# PINNED BY RENDER, not assumed. The engine exposes no queryable "unset" tag --
# every spelling of it measures -1 -- so this was settled by drawing an unfonted
# string over each candidate in the same rect (missions/layout_probe, "Pin Font")
# and taking the one that overlaid exactly. It is gui-2.
#
# It had been guessed as gui-3, reasoning from get_font_size(None) == 30. That
# guess was WRONG BY ONE STEP and in the forgiving direction: gui-3 is the wider
# font, so every unfonted widget was measured wider than it draws. Content
# columns therefore asked for more width than they needed -- wasteful and
# slightly off, but never overflowing, which is why nothing looked broken.
#
# NOTE the nominal em table still returns 30 for an unset font
# (layout.get_font_size), which no longer agrees with gui-2 == 24. That
# inconsistency is deliberate: get_font_size drives `em` arithmetic that
# existing layouts are tuned against, and changing it would resize every
# em-sized row in every mission. Measurement and em-nominal are separate
# numbers on purpose -- see the header of this file.
DEFAULT_FONT = "gui-2"


def _font(font):
    """Normalise to a font tag the engine will accept.

    Two engine behaviours make this load-bearing:

      * the Pybind signature is (fontTag: str, ...) and REJECTS None outright
      * an unrecognised tag does not raise -- it returns -1

    A style written `font: gui-3` stores " gui-3" WITH THE LEADING SPACE, and
    the engine does not recognise that, so it measured -1, which became a
    negative column width and an inverted rect: the text simply vanished. The
    mock never reproduced it because its lookup falls back to a gui-3 bucket
    for anything unknown and returns a positive number.
    """
    if not isinstance(font, str):
        return DEFAULT_FONT
    font = font.strip()
    return font if font else DEFAULT_FONT


def _sbs():
    """The live sbs module, or None if there is no frame context.

    No context means we cannot ask the engine, which means the thing is
    genuinely unmeasurable. Callers treat None as "unmeasurable" and fall back
    to flex sizing -- we do not invent a number.
    """
    ctx = FrameContext.context
    return ctx.sbs if ctx is not None else None


def _store(cache, key, value):
    if len(cache) >= CACHE_CAP:
        cache.clear()
    cache[key] = value
    return value


def measure_line_width(font, text):
    """Width in PIXELS of one unwrapped line, or None if unmeasurable."""
    if not text:
        return 0
    font = _font(font)
    key = (font, text)
    got = _line_w.get(key)
    if got is not None:
        _stats["hits"] += 1
        return got
    sbs = _sbs()
    if sbs is None:
        return None
    _stats["line_w"] += 1
    px = sbs.get_text_line_width(font, text)
    if px is None or px < 0:
        return None          # engine could not measure it -- see _valid()
    return _store(_line_w, key, px)


# A single line, asked for as a "block" one line wide enough never to wrap.
# 1<<20 px is far past any real screen, so the engine returns the height of the
# text on one line -- which is the line ADVANCE, not the ink.
_ONE_LINE_PX = 1 << 20


def measure_line_height(font, text):
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
    would bake a mock assumption into the library.
    """
    # An empty string has no block height (it is 0 by definition), but callers
    # asking for a line height still want the height a line WOULD occupy.
    return measure_block_height(font, text or "M", _ONE_LINE_PX)


def measure_block_height(font, text, px_width):
    """Height in PIXELS of `text` wrapped to `px_width`, or None.

    Wrapping is the ENGINE's, not ours. We ask rather than compute a line count
    -- computing it is exactly how the mock's wrap and the mock's measure became
    the same code, which is why the mock cannot detect its own wrap error.
    """
    if not text:
        return 0
    px_width = int(px_width)
    if px_width <= 0:
        return None
    font = _font(font)
    key = (font, text, px_width)
    got = _block_h.get(key)
    if got is not None:
        _stats["hits"] += 1
        return got
    sbs = _sbs()
    if sbs is None:
        return None
    _stats["block_h"] += 1
    px = sbs.get_text_block_height(font, text, px_width)
    if px is None or px < 0:
        return None
    return _store(_block_h, key, px)


def measure_min_word_width(font, text):
    """Width in PIXELS of the widest unbreakable token -- CSS `min-content`.

    The narrowest the text can be laid out without a word spilling past its
    box. Because the engine does not clip, going below this makes glyphs bleed
    over the neighbouring column, so it is the floor the layout shrinks to.
    """
    if not text:
        return 0
    widest = 0
    for word in text.split():
        w = measure_line_width(font, word)
        if w is None:
            return None
        if w > widest:
            widest = w
    return widest


def wrap_to_width(font, text, px_width):
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

    Words wider than a whole line are broken MID-WORD, as the engine does.
    """
    if not text:
        return []
    px_width = int(px_width)
    if px_width <= 0:
        return [text]

    words = text.split()
    if not words:
        return [text]

    def width_of(candidate):
        return measure_line_width(font, candidate)

    def word_width(word):
        # Memoized per word, so the sum walk below costs nothing after the
        # first time a word is seen.
        return width_of(word) or 0

    def fits(candidate):
        w = width_of(candidate)
        return w is not None and w <= px_width

    if width_of(text) is None:
        return [text]              # unmeasurable -- let the engine wrap it

    space_w = width_of(" ") or 0

    def split_long_word(word):
        """Break one over-wide word into pieces that each fit."""
        pieces = []
        piece = ""
        for ch in word:
            if piece and not fits(piece + ch):
                pieces.append(piece)
                piece = ch
            else:
                piece += ch
        if piece:
            pieces.append(piece)
        return pieces or [word]

    lines = []
    i = 0
    n = len(words)
    while i < n:
        if not fits(words[i]):
            # Single word too wide for a line: break it, keep the tail in play.
            pieces = split_long_word(words[i])
            lines.extend(pieces[:-1])
            words[i] = pieces[-1]

        # Extend by SUMMED word widths first. That is optimistic -- a joined
        # string measures a little wider than the sum of its parts -- but it is
        # nearly free, because each word's width is measured once and memoized.
        j = i + 1
        run = word_width(words[i])
        while j < n:
            nxt = run + space_w + word_width(words[j])
            if nxt > px_width:
                break
            run = nxt
            j += 1

        # Then pay for real measurements only at the boundary, shrinking until
        # the candidate actually fits. Since the sum only ever overshoots, this
        # needs to shrink and never to grow -- so the result is still exact,
        # at ~1-2 measurements per line instead of one per word.
        while j > i + 1 and not fits(" ".join(words[i:j])):
            j -= 1
        lines.append(" ".join(words[i:j]))
        i = j                       # a word is consumed only by being placed

    return lines or [text]


def px_to_pct_x(px, ar):
    """Pixels -> percent of region width, for this client's aspect ratio."""
    if px is None or ar is None or not ar.x:
        return None
    return (px / ar.x) * 100.0


def px_to_pct_y(px, ar):
    """Pixels -> percent of region height, for this client's aspect ratio."""
    if px is None or ar is None or not ar.y:
        return None
    return (px / ar.y) * 100.0


def pct_to_px_x(pct, ar):
    """Percent of region width -> pixels, for this client's aspect ratio."""
    if pct is None or ar is None or not ar.x:
        return None
    return (pct / 100.0) * ar.x


def measure_props(props, mode, avail_px, font, ar):
    """Natural size of a widget whose text lives in a props string.

    The shared body of Column.measure for every text-bearing widget (Text,
    Button, Checkbox, TextInput, ...), so they cannot drift apart on how text
    is extracted, which font wins, or how wrapping is asked for.

    Returns (width_pct, height_pct), or None if it cannot be measured.
    """
    from ...helpers import split_props

    #
    # Parse the props string ONCE. This used to call props_display_text() and
    # props_font(), each of which ran its own split_props scan -- and measured
    # at ~4.4us each against ~0.2us for a cached metric lookup, so the parsing
    # was roughly two thirds of the call. That cost is pure Python and is
    # identical in the engine, so it matters more than the sbs call it wraps.
    #
    parsed = split_props(props, "$text") if props else {}
    text = parsed.get("$text")
    if text is None:
        text = parsed.get("text")
    if text is None:
        #
        # No text key at all -- we do not know what this widget draws, so it is
        # UNMEASURABLE, not empty. Returning (0,0) here would collapse the
        # column to nothing and the widget would simply vanish; None makes it
        # fall back to flex, which is the safe direction under a cascading
        # `col-width: content` that reaches widgets it was never aimed at.
        #
        return None
    text = text.strip()
    if len(text) >= 2 and text.startswith("`") and text.endswith("`"):
        text = text[1:-1]
    if not text:
        # An explicitly EMPTY text is genuinely zero-sized, unlike the case
        # above where we simply could not find one.
        return (0.0, 0.0)

    # A font in the widget's own props beats the cascade: present() appends the
    # cascade props AFTER the message, so the engine reads the widget's value
    # last. Measuring in a different font than we render in would mis-size
    # every cell.
    own_font = parsed.get("font")
    if own_font:
        own_font = own_font.strip()
        if own_font:
            font = own_font

    width_px = measure_line_width(font, text)
    if width_px is None:
        return None

    if mode is not None and mode.is_min:
        width_px = measure_min_word_width(font, text)
        if width_px is None:
            return None

    # Height: ask the ENGINE how tall this text is at the width it will get.
    # Never compute a line count here -- that is precisely how the mock's wrap
    # and the mock's measure became the same code and stopped being able to
    # disagree. `max-content` is one unbroken line by definition, so it does
    # not wrap and does not need a width.
    wrap_px = None
    if avail_px is not None and not (mode is not None and mode.is_max):
        wrap_px = int(avail_px)
    if wrap_px is not None and wrap_px > 0:
        height_px = measure_block_height(font, text, wrap_px)
    else:
        # One line's OCCUPIED height, which is NOT get_text_line_height -- that
        # returns the ink extent (11px at 'smallest' where a line occupies 18).
        # Sizing a row from the ink extent makes it ~40% too short, and the
        # engine does not clip, so the text spills into whatever is below.
        height_px = measure_block_height(font, text, 1 << 20)
    if height_px is None:
        return None

    return (px_to_pct_x(width_px, ar), px_to_pct_y(height_px, ar))


def measure_cache_clear():
    """Drop every cached measurement and reset the counters. For tests/bench."""
    _line_w.clear()
    _line_h.clear()
    _block_h.clear()
    for k in _stats:
        _stats[k] = 0


def measure_cache_stats():
    """Engine-call counts + hits, as a copy. The bench's primary metric."""
    stats = dict(_stats)
    stats["engine_calls"] = stats["line_w"] + stats["line_h"] + stats["block_h"]
    stats["cached"] = len(_line_w) + len(_line_h) + len(_block_h)
    return stats


# --- overflow policies ------------------------------------------------------
#
# The engine does not clip: text wider or taller than its rect is drawn anyway,
# over whatever is beside or below it. The layout tries to size things so that
# never happens, but some text cannot fit at any width -- one unbreakable word
# wider than its row, or a paragraph in a band the author fixed the height of.
#
# `overflow:` lets the author say what should happen then. The default stays
# SPILL, because it is what the library has always done and because a visible
# failure gets fixed while a silent one does not.
#
# Ordered smallest-last: shrinking walks down this list.
FONT_LADDER = ["gui-6", "gui-5", "gui-4", "gui-3", "gui-2", "gui-1", "smallest"]

OVERFLOW_POLICIES = ("spill", "shrink", "ellipsis", "hide")

ELLIPSIS = "..."          # ASCII only -- the engine renders nothing else


def _fits(font, text, box_w, box_h):
    """Does `text` fit `box_w` x `box_h` pixels in `font`?"""
    w = measure_line_width(font, text)
    if w is None:
        return None                      # unmeasurable: caller should give up
    if box_h is None:
        return w <= box_w
    h = measure_block_height(font, text, max(1, int(box_w)))
    if h is None:
        return None
    return h <= box_h


def shrink_font_to_fit(font, text, box_w, box_h):
    """The largest ladder font at or below `font` that fits, or None.

    Returns the ORIGINAL font when it already fits, so a caller can tell
    "nothing to do" from "shrank". None means even the smallest font overflows,
    which is a real answer -- the caller then falls back to spilling rather
    than pretending.
    """
    if not text or box_w is None or box_w <= 0:
        return font
    start = FONT_LADDER.index(font) if font in FONT_LADDER else 0
    for candidate in FONT_LADDER[start:]:
        ok = _fits(candidate, text, box_w, box_h)
        if ok is None:
            return font                  # cannot measure; leave it alone
        if ok:
            return candidate
    return None


def truncate_to_fit(font, text, box_w):
    """Longest prefix of `text` plus "..." that fits `box_w` pixels.

    Returns text unchanged when it already fits, or None if not even the
    ellipsis fits -- at which point truncating would show "..." and no content,
    which is worse than spilling.
    """
    if not text or box_w is None or box_w <= 0:
        return text
    full = measure_line_width(font, text)
    if full is None:
        return text
    if full <= box_w:
        return text
    if (measure_line_width(font, ELLIPSIS) or 0) > box_w:
        return None
    # Binary search the prefix length -- measurement is memoized, so this is
    # a handful of cached lookups rather than a scan.
    lo, hi, best = 0, len(text), None
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid].rstrip() + ELLIPSIS
        w = measure_line_width(font, candidate)
        if w is None:
            return text
        if w <= box_w:
            best, lo = candidate, mid + 1
        else:
            hi = mid - 1
    return best


def apply_overflow(props, bounds, policy, cascade_font=None):
    """Adjust a props string so it honours `policy` inside `bounds`.

    Returns (props, draw). `draw` is False only for `hide`, when the text
    genuinely does not fit.

    Called at PRESENT time, because that is the first moment the final rect is
    known. Everything it does is expressible through send_gui_*: change the
    font, change the string, or do not send. It cannot ask the engine to clip,
    because the engine has no such thing.
    """
    from ...helpers import FrameContext, split_props, merge_props
    from ...gui import get_client_aspect_ratio

    if not policy or policy == "spill" or not props:
        return props, True

    parsed = split_props(props, "$text")
    raw = parsed.get("$text", parsed.get("text"))
    if raw is None:
        return props, True
    text = raw.strip()
    quoted = len(text) >= 2 and text.startswith("`") and text.endswith("`")
    if quoted:
        text = text[1:-1]
    if not text:
        return props, True

    ctx = FrameContext.context
    if ctx is None:
        return props, True
    ar = get_client_aspect_ratio(FrameContext.client_id)
    if ar is None or not ar.x:
        return props, True
    box_w = bounds.width / 100.0 * ar.x
    box_h = bounds.height / 100.0 * ar.y
    if box_w <= 0 or box_h <= 0:
        return props, True

    font = _font(parsed.get("font") or cascade_font)

    if policy == "shrink":
        fitted = shrink_font_to_fit(font, text, box_w, box_h)
        if fitted is None or fitted == font:
            # Even the smallest font overflows (or it already fitted): leave it
            # alone and let it spill, rather than silently rendering illegibly.
            return props, True
        parsed["font"] = fitted
        return merge_props(parsed), True

    if policy == "ellipsis":
        cut = truncate_to_fit(font, text, box_w)
        if cut is None or cut == text:
            return props, True
        parsed["$text"] = f"`{cut}`" if quoted else cut
        parsed.pop("text", None)
        return merge_props(parsed), True

    if policy == "hide":
        ok = _fits(font, text, box_w, box_h)
        return props, True if ok is None else bool(ok)

    return props, True
