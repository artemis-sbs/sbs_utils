# GUI draw_layer / occlusion plan

> **Status: DONE (2026-08-09), with phase A parked.** Phase B shipped and is engine-confirmed
> - the `layer:` style key is live (`procedural/style.py:117`, `mast/parsers.py:310`) and the
> layout literals are pinned. **Phase A (occlusion bands) is deliberately unbuilt**:
> `measure.py`'s `OVERFLOW_POLICIES` is still `("spill", "visible", "shrink", "ellipsis",
> "hide")` with no `occlude`. It is parked with a written unpark condition - read that before
> reviving it, the decision not to build was the point.
>
> The phase-0 engine probe table below is the durable half: it is the only recorded evidence
> of how the engine actually orders and occludes overflowing content.

**The problem.** In the **engine** (not the mock), GUI content overflows to the RIGHT and
to the BOTTOM and draws over its neighbours. The engine has no clip at any level -- text
wider or taller than its rect is drawn anyway. The library's answers today are to size
things so it cannot happen (content sizing, v1.4.0) and `overflow: spill | shrink |
ellipsis | hide` ([measure.py](sbs_utils/pages/layout/measure.py) `apply_overflow`), all of
which change the TEXT. None of them can hide a spill that has already happened.

**The question this plan answers.** Can `draw_layer` be used to avoid the overlap?

**The honest answer.** Not on its own -- `draw_layer` is z-order, not clipping. Two widgets
on the same pixels are both drawn; the layer only decides which wins. But paint order plus
an OPAQUE fill is occlusion, and occlusion is indistinguishable from clipping to the eye.

**Why it lines up so well.** Overflow only ever goes right and down (text lays out from the
rect's top-left). Document order is also left-to-right, top-to-bottom. So the VICTIM of a
spill is always emitted AFTER the spiller -- a monotonically increasing layer in document
order means "later paints over earlier", covering exactly the two directions that break.

---

## Status

| Phase | State |
|---|---|
| 0. Engine probe | **ANSWERED IN THE ENGINE, 2026-08-05. Occlusion works.** |
| B. Unpin the layer | **DONE and ENGINE-CONFIRMED** -- `layer:` style key, cascade, backgrounds and `gui_image` unpinned |
| A. `overflow: occlude` | **PARKED -- no production case found.** See the survey below |

### Phase B confirmed in the engine (`--map visual_layer_style`)

The same overflow twice, one row raised by `layer: 1500` and one untouched control:

- **blue band (with `layer:`) is SOLID** -- seven lines of overflow hidden behind it;
- **red band (control) shows every one of those lines drawn over it**, exactly as it
  always did.

So the whole chain -- style key -> section/row/column cascade -> unpinned backdrop ->
engine -- delivers, **and back-compat holds**: a layout that does not say `layer:` is
unchanged. (Second attempt. The first engine run was **inconclusive and looked like a
pass**: the paragraph ran the full panel width, wrapped to two lines, fit its row, and
so never reached either band -- both halves drew the same picture. A specimen whose two
halves cannot differ answers nothing. The spill now sits in a narrow column, and the
on-screen expectations lead with "check the spill actually reaches the band".)

## The engine result (2026-08-05)

Run in a real Cosmos session, not the mock. All six cells read cleanly:

| Cell | Result | What it establishes |
|---|---|---|
| 1 control | spill runs over the caption | baseline |
| **2 fill at 2000** | **solid blue, nothing through it** | **an opaque fill at a higher layer HIDES an overflow** |
| 3 fill, no layer | spill drawn ON TOP of the blue | on a tie **text beats an image even though the image was emitted later** |
| 4 fill at 500 | spill drawn on top of the blue | `draw_layer` is genuinely respected |
| 5 button under 5000 | button covered | button layer **< 5000** |
| 6 button under 500 | button visible | button layer **> 500** |

Cells 3 and 4 are what give cell 2 its meaning: **paint order is decided by the layer,
not by emission order**, so cell 2's fill won on the number alone. Cells 5+6 bracket the
button to `500 < button < 5000`, consistent with `1001` -- so the
[overlay.py:33](sbs_utils/procedural/gui/overlay.py#L33) comment claiming buttons sit at
`10000` is **stale**.

**Input is NOT stolen.** Hovering cell 5's covered button makes a thin highlight rim
appear around the outside of the fill, **only while hovering**. So the click/hover still
reaches a widget underneath an occluder -- Phase A may safely cover a control.

**And a fifth fact nobody was looking for: the engine draws button chrome OUTSIDE the
rect it was given.** The button and the fill in cell 5 were handed *identical* rects and
the fill still did not cover it. Consequence for Phase A: **a backdrop sized to the widget
it hides will leave a visible rim -- backdrops must be sized to the ROW or SECTION.**
Another argument for the section tier over per-widget occluders.

```
python -m cosmos_dev.mission_runner VisualTestRange --map visual_draw_layer --test 90   # data half
python -m cosmos_dev.mission_runner VisualTestRange --gui --map visual_draw_layer       # framing check only
```

The browser pass checks the FRAMING (are the six cells readable and clear of each
other), not the answer: the mock sets `zIndex` from `draw_layer` and clips at region
boundaries, so it will happily show its own opinion of a question only Cosmos can settle.

---

## What already exists (do not rebuild)

`draw_layer` is an existing style key on nearly every `send_gui_*` command (default
`1001`; see `f:/a/Cosmos-1-3-0/data/widget_stylestring_documentation.txt`), and the
library already carries it in three ways:

- **Widget props pass through verbatim.** `gui_text("$text:hi;draw_layer:5000;")` works
  today -- `self.message` goes straight to `send_gui_text`
  ([text.py:22](sbs_utils/pages/layout/text.py#L22)). Same for button, checkbox, slider,
  dropdown, typein.
- **Author intent is already respected.** [button.py:70](sbs_utils/pages/layout/button.py#L70)
  checks `if message.find("draw_layer") == -1` before adding its own. Precedent to follow.
- **Sub-regions carry a layer.** The overlay system stacks its slots this way
  ([overlay.py:249](sbs_utils/procedural/gui/overlay.py#L249)), `20000`-`30000`.

### The current layer map (as built, not as designed)

| Layer | Used by |
|---|---|
| `1000` | section / row / column background + border images (hardcoded literal) |
| `1001` | engine default; content; button text over a colorbutton |
| `10000` | claimed for buttons by the [overlay.py:33](sbs_utils/procedural/gui/overlay.py#L33) comment -- **contradicted** by button.py, which emits 1000/1001. One of the two is stale; Phase 0 settles it |
| `20000`-`30000` | overlay slots |

---

## The three real gaps

1. **Auto-emitted backgrounds are pinned to `1000`.** Literal in
   [row.py:170](sbs_utils/pages/layout/row.py#L170),
   [layout.py:1205](sbs_utils/pages/layout/layout.py#L1205),
   [column.py:239](sbs_utils/pages/layout/column.py#L239) (background AND border in each).
   Set `background_color` and it lands UNDER everything, with no way to raise it. This
   matters because the auto background is the only thing that spans the whole row/section
   box -- a hand-placed widget becomes a cell in the flow, not a backdrop behind it.
2. **`gui_image` silently drops `draw_layer`.** `ImageAtlas.__init__` parses only `image`
   and `color` out of a props string, and `get_props`
   ([image.py:253](sbs_utils/procedural/gui/image.py#L253)) rebuilds it from
   file/color/sub_rect. So the one widget type that can paint an opaque rectangle is the
   one that cannot be raised. Discovered while designing the probe.
3. **No cascade.** `get_cascade_props` carries font/color/justify only
   ([column.py:191](sbs_utils/pages/layout/column.py#L191)), so a section cannot set a
   layer for its contents -- it is per-widget hand-numbering.

---

## Phase 0 -- engine probe (built; gates everything)

`VisualTestRange/maps/visual_draw_layer.mast` + `visual_draw_layer_panel.py`.

**Raw emission on purpose.** The panel calls `sbs.send_gui_text` / `send_gui_image`
directly at explicit percent rects, bypassing the layout system entirely. Two reasons:
gaps 1 and 2 mean the probe cannot be built out of `gui_*` calls at all, and the question
is about ENGINE paint semantics, so involving our layout would only add variables.

Six cells, three questions:

| Cell | Setup | Reads as |
|---|---|---|
| 1 CONTROL | text overruns a short box, nothing over it | what a spill looks like -- the baseline |
| 2 OCCLUDE 2000 | same spill, opaque image over the spill zone at `draw_layer:2000` | **the whole plan.** Spill hidden = live |
| 3 NO LAYER | same, image with no `draw_layer` (engine default) | isolates layer from emission order |
| 4 UNDER 500 | same, image at `draw_layer:500` | if this ALSO hides it, draw_layer is ignored |
| 5 BUTTON vs 5000 | button with an opaque image over it at `draw_layer:5000` | covered = button below 5000 |
| 6 BUTTON vs 500 | same button, image at `draw_layer:500` | button visible = button above 500 |

Cells 5+6 bracket the real button layer and settle the 1001-vs-10000 contradiction. Hover
cell 5's covered button: if it still highlights, an occluder does NOT steal input, which is
the other thing occlusion has to not break.

**Decision:**

- Cell 2 hides the spill and cell 4 does not -> `draw_layer` occludes. Proceed to B.
- Cell 4 also hides it -> layer ignored, emission order rules. Occlusion is still possible
  but is ordering-based and far more fragile; re-plan.
- Cell 2 does NOT hide the spill -> the engine composites text above images regardless.
  **A and B are both dead**; the answer is sizing or `overflow: push`. Nothing spent.

---

## Phase B -- unpin the layer -- DONE

Everything a scripter needs to do occlusion BY HAND. Not a new mechanism -- A is this plus
automatic numbering.

- [x] `BACKDROP_LAYER` + `backdrop_props()` in
      [measure.py](sbs_utils/pages/layout/measure.py), which also carries the layer map and
      the engine evidence. The six hardcoded `draw_layer:1000` literals in
      `row.py` / `column.py` / `layout.py` (background AND border in each) now go through
      it. **Default is still `1000`, so no existing layout moves.**
- [x] `layer:` style key -- [parsers.py](sbs_utils/mast/parsers.py) case + a guarded int
      parse in [style.py](sbs_utils/procedural/style.py). Junk is ignored rather than
      taking the widget down.
- [x] Cascade. `Column.get_layer()`, `layer`/`default_layer` on Row and Layout aliased the
      way `color`/`font` already are, and a section->row->column resolution in `Layout.calc`
      beside the existing colour/justify block. So `layer:` on a **section** reaches every
      widget in it -- one declaration makes a whole panel occludable.
- [x] `get_cascade_props(..., layer=True, message=...)` emits `draw_layer` **only when one
      was set**, and **never** when the widget's own props already carry one (two
      `draw_layer` keys in one string is undefined; the nearer declaration wins -- the rule
      [button.py:70](sbs_utils/pages/layout/button.py#L70) already used). Wired into text,
      button, checkbox, text_input and the text area's simple path. Deliberately NOT wired
      into the text area's rich path, which folds the cascade into its own per-line `$$`
      language rather than an engine props string.
- [x] `ImageAtlas` carries `draw_layer` (gap 2): parsed from the props string, emitted by
      `get_props`, and overridable per USE exactly as `color` already is -- so
      `Image._present` passes `get_layer()` and a `layer:` style reaches an image, which is
      the widget that actually does the occluding.
- [x] Tests: [tests/test_layout_layer.py](tests/test_layout_layer.py), 11 cases (default
      unchanged, `layer: 0` is not "unset", author props win, cascade aliasing, the style
      key parses, unknown keys still dropped). Full suite **2636 OK**; LM map 0 against the
      working tree is clean with `--audit-layout` reporting 0 geometry findings.

---

## Why Phase A is PARKED -- the production survey

The overflows that prompted this had already been **worked around**, so a clean
`--audit-layout` sweep proves nothing. The workarounds themselves are the evidence: each
one marks a place someone wanted this. Every one found in LM and OU:

| Where | Real problem | What was actually done |
|---|---|---|
| `consoles/common_console_select.mast:207` | ship + console lists overflow their boxes | listbox `reveal`/`hint` -- **the container scrolls** |
| `consoles/server_console.py:27` | text spilling | reached for `gui_text_area` -- **the container scrolls** |
| `consoles/common_console_selection.py:37` | row-height rounding | **erred on the safe side** -- sizing |
| `consoles/layout_widgets.mast:99` | "Ship Data overlap" | section offset `45px` to clear the engine widget |

**Not one is a case occlusion would fix.** The first three are containers and sizing
doing their job -- which is the library working as designed, not a gap. The fourth cuts
against occlusion hardest: the thing overlapped is the **engine-drawn `ship_data`
widget**, so an opaque backdrop over the collision would hide content the player wants.
Repositioning was the CORRECT fix, not a workaround for a missing feature.

Nor does any production mission use `overflow: shrink | ellipsis | hide` -- only
`control_gallery` (the demo) and `issue672b` (the test). Authors are not reaching for the
existing policy either.

So automatic banding would buy a layer-numbering scheme, an audit that has to be taught
about it, and a comparison every `layer:`-free layout pays -- to fix nothing anyone has.
**Phase B already gives the capability to whoever hits a real case.**

**Unpark when** a panel actually needs to hide a spill AND what it spills onto is content
we draw ourselves (not an engine widget) AND the container for it does not already exist.
If that case is a whole panel over another panel, build ONLY the section tier -- it is a
renumber of backgrounds already being emitted, zero new widgets. The row tier needs its
own justification on top of that.

## Phase A -- `overflow: occlude` (automatic numbering) -- NOT BUILT

Only worth building where hand-numbering breaks down: loops, data-driven lists, listbox
item templates (generated sections nobody can number by hand).

1. **Section tier first.** Assign section content bands in document order and lift each
   section's EXISTING background image into the gap. **Zero new widgets** -- it is a
   renumber. Fixes panel-spilling-onto-panel.
2. **Row tier only if needed.** One backdrop image per row; costs a widget per row. Fixes
   row-onto-row inside one panel.
3. Teach [layout_audit.py](cosmos_dev/layout_audit.py) the banding scheme. It deliberately
   ignores overlap across different `draw_layer`s
   ([layout_audit.py:21](cosmos_dev/layout_audit.py#L21)) -- band every row and the tool
   that FINDS these bugs goes blind.
4. Write the layer map down (bands, strides, ceilings) so a stride cannot collide with the
   button or overlay bands.

---

## Limits -- what occlusion can never do

- **It needs a colour.** To paint over a spill you must paint something, and it has to be
  what should have been there. Over a `3dview` / `2dview` / background image it is
  impossible -- you would punch an opaque rectangle into the view to hide a line of text.
  **Occlusion is only available on solid-backed panels.** Panels over live views must be
  fixed by sizing.
- **It hides, it does not fix.** The text is still wrong; it is just not on top of anything
  any more. `spill` stays the default for exactly this reason -- a visible failure gets
  fixed, a silent one does not.
- **Widget cost.** The closest engine data is the console-latency measurement (9 engine
  console widgets: 18 missed engine ticks in 20s; 0 widgets: none). That was 2D/3D views,
  NOT `send_gui_*` text and images, so it does not transfer cleanly -- but it is a reason
  to prefer the section tier over the row tier.

---

## Open question (decides whether the row tier ships at all)

Is the reported overflow a **panel overrunning into the panel below/right of it** (section
tier, free) or **rows colliding inside one panel** (row tier, a widget per row)? And is
anything under the spill a live view? If so, that panel is a sizing fix, not an occlusion
one.

---

## Verification tiers

The **mock cannot answer any of this**: `client.html` clips regions (`overflow:hidden`), so
it hides the exact failure, and its UNCLIP toggle shows geometry, not blend order. Engine
session only. `--test` / `--audit-layout` green is not evidence here.

## Files

| File | Role |
|---|---|
| `VisualTestRange/maps/visual_draw_layer.mast` | Phase 0 specimen |
| `VisualTestRange/maps/visual_draw_layer_panel.py` | Phase 0 raw-emission panel |
| `sbs_utils/pages/layout/{row,column,layout}.py` | Phase B: the pinned literals |
| `sbs_utils/procedural/gui/image.py` | Phase B: `ImageAtlas` drops draw_layer |
| `sbs_utils/mast/parsers.py`, `sbs_utils/procedural/style.py` | Phase B: the `layer:` key |
| `cosmos_dev/layout_audit.py` | Phase A: must learn the banding |
