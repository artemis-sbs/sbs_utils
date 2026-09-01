# ePADD design canvas

Design source for the ePADD console tablet - the artboards behind the published
canvas, not library code.

    node build.mjs        # *.src + _style.inc  ->  *.dc.html

Then re-seed and publish with the `design` skill's `seed-canvas.mjs`, passing every
`*.dc.html`, every `epadd-*.png`, and `canvas.json`.

## What is here

| File | What it is |
|---|---|
| `_style.inc` | The Cosmos console vocabulary, shared by every artboard. Real values: Goldman / Goldman Sans Condensed, `#1572` / `#1578` panels, `#333` / `#999` strip buttons, gui-1..6 at 22/24/28/32/36/52px. |
| `Main.src` | ePADD home, Engineering. Interactive - clicking a tile opens it. Station and dev-build are tweak chips. |
| `BeforeAfter.src` | Today's eight-slot strip against the two-button one. |
| `HomeHelm.src` | The same shell on a console that registers no ship apps. |
| `AppCargo.src` | An app open, with the PADD bar above its own unchanged body. |
| `ManyApps.src` | What a console carrying more than twelve apps does. |
| `Spec.src` | Build sheet: geometry, color, type, the icon sheet, and three things the code has to get right. |
| `sheet.html` | **The icon sheet source.** 4 x 4 cells of 128px, white on transparent like `data/graphics/grid-icon-sheet.png`, so `color:` still does the tinting. |
| `epadd-icon-sheet.png` | That sheet, rasterized. |
| `epadd-<name>.png` | Its cells, sliced and tinted, for the artboards only. |

## Re-rendering the icon sheet

`sheet.html` is plain SVG, so a glyph is an edit to a path rather than a redraw:

    chrome --headless=new --disable-gpu --hide-scrollbars \
      --default-background-color=00000000 --window-size=512,512 \
      --screenshot=epadd-icon-sheet.png file:///<abs path>/sheet.html

The built-in engine sheet was tried first and rejected: it is game-icons.net art, so
Help is a pointing hand, Airwing an unreadable blob, and `wanted` has the word baked
into the glyph.
