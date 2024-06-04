from sbs_utils.gui import Widget
class Control(Column):
    """class Control"""
    def __init__ (self, left, top, right, bottom) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def invalidate_regions (self):
        ...
    @property
    def local_region_tag (self):
        """self.tag is inject after init"""
    def present (self, event):
        ...
