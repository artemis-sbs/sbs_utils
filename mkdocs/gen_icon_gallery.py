"""Regenerate the icon gallery in `docs/cosmos/gui_icons.md` from the library itself.

    python mkdocs/gen_icon_gallery.py

Writes two things and touches nothing else:

* `docs/media/icon-sheet.png` - the built-in sheet's 176 drawn glyphs, downscaled to
  64px cells (the page never shows them larger) so the docs carry ~1/40th of the art.
* the block between the BEGIN/END markers in the page - the prose around it is hand
  written and is left alone.

Generating rather than hand-listing is the point: the gallery cannot drift from
`icon_sheet.py`, so a new name shows up in the docs by re-running this.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from sbs_utils.procedural.gui.icon_sheet import ICON_GROUPS, ICON_ALIAS  # noqa: E402

SOURCE = r"f:/a/Cosmos-1-3-0/data/graphics/grid-icon-sheet.png"
CELL, COLS, DRAWN = 128, 20, 176
OUT_CELL = 64
SHEET_OUT = os.path.join(HERE, "docs", "media", "icon-sheet.png")
PAGE = os.path.join(HERE, "docs", "cosmos", "gui_icons.md")
BEGIN, END = "<!-- BEGIN generated gallery -->", "<!-- END generated gallery -->"


def build_sheet():
    """Crop to the drawn rows and downscale. The glyphs stay white on transparent, which
    is what lets one glyph serve every color - the page puts them on a dark chip so they
    read in both the light and the dark docs theme."""
    from PIL import Image
    rows = -(-DRAWN // COLS)
    sheet = Image.open(SOURCE).convert("RGBA").crop((0, 0, COLS * CELL, rows * CELL))
    sheet = sheet.resize((COLS * OUT_CELL, rows * OUT_CELL), Image.LANCZOS)
    # Every pixel is white, so the three color channels carry no information: LA drops
    # them, and 16 alpha levels are more than the eye finds on a 40px glyph. 543 KB -> 261.
    sheet = sheet.convert("LA")
    sheet.putalpha(sheet.getchannel("A").point(lambda v: round(v * 15 / 255) * 17))
    os.makedirs(os.path.dirname(SHEET_OUT), exist_ok=True)
    sheet.save(SHEET_OUT, optimize=True)
    return rows


def gallery(rows):
    by_look = {}
    for meaning, look in ICON_ALIAS.items():
        by_look.setdefault(look, []).append(meaning)

    out = [BEGIN, ""]
    for title, names in ICON_GROUPS.items():
        out.append(f"### {title}")
        out.append('<div class="icon-grid" markdown="0">')
        for name, idx in sorted(names.items(), key=lambda kv: kv[1]):
            col, row = idx % COLS, idx // COLS
            # Percentage sprite offsets: with a background sized to the whole sheet, 100%
            # is the LAST cell, so each step is 1/(count-1).
            x = col * 100.0 / (COLS - 1)
            y = row * 100.0 / (rows - 1)
            meanings = by_look.get(name)
            also = f'<em>{", ".join(sorted(meanings))}</em>' if meanings else ""
            out.append(
                f'<figure><i style="background-position:{x:.4f}% {y:.4f}%"></i>'
                f'<figcaption>{name}<span>{idx}</span>{also}</figcaption></figure>')
        out.append("</div>")
        out.append("")
    out.append(END)
    return "\n".join(out)


def main():
    rows = build_sheet()
    with open(PAGE, encoding="utf-8", newline="") as f:
        page = f.read()
    crlf = "\r\n" in page
    body = page.replace("\r\n", "\n")
    head, _, rest = body.partition(BEGIN)
    _, _, tail = rest.partition(END)
    body = head + gallery(rows) + tail
    with open(PAGE, "w", encoding="utf-8", newline=("\r\n" if crlf else "\n")) as f:
        f.write(body)
    total = sum(len(g) for g in ICON_GROUPS.values())
    print(f"{total} icons in {len(ICON_GROUPS)} groups -> {PAGE}")
    print(f"sheet {os.path.getsize(SHEET_OUT) // 1024} KB -> {SHEET_OUT}")


if __name__ == "__main__":
    main()
