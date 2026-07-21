# Text that does not fit — `overflow:`

**The engine does not clip.** Text wider than its box is drawn *over* whatever
sits beside it; text taller than its box is drawn *over* the row below. Nothing
is cut off, and nothing warns you.

That is fine most of the time — [sizing to content](gui_content_sizing.md) gives
a row or column the space its text needs. But sometimes there is no space to
give: a name is user-entered, a description is longer than the panel, a label has
to sit in a fixed strip. `overflow:` says what to do then.

```
gui_text("$text:`{ship_name}`;", "overflow: shrink;")
```

## The four policies

| policy | what it does |
|---|---|
| `spill` *(default; `visible` is an alias)* | draw it anyway — today's behaviour, and the historical one |
| `shrink` | step the font down until it fits |
| `ellipsis` | truncate and append `...` |
| `hide` | do not draw it at all |

`spill` is the default so that **no existing layout changes**. You opt in per
widget; there is no cascade.

Supported on every text-bearing widget: `gui_text`, `gui_button`, `gui_checkbox`,
`gui_input` (typein) and radio buttons.

## Choosing one

**`shrink`** keeps all the information and is usually right for a name or a
value. It walks down the font ladder (`gui-6` → … → `smallest`) and stops at the
first size that fits, so a slightly-too-long string barely changes and a wildly
too-long one becomes small but readable.

**`ellipsis`** is right when the *start* of the string identifies it and the tail
is detail — a file path, a long mission title in a list. The reader can tell
something was cut; with `shrink` they cannot.

**`hide`** is for decoration that is not worth overlapping other text. Use it
sparingly: silently dropping content is rarely what a player wants.

## A note on CSS names

`visible` is accepted as an alias of `spill`, since that is what CSS calls it.

`hidden` is deliberately **not** an alias of `hide`. In CSS, `overflow: hidden`
means *draw it and clip it*; ours means *do not draw it at all*, which is closer
to `display: none`. Borrowing the CSS word would be more misleading, not less —
precisely because this engine cannot clip.

## Gotchas

**It runs at present time, on the final rect.** The policy cannot be applied
until the layout is done, because until then the box is not known. That is also
why it costs nothing when unused — a widget with no policy never measures.

**A typein reacts as the player types.** `overflow: shrink` on `gui_input` means
the font steps down as the text grows past the box. That is correct, but it is a
live effect none of the other widgets have, so look at it before shipping it.
`ellipsis` on a field someone is still editing is almost never right.

**It is a last resort, not a layout tool.** If a row is *systematically* too
small, size it properly — `row-height: content`, or a bigger area. Reach for
`overflow:` when the content is genuinely unbounded and the space genuinely is
not.

**Interaction with content sizing.** A column that is `content`-sized has already
been given the width its text asked for, so a policy there only fires when the
layout could not honour that request (an oversubscribed row). The two work
together: size to content first, and let `overflow:` handle the leftovers.
