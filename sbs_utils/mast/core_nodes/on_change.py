from ..mast import MastNode, mast_node, BLOCK_START
from .await_cmd import Await
import re



@mast_node()
class OnChange(MastNode):
    rule = re.compile(r"on[ \t]+(change[ \t]+)?(?P<val>[^:]+)"+BLOCK_START)
    stack = []
    def __init__(self, end=None, val=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.value = val
        if val:
            self.value = compile(val, "<string>", "eval")

        self.is_end = False
        #
        # Check to see if this is embedded in an await
        #
        self.await_node = None
        if len(Await.stack) >0:
            self.await_node = Await.stack[-1]
        self.end_node = None

        if end is not None:
            OnChange.stack[-1].end_node = self
            self.is_end = True
            OnChange.stack.pop()
        else:
            OnChange.stack.append(self)

    def is_indentable(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        self.dedent_loc = loc
        end = OnChange("on_end", loc = loc)
        end.dedent_loc = loc+1
        return end


