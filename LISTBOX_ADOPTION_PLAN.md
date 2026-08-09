# Listbox reveal/hint — adoption inventory for LM and OU

> **Status: ACTIVE (2026-08-09).** Buckets 1-2 adopted in LM (7 files with `reveal=`, 31
> `get_selection_hint` sites). Buckets 3-4 unadopted, and **OpenUniverse has zero adoption**
> - all three OU listboxes (`admiral.mast:352`, `:452`, `universe.mast:954`) are still plain
> `gui_list_box(..., select=True)`. `common_console_select` still awaits its engine check.
>
> **Re-score bucket 4 before trusting it.** The ranking counted jumps *into* a page as if
> they were repaints, which is why `console_select` scored high and was then a wrong verdict.
> Count the page's own fall-through and its handlers' jumps instead - see the note at the end
> of this file.

`gui_list_box(..., reveal=True, hint=saved)` landed opt-in with the Control
Gallery's index as its only caller (design and what the build changed:
`LISTBOX_VIEW_PLAN.md`). This is the inventory of everywhere else it could go,
**ranked**, with the engine check each one needs. One at a time.

**Reminder of what the two parts do**, because it decides every row below:

- **`reveal=True`** — scrolls the selection into view at present time. Fixes
  *"selected but below the fold"*, which is what `set_selected_index(i, False)`
  leaves behind after a rebuild.
- **`hint=`** — keeps the selection in the SAME SLOT across a repaint. Fixes
  *"the row moved out from under the mouse"*. Reveal alone does not: a repaint
  starts at `cur=0`, so the clicked row lands at the bottom of the window.

They are not alternatives. A page that repaints *because* of the selection wants
both.

## Scope

31 live `gui_list_box(` call sites (LM 28, OU 3). Comment-only occurrences (21,
nearly all dead code in `gamemaster.mast`) excluded.

Also 6 live `gui_property_list_box(` sites. It returns a `LayoutListBox`, so it
would *accept* the arguments — but its rows hold controls rather than being
selectable, so there is nothing to reveal. **Out of scope.**

## Ranked

### 1. PRIME — selection triggers the repaint AND the selection is restored

The exact shape the feature was built for. Every one of these has the gallery's
bug today: click a row low in the list and it jumps somewhere else under your
cursor.

| # | repo | file:line | listbox | notes |
|---|---|---|---|---|
| 1 | LM | `documents/quest_tab.mast:47` | `qbox` | **DONE, ENGINE-VERIFIED** (scrolling confirmed after the repaint, which is the regression that matters). Hint captured at all four repaint sites |
| 2 | LM | `items/item_gui.mast:58` | `ubox` | **DONE, ENGINE-VERIFIED.** Hardest repaint in either repo: self-ticks ONCE A SECOND while an item is counting down, so the list snapped to the top every second |
| 3 | LM | `casino/casino.mast:68` | `game_box` | **DONE, ENGINE-VERIFIED.** 5 rebuild paths |
| 4 | LM | `casino/bar.mast:125` | `patron_box` | **DONE, ENGINE-VERIFIED.** Busiest rebuilder in either repo -- every conversation line |
| 5 | LM | `fabrication/beacon_tabs.mast:63` | `fab_box` | **DONE, ENGINE-VERIFIED.** 1-second self-tick while a build runs |
| 6 | LM | `fabrication/beacon_tabs.mast:164` | `car_box` | **DONE, ENGINE-VERIFIED.** Rebuilt by `item_changed`, which fires constantly |

**All six PRIME items are done and ENGINE-VERIFIED.**
#1 It also turned up a latent bug next door:
`get_selected_index()` returns `None` when nothing is selected, and the restore
read `quest_sel_index >= 0` — `None >= 0` raises. Guarded.

### 2. High value — the page is rebuilt from many places

Not caught by "selection triggers repaint", but rebuilt constantly by *other*
handlers while a selection is held. Reveal matters here even more than in PRIME,
because the rebuild is not something the user just did and will not be expecting
the view to move.

| repo | file:line | listbox | why |
|---|---|---|---|
| LM | `hangar/hangar.mast:156` | `dock_picker` | **DONE, ENGINE-VERIFIED.** The page is a LOOP: `await gui()` falls through to `jump show_hangar`, so every interaction rebuilds all three lists |
| LM | `hangar/hangar.mast:157` | `ride_picker` | same page, same commit, verified |
| LM | `hangar/hangar.mast:188` | `quest_box` | same page, same commit (sortie board), verified |
| LM | `consoles/common_console_select.mast:205` | `ship_select_lb` | **DONE, awaiting engine check.** 8 player ships overflow the box; it slammed to the TOP every rebuild |
| LM | `consoles/common_console_select.mast:233` | `console_select_lb` | **DONE, awaiting engine check.** Restores with `set_value()`, which never touches `cur` -- the selected console sat below the fold |

The hangar is the single biggest win: three selectable lists on a page rebuilt
from a dozen places.

### 3. Repaints on select but does NOT restore the selection

Check *why* first. Either the selection is meant to be transient (then `reveal`
alone), or losing it is a latent bug of its own (then it wants both, plus a
`set_selected_index`).

| repo | file:line | listbox |
|---|---|---|
| LM | `consoles/brain_scan.mast:46` | `obj_list` |
| OU | `admiral/admiral.mast:452` | `agv_roster_lb` |
| OU | `universe_core/universe.mast:952` | `loc_box` |

### 4. Review — selectable, dynamic items, one rebuild path

Lower value, still worth a look. All have dynamic item sources, so all can
overflow their box.

| repo | file:line | listbox |
|---|---|---|
| LM | `consoles/game_results.mast:211` | `quest_box` (collapsible; file has a watcher) |
| LM | `consoles/layout_widgets.mast:283,284` | `recent_listbox`, `history_listbox` |
| LM | `director/panel.mast:67,69,71` | `screen_lb`, `ship_lb`, `console_lb` |
| LM | `documents/document_screen.mast:48` | `obj_list` (file has a watcher) |
| LM | `gamemaster/gamemaster_controls.py:61` | unbound |
| OU | `admiral/admiral.mast:352` | `adm_qbox` (watcher + tabs) |

### 5. Not applicable — display only (7)

No `select`, so there is no selection to keep on screen: `casino/bar.mast:132`,
`consoles/debug.mast:116`, `consoles/game_results.mast:191,199`,
`gamemaster/gamemaster.mast:516`, `hangar/hangar.mast:344`, `hangar/hangar.py:605`.

### 6. DO NOT TOUCH

- `consoles/server_console.mast:167` — `mission_picker` is **`carousel=True`**.
  Its window is one item, so revealing is meaningless and the packing path is
  different. It restores a selection and repaints on select, so the scan flags it
  as PRIME-shaped; it is not.
- **Any `horizontal=True` listbox.** Separate packing path with its own known,
  unfixed bugs. Tread lightly.

## The change, per site

Two lines, and the second one is the part that gets forgotten:

```
    default saved_hint = None
    lb = gui_list_box(items, style, ..., select=True, reveal=True, hint=saved_hint)
    lb.set_selected_index(i, False)          # explicit selection still WINS over the hint
    ...
    on change lb.value:
        saved_hint = lb.get_selection_hint()  # HERE, before the jump -- this widget
        jump the_page                         # holds the view and never presents again
```

## The engine check, per site

The mock cannot answer this — it renders, but "did the row stay under my mouse"
is a thing you see. For each adopted site:

1. Open the console, scroll the list **past the first screenful** (the list must be
   longer than its box or nothing can be observed — three tests during the build
   were vacuous for exactly this reason).
2. Click a row near the BOTTOM of the window. It must stay in the same slot, not
   jump to the top and not scroll away.
3. Scroll again after the repaint — scrolling must still work. Reveal firing every
   present made the gallery's list completely unscrollable, and that regression
   looks like "the list is stuck", not like a selection bug.
4. If the page has tabs or a watcher, switch away and back, and let the watcher
   fire while a low row is selected.
5. Resize the window with a low row selected: the selection must stay visible; the
   exact slot is not preserved and is not meant to be.

## Notes from the first two adopters

- **`set_value()` is enough to arm the reveal.** The hangar restores its selection
  with `set_value(obj)` rather than `set_selected_index(i)`, and only the latter
  re-arms `_reveal_pending` — but the flag is armed in the listbox CONSTRUCTOR, and
  a repaint builds a new listbox, so any restore before the first present is fine.
  `set_selected_index`'s re-arm is for a later selection change on an
  already-presented widget, a different case.
- **Take the hint AFTER the widget has presented.** In the hangar the obvious spot
  looked like just before `await gui()`; that is build time, when `sections` do not
  exist yet, so the hint would carry nothing and silently do nothing. It belongs
  after `await gui()` returns, immediately before the loop jump.
- **Three lists on one page want a dict, not nine lines.** `hangar_hints_capture()`
  / `hangar_hint()` in `hangar/hangar.py` take all three at each rebuild site and
  read them back by name, and handle `quest_box` being `None` when the quests addon
  is not loaded.
- **`--exercise` cannot reach either screen.** It does not click top tabs (so the
  quest tab never builds) and `--exercise-console hangar` never enters the hangar
  page even though the console is offered and enabled (probed: `hangar` is in
  `gui_get_console_type_list()`). Compile coverage IS real for both files —
  mutation-checked, a deliberate syntax error is caught and named — but runtime
  wiring on these two is engine-only until the harness can reach them. Teaching
  `--exercise` to click top tabs would unblock the quest tab, the airwing tab, and
  the fabrication beacon tabs.

## Engine pass for #2-#6 — DONE

Batched deliberately: these five are the same shape and a round trip each was
costing more than it was worth. All verified in one engine run. The triggers that
were checked, kept for the record:

| screen | how to reach it | the distinctive trigger to exercise |
|---|---|---|
| Upgrades tab | any bridge console, `upgrade` top tab | **activate an item** so a cooldown starts, then watch a second or two with a low row selected -- this is the 1-second self-tick |
| Casino | casino console | **Buy 10 / Cash Out** with a low game selected (a rebuild from a button, not from the list) |
| Bar | casino, enter the bar | **let somebody talk**, or send a toast -- the list rebuilt on every conversation line |
| Fabricate tab | engineering, `fabricate` top tab | **start a build** and watch it tick with a low recipe selected |
| Cargo tab | engineering, `cargo` top tab | **pick up salvage or eject something** while a low row is selected |

In every case: scroll past the first screenful first (or nothing is observable),
then confirm scrolling STILL WORKS afterwards -- reveal firing every present made
the gallery unscrollable, and that regression reads as "the list is stuck".

## The console-select screen — I got this wrong first

**It is an adopter, and one of the most valuable.** With 8 player ships and a
dozen-plus consoles both lists overflow their boxes. Recorded because the mistake is
repeatable:

I checked `ship_select_lb`, saw `set_selected_index(i)` with no second argument
(`set_cur=True`, so the selection is scrolled to the top and therefore never
invisible), concluded there was nothing to reveal — and generalised that to the
whole screen. **The listbox beside it fails the opposite way:** `console_select_lb`
restores with `set_value()`, which assigns `selected` and **never touches `cur`**, so
nothing moves the view and the selected console really does sit below the fold.

Two listboxes, two different restore APIs, two different failures, one screen. The
lesson: **classify per listbox by which restore API it calls**, never per screen.

| restore call | what it does to the view | needs |
|---|---|---|
| `set_selected_index(i)` (set_cur default True) | slams the selection to the TOP every build | `hint` (stop the jump); `reveal` is redundant for visibility |
| `set_selected_index(i, False)` | nothing — selection held, possibly off screen | `reveal` **and** `hint` |
| `set_value(obj)` | nothing at all, ever | `reveal` **and** `hint` |

Both calls here now pass `False` so the view is governed by reveal/hint — the
smallest move that makes the selection visible — rather than by a slam to the top.

Covered by `tests/test_listbox_modes.py::TestSetValueRestorePath`, added with this
adoption because `set_value()` + `reveal` had no test before and is now load-bearing.
Mutation-checked: disabling the reveal branch fails both of its positive tests.

**Also fixed here:** the `on change PLAYER_COUNT` path clamped with
`min(client_selected_index, len(ship_list))`. `set_selected_index` ignores an index
that is not `< len`, so shrinking the ship count past the selection silently
**cleared** it. Now `len(ship_list)-1`, matching the clamp the line above already
uses.

**Only one of its rebuilds can carry a hint.** `select_console_clear_ready` and
`game_started_console` are entered from other consoles and from game start — a
different task, with no presented widget to read a hint from. Only the
`player_ship_destroyed` handler is on the live page. So `reveal` is the load-bearing
half here and the hint is the bonus, which is the reverse of the tab screens.

**The risk framing still holds** (first screen every player meets; LM history has a
revert of server-console changes), so this one wants its own engine check rather than
riding along with a batch.

**The ranking flaw is still real**, separately from the wrong verdict: this screen
scored "high value" because the scan counted **7 jumps to `select_console`**, and
those are other labels ENTERING the page, not the page repainting itself. The hangar
scored 11 the same way and was genuine — only because its `await gui()` falls through
to `jump show_hangar`. Count the page's own fall-through and its handlers' jumps.
Everything in the Review bucket was ranked the same flawed way and needs that
re-check before anyone trusts it.
