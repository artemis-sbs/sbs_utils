# GUI Layout Audit (spike: `gui-sizing-accuracy`)

A read-only, headless check that catches GUI **sizing** bugs — a widget whose rect
leaves its region, or two widgets that overlap — from the emitted `send_gui_*` rect
stream, instead of only by eyeballing the browser mock.

**Why it exists.** The browser mock *clips* at region boundaries (`overflow:hidden`
in `client.html`), so it **hides** the very overflow the real engine would draw. A
data-level audit sees what the browser conceals. And because **sbs_utils computes the
layout** (the mock runs the same Python), the rects the audit sees are the *exact*
rects the engine receives — so the positioning audit is faithful, not an
approximation.

## Running it

```
python -m cosmos_dev.mission_runner <mission> --map 0 --exercise --audit-layout
```

`--audit-layout` monkeypatches the sbs module's senders with recording wrappers
(zero render change, off unless the flag is passed) and prints a report at the end.
Works headless (`--test`) or with `--gui`. Findings are labelled with the console
they appear on and carry full rects for triage.

## What it checks

Coordinate model (confirmed against `client.html`): a widget's `left/top/right/
bottom` are **percent-local to its parent region** (`0..100`) at every nesting depth.
So the checks are uniform:

| Kind | Rule |
|---|---|
| `OVERFLOW` | a rect leaves `[0,100]` of its region (beyond `EPS=0.5`) |
| `OVERLAP` | two **same-`draw_layer`**, **content-kind** siblings intersect (> `MIN_OVERLAP=1%²`) |
| `DEGENERATE` | `right<=left` or `bottom<=top` (zero/negative area) |

Images / clickregions / sub_regions are excluded from `OVERLAP` (they're structural or
intentional background layers — text on a background image is not a collision). Findings
dedup across frames (the dirty system re-emits every tick).

Unit tests lock precision/recall: `tests/test_layout_audit.py` (11 cases — real bugs
flagged; clean / layered / different-draw_layer / dedup / per-client cases stay quiet).

## The UNCLIP browser toggle

`client.html` has an **UNCLIP** topbar button: it disables region clipping and outlines
regions (red) + widgets (blue), so overflow the engine would draw (but the browser
normally hides) becomes visible for a visual cross-check.

## Findings so far — LegendaryMissions map 0

Stable and converged across runs (598 frames → same 14 findings, no flapping):

1. **`normal_weap` checkbox overflow** (3×, systematic). Rect `(0,89.14)→(11.72,100.86)`
   — the "Manual" checkbox spills **0.86%** below its region floor. Source:
   `consoles/manual_weapons.mast` builds a **bottom-anchored** region ("Drawing is bottom
   to top") with a `3em` checkbox row whose accumulated height doesn't divide evenly into
   the region → the bottom row overshoots. **Real** row-height rounding, tiny magnitude.
2. **`mainscreen` color-row overlap** (11 pairs). Swatches tile at **11.9%** pitch while
   their text labels tile at **8.8%** — so every label straddles a swatch boundary rather
   than sitting on one swatch. Mismatched-pitch **misalignment** signature.

Both need a human severity/intent call (are they *ugly* / *intended*?), rendered to scale
in the eyeball artifact. Neither is a false positive.

## Font render fidelity — investigation result

Observed: text reads fine in the **engine** but is **larger / clipped** in the **browser
mock** (e.g. console-select names cut off). Root cause found, ruling out the obvious
suspects:

- **Not point-vs-pixel, not a wrong size table.** The browser's `_FONT_MAP`
  (`client.html`) **matches the engine's `data/preferences.json` exactly** — same faces,
  same sizes (`gui-3 = Goldman-Bold @28`, `gui-1 = GoldmanSansCd_Rg @22`, …).
- **Not a font-load fallback.** The Goldman `.ttf`s exist and serve `200` from
  `/fonts/` (`data/graphics/fonts/`).
- **It was CSS box overhead.** `.w-text` used `line-height:1.5` (= 42px on a 28px font)
  plus `padding:4px 6px`, while the sbs_utils layout only *budgets* rows at
  `get_text_line_height` (≈1.25× the font = ~35px). Browser text overran the reserved box
  and clipped. **Browser-only artifact — real missions and the engine are unaffected.**

**Fix applied:** `.w-text` → `line-height:1.2`, `padding:0 2px` (match the layout budget).
Evidence-based; needs a 5-second browser glance to confirm (does console-select stop
clipping?).

## Outcome so far

- **Audit findings across LM (map 0, Peacetime) + OU (universe): all benign.** The GUIs
  are clean because the layout work was done up front — so the audit's value is a
  **regression guard** (stay green on good code; red on a future regression), not a
  current-bug finder. `.w-text` browser clipping fixed (CSS box overhead); both LM findings
  judged benign in-engine.
- **Real production fix landed (engine-verified):** the actual sizing bug wasn't found by
  the audit but by the user's report — `TextArea` (`text_area.py`) estimated line capacity
  from the width of `M` (widest glyph), wrapping at ~60% of the usable width. Fixed to
  measure the real line's average → 100% width. Affects every `gui_text_area` everywhere.

## The real bug taxonomy (and which tool reaches each)

Overshoot is **resolution-dependent**: layouts mix percent with fixed px/em, so fixed
rows/fonts take a different fraction of a %-region as the window resizes (small windows =
worst). Three classes:

| Class | Caught by |
|---|---|
| 1. mixed %/fixed-unit overflow | mock audit **+ resolution sweep** |
| 2. listbox/text_area not re-adapting to bounds | mock audit **+ resolution sweep** |
| 3. engine word-wrap ≠ the measure functions | **real engine only** (mock wrap == mock measure) — needs `dev_queue`/EngineDriver |

## Roadmap / open items

- [ ] **Resolution sweep** (the high-value buildable piece) — vary `FrameContext.
  aspect_ratios`, re-present, take the WORST-case overflow per widget. Turns "audit at one
  resolution" into "find the window size where fixed fonts break the %-layout" (classes 1 & 2).
- [ ] **Real-engine measure-vs-render check** (class 3) — only the engine shows wrap ≠
  measure; drive it via `dev_queue`/EngineDriver, compare actual text extent to `get_text_*`.
- [ ] **Text-fit audit** stays deferred until the mock renders as tight as the engine
  (else browser-only false positives).
- [ ] **Font-metric table unification** to `preferences.json` (maintainability; touches
  mock tests — validate with the full suite). Low priority — cosmetic preview only.
- [ ] **Runner-chrome noise** — filter the error-overlay tags if it becomes a nuisance
  (error-free runs are already clean).

## Files

| File | Role |
|---|---|
| `cosmos_dev/layout_audit.py` | the audit (tap + checks + report) |
| `cosmos_dev/mission_runner.py` | `--audit-layout` flag |
| `cosmos_dev/mockgui/client.html` | UNCLIP toggle + `.w-text` fidelity fix |
| `tests/test_layout_audit.py` | precision/recall unit tests |
