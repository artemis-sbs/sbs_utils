"""The contact sheet: one still per shot, tiled into a single reviewable PNG.

This is the harness's primary output, not a debug aid. The person iterating the shot
list cannot watch video, so a sheet of stills IS the review - which is why a shot is
STEPPED and held rather than played on a clock, and why every tile is captioned with
enough of the shot record to act on what it shows.

Split deliberately: `tile_sheet` takes images and captions and knows nothing about OBS
or the engine, so the layout is testable with synthetic frames in milliseconds.
"""
import io
import os
import json

from PIL import Image, ImageDraw, ImageFont


CAPTION_H = 34
PAD = 8
BG = (24, 24, 28)
FG = (232, 232, 236)
DIM = (150, 150, 160)
MISSING = (52, 34, 34)


def _font():
    """A real font if one is around, else PIL's builtin - never a hard dependency."""
    for path in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(path, 13), ImageFont.truetype(path, 11)
        except Exception:
            continue
    f = ImageFont.load_default()
    return f, f


def caption_for(index, shot):
    """The two caption lines for a tile: what it is, and how it was framed.

    Framing rather than prose, because framing is the thing being judged - a tile that
    looks wrong is almost always a `Framing:`/`Yaw:` problem, and the fix should be
    readable off the sheet without opening the .amd.
    """
    label = shot.get("label") or shot.get("key") or "shot %d" % index
    framing = shot.get("framing")
    if isinstance(framing, (list, tuple)):
        framing = ",".join(str(f) for f in framing)
    bits = []
    if framing:
        bits.append(str(framing))
    elif shot.get("move"):
        bits.append("move")
    elif shot.get("lens"):
        bits.append("lens")
    if shot.get("yaw") is not None:
        bits.append("yaw %g" % shot["yaw"])
    if shot.get("pitch") is not None:
        bits.append("pitch %g" % shot["pitch"])
    if shot.get("seconds") is not None:
        bits.append("%gb" % shot["seconds"])
    subj = shot.get("subject")
    if subj is not None:
        bits.append("subj %s" % subj)
    return "%02d  %s" % (index, label), "  |  ".join(bits)


def tile_sheet(tiles, cols=6, width=480):
    """Tile (image_bytes_or_None, line1, line2) records into one captioned sheet.

    A None image is drawn as a labelled blank rather than skipped: a shot that produced
    no frame is information, and silently shortening the sheet hides it.
    """
    big, small = _font()
    frames = []
    for raw, l1, l2 in tiles:
        if raw is None:
            im = Image.new("RGB", (width, int(width * 9 / 16)), MISSING)
            d = ImageDraw.Draw(im)
            d.text((PAD, PAD), "no frame captured", font=big, fill=FG)
        else:
            im = Image.open(io.BytesIO(raw)).convert("RGB")
            if im.width != width:
                im = im.resize((width, max(1, round(im.height * width / im.width))))
        frames.append((im, l1, l2))

    if not frames:
        raise ValueError("no tiles to lay out")

    cell_w = width
    cell_h = max(im.height for im, _, _ in frames) + CAPTION_H
    cols = max(1, min(cols, len(frames)))
    rows = (len(frames) + cols - 1) // cols

    sheet = Image.new("RGB", (cols * cell_w + PAD * (cols + 1),
                              rows * cell_h + PAD * (rows + 1)), BG)
    draw = ImageDraw.Draw(sheet)
    for i, (im, l1, l2) in enumerate(frames):
        r, c = divmod(i, cols)
        x = PAD + c * (cell_w + PAD)
        y = PAD + r * (cell_h + PAD)
        sheet.paste(im, (x, y))
        draw.text((x + 2, y + im.height + 2), l1, font=big, fill=FG)
        draw.text((x + 2, y + im.height + 18), l2, font=small, fill=DIM)
    return sheet


def write_sheet(out_dir, tiles, shots, cols=6, width=480):
    """Write sheet.png, one full-size shot_NN.png per tile, and sheet.json.

    The per-tile files exist so one suspect frame can be looked at closely without
    re-shooting, and sheet.json records what each shot RESOLVED to - a dropped subject
    should read as data, not as a mysteriously short sheet.
    """
    os.makedirs(out_dir, exist_ok=True)
    captioned = []
    manifest = []
    for i, (raw, shot) in enumerate(zip(tiles, shots)):
        l1, l2 = caption_for(i, shot)
        captioned.append((raw, l1, l2))
        if raw is not None:
            with open(os.path.join(out_dir, "shot_%02d.png" % i), "wb") as f:
                f.write(raw)
        rec = {k: shot.get(k) for k in
               ("key", "label", "framing", "yaw", "pitch", "seconds", "ease")}
        rec["index"] = i
        rec["subject"] = shot.get("subject")
        rec["captured"] = raw is not None
        manifest.append(rec)

    sheet = tile_sheet(captioned, cols=cols, width=width)
    sheet_path = os.path.join(out_dir, "sheet.png")
    sheet.save(sheet_path)
    with open(os.path.join(out_dir, "sheet.json"), "w", encoding="utf-8") as f:
        json.dump({"shots": manifest, "cols": cols, "width": width}, f, indent=2)
    return sheet_path
