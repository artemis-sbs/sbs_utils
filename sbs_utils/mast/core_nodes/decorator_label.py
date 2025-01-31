from ..mast_node import mast_node
import re
from .label import Label


@mast_node()
class DecoratorLabel(Label):
    decorator_label = 0
    def next_label_id():
        DecoratorLabel.decorator_label += 1
        return DecoratorLabel.decorator_label

    def __init__(self, name, loc=None):
        super().__init__(name)
        self.loc = loc
        

    def can_fallthrough(self, parent):
        return False

    def generate_label_begin_cmds(self, compile_info=None):
        pass

    def generate_label_end_cmds(self, compile_info=None):
        from .yield_cmd import Yield
        #
        # Always have a yield        
        #
        p = compile_info.label if compile_info is not None else None
        if not self.can_fallthrough(p):
            cmd = Yield('success', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success at end {self.name}"
            self.add_child(cmd)

