from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
def gui_text_area (props, style=None):
    """Add a gui text object
    
    valid properties
        text
        color
        font
    
    
    props (str): property string
    style (style, optional): The style"""
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class AppendText(MastNode):
    """class AppendText"""
    def __init__ (self, message, if_exp, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class AppendTextRuntimeNode(MastRuntimeNode):
    """class AppendTextRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast_sbs.story_nodes.text.AppendText):
        ...
class Text(MastNode):
    """class Text"""
    def __init__ (self, message, if_exp, style_name=None, style=None, style_q=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (lines):
        ...
class TextRuntimeNode(MastRuntimeNode):
    """class TextRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast_sbs.story_nodes.text.Text):
        ...
