import struct # for images sizes
from ... import fs
import os
from .column import Column
from ...helpers import FrameContext
from ...gui import get_client_aspect_ratio

def split_props(s, def_key):
    ret = {}

    # get key
    start = 0
    key = -1
    end = -1
    while start < len(s):
        key = s.find(":", start)
        if key == -1:
            ret[def_key] = s
            return ret
        s_key = s[start:key]
        key += 1
        end = s.find(";", key)
        if end ==-1:
            s_value = s[key:]
            start = len(s)
        else:
            s_value = s[key:end]
            start = end+1
        ret[s_key] = s_value
    return ret
        
def merge_props(d):
    s=""
    for k,v in d.items():
        s += f"{k}:{v};"
    return s  


IMAGE_FIT = 0
IMAGE_ABSOLUTE = 1
IMAGE_KEEP_ASPECT = 2
IMAGE_KEEP_ASPECT_CENTER = 3


class Image(Column):
    #"image:icon-bad-bang; color:blue; sub_rect: 0,0,etc"
    def __init__(self, tag, file, mode=1) -> None:
        super().__init__()
        self.tag = tag
        self.update(file)
        self.mode = mode

    def update(self, file):
        fs.get_artemis_data_dir()
        props = split_props(file, "image")
        # to get size get absolute path
        self.file = os.path.abspath(props["image"].strip())
        # Make the file relative to artemis dir
        rel_file = os.path.relpath(props["image"].strip(), fs.get_artemis_data_dir()+"\\graphics")
        props["image"] = rel_file
        self.props = merge_props(props)

        self.width = -1
        self.height = -1
        self.get_image_size()
        
    def _present(self, event):
        ctx = FrameContext.context
        if self.width == -1:
            message = f"$text: IMAGE NOT FOUND {self.file}"
            ctx.sbs.send_gui_text(event.client_id, self.region_tag,
                self.tag, message,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        elif self.mode == IMAGE_ABSOLUTE:
            ar = get_client_aspect_ratio(event.client_id)
            x = 100* self.width / ar.x
            y = 100* self.height / ar.y

            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                self.tag, self.props,
                self.bounds.left, self.bounds.top, 
                self.bounds.left+x, self.bounds.top+y)
        elif self.mode >= IMAGE_KEEP_ASPECT:
            ar = get_client_aspect_ratio(event.client_id)
            # Get section in pixels
            space_x = (self.bounds.right-self.bounds.left)/100
            space_y = (self.bounds.bottom-self.bounds.top)/100
            pixels_x  = (space_x*ar.x)
            pixels_y  = (space_y*ar.y)

            r = pixels_x / self.width
            if r*self.height > pixels_y: 
                r = pixels_y / self.height 

            x = 100* self.width / ar.x  * r
            y = 100* self.height / ar.y * r
            ox=0
            oy=0
            if self.mode == IMAGE_KEEP_ASPECT_CENTER:
                ox = (space_x*100-x)/2
                oy = (space_y*100 - y)/2
            
            
            
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                self.tag, self.props,
                self.bounds.left+ox, self.bounds.top+oy, 
                self.bounds.left+ox+x, self.bounds.top+oy+y)
        else:
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                self.tag, self.props,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    # Get image width and height of image
    def get_image_size(self):
        try:
            with open(self.file+".png", 'rb') as f:
                data = f.read(26)
                # Chck if is png
                #if (data[:8] == '\211PNG\r\n\032\n'and (data[12:16] == 'IHDR')):
                w, h = struct.unpack('>LL', data[16:24])
                self.width = int(w)
                self.height = int(h)

        except Exception:
            self.width = -1
            self.height = -1
    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v
