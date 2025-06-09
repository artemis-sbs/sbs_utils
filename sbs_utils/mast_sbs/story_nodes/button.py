from ...mast.mast_node import MastNode, mast_node, BLOCK_START, OPT_DATA_REGEX, IF_EXP_REGEX, ParseData
from ...mast.core_nodes.await_cmd import Await
from ...mast.core_nodes.yield_cmd import Yield
import re
from ...mast_sbs.story_nodes.route_label import RouteDecoratorLabel, DecoratorLabel
from ...mast_sbs.story_nodes.define_format import DefineFormat

OPT_BLOCK_START = r"(?P<block>\:)?[ \t]*(?=\r\n|\n|\#)"
FORMAT_EXP = r"([ \t]*\[(?P<format>([\$\#]?\w+[ \t]*(,[ \t]*\#?\w+)?))\])?"
WEIGHT_EXP = r"(?P<weight>([ \t]*\^\d+[ \t]*))?"
PRIORITY_EXP = r"(?P<priority>([ \t]*!\d+[ \t]*))?"



@mast_node(append=False)
class Button(MastNode):
    rule = re.compile(r"(?P<button>\*|\+)"+PRIORITY_EXP+WEIGHT_EXP+FORMAT_EXP+r"""[ \t]*(?P<q>["'])(?P<message>[ \t\S]+?)(?P=q)([ \t]*(?P<path>[\w\/]+))?"""+OPT_DATA_REGEX+IF_EXP_REGEX+r"[ \t]*"+OPT_BLOCK_START)
    def __init__(self, message=None, button=None,  
                if_exp=None, format=None, label=None, 
                clone=False, q=None, weight=None,priority=None,
                new_task=None, data=None, path=None, block=None, promise=None,
                loc=None, compile_info=None):
        super().__init__()
        #
        # Remember any field in here need to be set in clone()
        #
        
        if clone:
            return
        self.message = self.compile_formatted_string(message)
        self.sticky = (button == '+' or button=="button")
        self.color = None
        if format is not None:
            f = DefineFormat.resolve_colors(format)
            if len(f)>=1:
                self.color = f[0]
            
        self.visited = set() if not self.sticky else None
        self.loc = loc
        # Note: label is used with python buttons
        # and is generally None
        self.await_node = None
        self.dedent_node = None
        self.is_block = block is not None
        self.use_sub_task = new_task
        self.label_weight = 0
        self.raw_weight = 100
        if weight is not None:
            try:
                weight = weight.strip()
                weight = weight[1:]
                self.raw_weight = int(weight)
            except:
                self.raw_weight = 101
        self.priority = 100
        if priority is not None:
            try:
                priority  = priority.strip()
                priority  = priority[1:]
                self.priority  = int(priority)
            except:
                self.priority  = 101
        #self.label_to_run = None
        
        if compile_info is not None and isinstance(compile_info.label, DecoratorLabel):
        #    self.label_to_run = compile_info.label
            self.label_weight = compile_info.label.label_weight
        if compile_info is not None and isinstance(compile_info.label, RouteDecoratorLabel):
            if self.is_block:
                self.use_sub_task = True
                label = compile_info.label
                
        elif label is None:
            self.await_node = Await.stack[-1]
            self.await_node.buttons.append(self)
        self.label = label
        self.promise = promise
        
        
        self.data = data
        if data is not None and isinstance(data, str):
            data = data.lstrip()
            self.data = compile(data, "<string>", "eval")
        self.path = None
        #
        # path from regex could be a path or a label
        # paths start with //, but we don't need those later
        #
        if path is not None and path.startswith('//'):
            self.path = path.strip('/')
        elif label is None:
            self.label = path
            self.use_sub_task = True

        if if_exp:
            if_exp = if_exp.lstrip()
            self.code = compile(if_exp, "<string>", "eval")
        else:
            self.code = None

        
    @property
    def weight(self):
        # Negative to make higher weights first
        # Then label_weight groups by label if raw_weight is the same
        # The order in which they were built is the final
        return self.raw_weight * 1000 + self.label_weight * 1000

    def visit(self, id_tuple):
        if self.visited is not None:
            self.visited.add(id_tuple)
    
    def been_here(self, id_tuple):
        if self.visited is not None:
            return (id_tuple in self.visited)
        return False

    def should_present(self, id_tuple):
        if self.visited is not None:
            return not id_tuple in self.visited
        return True

    def clone(self):
        proxy = Button(clone=True)
        proxy.message = self.message
        proxy.label = self.label
        proxy.promise = self.promise
        proxy.code = self.code
        proxy.color = self.color
        proxy.loc = self.loc
        proxy.await_node = self.await_node
        proxy.dedent_node = self.dedent_node
        proxy.sticky = self.sticky
        proxy.visited = self.visited
        proxy.data = self.data
        # proxy.for_code = self.for_code
        # proxy.for_name = self.for_name
        proxy.is_block = self.is_block
        proxy.use_sub_task = self.use_sub_task
        proxy.path = self.path
        proxy.label_weight = self.label_weight
        proxy.raw_weight = self.raw_weight
        proxy.priority = self.priority
        #proxy.label_to_run = self.label_to_run
        ####
        # This is used by the gui buttons
        proxy.layout_item = None 
        

        return proxy
    
    def expand(self):
        pass

    def is_indentable(self):
        return True
    
    def must_indent(self):
        return self.is_block
    
    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        if self.await_node is not None:
            self.await_node.dedent_loc = loc
        elif self.is_block:
            # Block buttons need to end
            end = Yield('success', compile_info=compile_info)
            # Dedent is one passed the end node
            self.dedent_loc = loc+1
            return end
    


    def resolve_data_context(self, task):
        if self.data is not None and not isinstance(self.data, dict):
            self.data = task.eval_code(self.data)
            self.message = task.format_string(self.message)

    def run(self, task, button_promise):
        task_data = self.data
        if self.data is not None and not isinstance(self.data, dict):
            task_data = task.eval_code(self.data)
        if self.promise is not None:
            self.promise.set_result(self)
            return None

        if self.use_sub_task and self.label:
            #
            # Block commands in a sub task is a strait jump to the button
            # The button should dedent to a yield_idle
            #
            #
            if self.is_block:
                sub_task = task.start_sub_task(self.label, inputs=task_data, defer=True, active_cmd=self.loc+1)
            else:
                sub_task = task.start_sub_task(self.label, inputs=task_data, defer=True)

            sub_task.set_variable("BUTTON_PROMISE", button_promise)
            sub_task.tick_in_context()
            return sub_task
        elif self.label:
            task.push_inline_block(self.label)
            task.tick_in_context()
        else:
            task.push_inline_block(task.active_label,self.loc+1)
            task.tick_in_context()

        return None


   
from ...mast.pollresults import PollResults
from ...mast.mast_runtime_node import MastRuntimeNode, mast_runtime_node
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...mast.mast import Mast
    from ...mast.mastscheduler import MastAsyncTask



@mast_runtime_node(Button)
class ButtonRuntimeNode(MastRuntimeNode):
    def enter(self, mast:'Mast', task:'MastAsyncTask', node: Button):
        from ...procedural.gui import ButtonPromise

        self.node_label = task.active_label
        if node.await_node is None:
            p = ButtonPromise.navigating_promise
            if p is not None:
                #
                # This is clone so this should be OK
                #
                clone = node.clone()
                clone.resolve_data_context(task)
                p.add_nav_button(clone)
    def poll(self, mast:'Mast', task:'MastAsyncTask', node: Button):
        if node.await_node:
            task.jump(self.node_label, node.await_node.end_await_node.dedent_loc)
            return PollResults.OK_JUMP
        if node.is_block:
            if node.dedent_loc is None:
                print("GOT IT ITS DEDENT")
            else:
                task.jump(self.node_label, node.dedent_loc)
                return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE