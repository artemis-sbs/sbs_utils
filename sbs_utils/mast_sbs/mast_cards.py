from ..mast.mast import IF_EXP_REGEX, MastNode, DecoratorLabel, STRING_REGEX_NAMED, mast_node
import re
from ..agent import Agent

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

class CardLabelBase(DecoratorLabel):
    def __init__(self, purpose, path, display_name=None, if_exp=None, loc=None, compile_info=None):

        # Label stuff
        id = DecoratorLabel.next_label_id()
        name = f"{purpose}/{path}/{id}"
        #
        # Should the card names be unique?
        #
        super().__init__(name, loc)

        self.path= path
        self.display_name = display_name
        self.description = ""
        self.if_exp = if_exp
        # need to negate if
        self.code = None
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            try:
                self.code = compile(self.if_exp, "<string>", "eval")
            except:
                raise Exception(f"Syntax error '{if_exp}'")
            
        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self, parent):
        return False
    
    def test(self, task):
        if self.code is None:
            return True
        return task.eval_code(self.code)

    def generate_label_end_cmds(self, compile_info=None):
        super().generate_label_end_cmds(compile_info)
        #
        # Spawn any sub tasks
        #

    def apply_meta_data(self, data):
        return super().apply_meta_data(data)
    
@mast_node()
class CardLabel(CardLabelBase):
    rule = re.compile(r'@card/(?P<path>([\w/]+))[ /t]*'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name=None, q=None, if_exp=None, loc=None, compile_info=None):
        super().__init__("card", path, display_name, if_exp, loc, compile_info)

    def generate_label_end_cmds(self, compile_info=None):
        super().generate_label_end_cmds(compile_info)
        #
        # Spawn any sub tasks
        #

    def apply_meta_data(self, data):
        return super().apply_meta_data(data)

@mast_node()
class ObjectiveLabel(CardLabelBase):
    rule = re.compile(r'@objective/(?P<path>([\w/]+))[ /t]*'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name=None, q=None, if_exp=None, loc=None, compile_info=None):
        super().__init__("objective", path, display_name, if_exp, loc, compile_info)
        
    def generate_label_end_cmds(self, compile_info=None):
        super().generate_label_end_cmds(compile_info)
        #
        # Spawn any sub tasks
        #

    def apply_meta_data(self, data):
        return super().apply_meta_data(data)

@mast_node()
class UpgradeLabel(CardLabelBase):
    rule = re.compile(r'@upgrade/(?P<path>([\w/]+))[ /t]*'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name=None, q=None, if_exp=None, loc=None, compile_info=None):
        super().__init__("upgrade", path, display_name, if_exp, loc, compile_info)
        
    def generate_label_end_cmds(self, compile_info=None):
        super().generate_label_end_cmds(compile_info)
        #
        # Spawn any sub tasks
        #

    def apply_meta_data(self, data):
        return super().apply_meta_data(data)
