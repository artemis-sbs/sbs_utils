from ...helpers import FrameContext
from ..style import apply_control_styles
from ...fs import get_mission_dir_filename, get_artemis_data_dir, get_mission_graphics_file, get_artemis_dir, get_artemis_graphics_dir
import os
import struct # for images sizes
from ...gui import get_client_aspect_ratio

def gui_image_stretch(props, style=None):
    """Add an image to the layout, stretched to fill its area.

    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string e.g. ``"image:media/logo;color:white;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.

    Returns:
        Image: The layout item created.

    Example:
        gui_image_stretch("media/backgrounds/nebula")
    """
    return gui_image(props, style=style, fit=0)

def gui_image_absolute(props, style=None):
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
        gui_image_absolute("media/icons/torpedo")
    """
    return gui_image(props, style=style, fit=1)

def gui_image_keep_aspect_ratio(props, style=None):
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
        gui_image_keep_aspect_ratio("media/ship/artemis")
    """
    return gui_image(props, style=style, fit=2)

def gui_image_keep_aspect_ratio_center(props, style=None):
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
        gui_image_keep_aspect_ratio_center("media/crew/captain")
    """
    return gui_image(props, style=style, fit=3)


def gui_image(props, style=None, fit=0):
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
        Image: The layout item created.
    """
    from ...pages.layout.image import Image
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    # Pass through
    #props = gui_image_get_props(props)
        
    tag = page.get_tag()
    layout_item = Image(tag,props, fit)
    apply_control_styles(".image", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_image_get_atlas(text):
    test = ImageAtlas.all.get(text)
    if test is None:
        return ImageAtlas(text, text)
    return test


IMAGE_FIT = 0
IMAGE_ABSOLUTE = 1
IMAGE_KEEP_ASPECT = 2
IMAGE_KEEP_ASPECT_CENTER = 3

from ...helpers import split_props
class ImageAtlas:
    all = {}
    def __init__(self, key, image, left=None, top=None, right=None, bottom=None, color=None):
        file = get_mission_dir_filename(image)

        color = color
        if ";" in image:
            props = split_props(file, "image")
            image = props.get("image")
            color = props.get("color", "white")
            file = get_mission_dir_filename(image)

    

        file_name =  file + ".png"
        
        if not os.path.exists(file_name):
            file = get_artemis_data_dir()+"\\graphics\\"+image
            file_name =  file + ".png"
            if not os.path.exists(file_name):
                file = get_mission_graphics_file(image)
                file_name =  file + ".png"
                if not os.path.exists(file_name):
                    file = os.path.join(get_artemis_dir(), image)
                    #file_name =  file + ".png"
        if file is None:
            return
        
        # Get relative path so it works on clients as well
    
        
        start = get_artemis_graphics_dir()
        file = os.path.relpath(file, start)
        

        self.file = file
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.color = color 
        if key is not None:
            ImageAtlas.all[key] = self

    def __str__(self):
        return self.get_props()

    def get_props(self, color=None):
        # File should already be relative
        # Needs to be done so clients aren't using server file paths
        rel_file = self.file.replace("\\", "/")  # forward slashes for URL
        color = color if color else self.color
        color = color if color else "white"
        if self.left is not None:
            return f"image:{rel_file};sub_rect:{self.left},{self.top},{self.right},{self.bottom};color:{color};"
        else:
            return f"image:{rel_file};color:{color}"

    def is_valid(self):
        file_name = os.path.normpath(os.path.join(get_artemis_graphics_dir(), self.file)) + ".png"
        return os.path.exists(file_name)

    def get_size(self):
        global _image_sizes
        if self.left is not None:
            w = self.right - self.left
            h = self.bottom - self.top
            return (w,h)

        # look in cache
        size = _image_sizes.get(self.file)
        if size is not None:
            return size[0], size[1]

        abs_file = os.path.normpath(os.path.join(get_artemis_graphics_dir(), self.file))
        size = gui_image_size_raw(abs_file)
        _image_sizes[self.file] = size
        return size

        
        
    
    def send_gui_image(self, SBS, client_id, region_tag, tag, mode, left,top,right,bottom, color=None):
        width, height = self.get_size()
        props = self.get_props(color=color)

        if not self.is_valid():
            file = self.file 
            message = f"$text: IMAGE NOT FOUND {file}"
            SBS.send_gui_text(client_id, region_tag,
                tag, message,
                left, top, right, bottom)
            return


        if mode == IMAGE_ABSOLUTE:
            ar = get_client_aspect_ratio(client_id)
            x = 100* width / ar.x
            y = 100* height / ar.y

            SBS.send_gui_image(client_id, region_tag,
                tag, props,
                left, top, 
                left+x, top+y)
        elif mode >= IMAGE_KEEP_ASPECT:
            ar = get_client_aspect_ratio(client_id)
            # Get section in pixels
            space_x = (right-left)/100
            space_y = (bottom-top)/100
            pixels_x  = (space_x*ar.x)
            pixels_y  = (space_y*ar.y)

            r = pixels_x / width
            if r*height > pixels_y: 
                r = pixels_y / height 

            x = 100* width / ar.x  * r
            y = 100* height / ar.y * r
            ox=0
            oy=0
            if mode == IMAGE_KEEP_ASPECT_CENTER:
                ox = (space_x*100-x)/2
                oy = (space_y*100 - y)/2
            
            
            
            SBS.send_gui_image(client_id, region_tag,
                tag, props,
                left+ox, top+oy, 
                left+ox+x, top+oy+y)
        else:
            SBS.send_gui_image(client_id, region_tag,
                tag, props,
                left, top, right, bottom)




def gui_image_add_atlas(key, image, left=None, top=None, right=None, bottom=None):
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
    ImageAtlas: The image Atlas object. This is a low level object typically used by the system 
"""
    return ImageAtlas(key, image, left, top, right, bottom)
    

_image_sizes = {}
def gui_image_size(file):
    """Return the pixel dimensions of an image file or atlas entry.

    Checks the atlas first, then reads the PNG header directly. Results are
    cached so repeated calls are free after the first read.

    Args:
        file (str): Atlas key or image path (without ``.png`` extension).

    Returns:
        tuple[int, int]: ``(width, height)`` in pixels, or ``(-1, -1)`` if
            the file cannot be read.

    Example:
        w, h = gui_image_size("media/backgrounds/nebula")
    """
    global _image_sizes
    size = _image_sizes.get(file)
    if size is not None:
        return size[0], size[1]
    atlas = ImageAtlas.all.get(file)
    if atlas:
        return atlas.get_size()
    w,h = gui_image_size_raw(file)
    _image_sizes[file] = (w,h)
    return (w,h)
    
def gui_image_size_raw(file):
    try:
        with open(file+".png", 'rb') as f:
            data = f.read(26)
            # Check if is png
            #if (data[:8] == '\211PNG\r\n\032\n'and (data[12:16] == 'IHDR')):
            w, h = struct.unpack('>LL', data[16:24])
            return w,h 

    except Exception:
        return (-1,-1)