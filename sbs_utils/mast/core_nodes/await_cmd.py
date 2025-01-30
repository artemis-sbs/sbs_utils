from ..mast import MastNode, mast_node, BLOCK_START
import re


@mast_node()
class Await(MastNode):
    """
    waits for an existing or a new 'task' to run in parallel
    this needs to be a rule before Parallel
    """
    stack = []
    rule = re.compile(r"""await[ \t]+(until[ \t]+(?P<until>\w+)[ \t]+)?(?P<if_exp>[^:\n\r\f]+)"""+BLOCK_START)
    def __init__(self, until=None, if_exp=None, is_end = None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.end_await_node = None
        self.inlines = None
        self.buttons = None
        self.until = until

        #####self.timeout_label = None
        self.on_change = None
        self.fail_label = None
        self.is_end = is_end
        if self.is_end is None:
            self.inlines = []
            self.buttons = []
            Await.stack.append(self)
        else:
            Await.stack[-1].end_await_node = self

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

    def add_inline(self, inline_data):
        self.inlines.append(inline_data)

    def is_indentable(self):
        return True
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        self.dedent_loc = loc
        end = Await(is_end=True, loc = loc)
        end.dedent_loc = loc+1
        return end

@mast_node()
class AwaitInlineLabel(MastNode):
    rule = re.compile(r"\=(?P<val>[^:\n\r\f]+)"+BLOCK_START)
    def __init__(self, val=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.inline = val
        self.await_node = Await.stack[-1]
        Await.stack[-1].add_inline(self)

    def is_indentable(self):
        return True
    def never_indent(self):
        return False


    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        self.dedent_loc = loc+1
        
