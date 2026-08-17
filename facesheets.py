"""Assemble the 512px face cells into stock-shaped sheets.

8x8 of 512 = 4096x4096, exactly the geometry of Skaraan_Set / Zimni_Set / etc, so
face.js's gridCols() (8 for any alias that is not 'ter') and the engine agree with
no special-casing. 192 cells therefore land in three sheets, which also satisfies
"at least 64 cells in a single png".

Emits the name -> face-string map alongside, because a face here is ONE layer:
    tng1 #fff <col> <row>;
"""
import json, os
from png import load
from pngw import save

CELLS = r"E:\a\Cosmos-dev\data\missions\Cosmos-TNG-Mod\new\work\facecells"
OUT = r"E:\a\Cosmos-dev\data\missions\Cosmos-TNG-Mod\new\work\facesheets"
CELL, GRID = 512, 8
PER = GRID * GRID
os.makedirs(OUT, exist_ok=True)

cells = json.load(open("cells_manifest.json"))
sheets = (len(cells) + PER - 1) // PER
faces = {}

for s in range(sheets):
    alias = f"tng{s+1}"
    W = H = CELL * GRID
    buf = bytearray(W * H * 4)
    placed = 0
    for k in range(PER):
        idx = s * PER + k
        if idx >= len(cells):
            break
        c = cells[idx]
        p = os.path.join(CELLS, c["name"] + ".png")
        if not os.path.exists(p):
            continue
        col, row = k % GRID, k // GRID
        w, h, ch, px, _, _ = load(p)
        ox, oy = col * CELL, row * CELL
        for y in range(min(h, CELL)):
            src = (y * w) * ch
            dst = ((oy + y) * W + ox) * 4
            for x in range(min(w, CELL)):
                i = src + x * ch
                o = dst + x * 4
                buf[o] = px[i]; buf[o+1] = px[i+1]; buf[o+2] = px[i+2]
                buf[o+3] = px[i+3] if ch == 4 else 255
        faces[c["key"]] = f"{alias} #fff {col} {row};"
        placed += 1
    name = f"TNG_Faces_{s+1}"
    save(os.path.join(OUT, name + ".png"), W, H, buf)
    print(f"{name}.png  {W}x{H}  {placed} cells  alias {alias}")

json.dump(faces, open(os.path.join(OUT, "tng_faces.json"), "w"), indent=1, sort_keys=True)
print(f"tng_faces.json: {len(faces)} face strings")
print("sample:", {k: faces[k] for k in list(sorted(faces))[:3]})
