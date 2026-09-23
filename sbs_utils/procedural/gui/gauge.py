from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.gauge import Gauge


def gui_gauge(value, max=100, label="", style=None, show=None, warn=None,
              crit=None, color=None, invert=False):
    """Add a gauge - label, value and a bar colored by how full it is - to the
    current GUI layout. The engine's status-panel look (Energy 946 over a green bar).

    For a value that changes often, hold the widget and update it; only the gauge
    repaints. (A `[Energy](gauge://946?max=1000)` line in `gui_text_area` draws the
    same thing, but a text area re-sends its whole document on any change.)

    Args:
        value (float): Current value. Out-of-range values clamp the bar, and the
            number shown is still the raw value. Above max the bar is full and
            cyan, the engineering console's TUNED color.
        max (float, optional): Full-scale value. Defaults to 100.
        label (str, optional): Text on the left. Defaults to "" (bar only).
        style (str, optional): Style overrides (e.g. ``font:gui-3;``).
        show (str, optional): ``value``, ``frac`` ("45 / 120"), ``pct`` or ``none``.
            Defaults to ``value`` with a label, ``none`` without.
        warn (float, optional): Fraction below which the bar is yellow. Default 0.5.
        crit (float, optional): Fraction below which the bar is red. Default 0.25.
        color (str, optional): A fixed bar color, ignoring warn/crit.
        invert (bool, optional): MORE is WORSE (wear, heat, damage): green while
            low, yellow then red as it climbs, red past max. Defaults to False.

    Returns:
        Gauge: The layout item. ``g.update(value=45)`` or ``g.value = 45`` repaints it.

    Example:
        shields = gui_gauge(120, 120, "FRNT SHLD")
        shields.value = 45
    """
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    if isinstance(label, str) and task is not None:
        label = task.compile_and_format_string(label)
    layout_item = Gauge(page.get_tag(), value, max, label, show, warn, crit, color, invert)
    apply_control_styles(".gauge", style, layout_item, task)
    page.add_content(layout_item, None)
    return layout_item
