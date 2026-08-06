"""Callout blocks - `> [!WARNING] Quarantine Notice` - for in-fiction documents.

`help_docs.amd` and `library_docs.amd` are the only two AMD files that have actually
SHIPPED, and both are pure prose. In-fiction documents want in-fiction document
formatting, so this is the body feature real players see soonest.

The syntax is Obsidian's, because a writer who has ever kept notes already knows it::

    > [!WARNING] Quarantine Notice
    > Do not dock. Contact TSN Command on channel 4.
    > Their manifest is sealed.

A block is the `[!KIND]` opening line plus every `>` line beneath it. Kinds are a
registry, ASCII, and an UNKNOWN kind renders as a plain quote and warns - a document
that used a word this build does not know must still be readable.

`amd_callout_render` returns the text with the `>` markers removed plus the
`line_styles` list `gui_text_area` already accepts, so a caller is::

    body, styles = amd_callout_render(record.get("body"))
    gui_text_area(body, line_styles=styles)

The per-line `background` is what draws the block. Whether consecutive per-line
backgrounds abut cleanly enough to read as ONE box is a render question, not a parse
one - see the note on grouping in the plan.
"""
from sbs_utils.procedural.amd import RE_CALLOUT, RE_CALLOUT_BODY

# kind -> {"style", "background", "prepend", "indent"}. Deliberately small and
# ASCII-only: engine-rendered strings carry no Unicode, so a callout is marked by
# color and an indent, never by a glyph the font may not have.
_CALLOUT_KINDS = {
    "note":    {"style": "font:gui-2;color:#9cf;", "background": "#1a2633", "prepend": ""},
    "tip":     {"style": "font:gui-2;color:#9f9;", "background": "#16281a", "prepend": ""},
    "warning": {"style": "font:gui-2;color:#fc6;", "background": "#332616", "prepend": ""},
    "danger":  {"style": "font:gui-2;color:#f88;", "background": "#331a1a", "prepend": ""},
    "quote":   {"style": "font:gui-2;color:#bbb;", "background": None, "prepend": ""},
}
_TITLE_EXTRA = "font:gui-3;"


def amd_register_callouts(domain, table):
    """Register callout kinds: `{name: {"style", "background", "prepend", "indent"}}`.

    Mirrors `amd_register_fields` - a clash with a differently-defined existing kind
    is a startup failure rather than silent drift."""
    for name, spec in (table or {}).items():
        key = str(name).strip().lower()
        if key in _CALLOUT_KINDS and _CALLOUT_KINDS[key] != spec:
            raise ValueError(f"{domain}: callout kind `{name}` is already registered")
        _CALLOUT_KINDS[key] = dict(spec)


def amd_callout_kinds():
    """Every registered kind name, for completion and lint."""
    return sorted(_CALLOUT_KINDS)


def amd_callout_blocks(text):
    """Parse `text` into callout blocks: `[{kind, title, lines, start, end, known}]`.

    `start`/`end` are 0-based line indexes into `text`, end-exclusive. Pure - no
    engine calls - so the whole thing is unit-testable."""
    lines = (text or "").splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        m = RE_CALLOUT.match(lines[i])
        if m is None:
            i += 1
            continue
        kind = m.group("kind").strip().lower()
        title = (m.group("title") or "").strip()
        body = []
        j = i + 1
        while j < len(lines):
            # A `>` line CONTINUES the block - unless it opens a new one.
            if RE_CALLOUT.match(lines[j]):
                break
            cont = RE_CALLOUT_BODY.match(lines[j])
            if cont is None:
                break
            body.append(cont.group("text"))
            j += 1
        blocks.append({"kind": kind, "title": title, "lines": body,
                       "start": i, "end": j, "known": kind in _CALLOUT_KINDS})
        i = j
    return blocks


def amd_callout_render(text):
    """`text` -> `(clean_text, line_styles)` ready for `gui_text_area`.

    The `>` markers come off (they are markup, not words) and each line of a block
    gets that kind's style, with the title line a size larger. Lines outside any
    block get `None`, which `line_style_for` already treats as "style it normally",
    so a document with no callouts renders exactly as it does today and passing the
    styles through is always safe."""
    lines = (text or "").splitlines()
    if not lines:
        return (text or ""), None
    blocks = amd_callout_blocks(text)
    if not blocks:
        return text, None

    out = list(lines)
    styles = [None] * len(lines)
    for block in blocks:
        spec = _CALLOUT_KINDS.get(block["kind"]) or _CALLOUT_KINDS["quote"]
        base = {"style": spec.get("style", ""), "indent": spec.get("indent", 2),
                "background": spec.get("background"), "prepend": spec.get("prepend", "")}
        title = block["title"] or block["kind"].title()
        out[block["start"]] = title
        head = dict(base)
        head["style"] = _TITLE_EXTRA + base["style"]
        styles[block["start"]] = head
        for offset, body_line in enumerate(block["lines"], start=1):
            out[block["start"] + offset] = body_line
            styles[block["start"] + offset] = dict(base)
    return "\n".join(out), styles
