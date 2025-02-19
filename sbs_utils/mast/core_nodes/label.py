from ..mast_node  import DescribableNode, mast_node
from ...agent import Agent, get_story_id
import re
import random

@mast_node()
class Label(DescribableNode, Agent):
    rule = re.compile(r'(?P<m>=|\?){2,}\s*(?P<replace>replace:)?[ \t]*(?P<name>\w+)[ \t]*((?P=m){2,})?')
    is_label = True

    def __init__(self, name, replace=None, m=None, loc=None, compile_info=None):
        DescribableNode.__init__(self)
        Agent.__init__(self)

        self.name = name
        self.cmds = []
        self.next = None
        self.loc = loc
        self.replace = replace is not None
        self.labels = {}
        self.metadata = {}
        self.id = get_story_id()
        self.add()
        self.add_role("__MAST_LABEL__")

    @property
    def desc(self):
        options = self.get_inventory_value("desc")
        # Could be a string set in meta data
        if isinstance(options, str):
            return options
        if options is None or len(options)==0:
            return ""
        return random.choice(options)

    def add_option(self, prefix, text):
        options = self.get_inventory_value("desc", [""])
        if prefix=='"':
            options[-1] += text
        else:
            options.append(text)
        self.set_inventory_value("desc", options)

    def append_text(self, prefix, text):
        self.add_option(prefix, text)
        pass
 

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
    
    def apply_metadata(self, data):
        #self.inventory |= data
        for k in data:
            self.set_inventory_value(k, data[k])
        return True

