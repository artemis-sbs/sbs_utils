from .column import Column
from ...helpers import FrameContext






class Image(Column):
    #"image:icon-bad-bang; color:blue; sub_rect: 0,0,etc"
    def __init__(self, tag, file, mode=1) -> None:
        super().__init__()
        self.tag = tag
        self.atlas = None
        self.update(file)
        self.mode = mode
        

    def update(self, file):
        from ...procedural.gui.image import gui_image_get_atlas
        self.file = file
        self.atlas = gui_image_get_atlas(file)
        
        
    def _present(self, event):
        ctx = FrameContext.context
        if self.atlas is None or not self.atlas.is_valid():
            file = self.file
            if self.atlas:
                file = self.atlas.file 
            message = f"$text: IMAGE NOT FOUND {file}"
            ctx.sbs.send_gui_text(event.client_id, self.region_tag,
                self.tag, message,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
            
        else:
            self.atlas.send_gui_image(ctx.sbs, event.client_id,
                    self.region_tag,  self.tag, self.mode,  
                    self.bounds.left,self.bounds.top,self.bounds.right,self.bounds.bottom)
            
    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v


