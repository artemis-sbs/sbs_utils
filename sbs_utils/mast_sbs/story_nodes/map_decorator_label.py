from ...mast.mast_node  import IF_EXP_REGEX, STRING_REGEX_NAMED, mast_node
from ...mast.core_nodes.decorator_label import DecoratorLabel
import re


@mast_node()
class MapDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'@map/(?P<path>[\/\w]+)[ \t]+'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name, if_exp=None, q=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        name = f"map/{path}/{id}"
        super().__init__(name, loc)

        self.path= path
        self.display_name= display_name
        self.if_exp = if_exp
        # need to negate if
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            self.if_exp = f'not ({self.if_exp})'

        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self, parent):
        return False
    
    def generate_label_end_cmds(self, compile_info=None):
        # Allow this to follow into === labels
        pass
