from __future__ import annotations
from functools import partial
import inspect
from .mast import *
import time
from ..agent import Agent, get_task_id
from ..helpers import FrameContext, format_exception
from ..futures import Promise, Waiter
from .label import get_fall_through
from .pollresults import PollResults

from .core_nodes.label import Label
from .core_nodes.inline_label import InlineLabel

from .mast_runtime_node import MastRuntimeNode
from .mast_globals import MastGlobals
    
    
    
class ChangeRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node):
        self.task = task
        self.node = node
        self.value = task.eval_code(node.value) 
        self.node_label = task.active_label

    def test(self):
        prev = self.value
        self.value = self.task.eval_code(self.node.value) 
        return prev!=self.value
        

    def poll(self, mast:Mast, task:MastAsyncTask, node):
        if node.await_node and node.await_node.dedent_loc:
            task.jump(self.node_label,node.await_node.dedent_loc)
            return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN





class PushData:
    def __init__(self, label, active_cmd, data=None, resume_node=None):
        self.label = label
        self.active_cmd = active_cmd
        self.data = data
        self.runtime_node = resume_node


class MastTicker:
    def __init__(self, task, main):
        self.done = False
        self.runtime_node = None
        self.last_poll_result = None
        self.active_label = None
        self.pop_on_jump = 0
        self.pending_pop = None
        self.pending_jump = None
        self.main = main
        self.task = task
        

    def end(self):
        #self.last_poll_result = PollResults.OK_END
        self.done = True


    def jump(self, label = "main", activate_cmd=0):
        # if self.pending_jump:
        #     print("PENDING")
        self.pending_jump = (label,activate_cmd)

        while self.pop_on_jump>0:
            # if this is a jump and there are tested push
            # get back to the main flow
            self.pop_on_jump-=1
            push_data = self.task.label_stack.pop()
            
    
    
    def do_jump(self, label = "main", activate_cmd=0):
        # Should call leave, but inline might trigger 
        # so don't do it until post 1.0
        ### self.call_leave()
        if label == "END" or label is None:
            self.active_cmd = 0
            self.runtime_node = None
            self.last_poll_result = PollResults.OK_END
            self.done = True
        else:
            if isinstance(label, str): 
                label_runtime_node = None
                active_node = self.main.mast.labels.get(self.active_label)
                if active_node is not None:
                    sub_label = active_node.labels.get(label)
                    if sub_label is not None:
                        #
                        # Must set label back to true label, not inline
                        #
                        label = self.active_label
                        activate_cmd = sub_label.loc

                label_runtime_node = self.main.mast.labels.get(label)
            elif isinstance(label, InlineLabel):
                label_runtime_node = self.main.mast.labels.get(self.active_label)
                activate_cmd=label.loc+1
            else:
                label_runtime_node = label
                label = label_runtime_node.name

            if label_runtime_node is not None:
                #
                #
                # Why is this here?
                #  Why remove the assignments 
                # Looking to remove or move to known place where Main Ends
                #
                #if self.active_label == "main":
                #    self.main.mast.prune_main()
                    
                self.cmds = label_runtime_node.cmds
                self.active_label = label
                self.active_cmd = activate_cmd
                self.runtime_node = None
                self.done = False
                #
                # This is for sub tasks so the can run again
                #
                self.last_poll_result = PollResults.OK_JUMP
                self.next()
            else:
                self.runtime_error(f"""Jump to label "{label}" command {activate_cmd} not found""")
                self.active_cmd = 0
                self.runtime_node = None
                self.done = True

    def do_resume(self, label, activate_cmd, runtime_node):
        label_runtime_node = self.main.mast.labels.get(label)
        if label_runtime_node is not None:
            self.cmds = self.main.mast.labels[label].cmds
            self.active_label = label
            self.active_cmd = activate_cmd
            self.runtime_node = runtime_node
            self.done = False
        else:
            self.runtime_error(f"""Jump to label "{label}" not found""")
            self.active_cmd = 0
            self.runtime_node = None
            self.done = True
    def push_label(self, label, activate_cmd=0, data=None):
        if self.active_label:
            pending_push = PushData(self.active_label, self.active_cmd, data)
            self.task.label_stack.append(pending_push)
        self.jump(label, activate_cmd)
    def push_inline_block(self, label, activate_cmd=0, data=None):
        #
        # This type of push resumes running the same runtime node 
        # that was active when the push occurred
        # This done by Buttons, Dropdown and event
        #
        push_data = PushData(self.active_label, self.active_cmd, data, self.runtime_node)
        self.task.label_stack.append(push_data)
        self.pop_on_jump += 1
        self.pending_jump = (label,activate_cmd)
        #self.jump(label, activate_cmd)



    def pop_label(self, inc_loc=True, true_pop=False):
        if len(self.task.label_stack)>0:
            #
            # Actual Pop was called in an inline block
            # So unwind the inline_blocks
            #
            if true_pop:
                while self.pop_on_jump>0:
                    # if this is a jump and there are tested push
                    # get back to the main flow
                    self.pop_on_jump-=1
                    push_data = self.task.label_stack.pop()
            elif self.pop_on_jump >0:
                self.pop_on_jump-=1
                # push_data: PushData
                # push_data = self.task.label_stack.pop()
                # return
            push_data: PushData
            push_data = self.task.label_stack.pop()
            if self.pending_jump is None:
                if inc_loc:
                    # TREAT THIS LIKE A JUMP
                    # I think this is a True POP in an inline
                    # So don't resume
                    self.pending_pop = (push_data.label, push_data.active_cmd+1, None)
                else:
                    #
                    # We didn't inc so the hope is to resume 
                    #
                    self.pending_pop = (push_data.label, push_data.active_cmd, push_data.runtime_node)
    def tick(self):
        cmd = None
        is_sub_task = self.task.is_sub_task

        try:
            if self.done:
                # should unschedule
                if is_sub_task:
                    return PollResults.FAIL_END
                return PollResults.OK_END

            count = 0
            while not self.done:
                if self.pending_jump:
                    jump_data = self.pending_jump
                    self.pending_jump = None
                    # Jump takes precedence
                    self.pending_pop = None
                    self.do_jump(*jump_data)
                elif self.pending_pop:
                    # Pending jump trumps pending pop
                    pop_data = self.pending_pop
                    self.pending_pop = None
                    if pop_data[2] is not None:
                        self.do_resume(*pop_data)
                    else:    
                        self.do_jump(pop_data[0], pop_data[1])

                if self.last_poll_result == PollResults.OK_IDLE:
                    return PollResults.OK_IDLE
                
                count += 1
                # avoid tight loops
                if count > 100000:
                    print(f"Mast Tick Threshold {self.active_label} possible performance loss")

                    if self.runtime_node is not None:
                        print(f"running {self.runtime_node.__class__}")
                        

                    this_cmd = self.cmds[self.active_cmd]
                    print(f"Mast command {this_cmd.__class__} {this_cmd.line_num}")
                    print(f"code  {this_cmd.line}")
                    break

                if self.runtime_node:
                    cmd = self.cmds[self.active_cmd]
                    # Purged Assigned are seen as Comments
                    if cmd.__class__== "Comment":
                        self.next()
                        continue
                    result = self.runtime_node.poll(self.main.mast, self.task, cmd)
                    match result:
                        case PollResults.OK_ADVANCE_TRUE:
                            self.last_poll_result = result
                            self.next()
                        case PollResults.OK_YIELD:
                            if self.task.yields_once:
                                self.done = True
                                self.last_poll_result = PollResults.OK_YIELD
                                return PollResults.OK_YIELD
                            
                            self.last_poll_result = result
                            self.next()
                            break
                        case PollResults.OK_ADVANCE_FALSE:
                            self.last_poll_result = result
                            self.next()
                        case PollResults.OK_END:
                            self.last_poll_result = result
                            self.done = True
                            return PollResults.OK_END
                        case PollResults.OK_IDLE:
                            self.last_poll_result = result
                            return PollResults.OK_IDLE
                        case PollResults.FAIL_END:
                            self.last_poll_result = result
                            self.done = True
                            return PollResults.FAIL_END

                        case PollResults.OK_RUN_AGAIN:
                            self.last_poll_result = result
                            break
                        case PollResults.OK_JUMP:
                            self.last_poll_result = result
                            continue
                        case _:
                            self.last_poll_result = result
                            break
            return PollResults.OK_RUN_AGAIN
        except BaseException as err:
            self.main.runtime_error(str(err))
            return PollResults.OK_END

    def get_runtime_error_info(self, rte):
        s = "mast RUNTIME ERROR\n"
        cmd = None 
        if self.runtime_node:
            cmd = self.cmds[self.active_cmd]
        if cmd is None:
            s += f"\n      mast label: {self.active_label}"
        else:
            file_name = Mast.get_source_file_name(cmd.file_num)
            s += f"\n      line: {cmd.line_num} in file: {file_name}"
            s += f"\n      label: {self.active_label}"
            s += f"\n      loc: {cmd.loc} cmd: {cmd.__class__.__name__}\n"
            if cmd.line:
                s += f"\n===== code ======\n\n{cmd.line}\n\n==================\n"
            else:
                s += "\nNOTE: to see code Set Mast.include_code to True is script.py only during development.\n\n"
        s += '\n'+rte
        return s
    
    def get_active_node(self):
        if self.cmds is None:
            return None
        if self.active_cmd >= len(self.cmds):
            return None
        return self.cmds[self.active_cmd]

    def runtime_error(self, rte):
        cmd = None
        s = self.get_runtime_error_info(rte)
        logger = logging.getLogger("mast.runtime")
        logger.error(s)

        self.main.runtime_error(s)
        self.done = True

    def call_leave(self):
        if self.runtime_node:
            cmd = self.cmds[self.active_cmd]
            self.runtime_node.leave(self.main.mast, self.task, cmd)
            self.runtime_node = None


    def next(self):
        try:
            if self.runtime_node:
                self.call_leave()
                #cmd = self.cmds[self.active_cmd]
                self.active_cmd += 1
            
            if self.active_cmd >= len(self.cmds):
                # move to the next label
                #
                # The first time Main is run, all shared 
                # Assignment should be purged
                # to avoid multiple assignments
                #
                self.main.mast.prune_main()

                active = self.main.mast.labels.get(self.active_label)
                next = active.next
                if next is None:
                    #if not self.task.is_sub_task:
                    self.done = True
                    return False
                return self.jump(next.name)
                
            
            cmd = self.cmds[self.active_cmd]
            runtime_node_cls = self.main.nodes.get(cmd.__class__.__name__, MastRuntimeNode)
            
            self.runtime_node = runtime_node_cls()
            self.runtime_node.enter(self.main.mast, self.task, cmd)
        except BaseException as err:
            self.main.runtime_error(str(err))
        
        return True


class PyTicker():
    def __init__(self, task) -> None:
        super().__init__()
        self.stack=[]
        self.delay_time = None
        self.task = task
        self.pending_jump = None
        self.pending_pop = None
        self.pop_on_jump = 0
        self.current_gen = None
        self.last_poll_result = None
        self.done = False
        self.fall_through_label = None



    def end(self):
        self.last_poll_result = PollResults.OK_END
        self.done = True

    @property
    def active_label(self):
        label = "PyMAST code"
        if self.current_gen is not None:
            label = self.current_gen
        return label
            

    def tick(self):
        # Keep running until told to defer or you've jump 100 time
        # Arbitrary number
        throttle = 0
        
        while not self.done and throttle < 100:
            throttle += 1
            if self.pending_jump:
                res = self.do_jump()
                self.pending_pop = None
                
            elif self.pending_pop:
                # Pending jump trumps pending pop
                self.current_gen = self.pending_pop
                self.pending_pop = None

            
            gen = self.current_gen
            # It is possible that the label
            # did not Yield, which is OK just End 
            if gen is None:
                #self.last_poll_result = PollResults.OK_END
                self.end()
                return self.last_poll_result
            
            #self.last_poll_result = None
            gen_done = True
            fallthrough = True
            self.last_poll_result = None
            for res in gen:
                is_new_jump = False
                if res is None:
                    gen_done = True
                    break
                gen_done = False
                fallthrough - False
                if res is not None:
                    self.last_poll_result = res
                if res == PollResults.OK_RUN_AGAIN:
                    return self.last_poll_result
                elif res == PollResults.OK_JUMP:
                    break
                elif res == PollResults.OK_END:
                    gen_done = True
                    fallthrough = False
                    self.end()
                    break
                elif isinstance(res, Waiter):
                    if self.current_gen is not None:
                        self.stack.append(self.current_gen)
                    self.current_gen = res.get_waiter()

                    self.last_poll_result = PollResults.OK_JUMP
                    break

                
            if self.last_poll_result == PollResults.OK_JUMP:
                continue

            if self.last_poll_result == PollResults.OK_END:
                continue
            if self.last_poll_result == PollResults.FAIL_END:
                continue
            
            if gen_done:
                #
                # The generator finished without jumping or popping
                #
                #
                # This could be because the handler did not yield
                #
                # If there is a pending Jump DON't pop
                #
                    
                
                if self.pending_jump is not None:
                #
                # jump was called and the generate just never yielded
                    pass
                elif len(self.stack)>0:
                    # if there things on the stack treat this as a pop
                    # Pop wasn't called
                    # assuming it should pop
                    self.last_poll_result = self.pop()
                elif fallthrough and self.fall_through_label:
                    # set pending jump
                    self.jump(self.fall_through_label)
                else:
                    self.current_gen = self.pending_pop
                    if self.current_gen is None:
                        self.end()
                        self.last_poll_result = PollResults.OK_END
                    else:
                        self.last_poll_result = PollResults.OK_JUMP
                    return self.last_poll_result
        return self.last_poll_result

    def do_jump(self):
        label = self.pending_jump
        self.pending_jump = None
        gen, res = self.get_gen(label)
        self.current_gen = gen
        # if gen is None:
        #     print("Get_gen failed?")
        return res

    def get_gen(self, label):
        gen = None
        self.fall_through_label = None
        res = PollResults.FAIL_END
        
            
        if inspect.ismethod(label):
            self.fall_through_label = get_fall_through(label)
            gen = label()
            res = PollResults.OK_JUMP
        elif inspect.isfunction(label):
            self.fall_through_label = get_fall_through(label)
            gen = label()
            res = PollResults.OK_JUMP
        elif isinstance(label, partial):
            #
            # Not sure this will work right?
            #
            self.fall_through_label = get_fall_through(label)
            gen = label()
            res = PollResults.OK_JUMP
        elif label == self.current_gen:
            res = PollResults.OK_ADVANCE_TRUE
        else:
            print(f"Unexpected label type: not function, method or partial {label} {label.__class__}")
        
        return (gen, res)
    
    def jump(self, label):
        while self.pop_on_jump>0:
            #self.pop_on_jump -= 1
            #self.stack.pop()
            self.pop()
        self.pending_jump = label
        # jump cancels out pops
        self.pending_pop = None
        return PollResults.OK_JUMP

    def push(self, label):
        if self.current_gen is not None:
            self.stack.append(self.current_gen)
        return self.jump(label)
    
    def quick_push(self, func):
        # The function proviced is expected to pop
        if self.current_gen is not None:
            self.stack.append(self.current_gen)
        #gen, res = self.get_gen(func)
        self.pending_jump = func 
        return PollResults.OK_JUMP
    
    def get_active_node(self):
        return self.current_gen
    
    def push_inline_block(self, label, _loc=0, data=None):
        if self.current_gen is not None:
            self.stack.append(self.current_gen)
        self.pending_jump = label
        self.pending_pop = None
        self.pop_on_jump += 1
        return PollResults.OK_JUMP

    def pop(self):
        if len(self.stack) > 0:
            if self.pop_on_jump >0:
                self.pop_on_jump-=1
            self.pending_pop = self.stack.pop()
            return PollResults.OK_JUMP
        return PollResults.FAIL_END
    
    def pop_label(self, inc_loc=True, true_pop=False):
        pass
    

    def get_runtime_error_info(self, rte):
        s = "mast python RUNTIME ERROR\n" 
        s += f"\n===== code ======\n\n{rte}\n\n==================\n"
        s += '\n'
        return s

    def runtime_error(self, rte):
        cmd = None
        s = self.get_runtime_error_info(rte)
        logger = logging.getLogger("mast.runtime")
        logger.error(s)

        self.main.runtime_error(s)
        self.done = True



class MastAsyncTask(Agent, Promise):
    main: 'MastScheduler'
    dependent_tasks = {}
    
    def __init__(self, main: 'MastScheduler', inputs=None, name= None):
        super().__init__()
        self.id = get_task_id()
        
        #self.runtime_node = None
        self.main= main
        self.name = name
        # if name:
        #     print(f"Creating task {name}")
        #self.vars= inputs if inputs else {}
        if inputs:
            for k in inputs:
                self.set_inventory_value(k, inputs[k])
            #self.inventory.collections |= inputs
        
        self.set_inventory_value("mast_task", self)
        self.mast_ticker = MastTicker(self, main)
        self.py_ticker = PyTicker(self)
        self.active_ticker = self.mast_ticker
        self.label_stack = []
        self.yield_results = None
        self.yields_once = True
        self.is_sub_task = False
        self.sub_tasks = []
        self.root_task = self

        self.add()
        self.add_role("__MAST_TASK__")

        self.pending_on_change_items = []
        self.on_change_items = []
        # So far this is used only of on change processing
        self.is_gui_task = False


    def queue_on_change(self, runtime_node):
        if self.is_gui_task:
            self.pending_on_change_items.append(runtime_node)
        else:
            self.on_change_items.append(runtime_node)

    def run_on_change(self):
        for change in self.on_change_items:
            if change.test():
                change.run()
                return True
        for st in self.sub_tasks:
            if st.run_on_change():
                return True
        return False
            
    def swap_on_change(self):
        if self.is_gui_task:
            for item in self.on_change_items:
                item.dequeue()

            self.on_change_items= self.pending_on_change_items
        self.pending_on_change_items = []

    def emit_signal(self, name, sender_task, label_info, data):
        # if sender_task == self:
        # If this is needed add it to the data instead of skipping
        #     return
        if sender_task is not None and sender_task.done():
            return
        if self.done():
            return
        
        if label_info.server and not self.main.is_server:
            return
        

        if label_info.is_jump:
            st = self.start_task(label_info.label, data, defer=True)
            st.tick_in_context()
        else:
            self.push_inline_block(label_info.label, label_info.loc, data)
            self.tick_in_context()
        return
    
    #
    # Promise cancel
    #
    def cancel(self, msg=None):
        self.end()
        super().cancel(msg)
        self._canceled = True

    
    def end(self):
        # if self.name is not None:
        #     print(f"Task {self.name} called end")
        # else:
        #     print("Task called end")

        self.active_ticker.end()
        self.set_result(self.active_ticker.last_poll_result)
        #self.done = True
        return self.active_ticker.last_poll_result
    #
    # Override of Promise
    #
    # def done(self):
    #     return self.active_ticker.done
    
    @property
    def active_label(self):
        #
        # PyMast will fail on this
        #
        if self.active_ticker is None:
            return "main"
        return self.active_ticker.active_label

    @property
    def active_label_object(self):
        #
        # PyMast will fail on this
        #
        if self.active_ticker is None:
            return self.main.mast.labels.get("main")
        label = self.active_ticker.active_label
        if isinstance(label, str):
            return self.main.mast.labels.get(label)
        return label


    @property
    def is_observable(self):
        # Allows to yield multiple times
        self.yields_once = False


    @property
    def tick_result(self):
        return self.active_ticker.last_poll_result
    
    def poll(self):
        return self.tick_result
    
    def get_active_node(self):
        return self.active_ticker.get_active_node()
    
    def get_active_node_source_map(self):
        node= self.active_ticker.get_active_node()
        if node is None:
            return None
        file_num = node.file_num
        if file_num is None:
            return None
        if file_num>= len(Mast.source_map_files):
            return None
        return Mast.source_map_files[file_num]


    def get_symbols(self):
        if self.root_task != self:
            m1 = self.root_task.get_symbols()
        else:
            # m1 = self.main.mast.vars | self.main.vars
            #mast_inv = self.main.get_symbols()
            m1 = self.main.get_symbols()
            m1 =   m1 | self.inventory.collections 

        for st in self.label_stack:
            data = st.data
            # print(f"GET SYMBOLS {data}")
            if data is not None:
                m1 =   m1 | data
        # if self.redirect and self.redirect.data:
        #     m1 = self.redirect.data | m1
        return m1

    def set_value(self, key, value, scope):
        if self.root_task != self:
            return self.root_task.set_value(key, value, scope)
        if scope == Scope.SHARED: #self.main.set_value(key,value, scope) != Scope.UNKNOWN:
            # # self.main.mast.vars[key] = value
            Agent.SHARED.set_inventory_value(key, value)
            return scope
        elif scope == Scope.TEMP:
            self.set_inventory_value(key, value)
            return scope
        else:
            self.set_inventory_value(key, value)
            return scope

    def set_value_keep_scope(self, key, value):
        if self.root_task != self:
            return self.root_task.set_value_keep_scope(key, value)
        scoped_val = self.get_value(key, value)
        scope = scoped_val[1]
        if scope is None:
            scope = Scope.TEMP
        # elif scope == Scope.UNKNOWN:
        #     scope = Scope.NORMAL
        self.set_value(key,value, scope)

    def get_value(self, key, defa=None):
        if self.root_task != self:
            return self.root_task.get_value(key, defa)
        data = None
        # if self.redirect:
        #     data = self.redirect.data
        if len(self.label_stack) > 0:
            data = self.label_stack[-1].data
        if data is not None:
            val = data.get(key, None)
            if val is not None:
                return (val, Scope.TEMP)
        val = self.get_inventory_value(key, None)
        #val = self.vars.get(key, None)
        if val is not None:
            return (val, Scope.NORMAL)
        val = self.main.get_value(key, defa)
        if val[1] != Scope.UNKNOWN:
            return val
        return (defa, Scope.NORMAL)
    
    def get_scoped_value(self, key, defa, scope):
        if self.root_task != self:
            return self.root_task.get_scoped_value(key, defa, scope)
        if scope == Scope.SHARED:
            return self.main.get_scoped_value(key, defa)
        if scope == Scope.TEMP:
            data = None
            # if self.redirect:
            #     data = self.redirect.data
            if len(self.label_stack) > 0:
                data = self.label_stack[-1].data
            if data is not None:
                val = data.get(key, None)
                if val is not None:
                    return val
        val = self.get_inventory_value(key, None)
        return val
        

    def get_variable(self, key, default=None):
        value = self.get_value(key, default)
        return value[0]
    
    def are_variables_defined(self, keys):
        keys = keys.split(",")
        for key in keys:
            value = self.get_value(key, None)
            if value[1] == Scope.UNKNOWN:
                return False
        return True

        
    
    def set_variable(self, key, value):
        self.set_value_keep_scope(key,value)

    def get_shared_variable(self, key, default=None):
        return Agent.SHARED.get_inventory_value(key, default)
    
    def set_shared_variable(self, key, value):
        Agent.SHARED.set_inventory_value(key, value)


    def format_string(self, message):
        if message is None:
            return ""
        if isinstance(message, str):
            return message
        allowed = self.get_symbols()
        # logger = logging.getLogger("mast.story")
        # for k,v in allowed.items():
        #     if k == "myslot":
        #         logger.info(f"{k}: {v}")
        try:
            value = eval(message, {"__builtins__": MastGlobals.globals}, allowed)
            return value
        except BaseException as err:
            s =  f"FORMAT String error:\n\t f'{message}'\n"
            s += str(err)
            self.main.runtime_error(s)
        return ""
        
    
    def compile_and_format_string(self, value):
        if isinstance(value, str) and "{" in value:
            value = f'''f"""{value}"""'''
            code = compile(value, "<string>", "eval")
            value = self.format_string(code)
        return value



    def eval_code(self, code, end_on_exception=True):
        value = None
        try:
            allowed = self.get_symbols()
            value = eval(code, {"__builtins__": MastGlobals.globals}, allowed)
        except:
            err = format_exception("", "Mast eval level Runtime Error:")
            if end_on_exception:
                # self.runtime_error(f"Mast eval level Runtime Error:\n{err}")
                self.runtime_error(err)
                self.end()
            else:
                print(err)
        finally:
            pass
        return value

    def exec_code(self, code, vars, gbls):
        try:
            if vars is not None:
                allowed = vars | self.get_symbols()
            else:                
                allowed = self.get_symbols()
            if gbls is not None:
                g = MastGlobals.globals | gbls
            else:
                g = MastGlobals.globals
            exec(code, {"__builtins__": g}, allowed)
        except:
            #err = traceback.format_exc()
            #err = format_exception("", "Mast exec level Runtime Error:")
            #self.runtime_error("Mast exec level Runtime Error:\n")
            err = format_exception("", "Mast eval level Runtime Error:")
            self.runtime_error(err)
            self.end()
        finally:
            pass
        

    def start_task(self, label = "main", inputs=None, task_name=None, defer=False, inherit=True, unscheduled=False)->MastAsyncTask:
        # Sub task share data noe need to inherit
        if self.is_sub_task and self.root_task != self:
            return self.root_task.start_task(label, inputs, task_name, defer, unscheduled=unscheduled)
        # Inherit mean it inherits copies of the calling task's value
        if inherit:
            if inputs is not None:
                inputs = self.inventory.collections | inputs
            else:
                inputs = self.inventory.collections | {}
        return self.main.start_task(label, inputs, task_name, defer, unscheduled)
            
      
    
    def start_sub_task(self, label = "main", inputs=None, task_name=None, defer=False, active_cmd=0)->MastAsyncTask:
        #
        # Sub task share task data
        #
        if self.is_sub_task and self.root_task != self:
            return self.root_task.start_sub_task(label, inputs, task_name, defer, active_cmd)
        if inputs is not None:
            for k in inputs:
                self.set_inventory_value(k, inputs[k])
        t= MastAsyncTask(self.main, None, task_name)

        t.is_sub_task = True
        t.root_task = self
        if task_name is not None:
            t.set_value(task_name, t, Scope.NORMAL)
            
        t.jump(label,active_cmd)
        self.sub_tasks.append(t)
        if not defer:
            t.tick_in_context()
        return t
    
    def remove_sub_task(self, t):
        t.stop()

    def remove_all_sub_tasks(self):
        for t in self.sub_tasks():
            t.stop()

    
    def tick_in_context(self):
        _page = FrameContext.page
        _task = FrameContext.task

        FrameContext.page = self.main.page
        FrameContext.task = self
        res = self.tick()
        FrameContext.page = _page
        FrameContext.task = _task
        return res

    def tick_subtasks(self):
        _page = FrameContext.page
        FrameContext.page = self.main.page
        restore = FrameContext.task
        done = []
        
        for task in self.sub_tasks:
            if task.done():
                done.append(task)
                continue
            self.active_task = task
            FrameContext.task = task
            res = task.tick()
            FrameContext.task = None
            if res == PollResults.FAIL_END:
                done.append(task)
            elif task.done():
                done.append(task)
        FrameContext.task = restore
        FrameContext.page = _page
        
        if len(done):
            for rem in done:
                if rem in self.sub_tasks:
                    self.sub_tasks.remove(rem)
            done = []

    def jump_restart_task(self, label = "main", activate_cmd=0):
        """
        Used by the mission runner to run multiple labels
        """
        self.set_result(None)
        self.active_ticker.done = False
        self.jump(label, activate_cmd)
        self.tick_in_context()


    def tick(self):
        # if self.name is not None:
        #     print(f"ticking {self.name}")
        restore = FrameContext.task
        page = FrameContext.page
        FrameContext.task = self
        FrameContext.page = self.main.page
        res = self.active_ticker.tick()
        FrameContext.task = restore
        FrameContext.page = page
        if self.active_ticker.done:
            if self.active_ticker.last_poll_result == PollResults.OK_YIELD:
                self.set_result(self.yield_results)
            else:
                self.set_result(self.active_ticker.last_poll_result)
        self.tick_subtasks()
        return res
        

    def jump(self, label = "main", activate_cmd=0, respect_inline=False):
        if isinstance(label, str) or isinstance(label, Label):
            self.active_ticker = self.mast_ticker
            if respect_inline:
                return self.mast_ticker.do_jump(label, activate_cmd)
            return self.mast_ticker.jump(label, activate_cmd)
        else:
            self.active_ticker = self.py_ticker
            return self.py_ticker.jump(label)
        

    def push_label(self, label, activate_cmd=0, data=None):
        self.active_ticker.push_label(label, activate_cmd, data)

    def push_inline_block(self, label, activate_cmd=0, data=None):
        self.active_ticker.push_inline_block(label, activate_cmd, data)

    def pop_label(self, inc_loc=True, true_pop=False):
        self.active_ticker.pop_label(inc_loc, true_pop)

    def get_runtime_error_info(self, rte):
        # avoid duplicate info calls
        if "mast RUNTIME ERROR" in rte:
            return rte
        
        return self.active_ticker.get_runtime_error_info(rte)

    def runtime_error(self, msg):
        
        self.active_ticker.runtime_error(msg)

        
    @classmethod
    def add_dependency(cls, id, task):
        the_set = MastAsyncTask.dependent_tasks.get(id, set())
        the_set.add(task)
        MastAsyncTask.dependent_tasks[id]=the_set

    @classmethod
    def stop_for_dependency(cls, id):
        the_set = MastAsyncTask.dependent_tasks.get(id, set())
        for task in the_set:
            task.end()
        MastAsyncTask.dependent_tasks.pop(id, None)





class MastScheduler(Agent):
    

    def __init__(self, mast: Mast, overrides=None):
        super().__init__()
        # Schedulers use task Id
        self.id = get_task_id()
        self.add()
        self.add_role("__MAST_SCHEDULER__")
        if overrides is None:
            overrides = {}
        self.nodes = MastRuntimeNode.nodes | overrides
        self.mast = mast
        self.tasks = []
        self.name_tasks = {}
        self.inputs = None
        #self.vars = {"mast_scheduler": self}
        self.set_inventory_value("mast_scheduler", self)
        self.done = []
        self.mast.add_scheduler(self)
        self.test_clock = 0
        self.active_task = None
        self.page = None
        
    def is_server(self):
        return False

    def runtime_error(self, message):
        print(f"mast level runtime error:\n {message}")
        pass

    def get_seconds(self, clock):
        """ Gets time for a given clock default is just system """
        if clock == 'test':
            self.test_clock += 0.2
            return self.test_clock
        return time.time()
    
    def set_inventory_value(self, collection_name, value):
        return super().set_inventory_value(collection_name, value)

    def get_inventory_value(self, collection_name, default=None):
        v = super().get_inventory_value(collection_name, default)
        return v

    def _start_task(self, label = "main", inputs=None, task_name=None)->MastAsyncTask:
        #if self.inputs is None:
        #    self.inputs = inputs
        label_name = label
        if isinstance(label, str):
            label =  self.mast.labels.get(label, None)
        if label is None:
            raise Exception(f"Calling undefined label {label_name}")
        # Add Meta data, but the task and passed data overrides it
        if hasattr(label, "inventory"):
            if inputs is None:
                inputs = label.inventory.collections.copy()
            else:
                inputs = label.inventory.collections.copy() | inputs
        t= MastAsyncTask(self, inputs, task_name)
        return t


    def start_task(self, label = "main", inputs=None, task_name=None, defer=False, unscheduled=False)->MastAsyncTask:
        t = self._start_task(label, inputs, task_name)
        if task_name is not None:
            t.set_value(task_name, t, Scope.NORMAL)

        restore = FrameContext.task
        FrameContext.task = t
        t.jump(label)
        FrameContext.task = restore
        if not unscheduled:
            self.tasks.append(t)
        if not defer:
            self.on_start_task(t)

        return t

    def on_start_task(self, t):
        self.active_task = t
        t.tick()
    def cancel_task(self, name):
        if isinstance(name, str):
            data = self.active_task.get_variable(name)
        else:
            data = name
        # Assuming its OK to cancel none
        if data is not None:
            data.cancel()
            self.done.append(data)

    def is_running(self):
        if len(self.tasks) == 0:
            return False
        return True

    def get_value(self, key, defa=None):
        """
        MastStoryScheduler completely overrided this so changes here should go there
        """
        val = MastGlobals.globals.get(key, None) # don't use defa here
        if val is not None:
            return (val, Scope.SHARED)
        # Check shared
        val = Agent.SHARED.get_inventory_value(key, None) # don't use defa here
        if val is not None:
            return (val, Scope.SHARED)
                
        val = self.get_inventory_value(key, None) # now defa make sense
        if val is not None:
            #TODO: Should this no longer be NORMAL
            return (val, Scope.NORMAL) # NORMAL is the same as TASK
        return (val, Scope.UNKNOWN)
    
    def get_symbols(self):
        mast_inv = Agent.SHARED.inventory.collections
        m1 = mast_inv | self.inventory.collections
        return m1

    
    def set_value(self, key, value, scope):
        if scope == Scope.SHARED:
            # self.main.mast.vars[key] = value
            Agent.SHARED.set_inventory_value(key, value)
            return scope
        return Scope.UNKNOWN

    def get_variable(self, key, defa=None):
        val = self.get_value(key, defa)
        return val[0]
    
    def set_variable(self, key):
        val = self.get_value(key)
        return val[0]
    
    def tick(self):
        restore = FrameContext.task

        FrameContext.mast = self.mast

        for task in self.tasks:
            self.active_task = task
            FrameContext.task = task
            
            res = task.tick()
            FrameContext.task = None
            if res == PollResults.OK_END:
                self.done.append(task)
            elif task.done():
                self.done.append(task)
        FrameContext.task = restore
        
        if len(self.done):
            for rem in self.done:
                if rem in self.tasks:
                    self.tasks.remove(rem)
            self.done = []

        for task in self.tasks:
            task.run_on_change()

        if len(self.tasks):
            return True
        else:
            return False


