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


def _set(item, key, value):
    """Write a field back to a row (dict, MastDataObject, or plain object)."""
    if isinstance(item, dict):
        item[key] = value
        return
    try:
        setattr(item, key, value)      # MastDataObject stores as attrs, not items
    except Exception:
        pass


def _widget_value(sender):
    """Read the current value from a control widget (get_value() or .value)."""
    getter = getattr(sender, "get_value", None)
    if callable(getter):
        try:
            return getter()
        except Exception:
            pass
    return getattr(sender, "value", None)


def _disp(value):
    """Display text for a $text:`...` cell. Empty renders as a space so the
    backtick-quoted value is never empty (`$text:``;` shows a stray backtick)."""
    s = str(value)
    return s if s != "" else " "


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
                         "just": just, "width": width,
                         "type": str(col.get("type", "text")),
                         "options": col.get("options", []),
                         "button_label": col.get("button_label", label)})
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
              header=True, font="gui-2", on_cell_change=None, **kwargs):
    """Add a declarative table (a selectable/scrollable gui_list_box) to the layout.

    Args:
        items: list of rows — dicts, MastDataObjects, or plain objects.
        columns: list of column specs, each a dict:
            {"key": <field name>,
             "label": <header text>            (default: key),
             "align": "l" | "c" | "r"          (default: "l"),
             "width": <percent number> | "auto" (default: "auto"),
             "type": "text" | "checkbox" | "dropdown" | "input" | "button"
                                               (default: "text", read-only),
             "options": [...]                  (dropdown choices),
             "button_label": <text>}           (button cell label; default: label)
            Interactive cells write their new value back to the row and fire
            on_cell_change. 'auto' columns are sized to the widest cell (header +
            data) and share whatever percent the fixed columns leave.
        style: row style (row-height, padding, ...).
        select: allow row selection (default False).
        header: render the column-label header row (default True).
        font: cell/header font tag (default gui-2).
        on_cell_change: fn(item, key, value) called when a cell control changes
            (value is None for a button press). The row is already updated.
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

    def _bind(widget, item, key):
        # write the control's new value back to the row + notify on_cell_change.
        # default-args capture item/key per call (dodges the for-loop closure trap).
        from . import gui_message_callback

        def handler(event, sender, _i=item, _k=key):
            v = _widget_value(sender)
            _set(_i, _k, v)
            if on_cell_change is not None:
                on_cell_change(_i, _k, v)
        gui_message_callback(widget, handler)

    def row_template(item):
        from . import (gui_row, gui_text, gui_checkbox, gui_drop_down,
                       gui_input, gui_button, gui_message_callback)
        gui_row(style)
        for c in cols:
            w = f"col-width:{c['width']};"
            key = c["key"]
            val = _cell(item, key)
            t = c["type"]
            if t == "checkbox":
                _bind(gui_checkbox(f"state:{bool(val)};", w), item, key)
            elif t == "dropdown":
                opts = ",".join(str(o) for o in c["options"])
                _bind(gui_drop_down(f"text:{val};list:{opts};", w), item, key)
            elif t == "input":
                _bind(gui_input(f"text:{val};", w), item, key)
            elif t == "button":
                btn = gui_button(str(c['button_label']), w)

                def press(event, sender, _i=item, _k=key):
                    if on_cell_change is not None:
                        on_cell_change(_i, _k, None)
                gui_message_callback(btn, press)
            else:  # "text" — read-only display
                gui_text(f"$text:`{_disp(val)}`;justify:{c['just']};font:{font};", w)

    title_template = None
    if header:
        def title_template():
            from . import gui_row, gui_text
            gui_row(style)
            for c in cols:
                gui_text(f"$text:`{_disp(c['label'])}`;justify:{c['just']};color:#bbb;font:{font};",
                         f"col-width:{c['width']};")

    return gui_list_box(items, style, item_template=row_template,
                        title_template=title_template, select=select, **kwargs)
