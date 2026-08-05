# Paint order — `layer:`

The engine draws widgets in **layer order**, and every widget has a layer
(`draw_layer`, default `1001`). A higher number is drawn later, so it lands on
top. `layer:` sets it from a style string.

```
gui_row("row-height: 6em; background: #2a4a6a; layer: 1500;")
```

This is **opt-in and cheap to ignore**. A layout that never says `layer:` emits
exactly the same thing it always did.

## What it is for

Two jobs, and it is worth knowing which one you are doing.

**1. Deciding what wins when things overlap.** The engine has no clip: text
wider or taller than its box is drawn over its neighbours anyway
([`overflow:`](gui_overflow.md) is the other half of that story). Raising a
widget's layer decides which of the two stays readable.

**2. Hiding a spill behind an opaque fill.** This is the interesting one. A
background raised **above** the content next to it *covers* that content, so an
overflowing string simply disappears behind it. It is not clipping — nothing is
cut — but to a player it looks the same.

```
# a row whose text overruns...
gui_row("row-height: 2em;")
gui_text("$text:`{a very long description}`;")

# ...and the row below hides the overflow instead of wearing it
gui_row("row-height: 8em; background: #2a4a6a; layer: 1500;")
```

Leave the `layer:` off that second row and the overflow is drawn across it,
which is what always happened and still does.

## Why the direction works out

Overflow only ever goes **right and down** — text lays out from its box's
top-left. Document order also runs left-to-right, top-to-bottom. So the widget
that gets damaged is always declared *after* the one that spills, and "later
declaration, higher layer" is exactly the rule you want.

## It cascades

`layer:` on a **section** or a **row** reaches everything inside it, the same
way `color` and `font` do. So one declaration can raise a whole panel:

```
gui_section("area: 50,10,99,90; layer: 1500;")   # every widget in here is raised
```

A widget's own `layer:` beats the one it inherits. And a `draw_layer` written
directly into a widget's props always wins over both — the nearest declaration
is the one that counts.

## The layer map

Pick numbers that do not collide with what the library already uses:

| Layer | Used by |
|---|---|
| `1000` | section / row / column backgrounds and borders (the default) |
| `1001` | the engine default — ordinary content, buttons |
| `20000`+ | [overlay](overlays.md) slots |

So `1002`–`9999` is yours. Above `20000` you are fighting the overlay system.

## What it cannot do

**It needs a colour.** Hiding a spill means painting *something* over it, and
that something has to be what should have been there. Over a solid panel that is
easy. **Over a `3dview` or `2dview` it is impossible** — you would punch an
opaque rectangle into the view to hide a line of text. Panels over live views
have to be fixed by [sizing](gui_content_sizing.md) instead.

**It hides; it does not fix.** The text is still wrong, it is just no longer on
top of anything. `spill` remains the default deliberately: a visible failure gets
fixed, a silent one does not.

**Size the backdrop to the row or section, not to the widget.** The engine draws
button chrome slightly *outside* the rect it was given, so a fill matching a
button's exact box still leaves a visible rim around it.

## Gotchas

**A covered widget still works.** Input is not blocked by whatever is painted on
top — a button under an opaque fill still takes the hover and the click. Handy,
and also a hazard: do not hide a control and assume it is disabled.

**Backgrounds default to `1000`, which is *under* content.** That is why a plain
`background:` cannot hide a neighbour's overflow on its own. Raising it is the
entire point of `layer:`.

**`gui_image` honours it too** — either in the props string
(`gui_image("image:smallWhite;color:#123;draw_layer:1500;")`) or as a style
(`gui_image_stretch("smallWhite", "layer: 1500;")`). An image is usually the
thing doing the covering.
