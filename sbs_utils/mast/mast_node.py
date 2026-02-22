from enum import Enum
from .mast_globals import MastGlobals
import random

class ParseData:
    def __init__(self, start, end, data):
        self.start = start
        self.end = end
        self.data = data



class MastNode:
    nodes = []
    file_num:int
    line_num:int
    is_label = False
    is_inline_label = False

    def __init__(self):
        self.dedent_loc = None

    def add_child(self, cmd):
        pass

    def is_indentable(self):
        return False
    
    def never_indent(self):
        return False
    
    def must_indent(self):
        return False

    def is_virtual(self):
        """ 
        Virtual nodes are not added to the command stack
        instead the interact with other nodes
        """
        return False

    def create_end_node(self, loc, dedent_obj, compile_info):
        self.dedent_loc = loc

    def post_dedent(self,compile_info):
        pass

    def compile_formatted_string(self, message):
        if message is None:
            return message
        if "{" in message:
            message = f'''f"""{message}"""'''
            code = compile(message, "<string>", "eval")
            return code
        else:
            return message

    @classmethod
    def parse(cls, lines):
        mo = cls.rule.match(lines)

        if mo:
            span = mo.span()
            data = mo.groupdict()
            return ParseData(span[0], span[1], data)
        else:
            return None
        
def mast_node(append=True):
    def dec_args(cls):
        if cls in MastNode.nodes:
            return cls
        if append:
            MastNode.nodes.append(cls)
        else:
            MastNode.nodes.insert(0,cls)
        return cls
    return dec_args


LIST_REGEX = r"""(\[[\s\S]+?\])"""

DICT_REGEX = r"""(\{[\s\S]+?\})"""
OPT_DATA_REGEX = r"""(?P<data>([ \t]*\{[^\n\r\f]+\}))?"""
STRING_REGEX = r"""((?P<quote>((["']{3})|["']))[ \t\S]*(?P=quote))"""
MULTI_LINE_STRING_REGEX = r"""((?P<quote>(["']{3}))[\s\S]*?(?P=quote))"""
def STRING_REGEX_NAMED(name):
    return f"""((?P<q>(["']{3})|["'])(?P<{name}>.*?)(?P=q))"""
def STRING_REGEX_NAMED_2(name):
    return f"""((?P<q2>(["']{3})|["'])(?P<{name}>.*?)(?P=q2))"""
def STRING_REGEX_NAMED_3(name):
    return f"""((?P<q3>(["']{3})|["'])(?P<{name}">.*?)(?P=q3))"""


IF_EXP_REGEX = r"""([ \t]+if(?P<if_exp>[^:\n\r\f]+))?"""
BLOCK_START = r":[ \t]*(?=\r\n|\n|\#)"


MIN_SECONDS_REGEX = r"""([ \t]*((?P<minutes>\d+))m)?([ \t]*((?P<seconds>\d+)s))?"""
TIMEOUT_REGEX = r"([ \t]*timeout"+MIN_SECONDS_REGEX + r")?"


class Scope(Enum):
    SHARED = 1  # per mast instance
    NORMAL = 2  # per task/subtask
    CLIENT = 10 # is the client handled by scheduler
    ASSIGNED = 20  # is the assigned ship
    SUB_TASK_LOCAL = 99 # Local sub task variables
    TEMP = 99  # Per task?
    UNKNOWN = 100

class DescribableNode(MastNode):
    def __init__(self):
        super().__init__()
        self.options = []


    @property
    def desc(self):
        if len(self.options)==0:
            return ""
        return random.choice(self.options)

    def add_option(self, prefix, text):
        self.options.append(text)

    def append_text(self, prefix, text):
        if prefix =='"':
            if len(self.options)==0:
                self.add_option("%", text)
            else:
                self.options[-1] += text
        else:
            self.add_option(prefix, text)
    def apply_metadata(self, data):
        return False


class MastDataObject(object):
    def __init__(self, dictionary):
        # for dictionary in initial_data:
        for key in dictionary:
            setattr(self, key, dictionary[key])

    def __repr__(self):
        return repr(vars(self))
    
    def get(self, key, defa= None):
        return getattr(self, key, defa)
        

MastGlobals.globals["MastDataObject"] = MastDataObject

