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
def engine_file (path):
    """A path in the shape the ENGINE resolves: relative to the Cosmos root.
    
    THE ONE PATH HELPER. Every asset class used to compute its own shape against its own
    base - audio against `data/audio`, images against `data/graphics`, a skybox as an
    absolute path for a mission asset but a bare name for a stock one, ship data already
    root-relative. Five spellings of the same idea, and only a run of the game could say
    which of them a given engine would open.
    
    The 2026-08-15 engine resolves ONE shape for all of them, measured against it
    (`data/missions/mediapath_probe`): a path from the Cosmos root, or an absolute path.
    Both open. What does NOT open is a bare name, or a path relative to the asset's own
    old base - `../missions/<m>/<file>` against `data/audio` is what this library built
    for audio until now, and on this engine it silently plays nothing.
    
    NOTE ON EXTENSIONS, because it is the opposite of what the shape suggests: the engine
    appends the extension itself, and passing one can make the lookup FAIL. A `.wav` on an
    audio path was measured not to open while the same path without it did. So callers
    name assets the way they always have - without a suffix - and this does not add one.
    
    An absolute path outside the install is passed through unchanged: it is still a path
    the engine accepts, and rewriting it to `../../..` would only make it fragile."""
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
def gui_image (props, style=None, fit=0, color=None):
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
        color (str, optional): Tint for this use only, overriding the atlas's own
            color. Lets one registered cell serve every state.
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
def gui_image_add_atlas (key, image, left=None, top=None, right=None, bottom=None, color=None, domain=None):
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
        color (str, optional): default tint for this key. A drawing call may override it.
        domain (str, optional): a namespace for the key. `ImageAtlas.all` is one
            process-wide dict, so two addons registering `card_back` collide silently and
            the last one loaded wins. A domain scopes the claim - and something that
            RESOLVES through a domain (icons do) will only honor a deliberate registration.
    
    Returns:
        ImageAtlas: The image Atlas object. This is a low level object typically used by the system """
def gui_image_add_atlas_grid (image, cols, rows=None, names=None, cell=None, color=None, domain=None, start=0):
    """Register a whole sheet of evenly spaced cells in one call.
    
    Cutting a sheet up by hand is the same four lines of arithmetic every time, and
    getting one of them wrong shows up as art that is off by a cell rather than as an
    error (`casino_media.py` hand-loops exactly this).
    
        gui_image_add_atlas_grid("media/icons/quest-sheet", 8, 8,
                                 ["job", "beat", "arc"], cell=64, domain="icon")
    
    Args:
        image (str): the sheet, without the extension.
        cols (int): cells across.
        rows (int, optional): cells down. Needed only to measure a cell from the file.
        names (list | dict, optional): a list is laid out ROW-MAJOR from `start`, and a
            `None` entry skips that cell; a dict is `{name: (col, row)}` for a sparse
            sheet. Omit to register nothing and just get the cell size back.
        cell (int | tuple, optional): cell size in PIXELS. Measured from the file
            (`width / cols`) when omitted, which requires the file to be readable.
        color (str, optional): default tint for every cell.
        domain (str, optional): namespace for the keys - see ``gui_image_add_atlas``.
        start (int, optional): index of the first name in row-major order.
    
    Returns:
        dict: {name: ImageAtlas} for everything registered."""
def gui_image_get_atlas (text, domain=None):
    """The atlas registered under a key, or one built from the text as a file name.
    
    Args:
        text (str): a registered key, or an image path / property string.
        domain (str, optional): look only in this domain (see ``gui_image_add_atlas``)."""
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
    def __init__ (self, key, image, left=None, top=None, right=None, bottom=None, color=None, domain=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __str__ (self):
        """Return str(self)."""
    def get_props (self, color=None, layer=None):
        ...
    def get_size (self):
        ...
    def is_valid (self):
        ...
    def qualify (key, domain=None):
        """The key a registration is stored under. `ImageAtlas.all` is one process-wide
        dict, so without a domain two addons can claim the same word and the last one
        loaded silently wins. A domain makes the claim explicit and scoped."""
    def send_gui_image (self, SBS, client_id, region_tag, tag, mode, left, top, right, bottom, color=None, layer=None):
        ...
