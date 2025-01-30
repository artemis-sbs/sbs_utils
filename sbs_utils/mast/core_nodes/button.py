from ..mast import MastNode, mast_node, BLOCK_START, OPT_DATA_REGEX, IF_EXP_REGEX, ParseData
from .await_cmd import Await
from .yield_cmd import Yield
import re

from .route_label import RouteDecoratorLabel
    





# OPT_STYLE = r"""([ \t]*style[ \t]*["'](?P<color>[ \t\S]+)["'])?"""
# FOR_RULE = r'([ \t]+for[ \t]+(?P<for_name>\w+)[ \t]+in[ \t]+(?P<for_exp>[ \t\S]+?))?'
OPT_BLOCK_START = r"(?P<block>\:)?[ \t]*(?=\r\n|\n|\#)"
FORMAT_EXP = r"(\[(?P<format>([\$\#]?\w+[ \t]*(,[ \t]*\#?\w+)?))\])?"

@mast_node()
class Button(MastNode):
    #### Pre routeLabels rule = re.compile(r"""(?P<button>\*|\+)[ \t]*(?P<q>["'])(?P<message>[ \t\S]+?)(?P=q)"""+OPT_STYLE+FOR_RULE+IF_EXP_REGEX+r"[ \t]*"+BLOCK_START)
    rule = re.compile(r"(?P<button>\*|\+)"+FORMAT_EXP+r"""[ \t]*(?P<q>["'])(?P<message>[ \t\S]+?)(?P=q)([ \t]*(?P<path>[\w\/]+))?"""+OPT_DATA_REGEX+IF_EXP_REGEX+r"[ \t]*"+OPT_BLOCK_START)
    def __init__(self, message=None, button=None,  
                if_exp=None, format=None, label=None, 
                clone=False, q=None, 
                new_task=None, data=None, path=None, block=None,loc=None, compile_info=None):
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
            from ...mast_sbs.story_nodes.comms_message import DefineFormat
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
        self.label_to_run = None
        
        if compile_info is not None:
            self.label_to_run = compile_info.label
        if compile_info is not None and isinstance(compile_info.label, RouteDecoratorLabel):
            if self.is_block:
                self.use_sub_task = True
                label = compile_info.label
        elif label is None:
            self.await_node = Await.stack[-1]
            self.await_node.buttons.append(self)
        self.label = label
        
        
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

        # self.for_name = for_name
        # if for_exp:
        #     for_exp = for_exp.lstrip()
        #     self.for_code = compile(for_exp, "<string>", "eval")
        # else:
        #     self.for_code = None
        

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
        proxy.label_to_run = self.label_to_run
        ####
        # This is used by the gui buttons
        proxy.layout_item = None 
        

        return proxy
    
    def expand(self):
        pass

    def is_indentable(self):
        return True
    
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
            #print( f"TODO: data {self.data}")
            self.data = task.eval_code(self.data)
            self.message = task.format_string(self.message)

    def run(self, task, button_promise):
        task_data = self.data
        if self.data is not None and not isinstance(self.data, dict):
            #print( f"TODO: data {self.data}")
            task_data = task.eval_code(self.data)

        if self.use_sub_task and self.label:
            #print(f"NEW TASK LABEL {self.message}")
            
            
            #
            # Block commands in a sub task is a strait jump to the button
            # The button should dedent to a yield_idle
            #
            #
            if self.is_block:
                #print(f"BLOCK NEW TASK LABEL {self.message} {self.label.name} {self.loc}")
                sub_task = task.start_sub_task(self.label, inputs=task_data, defer=True, active_cmd=self.loc+1)
            else:
                #print(f"NEW TASK LABEL {self.message} {self.label} {self.loc}")
                sub_task = task.start_sub_task(self.label, inputs=task_data, defer=True)

            sub_task.set_variable("BUTTON_PROMISE", button_promise)
            sub_task.tick_in_context()
            return sub_task
        elif self.label:
            #print(f"LABEL {self.label} {self.message}")
            task.push_inline_block(self.label)
            task.tick_in_context()
        else:
            #print(f"INLINE {self.path} {self.label_to_run} {task.active_label} {self.message}")
            task.push_inline_block(task.active_label,self.loc+1)
            task.tick_in_context()

        return None


