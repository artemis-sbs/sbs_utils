from ...helpers import FrameContext
from .listbox import gui_list_box

# Declarative table = a gui_list_box with a generated multi-column row template.
# The helper has ALL rows up front, so it can auto-size columns to the widest cell
# (header + data) — the one thing a per-row item_template can't do on its own.
# The result is still a real listbox: selectable, scrollable.

_ALIGN = {"l": "left", "c": "center", "r": "right",
          "left": "left", "center": "center", "right": "right"}


def _cell(item, key):
    """Read a field from a row (dict, MastDataObject, or plain object)."""
    if key is None:
        return ""
    if isinstance(item, dict):
        return item.get(key, "")
    getter = getattr(item, "get", None)
    if callable(getter):
        try:
            return getter(key, "")
        except Exception:
            pass
    return getattr(item, key, "")


def _resolve_columns(items, columns, font):
    """Normalize the column specs and turn every 'auto' width into a percent,
    sized to the widest measured cell and sharing the width the fixed columns
    leave free."""
    ctx = FrameContext.context
    sbs = ctx.sbs if ctx is not None else None

    def measure(text):
        if sbs is not None:
            return sbs.get_text_line_width(font, str(text))
        return len(str(text)) * 10.0          # headless fallback estimate

    resolved, auto_idx, natural = [], [], []
    for i, col in enumerate(columns):
        just = _ALIGN.get(str(col.get("align", "l")).lower(), "left")
        label = col.get("label", col.get("key", ""))
        width = col.get("width", "auto")
        resolved.append({"key": col.get("key"), "label": label,
                         "just": just, "width": width})
        if width == "auto" or width is None:
            auto_idx.append(i)
            mx = measure(label)
            for item in items:
                w = measure(_cell(item, col.get("key")))
                if w > mx:
                    mx = w
            natural.append(mx)
        else:
            natural.append(None)

    fixed = sum(float(resolved[i]["width"]) for i in range(len(resolved))
                if i not in auto_idx)
    avail = max(0.0, 100.0 - fixed)
    auto_total = sum(natural[i] for i in auto_idx) or 1.0
    for i in auto_idx:
        resolved[i]["width"] = round(avail * (natural[i] / auto_total), 2)
    return resolved


def gui_table(items, columns, style="row-height: 1.6em;", select=False,
              header=True, font="gui-2", **kwargs):
    """Add a declarative table (a selectable/scrollable gui_list_box) to the layout.

    Args:
        items: list of rows — dicts, MastDataObjects, or plain objects.
        columns: list of column specs, each a dict:
            {"key": <field name>,
             "label": <header text>            (default: key),
             "align": "l" | "c" | "r"          (default: "l"),
             "width": <percent number> | "auto" (default: "auto")}
            'auto' columns are sized to the widest cell (header + data) and share
            whatever percent the fixed columns leave.
        style: row style (row-height, padding, ...).
        select: allow row selection (default False).
        header: render the column-label header row (default True).
        font: cell/header font tag (default gui-2).
        **kwargs: forwarded to gui_list_box (multi, carousel, ...).

    Returns:
        The gui_list_box. Read the selected row with get_value()/get_selected().

    Example:
        gui_table(fleet, [
            {"key": "name",   "label": "Ship",    "align": "l"},
            {"key": "hull",   "label": "Hull",    "align": "c", "width": 20},
            {"key": "side",   "label": "Side",    "align": "r", "width": 20},
        ], select=True)
    """
    cols = _resolve_columns(items, columns, font)

    def row_template(item):
        from . import gui_row, gui_text
        gui_row(style)
        for c in cols:
            gui_text(f"$text:`{_cell(item, c['key'])}`;justify:{c['just']};font:{font};",
                     f"col-width:{c['width']};")

    title_template = None
    if header:
        def title_template():
            from . import gui_row, gui_text
            gui_row(style)
            for c in cols:
                gui_text(f"$text:`{c['label']}`;justify:{c['just']};color:#bbb;font:{font};",
                         f"col-width:{c['width']};")

    return gui_list_box(items, style, item_template=row_template,
                        title_template=title_template, select=select, **kwargs)
