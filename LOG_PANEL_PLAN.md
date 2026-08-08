# Log Panel - replacing the text waterfall

**Decision (Doug, 2026-08-07):** this is an UPGRADE that REPLACES the text waterfall, not a
second surface beside it.

The waterfall became a dumping ground. This feedback round alone produced four items against
it - raw quest ids printed to it (PRM-15), the wrong noun (PRM-16), fighter docking spam
(PRM-32), and a toast with nowhere sensible to live (PRM-8). Each was fixed on its own, but
they share a cause: one undifferentiated stream that everything writes to and nothing owns.

---

## The rule

> **The panel is for what you READ. Anything you ACT on stays interactive.**

Comms is deliberately NOT a tab. Comms is where a human acts - menus, dialogue, choices - and
folding it into a scrollback pane would turn participation into reading, flattening the thing
that makes a bridge feel like a crew. Info cards stay where they are too: read-only, but tied
to a comms interaction, and pulling them in would drag conversation back through the side door.

That rule decides future tabs without re-litigating this, and it is why the toast DOES belong
here (purely read-only) while comms never could.

---

## What is already confirmed

Checked, not assumed:

| Fact | Why it matters |
|---|---|
| **The engine never writes to the waterfall - it is all script** (Doug) | The widget can be fully retired. This is a replacement, not an "alongside". |
| `comms_broadcast(ids_or_obj, msg, color)` is the single write API | One choke point. Every mission follows without being rewritten. |
| `gui_text_area` already scrolls (`scroll_line`, `need_v_scroll`) | The container exists; this is composition, not invention. |
| `gui_text_area` already renders callouts (`_callout_styles` / `amd_callout`) | Callout formatting is reusable as-is. |
| Setting `.value` does NOT reset scroll | A tab switch is an assignment, not a page rebuild. |

---

## Architecture

**One `gui_text_area`. Tabs replace its content.** A tab is not a widget - it is a filter
argument. Switching tabs is `area.value = render(entries, tab)`, which the dirty system picks
up in place.

Three consequences worth stating, because they remove most of the expected work:

* **No page rebuild**, so none of the `reveal` / `get_selection_hint` machinery the quest tab
  and hangar needed applies here.
* **The content layer is a pure function** - `(entries, tab) -> markdown string` - so it is
  fully unit-testable with no GUI. That matters for a surface nobody can verify headlessly
  today.
* **The "N new below" affordance is just a line in the string.** No extra widget.

So the whole feature is: an append-only tagged store, a pure render function, a small tab row,
and one text area.

### Tabs

| Tab | Holds |
|---|---|
| **Log** | everything, chronological - the default and the safety net |
| **Ship** | damage, internal systems, docking, engineering events |
| **Mission** | objective and quest changes, mission beats |

Three, not four. "Alerts" was considered and rejected: it is a SEVERITY filter, not a
category, and anything urgent should already have announced via an overlay - so an Alerts tab
risks becoming the place urgency goes to be missed. Because a tab is a filter argument, adding
a fourth later is a data change, not a redesign.

### Callouts vs categories - two axes, not one

Asked (Doug, 2026-08-07): should a callout match a category? **No - they are orthogonal, and
collapsing them loses one of them.**

* **Category** = what the entry is ABOUT -> which tab it appears in.
* **Callout** = how URGENT it is -> how it looks.

A Ship entry can be routine ("docked at DS 1") or critical ("hull breach"); a Mission entry can
be a beat or a failure. Making the callout follow the category means either every Ship line
looks identical (severity lost) or severity picks the tab - which is the rejected "Alerts"
idea arriving by another road.

**A callout is also not free.** `_TITLE_HEIGHT = 24` + `_BODY_HEIGHT = 20` plus a background
box (`amd_callout._CALLOUT_KINDS`): give every line one and you roughly halve how many entries
fit in a small panel, and a wall of boxes is harder to scan than plain lines. So:

| Need | Mechanism | Cost |
|---|---|---|
| Which category is this line? | **color** (plus an optional short prefix) | free - one style string |
| Is this urgent? | **callout box** | 2 rows + background, so reserved |

That keeps the Log tab scannable, which is where it matters - entries from every category
interleave there and must be tellable apart at a glance.

**Reserve the boxes for severity, not topic:** `danger` (quest failed, hull breach, ship lost),
`warning` (timer expiring, shields critical), `tip` (a completion worth marking), and plain for
everything else, which is most of it.

**Two consequences worth having:**

* `quote` is the only kind with `background: None`, so a plain untagged message rendered that
  way looks essentially like a waterfall line does today. **Day-one visual parity is a
  rendering default, not extra work** - tagging later gains a color, escalating gains a box,
  both additive, matching the lossless migration above.
* The boxed entries should be exactly the ones that ALSO announced via an overlay. Something
  boxed in the log but never announced is an authoring bug the panel now makes visible.

### Tail-follow - CORRECTED, and it was backwards

The plan first said "add follow-to-tail". **Reading the widget showed the opposite is
needed.** `.value` sets `recalc = True`, and `calc_rich` then does
`self.scroll_line = min(self.last_line+1, len(self.lines))` - it snaps to the END on every
recalc.

So a text area ALREADY follows the tail. What was missing is the other half: nothing
preserved a reader's position when they had scrolled back, so new content yanked them to the
bottom mid-sentence. That was not a hypothetical to design around - it was the behavior.

**Implemented (2026-08-07):** a `follow_tail` flag on `TextArea`.

* Defaults **True**, so existing behavior is unchanged for every current caller.
* `calc_rich` snaps to the tail only while it is True; otherwise it restores the previous
  `scroll_line`, clamped (new content may be SHORTER than what the reader was looking at).
* The scrollbar sets it: scrolling away from the bottom -> False ("I am reading"), scrolling
  back to the bottom -> True ("follow along again"). The reader opts in and out by doing the
  obvious thing, with no extra control to find.

**Per-tab scroll: snap to tail on every switch.** You switch tabs to see what is happening now,
and remembering three offsets is state that will drift. If it is missed later it is a
`{tab: scroll_line}` dict.

### The toast lives here

The overlay principle is *overlay = attention, paired with a durable twin*. Putting the toast
in this panel makes that pairing SPATIAL: the notification appears exactly where its permanent
record lands, so "what was that?" is answered by looking at the same place.

It must occupy a **reserved strip** inside the panel, not float over the text - covering the
log while announcing something new is the one way this ends up worse than today. Retiring the
waterfall frees the space for it, which also settles the position question left open by PRM-8.

---

### Collapse

Asked (Doug, 2026-08-07): an icon that collapses the panel until the next content. Yes - the
panel spends real estate that helm and weapons may want back mid-fight.

**But "until the next content" taken literally means "hide for two seconds"** in a busy
mission, where content arrives constantly. The control would feel broken. So reuse the SEVERITY
axis rather than inventing a rule:

| Event while collapsed | Behavior |
|---|---|
| Routine entry (plain / `quote`) | stays collapsed; unread count increments |
| `warning` / `danger` | **auto-expands** |
| `tip` / completion | badge only - good news can wait |

Collapse then means "I do not want the chatter", not "hide briefly", and the only thing that
overrides the player's choice is the thing they would want overridden.

**Collapsed state IS the toast strip.** The toast already occupies a reserved strip inside the
panel, so a collapsed panel is not empty:

* collapsed = icon + unread badge + whatever toast is currently up
* expanded  = that same strip, plus the scrollback beneath it

You never lose the attention layer by collapsing - only the history. One surface with two
heights, rather than two things to design.

**Per-console, sticky for the session.** Helm may keep it collapsed while comms never does, so
tie the state to the console rather than the ship, and do not reset it on repaint or the player
will re-collapse it forever. The icon should communicate STATE (an unread badge does most of
the work); the glyph only needs to say "there is a log here".

## Scoping - the one thing awkward to retrofit

`comms_broadcast` takes EITHER player-ship ids OR client ids, and that distinction has to
survive:

* **Ship-scoped is primary.** Every console on a ship sees the same Log - that is what makes it
  the *ship's* log, and a crew asking "what did that say?" should be reading the same text.
* **Client-scoped is the exception**, a small per-console overlay for console-specific notices.

A console renders the union. Decide this before building: per-console-first gives five
diverging logs on one bridge and no way to merge them afterwards.

---

## Migration - lossless, and no mission rewrites

Keep `comms_broadcast(ids, msg, color)` exactly as it is; add an optional `category=`.

* Untagged messages appear in **Log** (which shows everything) and in no subset tab.
* Day one, with zero call sites touched, the panel behaves exactly like today's waterfall.
* Tagging a call site ADDS it to a subset tab; it never removes it from Log.
* So no message can go missing by being mis-tagged, and nothing has to change for this to ship.

Then tag at the SOURCE rather than per-mission - `quest_driver`'s completion/failure broadcasts
to Mission, docking and internal damage to Ship. Two library edits cover most of the value.

---

## Mechanism

### Mounting - it takes the waterfall's space, and the pattern already exists

`comms_waterfall` is an ENGINE console widget, named in each console's widget list
(`pages/start.py:94`, `gamemaster.mast:109`) and positioned with
`gui_layout_widget("comms_waterfall")`.

**LM already replaces its space today** - `consoles/layout_widgets.mast:287`:

    with gui_sub_section():
        water = gui_layout_widget("comms_waterfall")
        gui_hide(water)                       # claim the slot, hide the engine widget
        recent_listbox = gui_list_box(...)    # MAST content in the same sub-section
        history_text  = gui_text_area("", ...)

So mounting is a solved problem: claim the slot, hide the widget, draw into it. No new
layout scheme, and the panel inherits exactly the geometry the waterfall had on every console
that declares it.

### Getting rid of the engine waterfall - THREE wrong ways first

Worth writing down, because it cost real time and every wrong way reads as though it works.

**`gui_console()` is what declares it.** Not the layout. `procedural/gui/console.py` sets a
built-in widget list per console, and `text_waterfall` is in EVERY one of them:

    science:      science_2d_view^radar_zoom_ctrl^ship_data^...^text_waterfall^...
    helm/weapons/engineering/comms: all include it too

So the layout never had to ask for it, and REMOVING a `gui_layout_widget("text_waterfall")`
from a console's layout changes nothing at all - which is exactly what happened.

| Attempt | Why it fails |
|---|---|
| `gui_hide(widget)` | Clears `_show` on the layout PLACEHOLDER. The engine draws from the widget LIST and carries on. |
| Not calling `gui_layout_widget` | It was never the source - `gui_console` already declared it. |
| Expecting a new widget list to drop it | The engine KEEPS widgets it has been given. |

**What works: `gui_widget_offscreen(widget)`** - send it a rect at 100,100, out of view. That
is all `gui_panel_widget_hide` has ever done, now named, because an engine widget cannot be
un-declared.

`gui_hide()` now logs a warning when handed an engine widget, naming both remedies, so the
next person is told rather than left wondering.

**For the rollout:** when the tail goes to every console, the cleaner move is an `exclude`
argument on `gui_console` so the widget is never declared, rather than declaring it and
pushing it off screen on five consoles. Deliberately NOT added yet - it is speculative until
more than one console needs it.

### Tabs - reuse TabbedPanel, do not invent

`procedural/gui/tabbed_panel.py` already provides
`gui_info_panel_add(path, icon_index, show, hide=None, tick=None, var=None)` - tabs with icons
and per-tab show/hide/tick callbacks, re-represented on change. `gamemaster.mast:261` already
adds an engine widget as a tab through it.

This is the "tab panel similar to the info panel" from the brainstorm, and it exists. Log /
Ship / Mission become three `gui_info_panel_add` calls whose `show` sets
`area.value = render(entries, tab)`.

### Retention

Entries are strings, so MEMORY IS NOT THE CONSTRAINT. A waterfall line is ~40-120 chars
(~130-180 bytes as a `str`), plus a small record for its metadata - call it ~300 bytes an
entry. 500 entries is ~150 KB; 2000 is ~600 KB. Neither matters on a desktop.

**The real cost is RENDER**: the text area wraps and lays out every line on recalc, and this
surface updates whenever content arrives.

Start with a **single cap of 500 entries per scope**, rendered whole - one number, no paging,
~500 lines of scrollback (many screens, far more than anyone scrolls back through).

**The number that would change this is not memory, it is wrap cost.** Measure once with a
500-line text area; if it hitches, split the store (keep 500) from the render window (last
150-200) and add paging then, not now.

**Ring buffer with a monotonic sequence id per entry.** The id is what makes "N new below"
survive entries dropping off the top while a reader is scrolled back - without it, the count
drifts every time the buffer wraps.

### Font size - settled

Log text runs a size DOWN from document text: `LOG_FONT = "gui-1"` plain,
`LOG_CALLOUT_FONT = "gui-2"` for a severity line, so the hierarchy survives.

Why it needed setting at all: `amd_callout` is built for in-fiction DOCUMENTS, where a
callout has a title line and a body and the title SHOULD be bigger (`_TITLE_EXTRA` bumps it
to gui-3). Every log entry is a ONE-LINE callout - a title with no body - so it inherited
title emphasis for a line that is not a title. That is a consequence of reusing a document
feature for log lines, not a defect in `amd_callout`, which is left untouched: the override
lives entirely in `log_render`, and any other consumer of callouts still gets gui-2 body /
gui-3 title.

**Decided (Doug, 2026-08-07) after seeing it on a console: "for this with limited space this
looks good."** The panel shares a console with everything else, and density is worth more
here than matching document size. Do not raise it back on the argument that gui-1 is smaller
than the widget default - that is the point.

### Shapes

    entry = {
        "seq":      int,     # monotonic; survives the ring wrapping
        "t":        float,   # sim seconds, for ordering and any future timestamps
        "text":     str,     # what comms_broadcast was given
        "color":    str,     # its existing color argument, preserved
        "category": str,     # "log" (default) | "ship" | "mission"
        "severity": str,     # "" (plain) | "tip" | "warning" | "danger"
    }

    render(entries, tab) -> str     # PURE. filter by category, format to mini-markdown.
                                    # No GUI, no engine - unit-testable on its own.

`category` defaults to `"log"`, which is why an untagged message is lossless: Log shows
everything, subset tabs show their own.

### Where the store lives

Per SHIP (see Scoping), plus a small per-console overlay. **If it is a module-level container
it MUST be registered with `register_reset_state`** and cleared in `reset_mission_state` -
an unregistered per-mission container is a run-2 bug by construction, which is exactly what
PRM-3 and PRM-40 were this round.

### Interception

`comms_broadcast(ids_or_obj, msg, color)` keeps its signature and gains an optional
`category=` / `severity=`. During the parallel phase it does BOTH: append to the store AND
write the classic widget, so the two surfaces can be compared side by side on one console.
Retiring the widget is then deleting the second half of one function, per console.

## Build order

1. **`follow_tail` on `gui_text_area`** - the only real widget work, honored at recalc (not by
   poking `scroll_line`), and independently useful to any log-shaped text area.
2. **Store + `render(entries, tab)`** - pure, headlessly testable, no GUI. Tests: category
   filtering, the ring wrapping without breaking `seq`, severity picking the right callout,
   and an untagged entry appearing in Log and nowhere else.
3. **Mount on ONE console** via the existing `gui_layout_widget` + `gui_hide` pattern, Log tab
   only, with `comms_broadcast` doing both halves so the classic widget still renders beside
   it for comparison.
4. **Tabs** via `gui_info_panel_add`, then tag at the source (`quest_driver` -> Mission,
   docking + internal damage -> Ship).
5. **Collapse + toast strip**, once the expanded panel is proven.

Steps 1-2 need no console and no engine: they are the parts that can be verified properly.
Step 3 is the first thing to LOOK at, and it is a like-for-like - same content, new surface -
before any categorization or retirement decision.

## Open

* **Screen space.** It must be at least as large as the waterfall on consoles that are already
  crowded. Worth mocking one console at real proportions before committing.
* **Tabs hide things.** A crew under pressure will not switch tabs. Default to Log, and keep the
  rule that anything urgent still announces via overlay.
* **Panel-internal tabs, NOT console top-tabs.** That strip is capacity-limited and partly
  engine-owned (PRM-26); inheriting it would inherit that bug.

Related: `PRM_Feedback.md` (PRM-8, PRM-15, PRM-16, PRM-32), `OVERLAY_PLAN.md`.

## The strip was invisible: two causes, both found from one symptom

Reported as "I still do not see this control - anywhere", then narrowed by "all I see is
a back tick". Two separate bugs, either of which alone would have hidden it:

1. **An empty strip drew a lone backtick.** `TextArea` sends each line as
   ``$text:`text`;style``, so empty text reaches the engine as ``$text:``;`` -- a bare
   backtick, not blank. Until the first message arrived, that is all any console showed.
   Fixed with `log_tail_render()`, which substitutes a dim `...` for empty text. It lives
   in `log_panel.py`, not the GUI half, so it is testable without a page --
   `EmptyStripTests` in `tests/test_log_tail.py`, and that test was checked to FAIL with
   the substitution reverted.

2. **The strip never updated.** `gui_log_tail()` runs ONCE, while the console lays itself
   out; nothing repaints it afterwards, so it kept whatever the log held at that instant.
   Fixed with `log_tail_refresh()`, a push from `comms_broadcast` alongside `log_raise`.
   Registered tails live in `_TAILS` (client id -> widget, tab, count), cleared by
   `log_clear()`. Both `value` AND `line_styles` are replaced: `line_styles` is fixed at
   construction, so updating the value alone leaves the previous entry's color behind.

Together these are why a single run looked like "the feature does nothing" rather than
"the feature is stale" -- there was never a first frame to be stale from.

## Placement: under ship data, every console

Science and Engineering had drifted into a different COLUMN -- science put the strip
under `science_sorted_list`, engineering under `grid_object_list`. Both are now directly
below the info panel, matching comms/helm/weapons/main, and every one is `6em`. One
place to look on every console is the whole point of replacing the waterfall; a strip
that moves per console is worse than the widget it replaced.

## The colors were dropped by the FAST PATH, not by the strip

"It has text but not the colors." A `TextArea` whose value is a single line with no
`$`/`=` prefix sets `simple_text` and emits one ``$text:`line`;`` with no style at all --
and `line_styles` is read only by `calc_rich`. The strip is *always* exactly one line, so
it could never be colored, and neither could any other one-line `gui_text_area(...,
line_styles=[...])`. Silent, too: the text appears, just plain.

Caller-supplied `line_styles` is now treated as a request for the rich path
(`text_area.py`, `value` setter). It is a promise the fast path cannot keep.

Found by `tests/test_log_tail_render.py`, which renders a real MAST page and reads the
emitted `send_gui_text` stream -- the level these bugs live at. The store tests in
`test_log_tail.py` check WHICH entries are picked and were green throughout.

`log_tail_refresh` replaces `line_styles` as well as `value` for the same reason: styles
are fixed at construction, so a value-only update leaves the previous entry's color on
the new line -- a `danger` line would inherit chatter's.

## Background

`#0002` -- monochrome, low alpha. The strip sits behind text that carries meaning in
color (category tints, callout severity), so a tinted scrim shifts all of them. Black
rather than white because the consoles are dark: it reads as a slight recess.

## The toast is retired into the log

`status` and `minor` were the only announce levels with **no durable twin** -- the one
pair that broke this file's own house rule, since the corner toast was carrying the
information alone. It said its piece and took it with it: a console that connected a
second later never saw it, and neither did a crew looking at the 3D view. Every library
caller was a line worth keeping ("Docking moors active", "Pickup: nanites", "Objective
complete: ...").

So the toast writes to the ship's log now and draws nothing. The strip shows it where the
toast used to appear, and the log tab keeps it -- more visible AND recoverable.

Three entry points, one destination:

| entry point | before | now |
|---|---|---|
| `overlay_toast(...)` | corner card, stacking, auto-dismiss | log line |
| `announce(level="status"/"minor")` | corner card, no record | log line |
| `toast <text>` (AMD / quest directive) | corner card via `overlay_kind` | log line |

All three stay CALLABLE. There are thirteen `overlay_toast` call sites in LM alone and an
unknown number of authored `On complete: toast ...` directives; a MAST-facing name that
starts erroring is a break, not a retirement. `icon`, `seconds` and `slot` are accepted
and ignored -- they described a card that no longer exists.

`overlay_kind` intercepts `toast` itself rather than leaving it to the kind registry, so
the directive path and a direct call cannot drift apart again (they had: an authored
toast was registered STICKY while `overlay_toast` always expired).

`record=True` still forces a card, unchanged -- the escape hatch escapes where it always did.

`log_notify()` / `log_notify_all()` (gui/log_panel_gui.py) are now the single front door
for "the mission has something to say": log it, refresh the strips, raise if urgent.
Every producer needs those three steps and each one that hand-rolled them got a
different subset.

## Nothing raises the tab any more

`RAISE_ON = ()`. Raising made sense while the log was only a tab -- an urgent line nobody
opened the tab for was a line lost. The strip removed that reason and left only the
costs: it switched away from the ship data or message card the crew had chosen, with
nothing to switch back, so one warning left the panel stranded on the log.

Kept as a dial, not deleted: a mission that wants the panel seized for its worst news can
set `RAISE_ON = ("danger",)`, and `log_raise()` is still callable for the single beat
that has earned it.
