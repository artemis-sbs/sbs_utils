# Sizing to content — `auto`, `content`, `min-content`, `max-content`, `square`

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

## `1fr` — and why you rarely have to type it

`1fr` is the odd one out, and the one you are probably already getting:
**it is the default.** A row or column that says nothing is `1fr`.

> **Naming.** This mode is an equal share of the leftover space, with a minimum
> — which CSS spells `1fr` (grid) or `flex: 1` (flexbox). It used to be called
> `auto`, and **`auto` still works**, but the name mispredicted the behaviour:
> CSS's own `auto` means *size to your content and shrink under pressure*, which
> is nearly the opposite. Prefer `1fr` in new work. If `auto` is ever given its
> CSS meaning, only scripts that wrote `auto` explicitly will change.

`auto` keeps a column in the flex pool — it still shares the leftover space —
but puts a **floor** under it, so it is never squeezed below its `min-content`.
A column with a long word grows, and its roomier neighbours give way. The other
keywords take a column *out* of the pool and give it a size of its own.

That is the difference in one line:

| | in the flex pool? | floor |
|---|---|---|
| `1fr` (default, was `auto`) | yes — shares leftover space | never below `min-content` |
| `content` / `min-content` / `max-content` | no — sized from its content | n/a |
| `square` *(columns only)* | no — sized from the ROW HEIGHT | n/a |

Because `col-width` cascades column → row → section, putting `1fr` on a section
makes every column in it minimum-aware without annotating any of them.

## The keywords

| keyword | on a **column** | on a **row** |
|---|---|---|
| `1fr` *(default; `auto` is an alias)* | flex, but never below `min-content` | flex, but never below its content height |
| `content` *(`fit-content` is an alias)* | natural width, clamped to what is available | as tall as the tallest cell **at its final width**, wrapping included |
| `min-content` | the widest unbreakable word | *alias of `content`* |
| `max-content` | the whole line, unbroken | tallest cell measured as one unwrapped line |
| `square` | **as wide as it is tall** — sized from the row height | **not valid** (it would be circular; raises) |

## `square` — as wide as it is tall

The other keywords derive a width from the column's own content. `square` derives
it from the **other axis**: the column becomes as wide as the row is tall. It is
what a portrait, an icon, a ship render or a badge normally wants.

```
gui_row("row-height: 6em;")
gui_face(face, style="col-width: square")     # a 6em square
gui_text("$text:`Harkin`;justify:left")       # flex: takes the rest
```

**`square` and an explicit width are mutually exclusive** — setting either clears
the other. They are two answers to one question, and holding both is an illegal
state rather than a combination: a square column carrying a width is counted twice
when the row is divided up, so the row reserves its space twice over and, because
the engine does not clip, draws the surplus over and outside its neighbours.

`gui_face` and `gui_icon` are square by default. `gui_ship` and the image widgets
are **not** — left alone they flex, so a ship in a two-column strip takes half of
it. Say `col-width: square` and they behave like the others. An image keeps its
aspect ratio *inside* the square box, so a non-square source letterboxes rather
than distorting.

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

## What a row is guaranteed

Two guarantees worth knowing, both of which used to be violated:

**A row is never sized below its own content just to pay for another row.**
Space is shared by min-constrained water-filling — the same shape CSS uses for
flex items with a minimum: share evenly, freeze whatever cannot fit its share at
its floor, re-share the rest. A row whose content fits inside the even share is
completely unaffected.

**A nested section asks for the height its content really needs.** When the
width is known, a sub-section measures its rows *wrapped*, so it requests the
several lines it will actually occupy rather than one unwrapped line.

Both matter because the engine does not clip: a row squeezed below its content
does not truncate, it draws over its neighbour.

If the floors genuinely do not fit, they are all scaled together — nothing is
starved to pay for something else — and `--audit-layout` reports it as
`TEXT_TALL`. That is the section being too small, which is an authoring fix.

## Cost

**With the default (`1fr`), sizing is not free** — this is the important
correction to make. `1fr` is a content mode: an unannotated column is measured
to find its `min-content` floor, and an unannotated row is measured for its
content height. So "using no keywords" no longer means "no measuring"; it means
every column and row takes the measure path.

Measured on a full `calc()` of a text-heavy screen (mock, warm cache):

| screen | `1fr` default | pure FILL (`AUTO_DEFAULT=False`) |
|---|---|---|
| all rows & columns unannotated | ~0.58 ms | ~0.26 ms |
| fixed-height rows, columns `1fr` | ~0.35 ms | ~0.26 ms |

So the default is **1.4–2.2× a full layout calc** on a screen that is mostly
measurable text, and the cost falls as more of the layout is given fixed sizes.
(Before the per-widget result cache described below these were ~1.2 ms and
~0.6 ms — 2–5× — so most of that gap is now closed.)

Two things keep this from mattering in practice:

- **The engine boundary is free.** Text measurements are memoised in pixel
  space, so a repainted screen makes **zero** `sbs.get_text_*` calls. The whole
  cost above is Python arithmetic in the layout pass, not the Pybind boundary.
- **Full `calc()` is rare.** The dirty system re-lays-out only on a page present
  or a genuine layout change; a value cycling through same-width text stays
  visual-only and never re-measures. The millisecond above is paid when a screen
  is (re)built, not every frame.

If a screen is genuinely hot and mostly fixed anyway, `AUTO_DEFAULT = False`
restores pure FILL and the ~0.26 ms column — content keywords still work when
named explicitly.

Each widget's measured size is cached on its full inputs (text, mode, available
width, font, aspect ratio), so a repaint of an unchanged tree resolves every
measurement from a dict lookup rather than re-parsing props and re-measuring. The
cache is self-invalidating — change any input and the key changes — and is
cleared with the pixel memos. This is what closes most of the gap above; a screen
whose text genuinely changes every frame pays the uncached cost.
