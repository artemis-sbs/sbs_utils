from ...helpers import FrameContext
from ..style import apply_control_styles
from ...fs import get_mission_dir_filename, get_artemis_data_dir
import os
import struct # for images sizes

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


def gui_image_get_props(text):
    test = ImageAtlas.all.get(text)
    if test is not None:
        test = str(test)
        if "color:" not in test:
            test+="color:white;"
        return test

    if "image:" not in props:
        props = f"image:{props};"

    if "color:" not in props:
        props+="color:white;"

    return props
    

class ImageAtlas:
    all = {}
    def __init__(self, key, image, left=None, top=None, right=None, bottom=None, color=None):
        file = get_mission_dir_filename(image)
        file_name =  file + ".png"
        print(f"Image Atlas {file_name}")
        if not os.path.exists(file_name):
            file = image

        self.file = file
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.color = color 
        if key is not None:
            ImageAtlas.all[key] = self

    def __str__(self):
        rel_file = os.path.relpath(self.file, get_artemis_data_dir()+"\\graphics")
        color = self.color if self.color else "white"
        if self.left is not None:
            return f"image:{rel_file};sub_rect:{self.left},{self.top},{self.right},{self.bottom};color:{color};" 
        else:
            return f"image:{rel_file};color:{color}"
        
        
        
    def get_size(self):
        if self.left is None:
            return gui_image_size(self.file)
        w = self.right - self.left
        h = self.bottom - self.top
        return (w,h)



def gui_image_add_atlas(key, image, left=None, top=None, right=None, bottom=None):
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