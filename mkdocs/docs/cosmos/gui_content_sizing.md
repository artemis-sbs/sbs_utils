# Sizing to content — `auto`, `content`, `min-content`, `max-content`

Rows and columns **fill** by default: a section's height is split across its rows,
a row's width across its columns. That is usually what you want, but it means a
label like `Shields:` gets the same share as the value beside it, and you end up
hand-tuning percentages that then break at another window size.

Add a keyword and the row or column sizes itself to what is actually in it.

```
gui_row("row-height: content;")
gui_text("$text:`Shields:`;", "col-width: content;")   # hugs its own text
gui_text("$text:`{shield_pct}%`;")                     # takes the rest
```

The label is now exactly as wide as the word `Shields:` — at every window size,
with no percentages to maintain.

## `auto` — and why you rarely have to type it

`auto` is the odd one out, and the one you are probably already getting:
**it is the default.** A row or column that says nothing is `auto`.

`auto` keeps a column in the flex pool — it still shares the leftover space —
but puts a **floor** under it, so it is never squeezed below its `min-content`.
A column with a long word grows, and its roomier neighbours give way. The other
keywords take a column *out* of the pool and give it a size of its own.

That is the difference in one line:

| | in the flex pool? | floor |
|---|---|---|
| `auto` (default) | yes — shares leftover space | never below `min-content` |
| `content` / `min-content` / `max-content` | no — sized from its content | n/a |

Because `col-width` cascades column → row → section, putting `auto` on a section
makes every column in it minimum-aware without annotating any of them.

## The four keywords

| keyword | on a **column** | on a **row** |
|---|---|---|
| `auto` *(default)* | flex, but never below `min-content` | flex, but never below its content height |
| `content` | natural width, clamped to what is available | as tall as the tallest cell **at its final width**, wrapping included |
| `min-content` | the widest unbreakable word | *alias of `content`* |
| `max-content` | the whole line, unbroken | tallest cell measured as one unwrapped line |

`min-content` on a **row** is an intentional alias. A true CSS row `min-content`
(how tall it gets when wrapped as narrow as possible) is expensive to compute and
not useful for a console.

```
# same string, three widths
gui_text("$text:`AA EXTRAORDINARILY BB`;", "col-width: min-content;")  # ~ "EXTRAORDINARILY"
gui_text("$text:`AA EXTRAORDINARILY BB`;", "col-width: content;")      # natural, clamped
gui_text("$text:`AA EXTRAORDINARILY BB`;", "col-width: max-content;")  # the whole line
```

## Requests, not reservations

A content size says *"this is what I'd like"*, not *"reserve this for me"*. When
a row cannot hold everything, space is given up in a fixed order:

1. **flex columns shrink to 0** — they draw nothing, so this costs nothing visually
2. **content columns shrink** proportionally, down to `min-content`
3. below that it **clamps** and accepts the overflow

That order exists because **the engine does not clip text**. A zero-width flex
column is invisible; a content column squeezed past `min-content` draws its
letters across whatever is beside it.

Rows behave the same way: over-tall content rows scale down proportionally so the
flex rows are not left with a negative share. **Fixed rows are never scaled** — an
over-large fixed row is your instruction, and it is honoured.

## What can and cannot be measured

| measurable | sizes to |
|---|---|
| `gui_text`, `gui_button`, `gui_checkbox`, `gui_input`, radio buttons | their text |
| `gui_image` | the image's real pixel size |
| a sub-section (`gui_sub_section`) | its widest row / the sum of its row heights |
| `gui_blank` | zero — a spacer asked to size to content collapses |

| declines | why |
|---|---|
| `gui_drop_down`, `gui_slider` | width includes engine-drawn chrome (arrow, border) that cannot be measured |
| `gui_text_area` | already scrolls to handle its own overflow |
| `gui_ship`, engine console widgets | drawn by the engine, no reportable size |

**Anything that declines falls back to a normal flex share — never to zero.** That
is what makes this safe to put on a whole section:

```
gui_section("area: 10,10,90,90; col-width: content;")
```

Every column in that section sizes to its content, and the ones that cannot are
laid out exactly as they would have been before.

## Gotchas

**`col-width` is in the same units as `area:`.** Both are screen percent, not a
fraction of the panel. In a section spanning `51..99`, `col-width: 26` is about
half of it — `col-width: 55` runs off the right-hand edge.

**Content cannot invent space.** Fill a section with fixed `em` rows and the
content rows will correctly be squeezed to nothing:

```
gui_section("area: 1,1,49,20;")
gui_row("row-height: 2.4em;")   # x6 -- already taller than the section
...
gui_row("row-height: content;") # -> zero height, and rightly so
```

If a content row renders flat, the section is oversubscribed. Give it room.

**Squares are special.** An icon or face is square, so its size comes *from* the
row height — it therefore ignores `col-width: content`, and it never drives a
content row's height (that would be circular). A row containing nothing but
squares has no natural height and falls back to flex.

**`em` is one line of the ROW's font — not of the text inside it.** A row that
declares no font gets the **default font, `gui-2` (24px)**. If the text inside
declares something bigger, the row is too short, and because the engine does not
clip, the text draws over its neighbour:

```
gui_row("row-height: 1em;")                     # 24px -- the DEFAULT font
gui_text("$text:`{name}`;font:gui-3;")          # draws at 28px -> overdraws
```

Two fixes. Say the font on the row, so `em` means what you meant:

```
gui_row("row-height: 1em;font:gui-3;")          # now 28px
```

…or use `row-height: content`, which measures the real text and stays right if
the font changes later. One line of each font, for when you need the number:

| font | one line |
|---|---|
| `smallest` | 18px |
| `gui-1` | 22px |
| `gui-2` *(default)* | 24px |
| `gui-3` | 28px |
| `gui-4` | 32px |
| `gui-5` | 36px |
| `gui-6` | 52px |

**Padding is `left, top, right, bottom`, and top/bottom come out of the row
height.** A single value is horizontal only and costs no height:

| padding | row | text box |
|---|---|---|
| *(none)* | 48px | 48px |
| `13px` | 48px | 48px |
| `10px,10px,10px,0` | 48px | 38px |
| `0,10px,0,10px` | 48px | 28px |

So a row that must hold one line of `gui-3` **and** 10px of top padding needs
`row-height: 1em+10px`, not `1em`.

**Arithmetic works in `row-height` and `col-width`** — `1em+10px`, `62-25px`,
`2*3em`, `min(10,20)`. (Before v1.4.0 a `+` or `-` term was silently dropped and
you got just the first value, so old layouts may have been running with sizes
they did not ask for.)

**Inside a `gui_list_box` item template, size the ROWS — do not return a
height.** The listbox only resizes an item's section to its content when the
template returns `None`, and each section starts at zero height. Return a size
and the section stays degenerate: the row becomes unclickable, with no selection
highlight. Content keywords inside a listbox template also still fall back to
flex, so set the row heights explicitly there.

**Check narrow wrapping in a real session.** Row heights over text that wraps
inside a narrow column are the least certain case: the headless mock agrees with
the engine at column widths ≥600px, and 94% of the time at ≥300px, but diverges
below that. Since the engine does not clip, a row that is short by one line spills
into whatever sits under it. The `content_demo` mission exists to make that
visible.

## Cost

A layout that uses none of these keywords pays **one identity comparison per
column** and nothing else — no measuring, no allocation, no extra pass.

Sizing to content does turn a *value* change into a *layout* change: if a column
is as wide as its text, new text may mean a new width. That only triggers a
re-layout when the measured size **actually moves**, so a status line cycling
through same-width values stays on the cheap path.
