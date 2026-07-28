from .column import Column
from ...helpers import FrameContext






class Image(Column):
    #"image:icon-bad-bang; color:blue; sub_rect: 0,0,etc"
    def __init__(self, tag, file, mode=1, color=None) -> None:
        super().__init__()
        self.tag = tag
        self.atlas = None
        self.update(file)
        self.mode = mode
        # Per-USE tint, overriding the atlas's own. One registered cell can then serve
        # every state (a state pip recolored per state) instead of needing a key each.
        self.color = color
        

    def update(self, file):
        from ...procedural.gui.image import gui_image_get_atlas
        self.file = file
        self.atlas = gui_image_get_atlas(file)
        
        
    def measure(self, client_id, mode, avail_px, font, ar):
        # An image's natural size is its actual pixel size -- the one widget
        # whose content is measurable without asking the text engine.
        # gui_image_size checks the atlas, then the PNG header, and caches.
        from ...procedural.gui.image import gui_image_size
        from .measure import px_to_pct_x, px_to_pct_y

        w, h = gui_image_size(self.file)
        if w is None or w <= 0 or h <= 0:
            # Unreadable file -- unmeasurable, so fall back to flex rather
            # than collapsing the column to nothing.
            return None
        return (px_to_pct_x(w, ar), px_to_pct_y(h, ar))

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
                    self.bounds.left,self.bounds.top,self.bounds.right,self.bounds.bottom,
                    self.color)
            
    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v


