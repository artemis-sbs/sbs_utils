def amd_callout_blocks (text):
    """Parse `text` into callout blocks: `[{kind, title, lines, start, end, known}]`.
    
    `start`/`end` are 0-based line indexes into `text`, end-exclusive. Pure - no
    engine calls - so the whole thing is unit-testable."""
def amd_callout_kinds ():
    """Every registered kind name, for completion and lint."""
def amd_callout_render (text):
    """`text` -> `(clean_text, line_styles)` ready for `gui_text_area`.
    
    The `>` markers come off (they are markup, not words) and each line of a block
    gets that kind's style, with the title line a size larger. Lines outside any
    block get `None`, which `line_style_for` already treats as "style it normally",
    so a document with no callouts renders exactly as it does today and passing the
    styles through is always safe."""
def amd_callout_style_table ():
    """`{style_key: style_dict}` for a text widget's named-style table.
    
    ONE source of truth for what a callout looks like: the widget reads this rather
    than carrying its own copy of the colors, so the two cannot drift the way the
    parallel schema copy did before the field registry existed."""
def amd_register_callouts (domain, table):
    """Register callout kinds: `{name: {"style", "background", "prepend", "indent"}}`.
    
    Mirrors `amd_register_fields` - a clash with a differently-defined existing kind
    is a startup failure rather than silent drift."""
