# Rendering source text in a `gui_text_area`

A spec, not a change. Nothing here is implemented except an inert `literal` flag
sitting uncommitted in `pages/layout/text_area.py`.

## Why

The Control Gallery shows each specimen's own source. It currently renders that
as a **`gui_list_box` of one `gui_text` per line**, which was the wrong reach: it
reimplements — badly — what a text area already does well (measured word
wrapping, a scrollbar, its own overflow handling), and it inherited a bug the
text area does not have (a fixed one-line row that a wrapping line overdraws,
worked around with `overflow:ellipsis`, which truncates 42% of the corpus).

A code/log viewer is not gallery-specific. A mission log, a MAST error dump, an
AMD preview and the GUI editor all want the same thing.

## What a text area does to source today

Every one verified in `pages/layout/text_area.py`, not recalled.

| # | Transformation | Where | Hits |
|---|---|---|---|
| 1 | whole block `.strip()` | `value` setter | first/last line indent |
| 2 | **`^` → newline** | `value` setter, and the ENGINE | any `^`; 279 in LM `.mast` (mostly `@console ^5`) |
| 3 | `#` → heading, marker stripped | `get_markdown_line_style` | **every MAST comment** |
| 4 | `-` → bullet, first token consumed | same | `->END`, `--`, negatives |
| 5 | leading digit → ordered list | same | any line starting with a number |
| 6 | no marker → **inherits previous line's style** | same | one `#` restyles everything after it |
| 7 | `prepend` inserted for list styles | render loop | bullets/numbers injected into text |
| 8 | `=$name ...` consumed, line dropped | `rule_style_def` | rare in code |
| 9 | `[name]: ns://urn` consumed, dropped | `rule_link_def` | `foo[k]: v` |
| 10 | **any `[...]` → link ref, line replaced by remainder** | `rule_link_ref` | `item['key']`, `lines[0]`, list literals |
| 11 | `image://`/`ship://`/`face://`/`style://` become objects | render loop | any such literal in code |
| 12 | 2+ leading `\|` lines → GFM table | render loop | rare |
| 13 | `<br>` / `<br/>` → line break | render loop | rare |
| 14 | `{...}` f-string interpolated | `gui_text_area` wrapper | f-strings, dict literals |
| 15 | **`text.split()` collapses ALL whitespace** | `measure.wrap_to_width` | leading spaces (see B -- not the mechanism we need anyway) |

Failure mode is not graceful: any parse error replaces the whole area with
`Document syntax issue line number N`.

## The two features

### A. `literal=True` — markup off

Disables 3–13 and skips 14. Lines render in the widget's own style. Keeps
wrapping, scrolling and measurement, which is the entire reason to use a text
area.

Not sufficient alone: without B every line renders flush left in one colour, and
MAST indentation is semantic.

### B. A style PER LINE, supplied by the caller

Indent is already a style field, and the render loop already accepts a style
**dict** per line rather than a style name — that is the path `$$font:...;` takes:

```python
elif isinstance(style_key, dict):
    style = style_key
```

So B is not a parsing feature and the widget needs no whitespace rule: expose
that per-line style dict to the caller. The caller then supplies, per line, a
style carrying colour AND indent — it is the one that knows a `#` line is a
comment and knows its depth. The widget stays a renderer.

This also answers Q3 (per-line colour) with the same mechanism, and dissolves Q4
entirely: nothing derives meaning from leading whitespace, so there is no
"universal or literal-only" decision and no style-vs-source precedence rule.

Wrapped continuations inherit the line's style, so they align at its indent for
free.

Indent units are "X" at **gui-2**, hardcoded, regardless of the line's font.
Fine for a code look; worth knowing before someone renders code at gui-4.

### C. Subtract the indent from the wrap width

`pixel_width` (line 447) is the box width less the scrollbar and does **not**
subtract the indent, while the send rect is then shifted right by it. An
indented line therefore wraps as though it had the full width and spills past
the right edge — and the engine does not clip.

Today that is 2 character widths on `ul`/`ol`, small enough to have gone
unnoticed. At code indents of 12–16 it is lines running off the panel. Fix at the
`wrap_to_width` call site (line 638).

**A and B are both required.** A stops the parser eating content; B is how the
result gets indentation and colour. Either alone looks fixed and is not. C is a
bug fix that only becomes visible at code-sized indents.

## What we accept

- **Wrapping is fine.** The engine does not clip, so a line wider than the box is
  drawn over its neighbour regardless — wrapping is the only correct answer, not
  a compromise. (This is also why `wrap_to_width` exists and guarantees every
  returned line fits.)
- **`^` cannot be recovered.** It is an engine newline. Code containing `^` will
  break there whatever we do. In the gallery that is 2 lines out of 463, both
  inside the specimen that documents `^` — but it is 279 lines across
  LegendaryMissions, so a general viewer must expect it.

## Open questions

**Q1 — ANSWERED.** The engine does **not** preserve leading whitespace, and we do
not need it to: the text area's own `indent` mechanism offsets the rect instead.
The listbox's use of left `padding` was the right instinct for the wrong reason.

**Q2 — ANSWERED** by the mechanism: wrapped sub-lines carry the line's style, so
they align flush at the original indent. A hanging continuation indent would be
an extra feature, not the default.

**Q3 — ANSWERED: per line, as a specifier from the caller.** Folded into B above.

**Q4 — DISSOLVED.** It asked whether whitespace-derived indentation should be
universal or literal-only. With B supplying the style per line, nothing derives
indentation from whitespace at all, so the question does not arise — and neither
does the style-vs-source precedence rule that made "universal" risky.

**Q5 — tabs.** The CALLER expands them when it measures depth; the widget never
sees them. Only matters for sources that use them; the gallery's do not.

## Verification

`wrap_to_width` itself is untouched; C is one arithmetic fix at its call site.
Tests: a caller-supplied style applied per line, continuations inheriting it, and
an indented line no longer spilling past the right edge (C, which also covers
`ul`/`ol` today). The gallery is the
end-to-end case: 463 marked source lines, 42% over 55 characters, longest 308.
