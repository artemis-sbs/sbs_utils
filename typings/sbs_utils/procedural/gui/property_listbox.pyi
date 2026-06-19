from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from sbs_utils.helpers import FrameContextOverride
from sbs_utils.pages.widgets.layout_listbox import LayoutListBoxHeader
def _get_property_list (values):
    """flatten a tree to a list
        """
def _gui_properties_items (values=None):
    ...
def _property_lb_item_template_one_line (item):
    ...
def _property_lb_item_template_two_line (item):
    ...
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def gui_hole (count=1, style=None):
    """Reserve empty column space that the next layout item expands to fill.
    
    Unlike ``gui_blank``, a hole is consumed by the following item as extra
    width. Use it to make a single element span multiple column slots.
    
    Args:
        count (int, optional): Number of extra column slots to reserve.
            Defaults to 1.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Hole: The last hole layout item created.
    
    Example:
        gui_hole(2)
        gui_text("This text spans 3 columns")"""
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False):
    """Add a listbox to the current GUI layout.
    
    Args:
        items (list): Items to display. Plain strings render as text rows;
            ``LayoutListBoxHeader`` objects (from ``gui_list_box_header``)
            render as collapsible section dividers.
        style (str): CSS-like style overrides for the listbox container.
        item_template (callable | None, optional): Called per item to build
            its row layout. Defaults to None (built-in text row).
        title_template (str | callable | None, optional): Title for the
            listbox. A string is used as-is; a callable is invoked to build
            the title row. Defaults to None.
        section_style (str | None, optional): Style overrides applied to each
            item row section. Defaults to None.
        title_section_style (str | None, optional): Style overrides applied to
            the title section. Defaults to None.
        select (bool, optional): Allow item selection. Defaults to ``False``.
        multi (bool, optional): Allow multiple simultaneous selections. Only
            used when ``select=True``. Defaults to ``False``.
        carousel (bool, optional): Use carousel styling (e.g. ship-type
            selection). Defaults to ``False``.
        collapsible (bool, optional): Clicking a header collapses items until
            the next header. Defaults to ``False``.
        read_only (bool, optional): Prevent item modification. Defaults to
            ``False``.
    
    Returns:
        LayoutListbox: The layout object created.
    
    Example:
        gui_list_box(items, style="area:0,0,100,100;", select=True)"""
def gui_properties_set (p=None, tag=None):
    """Update the data displayed in a property list box.
    
    Parses ``p`` (a dict or YAML string) into a flat list of label/control
    pairs and refreshes the list box stored under ``tag`` in the GUI task.
    Call this whenever the underlying data changes to redraw the panel.
    
    Args:
        p (dict | str, optional): Property data as a Python dict or a YAML
            string. Dict keys become labels; values are Python expressions
            evaluated to produce the control widget. Nested dicts become
            collapsible sections. Defaults to None (clears the list).
        tag (str, optional): Task inventory key holding the list box widget.
            Defaults to ``"__PROPS_LB__"``.
    
    Example:
        gui_properties_set({"Speed": "gui_text(str(ship_speed))", "Shields": "gui_slider(shield_pct)"})"""
def gui_property_list_box (name=None, tag=None, temp=<function _property_lb_item_template_one_line at 0x00000215CB1C9BC0>):
    """Create a property list box with single-line label/control layout.
    
    Each property is rendered as a label on the left and its control widget
    on the right of the same row. Suitable for compact property panels.
    The widget is stored in the GUI task under ``tag`` so ``gui_properties_set``
    can refresh it later.
    
    Args:
        name (str, optional): Title shown in the list box header.
            Defaults to ``"Properties"``.
        tag (str, optional): Task inventory key used to store and retrieve
            the list box widget. Defaults to ``"__PROPS_LB__"``.
        temp (callable, optional): Item template function used to render each
            row. Defaults to the built-in one-line template.
    
    Returns:
        LayoutListBox: The list box widget.
    
    Example:
        gui_property_list_box("Navigation")
        gui_properties_set({"Heading": "gui_text(str(heading))", "Speed": "gui_text(str(speed))"})"""
def gui_property_list_box_stacked (name=None, tag=None):
    """Create a property list box with two-line stacked label/control layout.
    
    Each property is rendered as a label on one line and its control widget
    on the line below. Useful when controls are wide and need their own row.
    The widget is stored in the GUI task under ``tag`` so ``gui_properties_set``
    can refresh it later.
    
    Args:
        name (str, optional): Title shown in the list box header.
            Defaults to ``"Properties"``.
        tag (str, optional): Task inventory key used to store and retrieve
            the list box widget. Defaults to ``"__PROPS_LB__"``.
    
    Returns:
        LayoutListBox: The list box widget.
    
    Example:
        gui_property_list_box_stacked("Ship Systems")
        gui_properties_set({"Warp Core": "gui_slider(warp_pct)"})"""
def gui_represent (layout_item):
    """Redraw a layout item on the client screen.
    
    For sections and regions, recalculates the entire sub-layout and redraws
    all children. For individual items or rows, redraws that element only.
    
    Args:
        layout_item: The layout object to redraw.
    
    Example:
        gui_represent(my_section)"""
def gui_reset_variables (task):
    ...
def gui_reset_variables_add (task, var_name):
    ...
def gui_row (style=None):
    """Start a new layout row, pushing subsequent items to the next line.
    
    Call before adding items that should appear on a fresh row. Without
    explicit rows, items flow left-to-right across the current row.
    
    Args:
        style (str, optional): CSS-like style overrides for the row container.
            Defaults to None.
    
    Returns:
        Row: The row layout object.
    
    Example:
        gui_text("Name:")
        gui_row()
        gui_input("", var="ship_name")"""
def gui_text (props, style=None):
    """Add a text label to the current GUI layout.
    
    Args:
        props (str): Text content or property string, e.g. ``"Hello"`` or
            ``"$text:Hello;color:white;"``. Supports ``{var}`` interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Text: The layout item created.
    
    Example:
        gui_text("Hull: {hull_pct}%")
        gui_text("$text:WARNING;color:red;")"""
def is_dev_build ():
    """Check if the current mission is a development build.
    
    Returns True if a .git directory exists in the mission folder.
    
    Returns:
        bool: True if running in development mode, False otherwise."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
class PropertyControlItem(object):
    """class PropertyControlItem"""
    def __init__ (self, label, control):
        """Initialize self.  See help(type(self)) for accurate signature."""
