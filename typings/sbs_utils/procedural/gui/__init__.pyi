from sbs_utils.procedural.gui.gui import ButtonPromise
def gui (*args, **kwargs):
    ...
def gui_activate_console (console):
    """set the console name for the client
    
    Args:
        console (str): The console name"""
def gui_add_console_tab (id_or_obj, console, tab_name, label):
    """adds a tab definition
    
    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
        label (label): Label to run when tab selected"""
def gui_add_console_type (path, display_name, description, label):
    """adds a tab definition
    
    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
        label (label): Label to run when tab selected"""
def gui_blank (count=1, style=None):
    """adds an empty column to the current gui ow
    
    Args:
        style (_type_, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_button (props, style=None, data=None, on_press=None, is_sub_task=False):
    """Add a gui button
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
        data (object): The data to pass to the button's label
        on_press (label, callable, Promise): Handle a button press, label is jumped to, callable is called, Promise has results set
    
    Returns:
        layout object: The Layout object created"""
def gui_change (code, label):
    """Trigger to watch when the specified value changes
    This is the python version of the mast on change construct
    
    Args:
        code (str): Code to evaluate
        label (label): The label to jump to run when the value changes
    
    Returns:
        trigger: A trigger watches something and runs something when the element is clicked"""
def gui_checkbox (msg, style=None, var=None, data=None):
    """Draw a checkbox
    
    Args:
        props (str):
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the value to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_cinematic_auto (client_id):
    """Will automatically track the consoles assigned ship
    
    ??? Note:
        The tracked ship needs to have excitement values
        player ships automatically have that set
    
    Args:
        client_id (id): the console's client ID"""
def gui_cinematic_full_control (client_id, camera_id, camera_offset, tracked_id, tracked_offset):
    ...
def gui_click (name_or_layout_item=None, label=None):
    """Trigger to watch when the specified layout element is clicked
    
    Args:
        layout_item (layout object): The object to watch
    
    Returns:
        trigger: A trigger watches something and runs something when the element is clicked"""
def gui_client_id ():
    ...
def gui_clipboard_copy (s):
    ...
def gui_clipboard_get ():
    ...
def gui_clipboard_put (s):
    ...
def gui_console (console, is_jump=False):
    """Activates a console using the default set of widgets
    
    Args:
        console (str): The console name"""
def gui_console_clients (path, for_ships=None):
    """gets a set of IDs for matching consoles
    
    Args:
        console (str): The console name"""
def gui_content (content, style=None, var=None):
    """Place a python code widget e.g. list box using the layout system
    
    Args:
        content (widget): A gui widget code in python
        style (str, optional): Style. Defaults to None.
        var (str, optional): The variable to set the widget's value to. Defaults to None.
    
    Returns:
        layout object: The layout object"""
def gui_drop_down (props, style=None, var=None, data=None):
    """Draw a gui drop down list
    
    Args:
        props (str):
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_face (face, style=None):
    """queue a gui face element
    
    Args:
        face (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_get_console_type (key):
    """Get the list of consoles defined by @console decorator labels
    
        """
def gui_get_console_type_list ():
    """Get the list of consoles defined by @console decorator labels
    path is added as a value"""
def gui_get_console_types ():
    """Get the list of consoles defined by @console decorator labels
    
        """
def gui_hide (layout_item):
    """If the item is visible it will make it hidden
    
    ??? Note
        For sections it will recalculate the layout.
        For individual item or row, it will hide, but not layout.
        so you may also need to pair this with a gui_represent of a section
    
    Args:
        layout_item (layout_item): """
def gui_hide_choice ():
    ...
def gui_history_back ():
    """Jump back in history
    
        """
def gui_history_clear ():
    """Clears the history for the given page
        """
def gui_history_forward ():
    """Jump forward in history
        """
def gui_history_jump (to_label, back_name=None, back_label=None, back_data=None):
    """Jump to a new gui label, but remember how to return to the current state
    
    Args:
        to_label (label): Where to jump to
        back_name (str): A name to use if displayed
        back_label (label, optional): The label to return to defaults to the label active when called
        back_data (dict, optional): A set of value to set when returning back
    
    ??? Note:
        If there is forward history it will be cleared
    
    Returns:
        results (PollResults): PollResults of the jump"""
def gui_history_redirect (back_name=None, back_label=None, back_data=None):
    ...
def gui_history_store (back_text, back_label=None):
    """store the current
    
    Args:
        label (label): A mast label"""
def gui_hole (count=1, style=None):
    """adds an empty column that is used by the next item
    
    Args:
        count (int): The number of columns to use
        style (_type_, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_icon (props, style=None):
    """queue a gui icon element
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_icon_button (props, style=None):
    """queue a gui icon element
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image (props, style=None, fit=0):
    """queue a gui image element that draw based on the fit argument. Default is stretch
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
        fit (int): The type of fill,
    
    Returns:
        layout object: The Layout object created"""
def gui_image_absolute (props, style=None):
    """queue a gui image element that draw the absolute pixels dimensions
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image_keep_aspect_ratio (props, style=None):
    """queue a gui image element that draw keeping the same aspect ratio, left top justified
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image_keep_aspect_ratio_center (props, style=None):
    """queue a gui image element that keeps the aspect ratio and centers when there is extra
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_image_stretch (props, style=None):
    """queue a gui image element that stretches to fit
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_info_panel (tab=0, tab_location=0, icon_size=0, var=None):
    ...
def gui_info_panel_add (path, icon_index, show, hide=None, tick=None, var=None):
    ...
def gui_info_panel_remove (path, var=None):
    ...
def gui_info_panel_send_message (*args, **kwargs):
    ...
def gui_input (props, style=None, var=None, data=None):
    """Draw a text type in
    
    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_int_slider (msg, style=None, var=None, data=None):
    """Draw an integer slider control
    
    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_layout_widget (widget):
    """Places a specific console widget in the a layout section. Placing it at a specific location
    
    Args:
        widget (str): The gui widget
    
    Returns:
        layout element: The layout element"""
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False):
    ...
def gui_message (layout_item, label=None):
    """Trigger to watch when the specified layout element has a message
    
    Args:
        layout_item (layout object): The object to watch
    
    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached"""
def gui_message_callback (layout_item, cb):
    """Trigger to watch when the specified layout element has a message
    
    Args:
        layout_item (layout object): The object to watch
    
    Returns:
        trigger: A trigger watches something and runs something when the trigger is reached"""
def gui_message_label (layout_item, label):
    ...
def gui_panel_console_message (cid, left, top, width, height):
    ...
def gui_panel_console_message_list (cid, left, top, width, height):
    ...
def gui_panel_console_message_tick (info_panel):
    ...
def gui_panel_upgrade_list (cid, left, top, width, height):
    ...
def gui_panel_widget_hide (cid, left, top, width, height, widget):
    ...
def gui_panel_widget_show (cid, left, top, width, height, widget):
    ...
def gui_percent_from_ems (client_id, ems, font):
    ...
def gui_percent_from_pixels (client_id, pixels):
    ...
def gui_properties_change (var, label):
    """create an on change on the client GUI for a property
    
    Args:
        var (str): The variable to watch
        label (str or label): The label to run"""
def gui_properties_set (p=None, tag=None):
    ...
def gui_property_list_box (name=None, tag=None, temp=<function _property_lb_item_template_one_line at 0x00000281904F44A0>):
    ...
def gui_property_list_box_stacked (name=None, tag=None):
    ...
def gui_radio (msg, style=None, var=None, data=None, vertical=False):
    """Draw a radio button list
    
    Args:
        props (str): List of buttons to use
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
        vertical (bool): Layout vertical if True, default False means horizontal
    
    Returns:
        layout object: The Layout object created"""
def gui_rebuild (region):
    """prepares a section/region to be build a new layout
    
    Args:
        region (layout_item): a layout/Layout item
    
    Returns:
        layout object: The Layout object created"""
def gui_refresh (label):
    """refresh any gui running the specified label
    
    Args:
        label (label): A mast label"""
def gui_region (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_remove_console_type (path, display_name, label):
    """adds a tab definition
    
    Args:
        path (str): Console path
        display_name (str): Display name
        label (label): Label to run when tab selected"""
def gui_represent (layout_item):
    """redraw an item
    
    ??? Note
        For sections it will recalculate the layout and redraw all items
    
    Args:
        layout_item (layout_item): """
def gui_request_client_string (client_id, key, timeout=None):
    ...
def gui_reroute_client (client_id, label, data=None):
    ...
def gui_reroute_clients (label, data=None, exclude=None):
    """reroute client guis to run the specified label
    
    Args:
        label (label): Label to jump to
        exclude (set, optional): set client_id values to exclude. Defaults to None."""
def gui_reroute_server (label, data=None):
    """reroute server gui to run the specified label
    
    Args:
        label (label): Label to jump to"""
def gui_row (style=None):
    """queue a gui row
    
    Args:
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_screen_size (client_id):
    ...
def gui_screenshot (image_path):
    ...
def gui_section (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_set_style_def (name, style):
    ...
def gui_ship (props, style=None):
    """renders a 3d image of the ship
    
    Args:
        props (str): The ship key
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_show (layout_item):
    """gui show. If the item is hidden it will make it visible again
    
    ??? Note
        For sections it will recalculate the layout.
        For individual item or row, it will hide, but not layout.
        so you may also need to pair this with a gui_represent of a section
    
    Args:
        layout_item (layout_item): """
def gui_slider (msg, style=None, var=None, data=None, is_int=False):
    """Draw a slider control
    
    Args:
        props (str): hi, low etc.
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
        is_int (bool): Use only integers values
    
    Returns:
        layout object: The Layout object created"""
def gui_style_def (style):
    ...
def gui_sub_section (style=None):
    """Create a new gui section that uses the area specified in the style
    
    Args:
        style (style, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_tabbed_panel (items=None, style=None, tab=0, tab_location=0, icon_size=0):
    ...
def gui_task_for_client (client_id):
    ...
def gui_text (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def gui_text_area (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def gui_update (tag, props, shared=False, test=None):
    """Update the properties of a current gui element
    
    Args:
        tag (str):
        props (str): The new properties to use
        shared (bool, optional): Update all gui screen if true. Defaults to False.
        test (dict, optional): Check the variable (key) update if any value is different than the test. Defaults to None."""
def gui_update_shared (tag, props, test=None):
    ...
def gui_update_widget_list (add_widgets=None, remove_widgets=None):
    """Set the engine widget list. i.e. controls engine controls
    
    Args:
        console (str): The console type name
        widgets (str): The list of widgets"""
def gui_update_widgets (add_widgets, remove_widgets):
    """Set the engine widget list. i.e. controls engine controls
    
    Args:
        console (str): The console type name
        widgets (str): The list of widgets"""
def gui_vradio (msg, style=None, var=None, data=None):
    """Draw a vertical radio button list
    
    Args:
        props (str): List of buttons to use
        style (style, optional): Style. Defaults to None.
        var (str, optional): Variable name to set the selection to. Defaults to None.
        data (object, optional): data to pass the handler. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def gui_widget_list (console, widgets):
    """Set the engine widget list. i.e. controls engine controls
    
    Args:
        console (str): The console type name
        widgets (str): The list of widgets"""
def gui_widget_list_clear ():
    """clear the widet list on the client
        """
