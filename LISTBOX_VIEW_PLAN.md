# Listbox: keeping the selection on screen across a repaint

> **Status: DONE (2026-08-09).** Both parts shipped opt-in and engine-verified:
> `procedural/gui/listbox.py:84` takes `reveal=False, hint=None`, documented at :110-116;
> tests in `test_listbox_modes.py` and `test_listbox_packing.py`. Default-on is deliberately
> deferred ("a later conversation"), and the `horizontal=True` packing path is untouched.
> Adoption elsewhere is tracked separately in `LISTBOX_ADOPTION_PLAN.md`.
>
> The four "what the build changed" contracts below are behavioral rules, not history - reveal
> fires ONCE rather than every present, indices are DISPLAY indices, and an explicit selection
> beats the hint's.

**BOTH PARTS BUILT and engine-verified**: `gui_list_box(reveal=True, hint=...)`,
opt-in, with the Control Gallery's index as the first caller. Four things the
build changed in this plan:

- **Reveal ONCE, not at every present.** The plan said "at present time" and I
  read that as every frame -- which drags the view back and makes the list
  unscrollable. Armed on view-(re)establish and selection change; disarmed by the
  reveal and by a deliberate scroll, which is the later instruction and wins.
- **DISPLAY indices, not unfiltered.** A collapsible list has two spaces and they
  diverge once a header collapses. This broke the gallery twice.
- **Opt-in, not default-on.** The plan argued for default-on. Two regressions in
  a load-bearing widget say otherwise; default-on is a later conversation.
- **An EXPLICIT selection beats the hint's.** Not in the plan at all. The caller
  sets the selection after construction while the hint applies at present time,
  so applying it unconditionally lets a stale hint override a deliberate choice --
  which would have broken the tour, that moves the selection itself every step.
  The hint's job is the VIEW; its selection is a fallback.

**And the reveal alone was not enough**, which the plan did say and I still had
to be told: it promises VISIBLE, not UNMOVED. A repaint starts at cur=0, so the
clicked row landed at the bottom of the window. Part 2 is what keeps it under the
mouse -- the two are not alternatives.

Also: testing it means driving `_present` and `on_scroll`, and keeping the window
SMALLER than the list -- three tests here were vacuous because everything fitted
on screen. See tests/test_listbox_modes.py.

---

Pre-existing behaviour, reported 2026-07-29.

## The bug

A repaint rebuilds the listbox, the caller restores the selection with
`set_selected_index(i, False)`, and the view starts at the top. The selection is
held but may be **below the fold** — selected and invisible.

The caller's only alternative today is `set_selected_index(i, True)`, which sets
`self.cur = i` — scrolling the selection to the **top** of the box. Visible, but
it jumps on every repaint, and an item near the end cannot be at the top anyway.

So the two available behaviours are "maybe invisible" and "always jumps".

## What the widget actually tracks

| | |
|---|---|
| `self.cur` | index of the **first visible** item — the scroll offset |
| `max_slots` | how many items fit, packed from **real row heights** starting at `cur` |
| `self.selected` | the selected item objects (not indices) |
| `self.sections[n].item_index` | slot -> item, rebuilt every present. `on_click` reads it, so the slot is already recorded — it just is not exposed |

Two consequences that shape everything below:

- **`max_slots` depends on `cur`.** Rows are not uniform — packing walks
  `items[cur:]` accumulating heights until the box is full. So "is the selection
  visible" cannot be answered without knowing where the view starts, and moving
  the view changes the answer.
- **A repaint builds a DIFFERENT listbox.** It shares nothing with the one before
  it — not the object, not the tag (`page.get_tag()` regenerates), not `sections`,
  which do not exist until it first presents.

## The fix, in two parts

### 1. Reveal the selection at present time (automatic)

Not in `set_selected_index` — `max_slots` is not known until the rows have been
measured. During present, after packing:

- selection **above** the window (`sel < cur`) → `cur = sel`
- selection **below** (`sel >= cur + max_slots`) → back-pack: walk upward from
  `sel` accumulating row heights until the next row would not fit; the last index
  that fits becomes `cur`. That puts the selection at the BOTTOM of the window —
  the smallest move that reveals it.
- then clamp: `cur` never exceeds `len(items) - max_slots`, so the list cannot
  scroll past the end and leave blank space.

Moving `cur` changes `max_slots`, so pack once more after the adjustment. Once,
not to convergence — a second pass cannot hide the selection again, because the
back-pack was computed against the row heights it will use.

**This alone fixes the reported bug**, for every existing screen, with no caller
change: the selection is always on screen and the view moves the minimum needed.

### 2. An opaque hint, passed to the next clone (opt-in)

Revealing is not the same as *not moving*. To hold the selection in the same
slot, something has to cross the rebuild — and since the new listbox shares
nothing with the old, that something must be carried by the caller.

```python
lb = gui_list_box(items, style, select=True, hint=saved_hint)
...
on change lb.value:
    saved_hint = lb.get_selection_hint()
    jump repaint
```

`get_selection_hint()` returns an **opaque token**. The caller never inspects it;
it just hands it to the next clone. That is the whole contract.

Why opaque matters: the contents can then change without an API break. Today it
would carry `cur`, the selected index, the slot from `sections`, and the bounds
it was measured at. Tomorrow it can carry an item fingerprint so a shifted list
re-finds its selection. No caller is affected, because no caller ever looked
inside.

**What this design avoids**, all of which an earlier draft of this plan had:

- no widget registry, no per-client store, and so nothing to prune when a console
  changes screens
- no identity guessing (a build ordinal, a `view_key` string) and so no
  collisions between two lists that happen to share a key
- **no multi-client hazard.** The hint lives in a task variable, and tasks are
  already per client — where an ordinal counter would have had two consoles
  building the same screen in one frame swapping each other's scroll positions,
  intermittently, by tick order.

The cost is two lines in the caller. That is the right trade: it is explicit,
it has no hidden lifetime, and the screens that care are exactly the screens that
will write them.

**A hint is always a HINT.** Stale is the normal case — a shorter list, a
collapsed section, a different screen entirely. So applying one is followed by:
clamp `cur` into range, drop a selection past the end, then the reveal pass.
Every one of those is needed for resize anyway, so it is no extra machinery, and
a hint from an unrelated list degrades to a harmless wrong scroll position that
the reveal immediately corrects.

## When the repaint is triggered BY the selection

The common case, and the Control Gallery's: `on change lb.value: jump screen`.
The user clicks a visible row, that fires the repaint, and the page is rebuilt.

Two things make this work, both verified rather than assumed:

- **A click does not move the view.** `on_click` only resolves an index; nothing
  assigns `self.cur`. So at click time the scroll position is still exactly what
  was last presented, and a hint taken in the handler is accurate.
- **The widget that captured the click is the OLD one, and it will never present
  again** — so the hint must be taken in the handler, before the jump. It cannot
  be collected later, and there is nothing to collect it from.

Done this way the clicked row stays exactly where it was clicked, and the reveal
pass never fires — the selection was visible by definition, since the user just
clicked it.

## The slot is recoverable — use it, don't compute it

`on_click` resolves `index = self.sections[slot_index].item_index`, so the widget
already records **slot -> item index** for every visible row, every present.

The hint should carry that, not `selected_index - cur`. The arithmetic is wrong
as soon as a list has collapsible headers, a filter, or non-uniform rows — all
three of which the gallery's own index has. Restoring a slot then means choosing
the `cur` that puts the selection back at that section position, which is the
same back-pack the reveal already needs.

## Resize

**Resize needs no special case** — the point of doing the reveal at present time
rather than at selection time.

A resize is a present with different bounds, so: the hint's `cur` is applied,
`max_slots` is packed against the new height, the reveal clamps `cur` so the
selection is inside the new window, and the end-clamp stops a shrunken list
scrolling past its end. Three cases fall out, none detected explicitly:

- **Box grew** — the saved `cur` is still valid; more items visible below.
- **Box shrank, selection still fits** — `cur` unchanged, fewer rows below.
- **Box shrank past the selection** — the reveal pulls `cur` down until it shows.

The hint carries the bounds it was measured at, so a future version could tell a
resize from a plain repaint and prefer the slot ratio. Not needed for the
reported bug; recorded because the opaque token makes it addable later.

What is NOT preserved across a resize is the exact slot number: if the selection
sat in slot 8 and only 5 rows now fit, slot 8 does not exist. **Slot is a
preference, visibility is the invariant** — the reveal encodes that ordering.

## Multiple clients

Verified: `Gui.clients[client_id]` each hold their own `page_stack` with their
own `Page`, which builds its own widgets. So the listbox instance is **already
per client**, `self.cur` is already per client, and two consoles on one screen do
not scroll each other today. The server (client 0) showing the gallery and a
console showing it are two pages, two listboxes, two scroll positions.

With the hint carried in a task variable, that stays true for free — there is no
shared state to key correctly.

## Backward compatibility

- **`hint` and `get_selection_hint()` are additive.** A listbox that ignores them
  behaves as now.
- **The reveal pass is a behaviour change**, default ON: a selection the user
  cannot see is not a state anything wants, and today's alternative is a jump to
  the top. It moves the view only when the selection would otherwise be invisible.
  The one screen it could surprise is a list deliberately showing the top with
  something far down selected — worth a flag if such a screen turns up, not
  before.
- `set_selected_index(i, True)` keeps its meaning (selection to the top); callers
  use it deliberately for "scroll here".

## Tests

The packing is per-row, so the cases that matter use **non-uniform heights**:

- selection below the fold becomes visible, and lands at the BOTTOM of the window
  (smallest move), not the top
- selection above the window scrolls up to it
- `cur` never exceeds `len(items) - max_slots` (no scrolling past the end)
- **hint round-trip**: take a hint, build a new listbox with it, the selection is
  in the same slot
- **selection-triggered repaint**: click a row that is not slot 0, rebuild with
  the hint, that row is still in the same slot — the gallery's flow, and the one
  a naive "restore selection" gets wrong
- the slot comes from `sections[].item_index`, so a list WITH headers reports the
  slot the user actually clicked
- **stale hint**: apply one from a list that has since shrunk — `cur` clamped, an
  out-of-range selection dropped, nothing raises
- box shrinks past the selection → visible again, slot not preserved
- box grows → nothing moves
- a list with no selection is unaffected
- uniform-height list produces the same numbers as today (no existing listbox
  moves)

Mutation-check each: remove the reveal, remove the clamp — the relevant test must
fail, or it is asserting nothing.
