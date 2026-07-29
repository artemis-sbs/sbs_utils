# Listbox: keeping the selection on screen across a repaint

A plan, not a change. Pre-existing behaviour, reported 2026-07-29.

## The bug

A repaint rebuilds the listbox, the caller restores the selection with
`set_selected_index(i, False)`, and the view starts at the top. The selection is
held but may be **below the fold** — selected and invisible.

The caller's only alternative today is `set_selected_index(i, True)`, which sets
`self.cur = i` — scrolling the selection to the **top** of the box. That is
visible but jarring: the list jumps on every repaint, and an item near the end
cannot be at the top anyway.

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
- **`cur` is never exposed.** A caller cannot save it before a rebuild or restore
  it after, which is why a repaint always starts at the top.

## The fix, in three parts

### 1. Reveal the selection at present time

Not in `set_selected_index` — `max_slots` is not known until the rows have been
measured. During present, after packing:

- selection **above** the window (`sel < cur`) → `cur = sel`
- selection **below** (`sel >= cur + max_slots`) → back-pack: walk upward from
  `sel` accumulating row heights until the next row would not fit; the last index
  that fits becomes `cur`. This puts the selection at the BOTTOM of the window,
  which is the smallest move that reveals it.
- then clamp: `cur` never exceeds `len(items) - max_slots`, so the list cannot
  scroll past the end and leave blank space.

Moving `cur` changes `max_slots`, so pack once more after the adjustment. Once,
not to convergence — a second pass cannot make the selection invisible again,
because the back-pack was computed against the row heights it will use.

This alone fixes the reported bug: the selection is always on screen, and the
view moves the minimum needed rather than jumping to the top.

### 2. Keeping the slot across a repaint

**A repaint builds a DIFFERENT listbox.** It shares nothing with the one before
it — not the object, not the tag (`page.get_tag()` regenerates), not `sections`,
which are empty until it first presents. So there is no continuity to lean on:
whatever carries `cur` across has to be stored outside the widget and found again
by something stable.

The thread cannot be the tag. It has two candidates:

**a. Build ordinal (the default).** Within one page build, listboxes are created
in a deterministic order, so "the Nth listbox built on this client's page" is
stable across repaints of the same screen. That means the fix costs callers
NOTHING — the gallery, and every existing screen, gets it without a line
changing.

It mis-maps only when a page conditionally builds a *different number* of
listboxes before the one in question, so the Nth is a different list than last
time. That is real but rare, and it degrades to "restored a position from another
list", which the clamp and the reveal pass immediately correct.

**b. `view_key="…"` (the override).** For pages that do vary, and for anything
that wants to be explicit:

```python
gui_list_box(items, style, select=True, view_key="gallery_nav")
```

Storage is `{cur, selected_index}` per client, under the ordinal or the key.

**Stale state is expected, not exceptional.** Same key, different list; item
count changed; a section collapsed. So restoring is a HINT, always followed by:
clamp `cur` into `0..len(items)-max_slots`, drop a `selected_index` past the end,
then the reveal pass. Every one of those is needed by resize anyway, so this adds
no new machinery.

Selection is restored **by index**, not item identity: items are rebuilt each
repaint, so object identity does not survive. Index is right for a stable list
and an approximation when contents shift. A caller needing better can pass a key
function later; nothing needs it today.

### 3. Expose the view state

For callers that want to drive it directly — and because "the slot is internal"
is the actual complaint:

```python
lb.get_scroll_index()        # cur
lb.set_scroll_index(i)
lb.get_view_state()          # {"cur": n, "selected_index": m}
lb.set_view_state(state)
```

The ordinal/`view_key` mechanism is these two plus storage; a caller doing
something unusual can use them directly.

Note `get_view_state()` on a FRESHLY BUILT listbox returns the restored hint, not
a measured slot -- `sections` do not exist until it has presented once.

## Multiple clients

Verified rather than assumed: `Gui.clients[client_id]` each hold their own
`page_stack` with their own `Page`, and each page builds its own widgets. So the
**listbox instance is already per client**, `self.cur` is already per client, and
two consoles on the same screen do not scroll each other today. The server (client
0) showing the gallery and a console showing it are two pages, two listboxes, two
scroll positions — correctly.

That means the storage must be keyed by **(client, key)**, which per-client
inventory gives for free.

**But the build ordinal is a real hazard.** If the counter were module-level,
two clients building the same screen in the same frame would interleave and each
would get the other's slot number — scroll positions swapping between consoles,
intermittently, depending on tick order. The counter must live on the **page**
(which is per client, and distinct per entry in a `page_stack`, so a pushed page
cannot collide with the one beneath it) and reset at the start of each build,
where the tag counter already resets.

This is the one place where "it works on my single console" would hide a bug, so
it wants a test with two client ids building the same screen and scrolling
differently.

The common case, and the Control Gallery's: `on change lb.value: jump screen`.
The user clicks a visible row, that fires the repaint, and the page is rebuilt.

Two things make this work, both verified rather than assumed:

- **A click does not move the view.** `on_click` only resolves an index; nothing
  assigns `self.cur`. So at click time the scroll position is exactly what was
  last presented.
- **The widget that captured the click is the OLD one, and it will never present
  again.** So the view state cannot be saved "on the way out" — by the time the
  new listbox exists, the old object is gone. Save it **at the end of present**
  (and on `on_scroll`, which does move `cur`). Because a click leaves `cur`
  alone, the last presented value is still correct when the rebuild reads it.

Done this way the gallery case needs nothing from the caller: the clicked row
stays exactly where it was clicked, and the reveal pass does not fire at all —
the selection was visible by definition, since the user just clicked it.

## The slot is recoverable — use it, don't compute it

`on_click` resolves `index = self.sections[slot_index].item_index`, so the widget
already records **slot -> item index** for every visible row, every present.

That is the honest slot, and `get_view_state` should read it rather than
computing `selected_index - cur`. The arithmetic is wrong as soon as the list has
collapsible headers, a filter, or non-uniform rows — all three of which the
gallery's own index has. Restoring a slot then means choosing the `cur` that puts
the selection back at that section position, which is the same back-pack the
reveal already needs.

## Resize

The plan is that **resize needs no special case** — which is the point of doing
the reveal at present time rather than at selection time.

A resize is just a present with different bounds, so:

1. the saved `cur` is restored as a **hint**,
2. `max_slots` is packed against the new height,
3. the reveal pass clamps `cur` so the selection is inside the new window,
4. the end-clamp stops a shrunken list scrolling past its end.

Three cases fall out, and none needs to be detected explicitly:

- **Box grew** — more slots; the saved `cur` is still valid; more items become
  visible below. Nothing moves.
- **Box shrank, selection still fits** — `cur` unchanged, fewer rows below.
- **Box shrank past the selection** — the reveal pass pulls `cur` down until the
  selection is visible again.

The one thing NOT preserved across a resize is the exact slot number: if the
selection sat in slot 8 and only 5 rows now fit, slot 8 does not exist. Slot
position is a preference, visibility is the invariant — the reveal pass encodes
that ordering deliberately.

## Backward compatibility

- **The accessors are additive.**
- **The ordinal default is the behaviour change worth arguing about**: every
  existing listbox starts remembering its scroll position across repaints. That
  is the fix, and for the screens this was reported against it is exactly what is
  wanted -- but it does mean a screen that relied on "a repaint returns me to the
  top" no longer does. `view_key` cannot opt out of that; if an opt-out is
  needed it wants its own flag.
- **The reveal pass is a behaviour change** and I would default it ON: a
  selection the user cannot see is not a state anything wants, and today's
  alternative is a jump to the top. The one screen it could surprise is a list
  deliberately showing the top while something far down is selected — worth a
  flag (`reveal=False`) if such a screen turns up, but I would not add the flag
  before it does.
- `set_selected_index(i, True)` keeps its current meaning (selection to the top),
  since callers use it deliberately for "scroll here".

## Tests

The packing is per-row, so the cases that matter use **non-uniform heights**:

- selection below the fold becomes visible, and lands at the BOTTOM of the window
  (smallest move), not the top
- selection above the window scrolls up to it
- `cur` never exceeds `len(items) - max_slots` (no scrolling past the end)
- slot preserved across a rebuild at the same size (`view_key`)
- **selection-triggered repaint**: click a row that is NOT slot 0, rebuild, and
  that row is still in the same slot -- the gallery's own flow, and the one a
  naive "restore selection" gets wrong
- the slot is read from `sections[].item_index`, so a list WITH headers still
  reports the slot the user actually clicked
- box shrinks past the selection → selection visible again, slot not preserved
- box grows → nothing moves
- a list with no selection is unaffected
- **stale state**: restore a position from a list that has since shrunk -- `cur`
  is clamped, a `selected_index` past the end is dropped, nothing raises
- **ordinal identity**: two listboxes on one page keep separate positions, and
  the second page build maps each to the same one as the first
- **two clients, same screen**: each keeps its own scroll position; building both
  in one frame does not swap them (the ordinal counter is per page, not global)
- **a pushed page** over another does not collide with the page beneath it
- uniform-height list produces the same numbers as today (no existing listbox moves)

Mutation-check each: remove the reveal, remove the clamp — the relevant test must
fail, or it is asserting nothing.

## Open question

**Where does `view_key` storage live?** Per client (`set_inventory_value` on
`client_id`) is the obvious home and matches how console tabs already persist.
It leaks one small dict per key per client for the session, which nothing cleans
up when a console changes screens. Acceptable, but worth a decision rather than
a default.
