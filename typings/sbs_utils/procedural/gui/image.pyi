from sbs_utils.helpers import FrameContext
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply style information to a layout item based on the type of the layout, and apply the extra styles as needed.
    Args:
        control_name (str): The name of the control style.
        extra_style (str): A CSS-style string containing extra style definitions which override those in the control style.
        layout_item (LayoutItem): The layout item for which the style is to be applied."""
def get_artemis_data_dir ():
    """Get the path to the Artemis Cosmos data directory.
    
    Returns:
        str: The data folder path (executable directory + "/data")."""
def get_artemis_dir ():
    """Get the path to the root Artemis Cosmos installation directory.
    
    Returns:
        str: The parent directory of the data folder."""
def get_artemis_graphics_dir ():
    """Get the path to the Artemis Cosmos graphics directory.
    
    Returns:
        str: The graphics folder path (data directory + "\graphics")."""
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
def get_mission_dir_filename (filename):
    """Get the full path to a file in the current mission directory.
    
    Args:
        filename (str): The relative path from the mission directory.
    
    Returns:
        str: The full path to the file in the mission directory."""
def get_mission_graphics_file (file):
    """Get the relative path to a graphics file from the mission directory.
    
    Args:
        file (str): The relative file path from the graphics directory.
    
    Returns:
        str: The relative path from graphics directory to the file."""
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
def gui_image_size_raw (file):
    ...
def gui_image_stretch (props, style=None):
    """queue a gui image element that stretches to fit
    
    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
    
    Returns:
        layout object: The Layout object created"""
def split_props (s, def_key):
    ...
class ImageAtlas(object):
    """class ImageAtlas"""
    def __init__ (self, key, image, left=None, top=None, right=None, bottom=None, color=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __str__ (self):
        """Return str(self)."""
    def get_props (self, color=None):
        ...
    def get_size (self):
        ...
    def is_valid (self):
        ...
    def send_gui_image (self, SBS, client_id, region_tag, tag, mode, left, top, right, bottom, color=None):
        ...
