from ..mast_node  import MastNode, mast_node
import re

@mast_node()
class InlineLabel(MastNode):
    rule = re.compile(r'(?P<m>-){2,}[ \t]*(?P<name>\w+)[ \t]*((?P=m){2,})?')
    is_label = False
    is_inline_label = True

    def __init__(self, name, m=None, loc=None, compile_info=None):
        super().__init__()
        self.name = name
        self.next = None
        self.loc = loc
        self.desc = None
        self.label = compile_info.label
        compile_info.label.add_label(name, self)

    def never_indent(self):
        return True
    


from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node

@mast_runtime_node(InlineLabel)
class InlineLabelRuntimeNode(MastRuntimeNode):
    pass
