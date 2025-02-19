from ..mast_node  import DescribableNode, mast_node
import re

@mast_node()
class Label(DescribableNode):
    rule = re.compile(r'(?P<m>=|\?){2,}\s*(?P<replace>replace:)?[ \t]*(?P<name>\w+)[ \t]*((?P=m){2,})?')
    is_label = True

    def __init__(self, name, replace=None, m=None, loc=None, compile_info=None):
        super().__init__()

        self.name = name
        self.cmds = []
        self.next = None
        self.loc = loc
        self.replace = replace is not None
        self.labels = {}
        self.meta_data = {}

    def add_child(self, cmd):
        if not cmd.is_virtual():
            cmd.loc = len(self.cmds)
            self.cmds.append(cmd)

    def add_label(self, name, label):
        self.labels[name] = label

    def can_fallthrough(self, parent):
        return True
    
    def can_fall_into(self, parent):
        return True
    


    def generate_label_begin_cmds(self, compile_info=None):
        pass

    def generate_label_end_cmds(self, compile_info=None):
        pass
    
    def apply_meta_data(self, data):
        self.meta_data |= data
        return True

