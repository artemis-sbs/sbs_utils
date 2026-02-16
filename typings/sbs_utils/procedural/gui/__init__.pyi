from sbs_utils.procedural.gui.gui import ButtonPromise
def gui (buttons=None, timeout=None):
    """present the gui that has been queued up
    
    Args:
        buttons (dict, optional): _description_. Defaults to None.
        timeout (promise, optional): A promise that ends the gui. Typically a timeout. Defaults to None.
    
    Returns:
        Promise: The promise for the gui, promise is done when a button is selected"""
def gui_activate_console (console):
    """set the console name for the client
    
    Args:
        console (str): The console name"""
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
        props (str): Properties. Usually just the text on the button
        style (str, optional): Style. Defaults to None. End each style with a semicolon, e.g. `color:red;`
        data (object): The data to pass to the button's label
        on_press (label, callable, Promise): Handle a button press, label is jumped to, callable is called, Promise has results set
        is_sub_task (bool): Set to True if the button is only responding to the button. Use False only if the whole gui will be changed via `await gui()`. Default is False for backwards-compatibility.
    
    Valid Styles:
        area:
            Format as `top, left, bottom, right`.
            Just numbers indicates percentage of the section or page to cover.
            Can also use `px` (pixels) or `em` (1em = height of text font).
            Can combine different units, e.g. `5+5px, 3em, 100-10em, 50px;` is a valid area.
        color:
            The color of the text
        background-color:
            The background color of the button
        padding:
            A gap inside the element (makes the button smaller, but the background still is there.)
        margin:
            The gap outside the element (makes the button smaller).
        col-width:
            The width of the button
        justify:
            Where the text is placed inside the button. `left`, `center`, or `right`
        font:
            The font to use. Overrides the font in prefernces.json
    
    
    
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
def gui_image_add_atlas (key, image, left=None, top=None, right=None, bottom=None):
    """The image atlas allows a key name to be used to assign to a set of image properties.
    This key can be used instead of image properties in any command that expect image properties.
    
    The image file passed will be used to search for the file. It will first check the mission directory followed by data/graphics folder.
    In the future this could be modified to account for mods, e.g. a common media folders.
    The image atlas takes care of supplying the correct path for the engine to use.
    
    By specifying the rect (left,top, right, bottom) the image key can reference a part of an image.
    
    
    Add a key to reference a full image
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    gui_image_add_atlas("test", "media/LegendaryMissions/operator")
    ```
    
    Add a key to reference a full image
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    gui_image_add_atlas("test2", "media/LegendaryMissions/operator", 645,570, 950,820)
    ```
    
    Once the atlas is added the key can be used anywhere images can be used.
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    gui_image("test")
    ```
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    # Text area also use the image atlas for images
    gui_text_area("![](image://test2?scale=0.5&fill=center)")
    ```
    
    
    
    Args:
        key (str): the key to define in the image atlas
        image (str): The file of the image. This can also be a image property string do not include the extension. Only PNG files are valid.
        left (float, optional): The pixel location of the left. Defaults to None.
        top (float, optional): The pixel location of the top. Defaults to None.
        right (float, optional): The pixel location of the right. Defaults to None.
        bottom (float, optional): The pixel location of the bottom. Defaults to None.
    
    Returns:
        ImageAtlas: The image Atlas object. This is a low level object typically used by the system """
def gui_image_get_atlas (text):
    ...
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
def gui_image_size (file):
    ...
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
def gui_info_panel_send_message (client_id, message=None, message_color=None, path=None, title=None, title_color=None, banner=None, banner_color=None, face=None, icon_index=None, icon_color=None, button=None, history=True, time=-1):
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
    """Build a LayoutListBox gui element
    
    Args:
        items: A list of the items that should be included
        style (str): Custom style attributes
        item_template (list(str|LayoutListBoxHeader)): A list of strings, or, if a header is desired, then that item should be a LayoutListBoxHeader object
        title_template (str|callable): if a callable, will call the function to build the title. If a string, then title_template will be used as the title of the listbox
        section_style (str): Style attributes for each section
        title_section_style (str): Style attributes for the title
        select (boolean): If true, item(s) within the listbox can be selected.
        multi (boolean): If true, multiple items can be selected. Ignored if `select` is None
        carousel (boolean): If true, will use the carousel styling, e.g. the ship type selection menu
        collapsible (boolean): If true, clicking on a header will collapse everything until the next header
        read_only (boolean): Can the items be modified
    Returns:
        The LayoutListBox layout object"""
def gui_list_box_header (label, collapse=False, indent=0, selectable=False, data=None, visual_indent=None):
    """Created a gui_list_box_header element
    
    Args:
        label (str): The label text
        collapse (bool, optional): Default the collapsed state. Defaults to False.
        indent (int): The indention level e.g. for a tree like structure
        selectable (bool): If the header is also selectable
        collapse_pixel_size (int): The size in pixels for the hit area (only used if selectable)
        select_first (bool): If the select area is before the collapse click area (only used if selectable)
        data (any): Optional additional data
    
    Returns:
        LayoutListBoxHeader : _description_"""
def gui_list_box_is_header (item):
    """Created a gui_list_box_header element
    
    Args:
        label (str): The label text
        collapse (bool, optional): Default the collapsed state. Defaults to False.
    
    Returns:
        _type_: _description_"""
def gui_listbox_items_convert_headers (items):
    """Converts a list of strings into a list of objects that allow a listbox to collapse if a header is clicked
    To make a header, prefix the name with `>>`.
    Example usage:
        ```python
        item = [">>Header","Item1","Item2",">>Another Header","Another Item 1","Another Item 2"]
        ret = gm_convert_listbox_items(item)
        gui_list_box(items=ret, style="", select=True, collapsible=True)
        ```
    Args:
        items (list(str)): A list of strings
    Returns:
        (list(str|LayoutListBoxHeader)): A list of LayoutListBoxHeader (for the headers) and strings (for the items)"""
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
def gui_property_list_box (name=None, tag=None, temp=<function _property_lb_item_template_one_line at 0x0000021B76120360>):
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
def gui_tab_activate (tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    This is general called automatically by //gui/tab and //console labels
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_add_top (tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_back (tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    The back tag is set by //gui/tab and //console labels
    This allows overriding
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_clear_top ():
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_enable (tab_name: str):
    """Enable a tab on the console tabs
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_enable_top ():
    ...
def gui_tab_get_active ():
    """returns the active tab
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_get_list ():
    ...
def gui_tab_is_top (tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_remove_top (tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
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
