from ...helpers import FrameContext
from ..style import apply_control_styles
from ...fs import get_mission_dir_filename, get_artemis_data_dir, get_mission_graphics_file, get_artemis_dir
import os
import struct # for images sizes
from ...gui import get_client_aspect_ratio

def gui_image_stretch(props, style=None):
    """queue a gui image element that stretches to fit

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """            
    return gui_image(props, style=style, fit=0)

def gui_image_absolute(props, style=None):
    """queue a gui image element that draw the absolute pixels dimensions

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    return gui_image(props, style=style, fit=1)

def gui_image_keep_aspect_ratio(props, style=None):
    """queue a gui image element that draw keeping the same aspect ratio, left top justified

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    return gui_image(props, style=style, fit=2)

def gui_image_keep_aspect_ratio_center(props, style=None):
    """queue a gui image element that keeps the aspect ratio and centers when there is extra

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.

    Returns:
        layout object: The Layout object created
    """                
    return gui_image(props, style=style, fit=3)


def gui_image(props, style=None, fit=0):
    """queue a gui image element that draw based on the fit argument. Default is stretch

    Args:
        props (str): _description_
        style (str, optional): Style. Defaults to None.
        fit (int): The type of fill, 

    Returns:
        layout object: The Layout object created
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
        rel_file = os.path.relpath(self.file, get_artemis_data_dir()+"\\graphics")
        color = color if color else self.color
        color = color if color else "white"
        if self.left is not None:
            return f"image:{rel_file};sub_rect:{self.left},{self.top},{self.right},{self.bottom};color:{color};" 
        else:
            return f"image:{rel_file};color:{color}"
        
    def is_valid(self):
        file_name =  self.file + ".png"
        return os.path.exists(file_name)
        
    def get_size(self):
        if self.left is None:
            return gui_image_size(self.file)
        w = self.right - self.left
        h = self.bottom - self.top
        return (w,h)
    
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
    """The image atlas allows a key name to be used to assign to a set of image properties
    ths key can be used instead of image properties in any command that expect image properties.

    The image file passed will be used to search for the file. It will first check the mission directory and the data/graphics folder.
    In the future this could be modified to account for mods, e.g. a common media folders.

    By specifying the rect (left,top, right, bottom) the image key can reference a part of an image file.

    Add a key to reference a full image

    gui_image_add_atlas("test", "media/LegendaryMissions/operator")

    Add a key to reference a full image

    gui_image_add_atlas("test2", "media/LegendaryMissions/operator", 645,570, 950,820)

    Once the atlas is added the key can be used anywhere images can be used.

### :mast-icon: MAST / :simple-python: python

``` python
    gui_image("test")
```

### :mast-icon: MAST / :simple-python: python

``` python
    # Text area also use the image atlas for images
    gui_text_area("![](image://test2?scale=0.5&fill=center)")
```



    Args:
        key (str): the key to define in the image atlas
        image (str): The file of the image. This can also be a image property string
        left (float, optional): The pixel location of the left. Defaults to None.
        top (float, optional): The pixel location of the top. Defaults to None.
        right (float, optional): The pixel location of the right. Defaults to None.
        bottom (float, optional): The pixel location of the bottom. Defaults to None.

    Returns:
        ImageStales: The image Atlas object. This is a low level object typically used by the system 
    """
    return ImageAtlas(key, image, left, top, right, bottom)
    

_image_sizes = {}
def gui_image_size(file):
    global _image_sizes
    size = _image_sizes.get(file)
    if size is not None:
        return size[0], size[1]
    atlas = ImageAtlas.all.get(file)
    if atlas and atlas.left:
        return atlas.get_size()
    try:
        with open(file+".png", 'rb') as f:
            data = f.read(26)
            # Check if is png
            #if (data[:8] == '\211PNG\r\n\032\n'and (data[12:16] == 'IHDR')):
            w, h = struct.unpack('>LL', data[16:24])
            _image_sizes[file] = (w,h)
            return w,h 

    except Exception:
        return (-1,-1)