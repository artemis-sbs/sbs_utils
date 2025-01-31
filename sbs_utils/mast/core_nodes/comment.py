from ..mast_node import MastNode, mast_node, BLOCK_START
import re


@mast_node()
class Comment(MastNode):
    #rule = re.compile(r'#[ \t\S]*)')
    rule = re.compile(r'(#[ \t\S]*)|(/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)|([!]{3,}\s*(?P<com>\w+)\s*[!]{3,}[\s\S]+[!]{3,}\s*end\s+(?P=com)\s*[!]{3,})')

    def __init__(self, com=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc


