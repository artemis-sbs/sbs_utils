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
        return compile_format_string(message)

    @classmethod
    def parse(cls, src, pos=0):
        # match(src, pos) anchors at pos without copying; with the default
        # pos=0 this is identical to the old match(src) single-arg form.
        mo = cls.rule.match(src, pos)

        if mo:
            span = mo.span()
            data = mo.groupdict()
            return ParseData(span[0], span[1], data)
        else:
            return None
        
def compile_format_string(message):
    """Compile a MAST format string into a code object (eval mode).

    Text containing ``{`` is wrapped as an f-string and compiled so it can be
    formatted later; other text is returned unchanged. A triple-quote delimiter
    that does not occur in the text (and won't be escaped by a trailing quote)
    is chosen so embedded quotes don't terminate the literal early. If the text
    still cannot be wrapped safely, a clear error is raised rather than emitting
    broken code (the old ``f\"\"\"{message}\"\"\"`` wrapping silently produced a
    cryptic SyntaxError on any embedded triple-quote).
    """
    if message is None or "{" not in message:
        return message
    if '"""' not in message and not message.endswith('"'):
        delim = '"""'
    elif "'''" not in message and not message.endswith("'"):
        delim = "'''"
    else:
        raise Exception(f"Cannot compile format string (mixed triple quotes): {message!r}")
    try:
        return compile(f'f{delim}{message}{delim}', "<string>", "eval")
    except SyntaxError as e:
        raise Exception(f"Invalid format string {message!r}: {e}")


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
    return f"""((?P<q3>(["']{3})|["'])(?P<{name}>.*?)(?P=q3))"""


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
        # Parallel to options: per-line weight (int) and optional gate (a
        # condition string). Plain "%" lines are weight 1, no gate (backward
        # compatible). "%N" weights the random pick; "%{cond}" includes the line
        # only if cond is truthy in the task scope; "%N{cond}" combines them.
        self.option_weights = []
        self.option_gates = []


    @property
    def desc(self):
        if len(self.options)==0:
            return ""
        return random.choice(self.options)

    def add_option(self, prefix, text):
        weight = 1
        gate = None
        if prefix and prefix.startswith("%"):
            body = prefix[1:]
            gi = body.find("{")
            if gi != -1 and body.endswith("}"):
                gate = body[gi + 1:-1].strip() or None
                body = body[:gi]
            if body.isdigit():
                weight = int(body)
        self.options.append(text)
        self.option_weights.append(weight)
        self.option_gates.append(gate)

    def append_text(self, prefix, text):
        if prefix =='"':
            if len(self.options)==0:
                self.add_option("%", text)
            else:
                self.options[-1] += text
        else:
            self.add_option(prefix, text)

    def pick_option(self, task=None):
        """Choose a line: drop gated lines whose condition is false (evaluated in
        the task scope), then weighted-random among the rest. Returns None if
        nothing is eligible (author should include an ungated fallback). Falls
        back to uniform choice when no task or no gates are present."""
        if len(self.options) == 0:
            return None
        gated = any(self.option_gates)
        if task is None or not gated:
            return random.choice(self.options)
        eligible = []
        weights = []
        for i, text in enumerate(self.options):
            gate = self.option_gates[i]
            if gate:
                ok = task.eval_code(gate, end_on_exception=False)
                if not ok:
                    continue
            eligible.append(text)
            weights.append(self.option_weights[i])
        if not eligible:
            return None
        return random.choices(eligible, weights=weights)[0]
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

