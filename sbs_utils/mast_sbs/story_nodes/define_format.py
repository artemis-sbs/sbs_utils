from ...mast.mast_node import MastNode, mast_node
import re

@mast_node(append=False)
class DefineFormat(MastNode):
    rule = re.compile(r"""\=\$(?P<name>\w+)(?P<format>[^\n\r\f]*)""")
    colors = {
        "alert": ["red", "white"],
        "info": ["blue", "white"],
        "status": ["orange", "white"]
    }
    def is_indentable(self):
        return False

    def is_virtual(self):
        return True
    
    def __init__(self, name, format, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        DefineFormat.colors[name] = [c.strip() for c in format.split(",")]
        

    @staticmethod
    def resolve_colors(c):
        colors = c.split(",")
        ret = []
        for c in colors:
            c = c.strip()
            if c.startswith("$"):
                ret.extend(DefineFormat.colors.get(c[1:], ["white", "white"]))
            else:
                ret.append(c)
        return ret
