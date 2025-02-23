from ..mast_node import MastNode, mast_node, BLOCK_START
import re
from ... import yaml

MAST_CODE_BLOCK = r"[ \t]*```([ \t]*(?P<tag>(\w+)))?[ \t]*\n(?P<data>([\s\S]*?))\n```"

@mast_node()
class MetaDataBlock(MastNode):
    rule = re.compile(r"metadata:"+MAST_CODE_BLOCK)
    def __init__(self, tag=None, data=None, loc=None, compile_info=None):
        super().__init__()
        
        self.tag = tag
        self.is_label_metadata = True

        self.loc = loc
        # compile_info label is Card etc.
        # tag tag = label?
        # Process now
        if self.tag is None:
            self.tag = tag = 'yaml'
        match self.tag:
            case "yaml":
                self.data = yaml.safe_load(data)
                if self.is_label_metadata:
                    supported = compile_info.label.apply_metadata(self.data)
                    #if not supported:
            #    raise Exception("meta data not supported here.")
        

    def is_virtual(self):
        return self.is_label_metadata
    
    def is_indentable(self):
        return False

