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
    key = (font, text)
    got = _line_w.get(key)
    if got is not None:
        _stats["hits"] += 1
        return got
    sbs = _sbs()
    if sbs is None:
        return None
    _stats["line_w"] += 1
    return _store(_line_w, key, sbs.get_text_line_width(font, text))


def measure_line_height(font, text):
    """Height in PIXELS of one unwrapped line, or None if unmeasurable.

    `text` is part of the key on purpose. The engine may vary line height with
    the glyphs present; the mock happens to ignore the argument, but encoding
    that belief here would bake a mock assumption into the library.
    """
    key = (font, text)
    got = _line_h.get(key)
    if got is not None:
        _stats["hits"] += 1
        return got
    sbs = _sbs()
    if sbs is None:
        return None
    _stats["line_h"] += 1
    return _store(_line_h, key, sbs.get_text_line_height(font, text))


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
    key = (font, text, px_width)
    got = _block_h.get(key)
    if got is not None:
        _stats["hits"] += 1
        return got
    sbs = _sbs()
    if sbs is None:
        return None
    _stats["block_h"] += 1
    return _store(_block_h, key, sbs.get_text_block_height(font, text, px_width))


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
        return (0.0, 0.0)
    text = text.strip()
    if len(text) >= 2 and text.startswith("`") and text.endswith("`"):
        text = text[1:-1]
    if not text:
        # Nothing drawn -- genuinely zero, not unmeasurable.
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
