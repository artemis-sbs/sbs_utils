from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.gauge import Gauge
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def gui_gauge (value, max=100, label='', style=None, show=None, warn=None, crit=None, color=None, invert=False):
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
        shields.value = 45"""
