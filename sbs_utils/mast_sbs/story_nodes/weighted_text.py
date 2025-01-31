from ...mast.mast_node import MastNode, mast_node
import re
from ...mast.mast_node import DescribableNode
        
@mast_node(append=False)
class WeightedText(MastNode):
    rule = re.compile(r"""(?P<mtype>\%\d*|\")(?P<text>[^\n\r\f]*)""")
    def __init__(self, mtype, text,  loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        # Try to attach to a label
        if loc == 0 and compile_info is not None and compile_info.label is not None:
            compile_info.label.append_text(mtype, text)
        elif isinstance(compile_info.prev_node, DescribableNode):
            compile_info.prev_node.append_text(mtype, text)
        else:
            raise Exception("Weighted text without start. or not indented properly.")
        

    def is_indentable(self):
        return False
        
    def is_virtual(self):
        return True    