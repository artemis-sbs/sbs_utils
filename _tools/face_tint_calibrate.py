"""Measure each face sheet's base skin/hair color and emit multiply-corrected palettes.

The engine tints a face layer by MULTIPLYING it (cosmos_dev/mockgui/face.js drawLayer),
so a tint can only ever DARKEN. The old `skin_tones` table was authored as if the tint
replaced the color: half its entries are lighter than the painted skin underneath, so
they multiplied to roughly nothing and the slider did nothing for a third of its travel.

Matching a tone ABSOLUTELY (tint = D/B) is arithmetically correct and useless: measured
against the new art only 3 of 31 tones survive on Kralien and 8 on Skaraan, because the
painted skin is darker than most of the palette. A three-entry slider is worse than the
broken one.

So the palette keeps each tone's HUE and SATURATION and re-maps only its LIGHTNESS onto
the range multiply can actually reach. "fair" ends up as near-no-tint (the skin as
painted, which IS the light end), "dark5" as a deep warm multiply, "green3" as a teal
shift - every position visibly different, monotonic, and honest about what it is: a ramp
down from the painted skin, not an absolute color picker. Absolute control needs a
desaturated grey body cell in the art; ABSOLUTE_REACH below reports how far off we are,
so that ask stays measurable.

    python _tools/face_tint_calibrate.py            # table + reachability report
    python _tools/face_tint_calibrate.py --write    # regenerate sbs_utils/face_tints.py

Dev-only. faces.py carries the BAKED result so nothing measures at runtime.
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from face_contact_sheet import CELL, SHEETS, graphics_dir  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

#: Where each race's skin lives, and where its hair lives, as (row, col). Hair is
#: measured from a cell drawn in the neutral white/grey the new sheets use; a race with
#: no hair row has None and gets no hair palette.
BASE_CELLS = {
    "ter": {"skin": (0, 0), "hair": (3, 0)},
    "tor": {"skin": (0, 0), "hair": None},
    "ska": {"skin": (0, 0), "hair": (3, 1)},
    "kra": {"skin": (0, 0), "hair": None},
    "zim": {"skin": (0, 0), "hair": (1, 0)},
    # Arvonian gets one too. This was withheld on the reasoning that its eight busts have
    # their patterns painted in, so tinting one is tinting somebody's tattoos - which
    # sounded right and is wrong when you look at it: the patterns take the tint with the
    # skin and read as a different coloration of the same person, which is exactly what
    # the control is for. Rendered before changing it.
    "arv": {"skin": (0, 0), "hair": (2, 0)},
}

#: The authored intent - the colour somebody wanted to SEE - plus which correction to use.
#:
#: "ramp" keeps the painted skin's own character and moves only its lightness/warmth. It
#: is right for human tones: `fair1` should read as the face as drawn, and hue-correcting
#: it would flatten a warm complexion to grey.
#:
#: "hue" FORCES the hue by dividing out the base skin. It is the only thing that works for
#: a non-human colour: the base is warm (R>G>B), so an uncorrected blue tint merely darkens
#: toward the base and comes out BROWN - measured, `ice-blue` read #67553f. Corrected,
#: it reads as blue.
#:
#: A NOTE ON HOW DARK: reasoning about this from the median skin value badly understates
#: it. The median says a Terran blue caps at 30% brightness and must land muddy; the
#: rendered face does not, because its highlights sit far above the median and carry the
#: hue. Checked on all five tinted races, including Torgoth (base #302a25), green, blue
#: and red all read clearly. Render it, do not predict it.
#:
#: NEW TONES ARE APPENDED, never inserted. Old code passes an INDEX into this list.
SKIN_TONES = [
    ("none", "ffffff"),
    ("c1", "ffcd94"), ("c2", "fff0bd"), ("c3", "eac086"), ("c4", "ffe39f"), ("c5", "ffab60"),
    ("fair1", "f2efee"), ("fair2", "efe6dd"), ("fair3", "ebd3c5"), ("fair4", "d7b6a5"),
    ("fair5", "9f7967"),
    ("dark1", "70361c"), ("dark2", "714937"), ("dark3", "65371e"), ("dark4", "492816"),
    ("dark5", "321b0f"),
    ("warm1", "bf9169"), ("warm2", "8c644d"), ("warm3", "593123"),
    # The pre-existing alien tones. Moved to "hue" - as a plain ramp they all read as
    # mud, which is why nobody used them.
    ("green1", "964b00", "hue"), ("green2", "6d8b01", "hue"),
    ("green3", "009973", "hue"), ("green4", "69e1c3", "hue"),
    ("blue1", "0095b3", "hue"), ("blue2", "00c3e6", "hue"), ("blue3", "95e3f3", "hue"),
    ("violet1", "573d76", "hue"), ("violet2", "6e5e8e", "hue"),
    ("olive", "acb057", "hue"), ("pale-violet", "c0caff", "hue"),
    ("indigo", "333d70", "hue"),
    # Non-human skin tones (2026-09-20, by request). Named for the COLOUR and nothing
    # else - these ship in the product, so no borrowed species names.
    ("emerald", "6f9b3f", "hue"),     # vivid yellow-green
    ("jade", "3f7d54", "hue"),        # deeper, cooler green
    ("ice-blue", "9dc4d8", "hue"),    # pale blue
    ("cobalt", "4a7ea3", "hue"),      # deeper blue
    ("rust", "a8564a", "hue"),        # exact on Terran
    ("crimson", "8c3b35", "hue"),     # exact on Terran
    ("ashen", "9aa48e", "hue"),       # cool grey-green
    ("amber", "c9922f", "hue"),       # warm metallic
]

HAIR_TONES = [
    ("none", "ffffff"), ("blonde", "faf0be"), ("brown", "3d2314"), ("sandy", "cc9966"),
    ("chestnut", "97502d"), ("gunmetal", "1e1a33"), ("red", "7c0a02"),
    ("olive", "968b00"), ("green", "964b00"), ("violet", "3d0463"),
    ("indigo", "2a1a5e"), ("fuchsia", "fa01b3"),
]


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


def rgb_to_hex(rgb):
    return "".join(f"{int(round(max(0, min(255, c)))):02x}" for c in rgb)


def base_color(im, row, col):
    """The representative color of a cell: the per-channel MEDIAN of its opaque pixels.

    Median rather than mean because a bust carries specular highlights and deep shadow;
    the mean drags toward whichever the artist used more of, while the median lands on
    the midtone that actually reads as "this person's skin".
    """
    a = np.asarray(im.crop((col * CELL, row * CELL, (col + 1) * CELL, (row + 1) * CELL)),
                   dtype=np.float64)
    opaque = a[:, :, 3] > 200
    if not opaque.any():
        return None
    return np.median(a[:, :, :3][opaque], axis=0)


#: How dark the darkest tone is allowed to drive the layer. Below about a third the
#: sprite stops reading as skin and starts reading as a silhouette.
FLOOR = 0.34


def calibrate(base, tones):
    """[(name, tint_hex, absolutely_reachable, want)] for each authored tone.

    Two corrections, chosen per tone (see SKIN_TONES):

    "ramp"  keeps the tone's own hue and saturation and scales by a lightness factor from
            its luminance, so the palette spans FLOOR..1 instead of collapsing wherever
            the art is darker than the authored colour. Right for human tones.
    "hue"   divides the wanted colour by the BASE, so the base's own warmth is cancelled
            and the hue survives the multiply. Then darkens toward the wanted lightness.
            The only thing that works for a non-human colour.

    Index 0 stays exactly white either way - "no tint" has to mean no tint, or the face as
    the artist drew it becomes unreachable.
    """
    out = []
    for i, tone in enumerate(tones):
        name, want = tone[0], tone[1]
        mode = tone[2] if len(tone) > 2 else "ramp"
        d = hex_to_rgb(want)
        absolute = d / np.maximum(base, 1.0)
        reachable = bool((absolute <= 1.02).all())
        if i == 0:
            tint = np.array([255.0, 255.0, 255.0])
        elif mode == "hue":
            ratio = d / np.maximum(base, 1.0)
            tint = ratio / max(ratio.max(), 1e-6)     # most saturated version in reach
            lit = base * tint
            # Only darken - if the wanted colour is lighter than this, this IS the answer.
            k = min(1.0, float(d.mean()) / max(float(lit.mean()), 1.0))
            tint = np.clip(tint * k, 0.0, 1.0) * 255.0
        else:
            hue = d * (255.0 / max(d.max(), 1.0))
            k = FLOOR + (1.0 - FLOOR) * (float(d.mean()) / 255.0)
            tint = np.clip(hue * k, 0.0, 255.0)
        out.append((name, rgb_to_hex(tint), reachable, want))
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit", action="store_true", help="print the generated module")
    ap.add_argument("--write", action="store_true", help="write sbs_utils/face_tints.py")
    args = ap.parse_args(argv)

    gfx = graphics_dir()
    if gfx is None:
        raise SystemExit("could not find data/graphics")

    skin, hair, bases = {}, {}, {}
    for alias, spec in BASE_CELLS.items():
        im = Image.open(os.path.join(gfx, SHEETS[alias] + ".png")).convert("RGBA")
        for kind, tones, sink in (("skin", SKIN_TONES, skin), ("hair", HAIR_TONES, hair)):
            cell = spec[kind]
            if cell is None:
                continue
            b = base_color(im, *cell)
            bases[(alias, kind)] = b
            sink[alias] = calibrate(b, tones)

    for (alias, kind), b in sorted(bases.items()):
        rows = (skin if kind == "skin" else hair)[alias]
        n_ok = sum(1 for r in rows if r[2])
        print(f"{alias} {kind}: base #{rgb_to_hex(b)}  "
              f"absolute-reach {n_ok}/{len(rows)} (ramp gives all {len(rows)})")
        if not args.emit:
            for name, tint, ok, want in rows:
                res = rgb_to_hex(b * hex_to_rgb(tint) / 255.0)
                print(f"    {name:12s} want #{want}  tint #{tint}  -> reads #{res}"
                      f"{'' if ok else '   (not an absolute match)'}")

    if args.emit or args.write:
        out = ['"""Multiply-corrected tint palettes, one per face atlas.',
               "",
               "GENERATED by _tools/face_tint_calibrate.py - do not hand-edit; rerun the tool.",
               "",
               "Each entry is (name, tint_hex). The tint is what gets MULTIPLIED through the",
               "layer, not the color you end up seeing: the engine has no other blend mode, so",
               "a palette has to be expressed in the base art's terms. Index 0 is always pure",
               "white, because 'no tint' must keep meaning the face exactly as it was drawn.",
               '"""',
               ""]
        for label, table in (("SKIN_TINTS", skin), ("HAIR_TINTS", hair)):
            out.append(f"{label} = {{")
            for alias, rows in sorted(table.items()):
                out.append(f'    "{alias}": [')
                for n, t, _ok, _w in rows:
                    out.append(f'        ("{n}", "{t}"),')
                out.append("    ],")
            out.extend(["}", ""])
        text = "\n".join(out)
        if args.write:
            dest = os.path.normpath(os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "sbs_utils", "face_tints.py"))
            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            print(f"\nwrote {dest}")
        else:
            print("\n" + text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
