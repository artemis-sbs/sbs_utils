# Listbox reveal/hint — adoption inventory for LM and OU

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
| 2 | LM | `items/item_gui.mast:58` | `ubox` | **DONE, awaiting engine check.** Hardest repaint in either repo: self-ticks ONCE A SECOND while an item is counting down, so the list snapped to the top every second |
| 3 | LM | `casino/casino.mast:68` | `game_box` | **DONE, awaiting engine check.** 5 rebuild paths |
| 4 | LM | `casino/bar.mast:125` | `patron_box` | **DONE, awaiting engine check.** Busiest rebuilder in either repo -- every conversation line |
| 5 | LM | `fabrication/beacon_tabs.mast:63` | `fab_box` | **DONE, awaiting engine check.** 1-second self-tick while a build runs |
| 6 | LM | `fabrication/beacon_tabs.mast:164` | `car_box` | **DONE, awaiting engine check.** Rebuilt by `item_changed`, which fires constantly |

**All six PRIME items are done.** #1 engine-verified; #2-#6 await one engine pass.
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
| LM | `consoles/common_console_select.mast:205` | `ship_select_lb` | restores a selection; 7 jumps to `select_console` |
| LM | `consoles/common_console_select.mast:233` | `console_select_lb` | same page |

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

## One engine pass for #2-#6

Batched deliberately: these five are the same shape and a round trip each was
costing more than it was worth. Check them in this order -- each has a distinctive
rebuild trigger, and the trigger is the thing most likely to be wrong:

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

## Deliberately NOT batched: the console-select screen

`consoles/common_console_select.mast:205,233` are ranked high value and left alone
on purpose. It is the screen every player meets first, LM's history has a
"Revert this session's server-console changes" commit in it, and a regression there
locks people out of the game rather than annoying them. Worth its own pass, with
its own engine check, once the five above are confirmed.
