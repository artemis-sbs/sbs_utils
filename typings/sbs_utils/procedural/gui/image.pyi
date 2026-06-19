from sbs_utils.helpers import FrameContext
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
    """Add an image to the current GUI layout.
    
    Resolves the image via the atlas, mission directory, and engine graphics
    path in that order. Prefer the named wrappers (``gui_image_stretch``,
    ``gui_image_absolute``, etc.) over calling this directly.
    
    Args:
        props (str): Image filename (without extension), a registered atlas
            key (see ``gui_image_add_atlas``), or an image property string
            like ``"image:media/logo;color:white;"``. Supports ``{var}``
            interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
        fit (int, optional): Scaling mode — 0=stretch, 1=absolute pixels,
            2=keep aspect ratio (top-left), 3=keep aspect ratio (centered).
            Defaults to 0.
    
    Returns:
        Image: The layout item created."""
def gui_image_absolute (props, style=None):
    """Add an image to the layout at its native pixel dimensions.
    
    The image is drawn at 1:1 pixel size relative to the client's screen
    resolution, anchored at the top-left of the layout area.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_absolute("media/icons/torpedo")"""
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
    """Add an image scaled to fit the area while preserving aspect ratio.
    
    Scales the image as large as possible without cropping, anchored
    top-left. Leaves empty space if the area's aspect ratio differs from
    the image's.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_keep_aspect_ratio("media/ship/artemis")"""
def gui_image_keep_aspect_ratio_center (props, style=None):
    """Add an image scaled to fit the area while preserving aspect ratio, centered.
    
    Like ``gui_image_keep_aspect_ratio`` but centers the image in the
    remaining space when the aspect ratios differ.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_keep_aspect_ratio_center("media/crew/captain")"""
def gui_image_size (file):
    """Return the pixel dimensions of an image file or atlas entry.
    
    Checks the atlas first, then reads the PNG header directly. Results are
    cached so repeated calls are free after the first read.
    
    Args:
        file (str): Atlas key or image path (without ``.png`` extension).
    
    Returns:
        tuple[int, int]: ``(width, height)`` in pixels, or ``(-1, -1)`` if
            the file cannot be read.
    
    Example:
        w, h = gui_image_size("media/backgrounds/nebula")"""
def gui_image_size_raw (file):
    ...
def gui_image_stretch (props, style=None):
    """Add an image to the layout, stretched to fill its area.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string e.g. ``"image:media/logo;color:white;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_stretch("media/backgrounds/nebula")"""
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
