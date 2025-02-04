from ...mast.mast_node import IF_EXP_REGEX, MastNode, STRING_REGEX_NAMED, mast_node
from ...mast.core_nodes.decorator_label import DecoratorLabel
import re

@mast_node()
class InlineRoute(MastNode):
    rule = re.compile(r'///(?P<path>[\w/]+)')
    is_label = False
    is_inline_label = True

    def __init__(self, path, m=None, loc=None, compile_info=None):
        super().__init__()
        self.path = path
        self.next = None
        self.loc = loc
        self.desc = None
        self.label = compile_info.label
        compile_info.label.add_label(path, self)

    def never_indent(self):
        return True
    
    def is_indentable(self):
        return True

