from ..mast import MastNode, mast_node, BLOCK_START, ParseData
import re



class WithEnd(MastNode):
    """
    LoopEnd is a node that is injected to allow loops to know where the end is
    """
    #rule = re.compile(r'((?P<loop>next)[ \t]*(?P<name>\w+))')
    def __init__(self, start=None, name=None,loc=None, compile_info=None):
        super().__init__()
        self.start = start
        self.loc = loc
        self.start.end = self

@mast_node()
class WithStart(MastNode):
    rule = re.compile(r'(with[ \t]*(?P<obj>[^\n\r\f]+))')
    with_vars = 0
    def __init__(self, obj=None, name=None, loc=None, compile_info=None):
        super().__init__()
        if obj:
            self.code = compile(obj, "<string>", "eval")
        else:
            self.code = None
        self.name = name
        self.with_name = f"__WITH_{WithStart.with_vars}"
        WithStart.with_vars += 1

        self.loc = loc
        self.end = None
        
    def is_indentable(self):
        return True
    
    @classmethod
    def parse(cls, lines):
        mo = cls.rule.match(lines)
        if mo:
            span = mo.span()
            data = mo.groupdict()
            obj= data.get("obj")
            if obj is None:
                return None
            obj = obj.strip()

            if not obj.endswith(":"):
                return None
            obj = obj[:-1]
            obj = obj.strip()
            
            has_as = obj.rsplit(" as ")
            if len(has_as)==2:
                data["name"] = has_as[1]
                data["obj"] = has_as[0]
            elif len(has_as)!=1:
                return None
            else:
                data["obj"] = obj

            return ParseData(span[0], span[1], data)
        else:
            return None


    def create_end_node(self, loc, _,  compile_info):
        end =  WithEnd(self, loc=loc)
        # Dedent is one passed the end node
        self.dedent_loc = loc+1
        return end
   