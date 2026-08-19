"""Which interior cells a ship hull actually has - reconstructed from its silhouette art.

WHY THIS EXISTS. The engine owns the authoritative answer
(`hullmap.is_grid_point_open`), computed from `graphics/ships/<artfileroot>1024.png`.
The mock's hullmap was a stub: `is_grid_point_open` hardcoded `return 1`, `w`/`h` stayed
0, and `get_objects_at_point` returned `[]`. So headless, every ship was a solid
rectangle with no interior at all - nothing in the test path could tell you a room was
placed outside the hull, and damcon room-detection could never work. This module gives
the mock eyes.

**Mock and tooling only.** In the engine, ASK THE ENGINE - `is_grid_point_open` is
authoritative and free. Nothing here runs in production, which is why decoding a PNG in
Python is an acceptable cost.

TWO SOURCES, IN ORDER.

1. **The CAPTURE** (`hull_capture.py`) - the engine's own `is_grid_point_open`, recorded.
   Exact, and the only correct answer.
2. **This approximation** - alpha bounding box split into `internalmapw x internalmaph`
   with grid row 0 at the BOTTOM (the art is stored bow-down).

The approximation was once believed to BE the rule: it scores 0.987 against the authored
interiors. The engine refuted it - measured against `is_grid_point_open` it agrees only
**0.790**. The 0.987 was measuring whether authored rooms fall inside the silhouette,
which they do, and which is a weaker claim with no negative evidence in it. See
`GRID_REFERENCE.md` s2.

So this is now a FALLBACK, for hulls with no capture - a new mod ship, or a ship added
since the last probe run. It is good enough to be useful and is known to be wrong in
detail; never treat a fallback result as authoritative, and re-run the probe instead.

NO THIRD-PARTY DEPENDENCIES. `sbs_utils` takes no pip packages and `cosmos_dev` does not
either. A PNG is chunked zlib-compressed scanlines, so `zlib` plus the five unfilter
predictors is the whole decoder. We only ever need the alpha channel.
"""

import os
import struct
import zlib


# Alpha above this counts as hull. The silhouettes are hard-edged, so the exact value
# barely matters; it is here to reject stray near-transparent antialiasing.
_ALPHA_THRESHOLD = 8

# A cell counts as open when at least this fraction of its samples are opaque. Authored
# interiors put rooms on cells as thin as ~30% coverage at the hull edge, so a stricter
# cut would report false "off-hull" errors on shipped data.
_COVERAGE = 0.30

# Samples per axis within a cell. 10x10 is plenty: cells are tens of pixels across, and
# this runs once per (art, w, h) and is then cached.
_SAMPLES = 10

_BYTES_PER_PIXEL = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}   # gray, rgb, palette, gray+a, rgba


class PngAlphaError(Exception):
    """The file is not a PNG this decoder can read."""


def _unfilter(data, width, height, bpp):
    """Reverse the per-scanline PNG filters. Returns raw bytes, height * stride long."""
    stride = width * bpp
    out = bytearray(stride * height)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        ftype = data[pos]
        pos += 1
        line = bytearray(data[pos:pos + stride])
        pos += stride
        if ftype == 1:      # Sub
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:    # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:    # Average
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:    # Paeth
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 0xFF
        elif ftype != 0:
            raise PngAlphaError(f"unknown PNG filter type {ftype} on row {y}")
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return bytes(out)


def read_alpha(path):
    """Read a PNG's alpha channel.

    Returns ``(width, height, alpha)`` where ``alpha`` is a ``bytes`` of length
    ``width * height``. A PNG with no alpha channel reports every pixel opaque, which is
    the right answer for a silhouette stored without one.

    Raises PngAlphaError on anything this decoder does not handle (interlaced, 16-bit,
    palette with tRNS). Those do not occur in the ship art; the error names the case
    rather than silently returning a wrong mask.
    """
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise PngAlphaError(f"not a PNG: {path}")

    pos = 8
    width = height = depth = color = interlace = None
    idat = bytearray()
    while pos + 8 <= len(raw):
        (length,) = struct.unpack(">I", raw[pos:pos + 4])
        ctype = raw[pos + 4:pos + 8]
        body = raw[pos + 8:pos + 8 + length]
        pos += 12 + length              # 4 len + 4 type + body + 4 crc
        if ctype == b"IHDR":
            width, height, depth, color, _comp, _filt, interlace = struct.unpack(
                ">IIBBBBB", body)
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            break

    if width is None:
        raise PngAlphaError(f"no IHDR: {path}")
    if interlace:
        raise PngAlphaError(f"interlaced PNG not supported: {path}")
    if depth != 8:
        raise PngAlphaError(f"bit depth {depth} not supported (need 8): {path}")
    if color not in _BYTES_PER_PIXEL:
        raise PngAlphaError(f"color type {color} not supported: {path}")

    bpp = _BYTES_PER_PIXEL[color]
    pixels = _unfilter(zlib.decompress(bytes(idat)), width, height, bpp)

    if color == 6:      # RGBA
        return width, height, bytes(pixels[3::4])
    if color == 4:      # gray + alpha
        return width, height, bytes(pixels[1::2])
    # No alpha channel at all - a fully opaque image.
    return width, height, b"\xff" * (width * height)


def alpha_bbox(width, height, alpha):
    """Bounding box of the non-transparent pixels as ``(x0, y0, x1, y1)``, x1/y1
    exclusive. Returns ``None`` when the image is fully transparent."""
    min_x, min_y, max_x, max_y = width, height, -1, -1
    for y in range(height):
        row = y * width
        for x in range(width):
            if alpha[row + x] > _ALPHA_THRESHOLD:
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y
    if max_x < 0:
        return None
    return (min_x, min_y, max_x + 1, max_y + 1)


def _cells_from_alpha(width, height, alpha, w, h):
    """The rule itself, isolated so the engine probe has one place to correct.

    Returns a list of ``h`` rows of ``w`` booleans, row 0 first (bow).
    """
    box = alpha_bbox(width, height, alpha)
    if box is None:
        return [[False] * w for _ in range(h)]
    x0, y0, x1, y1 = box
    cell_w = (x1 - x0) / w
    cell_h = (y1 - y0) / h

    rows = []
    for gy in range(h):
        # THE FLIP: grid row 0 is the BOTTOM of the bounding box.
        uy = h - 1 - gy
        row = []
        for gx in range(w):
            opaque = total = 0
            for j in range(_SAMPLES):
                py = int(y0 + cell_h * (uy + (j + 0.5) / _SAMPLES))
                if py < 0 or py >= height:
                    continue
                base = py * width
                for i in range(_SAMPLES):
                    px = int(x0 + cell_w * (gx + (i + 0.5) / _SAMPLES))
                    if px < 0 or px >= width:
                        continue
                    total += 1
                    if alpha[base + px] > _ALPHA_THRESHOLD:
                        opaque += 1
            row.append(total > 0 and (opaque / total) >= _COVERAGE)
        rows.append(row)
    return rows


_cache = {}


def _art_1024(art_file_root, ships_dir=None):
    """Where the `<root>1024.png` silhouette for an artfileroot lives.

    THE ENGINE MAKES MULTIPLE CHECKS, and `data/graphics` IS THE ASSUMED DEFAULT BASE.
    This mirrors that, in the same order:

      1. GRAPHICS-RELATIVE - THE DEFAULT. `ships/<name>`, which is what stock
         `data/shipData.yaml` reads for all 184 entries, and `../missions/<pack>/...`
         for a pack reaching out of the graphics folder.
      2. EXE-RELATIVE  `data/missions/__lib__/media/<pack>/ships/<name>`. Engine v1.3.6
         made artfileroot carry the whole path this way, and retired the companion
         `artfilepath` field; it is what a mod built after v1.3.6 ships.
      3. BARE `<name>`, resolved under `graphics/ships` - older packs, and all over the
         extra ship-data files mods and LegendaryMissions ship.

    All of them are accepted because those files are versioned separately from the engine,
    so the spellings coexist for as long as any pack does.

    WHY A MISS IS EXPENSIVE HERE. A missing mask is deliberately read as "unknown" rather
    than "solid", so getting the base wrong does not raise - it shows up as every hull in
    the mock quietly losing its interior. That is exactly how the previous base change was
    found, and why a new spelling gets a candidate rather than a replacement.

    `ships_dir` is a caller-supplied override, tried first. Nothing in the mock passes one
    any more - the hullmap used to hand over a folder taken from a shipData `artfilepath`
    key, which does not exist: `artfileroot` carries the whole path and no companion field
    is needed. Kept for tests that want to point the resolver at a temp folder.
    """
    from sbs_utils import fs
    leaf = f"{art_file_root}1024.png"
    parts = leaf.replace(chr(92), "/").split("/")
    graphics = os.path.join(fs.get_artemis_data_dir(), "graphics")
    candidates = []
    if ships_dir is not None:
        candidates.append(os.path.join(ships_dir, leaf))
    # data/graphics is the assumed default and is tried first; exe-relative (v1.3.6+)
    # and the bare-name form follow. See the docstring.
    candidates.append(os.path.join(graphics, *parts))
    candidates.append(os.path.join(fs.get_artemis_dir(), *parts))
    candidates.append(os.path.join(graphics, "ships", leaf))
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]        # report against the first place we looked


def open_cells(art_file_root, w, h, ships_dir=None, ship_key=None):
    """Open-cell grid for one hull, or ``None`` if it cannot be determined.

    Prefers the engine CAPTURE for ``ship_key``; falls back to approximating from the art.
    ``None`` means "unknown", and callers should stay permissive rather than reporting a
    whole ship as solid rock - a missing capture and a missing art file are both mock
    limitations, not statements about the hull.

    Cached per ``(ship_key, art, w, h)``: decoding a 1024x1024 PNG in Python is not
    something to do per tick.
    """
    if w <= 0 or h <= 0:
        return None
    key = (ship_key, art_file_root, w, h)
    if key in _cache:
        return _cache[key]

    # 1. The engine's own answer, if we have it.
    if ship_key:
        from . import hull_capture
        captured = hull_capture.captured_cells(ship_key, w, h)
        if captured is not None:
            _cache[key] = captured
            return captured

    # 2. Fall back to approximating from the silhouette.
    if not art_file_root:
        _cache[key] = None
        return None

    path = _art_1024(art_file_root, ships_dir)


    cells = None
    if os.path.exists(path):
        try:
            width, height, alpha = read_alpha(path)
            cells = _cells_from_alpha(width, height, alpha, w, h)
        except (PngAlphaError, OSError, zlib.error):
            cells = None            # unreadable art -> unknown, not "no hull"
    _cache[key] = cells
    return cells


def clear_cache():
    """Drop the decoded-mask cache. Art does not change mid-session, so this is for
    tests and for a mission restart that might point at a different data directory."""
    _cache.clear()


def cache_size():
    """Reset-ledger probe / test helper."""
    return len(_cache)
