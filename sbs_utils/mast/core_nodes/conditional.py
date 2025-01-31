from ..mast_node import MastNode, mast_node, BLOCK_START
import re



    
@mast_node()
class IfStatements(MastNode):
    rule = re.compile(r'((?P<end>else:)|(((?P<if_op>if|elif)[ \t]+?(?P<if_exp>[ \t\S]+?)'+BLOCK_START+')))')

    if_chains = {}

    def __init__(self, end=None, if_op=None, if_exp=None, loc=None, compile_info=None):
        super().__init__()
        self.code = None
        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")

        self.end = end
        self.if_op = if_op
        self.if_chain = None
        self.if_node = None
        self.loc = loc


        if "end_if" == self.end:
            self.if_node = IfStatements.if_chains.get(compile_info.indent)
            if self.if_node is not None:
                self.if_node.if_chain.append(self)
            IfStatements.if_chains[compile_info.indent] = None
        elif "else:" == self.end:
            self.if_node = IfStatements.if_chains.get(compile_info.indent)
            if self.if_node is not None:
                self.if_node.if_chain.append(self)
            
        elif "elif" == self.if_op:
            self.if_node = IfStatements.if_chains.get(compile_info.indent)
            if self.if_node is not None:
                self.if_node.if_chain.append(self)
            
        elif "if" == self.if_op:
            self.if_chain = [self]
            self.if_node = self
            IfStatements.if_chains[compile_info.indent] = self
            

    def is_indentable(self):
        return True
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        self.if_node.dedent_loc = loc

        return None
    
from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..mast import Mast
    from ..mastscheduler import MastAsyncTask
   
@mast_runtime_node(IfStatements)
class IfStatementsRuntimeNode(MastRuntimeNode):
    def poll(self, mast:'Mast', task:'MastAsyncTask', node:IfStatements):
        """ """
        # if this is THE if, find the first true branch
        if node.if_op == "if":
            activate = self.first_true(task, node)
            if activate is not None:
                task.jump(task.active_label, activate.loc+1)
                return PollResults.OK_JUMP

        # Everything else jumps to past all things involved in this chain
        if node.if_node.dedent_loc is not None:
            task.jump(task.active_label, node.if_node.dedent_loc)
            return PollResults.OK_JUMP
        else:
            print("DEDENT IS NONE IN AN IF")

    def first_true(self, task: 'MastAsyncTask', node: IfStatements):
        cmd_to_run = None
        for i in node.if_chain:
            test_node = i # task.mast_ticker.cmds[i]
            if test_node.code:
                value = task.eval_code(test_node.code)
                if value:
                    cmd_to_run = i
                    break
            elif test_node.end == 'else:':
                cmd_to_run = i
                break
            elif test_node.end == 'end_if':
                cmd_to_run = i
                break

        return cmd_to_run


@mast_node()
class MatchStatements(MastNode):
    #rule = re.compile(r'((?P<end>case[ \t]*_:|end_match)|(((?P<op>match|case)[ \t]+?(?P<exp>[^\n\r\f]+)'+BLOCK_START+')))')
    rule = re.compile(r'((?P<op>match|case)[ \t]+?(?P<exp>(_)|([^\n\r\f]+))'+BLOCK_START+')')
    chains = []
    def __init__(self, end=None, op=None, exp=None, loc=None, compile_info=None):
        super().__init__()

        self.loc = loc
        self.match_exp = None
        self.end = end
        self.op = op
        self.chain = None
        self.match_node = None

        if "case" == op:
            the_match_node = MatchStatements.chains[-1]
            self.match_node = the_match_node
            the_match_node.chain.append(self)
        elif "match" == op:
            self.match_node = self
            self.chain = []
            MatchStatements.chains.append(self)
            
        if op == "match":
            self.match_exp = exp.lstrip()
        elif exp:
            exp = exp.lstrip()
            if exp == "_":
                self.code = compile('True', "<string>", "eval")
            else:
                exp = self.match_node.match_exp +"==" + exp
                self.code = compile(exp, "<string>", "eval")
        else:
            self.code = None

    def is_indentable(self):
        return True
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        if dedent_obj is None:
            # Dandling
            self.match_node.dedent_loc = loc
            if self.op == 'match':
                MatchStatements.chains.pop()
        elif dedent_obj.__class__ == MatchStatements and self.op == 'match':
            if dedent_obj.op=='match':
                MatchStatements.chains.pop()
                MatchStatements.chains.pop()
                self.match_node.dedent_loc = loc
                MatchStatements.chains.append(dedent_obj)
            else:
                self.match_node.dedent_loc = loc

        elif dedent_obj.__class__ == MatchStatements:
            self.match_node.dedent_loc = loc
        else:
            self.match_node.dedent_loc = loc
            if self.op == 'match':
                MatchStatements.chains.pop()

        return None

@mast_runtime_node(MatchStatements)
class MatchStatementsRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:MatchStatements):
        """ """
        # if this is THE if, find the first true branch
        if node.op == "match":
            activate = self.first_true(task, node)
            if activate is not None:
                task.jump(task.active_label, activate.loc+1)
                return PollResults.OK_JUMP
            
        task.jump(task.active_label, node.match_node.dedent_loc)
        return PollResults.OK_JUMP

    def first_true(self, task: 'MastAsyncTask', node: MatchStatements):
        cmd_to_run = None
        for i in node.chain:
            test_node = i # task.mast_ticker.cmds[i]
            if test_node.code:
                value = task.eval_code(test_node.code)
                if value:
                    cmd_to_run = i
                    break
            elif test_node.end == 'case_:':
                cmd_to_run = i
                break
            elif test_node.end == 'end_match':
                cmd_to_run = i
                break

        return cmd_to_run


