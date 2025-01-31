from ..mast_node import MastNode, mast_node, BLOCK_START
import re
from ... import yaml

@mast_node()
class YamlBlock(MastNode):
    rule = re.compile(r'\s*---(\s*!(?P<tag>(\w+)))?\n(?P<data>([\s\S]*?))\n\.\.\.')
    def __init__(self, tag=None, data=None, loc=None, compile_info=None):
        super().__init__()
        
        self.tag = tag
        self.is_label_meta_data = True

        self.loc = loc
        # compile_info label is Card etc.
        # tag tag = label?
        # Process now
        self.data = yaml.safe_load(data)
        if self.is_label_meta_data:
            supported = compile_info.label.apply_meta_data(self.data)
            #if not supported:
            #    raise Exception("meta data not supported here.")
        

    def is_virtual(self):
        return self.is_label_meta_data
    
    def is_indentable(self):
        return False

