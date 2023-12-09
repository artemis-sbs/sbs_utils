from __future__ import annotations
from enum import IntEnum
from functools import partial
import inspect
from typing import List
from .mast import *
import time
import traceback
from ..agent import Agent, get_task_id
from ..helpers import FrameContext
from ..futures import Promise, Waiter, AwaitBlockPromise
from .label import get_fall_through
from .pollresults import PollResults


class MastRuntimeNode:
    def enter(self, mast, scheduler, node):
        pass
    def leave(self, mast, scheduler, node):
        pass
    
    def poll(self, mast, scheduler, node):
        return PollResults.OK_ADVANCE_TRUE


# class MastAsyncTask:
#     pass

class EndRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:End):
        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
        return PollResults.OK_END

class ReturnIfRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:ReturnIf):
        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
        task.pop_label(False, False)
        return PollResults.OK_JUMP

class FailRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:Fail):
        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
    
        return PollResults.FAIL_END
    
class YieldRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:Yield):
        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
        if node.result is None:
            return PollResults.OK_YIELD
        if node.result.lower() == 'fail':
            return PollResults.FAIL_END
        if node.result.lower() == 'success':
            return PollResults.OK_END
        return PollResults.OK_RUN_AGAIN
    
class ChangeRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Change):
        self.task = task
        self.node = node
        self.value = task.eval_code(node.value) 

    def test(self):
        prev = self.value
        self.value = self.task.eval_code(self.node.value) 
        return prev!=self.value
        

    def poll(self, mast:Mast, task:MastAsyncTask, node: Change):
        if node.await_node and node.await_node.end_await_node:
            task.jump(task.active_label,node.await_node.end_await_node.loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN




class AssignRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task:MastAsyncTask, node:Assign):
        #try:
        value = task.eval_code(node.code)
        start = task.get_variable(node.lhs) 
        match node.oper:
            case Assign.EQUALS:
                pass
            case Assign.INC:
                value = start + value
            case Assign.DEC:
                value = start - value
            case Assign.MUL:
                value = start * value
            case Assign.MOD:
                value = start % value
            case Assign.DIV:
                value = start / value
            case Assign.INT_DIV:
                value = start // value


        if "." in node.lhs or "[" in node.lhs:
            task.exec_code(f"""{node.lhs} = __mast_value""",{"__mast_value": value}, None )
            
        elif node.scope: 
            task.set_value(node.lhs, value, node.scope)
        else:
            task.set_value_keep_scope(node.lhs, value)
            
        # except:
        #     task.main.runtime_error(f"assignment error {node.lhs}")
        #     return PollResults.OK_END

        return PollResults.OK_ADVANCE_TRUE

class PyCodeRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task:MastAsyncTask, node:PyCode):
        def export(cls):
            add_to = task.main.inventory.collections
            def decorator(*args, **kwargs):
                # if 'task' in inspect.signature(cls).parameters:
                #     kwargs['task'] = task
                #add_to[cls.__name__] = cls
                return cls(*args, **kwargs)
            add_to[cls.__name__] = decorator
            return decorator

        def export_var(name, value, shared=False):
            if shared:
                #
                #task.main.mast.vars[name] = value
                Agent.SHARED.set_inventory_value(name, value, None)
            else:
                # task.main.vars[name] = value
                task.main.set_inventory_value(name, value, None)
                




        task.exec_code(node.code,{"export": export, "export_var": export_var}, None )
        return PollResults.OK_ADVANCE_TRUE

class FuncCommandRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task:MastAsyncTask, node:FuncCommand):
        self.value = task.eval_code(node.code)
        self.is_await = node.is_await
        if self.is_await and not isinstance(self.value, Promise):
            self.is_await = False

    def poll(self, mast, task:MastAsyncTask, node:FuncCommand):
        #
        # await the promise to complete
        #
        if node.is_await and self.value is not None and not self.value.done():
            return PollResults.OK_RUN_AGAIN
        return PollResults.OK_ADVANCE_TRUE

class JumpRuntimeNode(MastRuntimeNode):
    def poll(self, mast:Mast, task:MastAsyncTask, node:Jump):
        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
            
        if node.push:
            args = node.args
            if node.args is not None:
                args = task.eval_code(node.args)
            task.push_label(node.label, data=args)
        elif node.pop_jump:
            task.pop_label(True,True)
            task.jump(node.label)
        elif node.pop_push:
            task.pop_label(True,True)
            task.push_label(node.label)
        elif node.pop:
            task.pop_label(True,True)
        else:
            task.jump(node.label)
        return PollResults.OK_JUMP



class LoopStartRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task:MastAsyncTask, node:LoopStart):
        #scoped_val = task.get_scoped_value(node.name, Scope.TEMP, None)
        scoped_cond = task.get_scoped_value(node.name+"__iter", None, Scope.TEMP)
        # The loop is running if cond
        if scoped_cond is None:
            # set cond to true to show we have initialized
            # setting to -1 to start it will be made 0 in poll
            if node.is_while:
                task.set_value(node.name, -1, Scope.TEMP)
                task.set_value(node.name+"__iter", True, Scope.TEMP)
            else:
                value = task.eval_code(node.code)
                try:
                    _iter = iter(value)
                    task.set_value(node.name+"__iter", _iter, Scope.TEMP)
                except TypeError:
                    task.set_value(node.name+"__iter", False, Scope.TEMP)

    def poll(self, mast, task, node:LoopStart):
        # All the time if iterable
        # Value is an index
        current = task.get_scoped_value(node.name, None, Scope.TEMP)
        scoped_cond = task.get_scoped_value(node.name+"__iter", None, Scope.TEMP)
        if node.is_while:
            current += 1
            task.set_value(node.name, current, Scope.TEMP)
            if node.code:
                value = task.eval_code(node.code)
                if value == False:
                    inline_label = f"{task.active_label}:{node.name}"
                    # End loop clear value
                    task.set_value(node.name, None, Scope.TEMP)
                    task.set_value(node.name+"__iter", None, Scope.TEMP)
                    task.jump(task.active_label, node.end.loc+1)
                    return PollResults.OK_JUMP

            
        elif scoped_cond == False:
            print("Possible badly formed for")
            # End loop clear value
            task.set_value(node.name, None, Scope.TEMP)
            task.set_value(node.name+"__iter", None, Scope.TEMP)
            task.jump(task.active_label, node.end.loc+1)
            #task.jump_inline_end(inline_label, False)
            return PollResults.OK_JUMP
        else:
            try:
                current = next(scoped_cond)
                task.set_value(node.name, current, Scope.TEMP)
            except StopIteration:
                # done iterating jump to end
                task.set_value(node.name, None, Scope.TEMP)
                task.set_value(node.name+"__iter", None, Scope.TEMP)
                task.jump(task.active_label, node.end.loc+1)
                return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

class LoopEndRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:LoopEnd):
        if node.loop == True:
            task.jump(task.active_label, node.start.loc)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

class LoopBreakRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task:MastAsyncTask, node:LoopBreak):
        scoped_val = task.get_value(node.start.name, None)
        index = scoped_val[0]
        scope = scoped_val[1]
        if index is None:
            scope = Scope.TEMP
        self.scope = scope

    def poll(self, mast, task, node:LoopBreak):
        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
            
        if node.op == 'break':
            #task.jump_inline_end(inline_label, True)
            task.set_value(node.start.name, None, self.scope)
            task.set_value(node.start.name+"__iter", None, Scope.TEMP)
            task.jump(task.active_label, node.start.end.loc+1)
            # End loop clear value
            
            return PollResults.OK_JUMP
        elif node.op == 'continue':
            task.jump(task.active_label, node.start.loc)
            #task.jump_inline_start(inline_label)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

class IfStatementsRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:IfStatements):
        """ """
        # if this is THE if, find the first true branch
        if node.if_op == "if":
            activate = self.first_true(task, node)
            if activate is not None:
                task.jump(task.active_label, activate+1)
                return PollResults.OK_JUMP
        else:
            # Everything else jumps to past the endif
            activate = node.if_node.if_chain[-1]
            task.jump(task.active_label, activate+1)
            return PollResults.OK_JUMP

    def first_true(self, task: MastAsyncTask, node: IfStatements):
        cmd_to_run = None
        for i in node.if_chain:
            test_node = task.mast_ticker.cmds[i]
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

class MatchStatementsRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:MatchStatements):
        """ """
        # if this is THE if, find the first true branch
        if node.op == "match":
            activate = self.first_true(task, node)
            if activate is not None:
                task.jump(task.active_label, activate+1)
                return PollResults.OK_JUMP
        else:
            # Everything else jumps to past the endif
            activate = node.match_node.chain[-1]
            task.jump(task.active_label, activate+1)
            return PollResults.OK_JUMP

    def first_true(self, task: MastAsyncTask, node: MatchStatements):
        cmd_to_run = None
        for i in node.chain:
            test_node = task.mast_ticker.cmds[i]
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


    
# class BehaviorRuntimeNode(MastRuntimeNode):
#     def enter(self, mast, task: MastAsyncTask, node:Behavior):
#         vars = {} | task.inventory.collections if node.labels is not None else None
#         if node.code:
#             inputs = task.eval_code(node.code)
#             vars = vars | inputs
#         if isinstance(node.labels, list):
#             if node.sequence:
#                 task = task.main.start_sequence_task(node.labels, vars, task_name=node.name, conditional=node.conditional)
#             elif node.fallback:
#                 task = task.main.start_fallback_task(node.labels, vars, task_name=node.name, conditional=node.conditional)

#         self.task = task # if node.is_await else None
#         self.timeout = FrameContext.sim_seconds + (node.minutes*60+node.seconds)
        
#     def poll(self, mast, task: MastAsyncTask, node:Behavior):
#         if self.task:
#             if not self.task.done():
#                 return PollResults.OK_RUN_AGAIN
#             if node.is_yield:
#                 return self.task.tick_result
#             if node.fail_label and self.task.done() and self.task.tick_result == PollResults.FAIL_END:
#                 task.jump(task.active_label,node.fail_label.loc+1)
#             elif node.until == "success" and self.task.done():
#                 if  self.task.tick_result == PollResults.FAIL_END:
#                     return self.task.rewind()
#             elif node.until == "fail" and self.task.done():
#                 if  self.task.tick_result != PollResults.FAIL_END:
#                     return self.task.rewind()
#         if node.timeout_label and self.timeout < FrameContext.sim_seconds:
#             task.jump(task.active_label,node.timeout_label.loc+1)

#         return PollResults.OK_ADVANCE_TRUE


# class TimeoutRuntimeNode(MastRuntimeNode):
#     def poll(self, mast, task: MastAsyncTask, node:Timeout):
#         # if you run into this its from another sub-label
#         if node.await_node and node.await_node.end_await_node:
#             task.jump(task.active_label,node.await_node.end_await_node.loc+1)

# class AwaitFailRuntimeNode(MastRuntimeNode):
#     def poll(self, mast, task: MastAsyncTask, node:AwaitFail):
#         # if you run into this its from another sub-label
#         if node.await_node and node.await_node.end_await_node:
#             task.jump(task.active_label,node.await_node.end_await_node.loc+1)


class EndAwaitRuntimeNode(MastRuntimeNode):
    pass

class AwaitRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: Await):
        value = task.eval_code(node.code)
        self.promise = None
        if isinstance(value, Promise):
            self.promise = value
            self.promise.inlines = node.inlines
            self.promise.buttons = node.buttons


    def poll(self, mast:Mast, task:MastAsyncTask, node: Await):
        if self.promise:
            if self.promise.done():
                return PollResults.OK_ADVANCE_TRUE
            else:
                return PollResults.OK_RUN_AGAIN

        value = task.eval_code(node.code)
        if value:
            return PollResults.OK_ADVANCE_TRUE

        return PollResults.OK_RUN_AGAIN


class AwaitInlineLabelRuntimeNode(MastRuntimeNode):
    def poll(self, mast:Mast, task:MastAsyncTask, node: Button):
        #task.redirect_pop_label(True)
        #return PollResults.OK_JUMP
        if node.await_node and node.await_node.end_await_node:
            #print(f"Button return {task.active_label} {node.await_node.end_await_node.loc+1}")
            task.jump(task.active_label,node.await_node.end_await_node.loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE


class ButtonRuntimeNode(MastRuntimeNode):
    def poll(self, mast:Mast, task:MastAsyncTask, node: Button):
        #task.redirect_pop_label(True)
        #return PollResults.OK_JUMP
        if node.await_node and node.await_node.end_await_node:
            #print(f"Button return {task.active_label} {node.await_node.end_await_node.loc+1}")
            task.jump(task.active_label,node.await_node.end_await_node.loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE




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
        self.pending_push = None
        self.main = main
        self.task = task

    def end(self):
        #self.last_poll_result = PollResults.OK_END
        self.done = True


    def jump(self, label = "main", activate_cmd=0):
        self.pending_jump = (label,activate_cmd)
        while self.pop_on_jump>0:
            # if this is a jump and there are tested push
            # get back to the main flow
            self.pop_on_jump-=1
            push_data = self.task.label_stack.pop()
            #print(f"POP: {push_data.label}")
    
    
    def do_jump(self, label = "main", activate_cmd=0):
           
        if label == "END" or label is None:
            self.active_cmd = 0
            self.runtime_node = None
            self.done = True
        else:
            # label_runtime_node = Agent.SHARED.get_inventory_value(label)
            if isinstance(label, str): 
                label_runtime_node = self.main.mast.labels.get(label)
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
                self.next()
            else:
                self.runtime_error(f"""Jump to label "{label}" not found""")
                self.active_cmd = 0
                self.runtime_node = None
                self.done = True

    def do_resume(self, label, activate_cmd, runtime_node):
        #print("I am RESUMING")
        label_runtime_node = self.main.mast.labels.get(label)
        if label_runtime_node is not None:
            self.cmds = self.main.mast.labels[label].cmds
            self.active_label = label
            self.active_cmd = activate_cmd
            #print(f"ACTIVE_CMD {self.cmds[self.active_cmd]}")

            #print(f"RUNTIME NODE {runtime_node}")
            self.runtime_node = runtime_node
            self.done = False
        else:
            self.runtime_error(f"""Jump to label "{label}" not found""")
            self.active_cmd = 0
            self.runtime_node = None
            self.done = True
    def push_label(self, label, activate_cmd=0, data=None):
        #print("PUSH")
        if self.active_label:
            self.pending_push = PushData(self.active_label, self.active_cmd, data)
            self.task.label_stack.append(self.pending_push)
        self.jump(label, activate_cmd)
    def push_inline_block(self, label, activate_cmd=0, data=None):
        #
        # This type of push resumes running the same runtime node 
        # that was active when the push occurred
        # This done by Buttons, Dropdown and event
        #
        #print("PUSH JUMP POP")
        push_data = PushData(self.active_label, self.active_cmd, data, self.runtime_node)
        self.task.label_stack.append(push_data)
        self.pop_on_jump += 1
        self.pending_jump = (label,activate_cmd)
        #print(f"PUSH: {label}")
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
            #print(f"POP: {push_data.label}")
            #print(f"POP DATA {push_data.label} {push_data.active_cmd} len {len(self.task.label_stack)}")
            if self.pending_jump is None:
                if inc_loc:
                    # TREAT THIS LIKE A JUMP
                    # I think this is a True POP in an inline
                    # So don't resume
                    #print(f"I inc'd {true_pop}")
                    self.pending_pop = (push_data.label, push_data.active_cmd+1, None)
                else:
                    #
                    # We didn't inc so the hope is to resume 
                    #
                    #print(f"I DID NOT inc {push_data.runtime_node}")
                    self.pending_pop = (push_data.label, push_data.active_cmd, push_data.runtime_node)
    def tick(self):
        cmd = None
        try:
            if self.done:
                # should unschedule
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

                count += 1
                # avoid tight loops
                if count > 1000:
                    break

                if self.runtime_node:
                    cmd = self.cmds[self.active_cmd]
                    # Purged Assigned are seen as Comments
                    if cmd.__class__== "Comment":
                        self.next()
                        continue

                    #print(f"{cmd.__class__} running {self.runtime_node.__class__}")
                    result = self.runtime_node.poll(self.main.mast, self.task, cmd)
                    match result:
                        case PollResults.OK_ADVANCE_TRUE:
                            self.last_poll_result = result
                            self.next()
                        case PollResults.OK_YIELD:
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
                        case PollResults.FAIL_END:
                            self.last_poll_result = result
                            self.done = True
                            return PollResults.FAIL_END

                        case PollResults.OK_RUN_AGAIN:
                            break
                        case PollResults.OK_JUMP:
                            continue
            return PollResults.OK_RUN_AGAIN
        except BaseException as err:
            self.main.runtime_error(str(err))
            return PollResults.OK_END

        

    def runtime_error(self, rte):
        cmd = None
        logger = logging.getLogger("mast.runtime")
        logger.error(rte)
        s = "mast RUNTIME ERROR\n" 
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
                    self.done = True
                    return False
                return self.jump(next.name)
                
            
            cmd = self.cmds[self.active_cmd]
            runtime_node_cls = self.main.nodes.get(cmd.__class__.__name__, MastRuntimeNode)
            
            self.runtime_node = runtime_node_cls()
            #print(f"RUNNER {self.runtime_node.__class__.__name__}")
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
            

    def tick(self):
        # Keep running until told to defer or you've jump 100 time
        # Arbitrary number
        throttle = 0
        
        while not self.done and throttle < 100:
            throttle += 1
            if self.pending_jump:
                #print(f"jump to {self.pending_jump}")
                res = self.do_jump()
                self.pending_pop = None
                
            elif self.pending_pop:
                # Pending jump trumps pending pop
                #print(f"pending pop to {self.pending_pop.__name__}")
                self.current_gen = self.pending_pop
                self.pending_pop = None

            
            gen = self.current_gen
            # It is possible that the label
            # did not Yield, which is OK just End 
            if gen is None:
                #print("Gen None")
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
                    #print("Label yielded None")
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
            #print(f"IS METHOD {label.__name__}")
            self.fall_through_label = get_fall_through(label)
            gen = label()
            res = PollResults.OK_JUMP
        elif inspect.isfunction(label):
            #print(f"IS func {label.__name__}")
            self.fall_through_label = get_fall_through(label)
            gen = label()
            res = PollResults.OK_JUMP
            #print(f"IS method {label.__name__} {gen}")
        elif isinstance(label, partial):
            #
            # Not sure this will work right?
            #
            self.fall_through_label = get_fall_through(label)
            gen = label()
            res = PollResults.OK_JUMP
        else:
            print("Unexpected label type: not function, method or partial")
        
        return (gen, res)
    
    def jump(self, label):
        while self.pop_on_jump>0:
            #print(f"I popped {label.__name__}")
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

    
    def push_jump_pop(self, label):
        if self.current_gen is not None:
            self.stack.append(self.current_gen)
        self.pending_jump = label
        self.pop_on_jump += 1
        return PollResults.OK_JUMP

    def pop(self):
        if len(self.stack) > 0:
            if self.pop_on_jump >0:
                self.pop_on_jump-=1
            self.pending_pop = self.stack.pop()
            return PollResults.OK_JUMP
        return PollResults.FAIL_END
    
    def runtime_error(self, rte):
        cmd = None
        logger = logging.getLogger("mast.runtime")
        logger.error(rte)
        s = "mast python RUNTIME ERROR\n" 
        s += f"\n===== code ======\n\n{rte}\n\n==================\n"
        s += '\n'+rte

        logger = logging.getLogger("mast.runtime")
        logger.error(s)

        self.main.runtime_error(s)
        self.done = True



class MastAsyncTask(Agent, Promise):
    main: 'MastScheduler'
    dependent_tasks = {}
    
    def __init__(self, main: 'MastScheduler', inputs=None, conditional= None):
        super().__init__()
        self.id = get_task_id()
        
        #self.runtime_node = None
        self.main= main
        #self.vars= inputs if inputs else {}
        if inputs:
            self.inventory.collections = dict(self.inventory.collections, **inputs)
            #self.inventory.collections |= inputs
        
        #self.label_stack = []
        
        #self.events = {}
        #self.vars["mast_task"] = self
        self.set_inventory_value("mast_task", self)
        #self.redirect = None
        # self.pop_on_jump = 0
        # self.pending_pop = None
        # self.pending_jump = None
        # self.pending_push = None
        self.mast_ticker = MastTicker(self, main)
        self.py_ticker = PyTicker(self)
        self.active_ticker = self.mast_ticker
        self.label_stack = []

        #self.done = False
        #self.result = None
        #self.active_label = None
        self.add()
    
    def end(self):
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
        if self.active_ticker is None:
            return "main"
        return self.active_ticker.active_label
    
    @property
    def tick_result(self):
        return self.active_ticker.last_poll_result

    def get_symbols(self):
        # m1 = self.main.mast.vars | self.main.vars
        mast_inv = Agent.SHARED.inventory.collections
        m1 = mast_inv | self.main.inventory.collections
        m1 =   m1 | self.inventory.collections 
        for st in self.label_stack:
            data = st.data
            if data is not None:
                m1 =   m1 | data
        # if self.redirect and self.redirect.data:
        #     m1 = self.redirect.data | m1
        return m1

    def set_value(self, key, value, scope):
        if scope == Scope.SHARED:
            # self.main.mast.vars[key] = value
            Agent.SHARED.set_inventory_value(key, value)
        elif scope == Scope.TEMP:
            self.set_inventory_value(key, value)
            #self.vars[key] = value
        else:
            self.set_inventory_value(key, value)
            #self.vars[key] = value

    def set_value_keep_scope(self, key, value):
        scoped_val = self.get_value(key, value)
        scope = scoped_val[1]
        if scope is None:
            scope = Scope.TEMP
        # elif scope == Scope.UNKNOWN:
        #     scope = Scope.NORMAL
        self.set_value(key,value, scope)

    def get_value(self, key, defa):
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
        return self.main.get_value(key, defa)
    
    def get_scoped_value(self, key, defa, scope):
        if scope == Scope.SHARED:
            return self.main.get_value(key, defa)
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
    
    def set_variable(self, key, value):
        self.set_value_keep_scope(key,value)

    def get_shared_variable(self, key, default=None):
        return Agent.SHARED.get_inventory_value(key, default)
    
    def set_shared_variable(self, key, value):
        Agent.SHARED.set_inventory_value(key, value)


    def format_string(self, message):
        if isinstance(message, str):
            return message
        allowed = self.get_symbols()
        # logger = logging.getLogger("mast.story")
        # for k,v in allowed.items():
        #     if k == "myslot":
        #         logger.info(f"{k}: {v}")
        value = eval(message, {"__builtins__": Mast.globals}, allowed)
        return value
    
    def compile_and_format_string(self, value):
        if isinstance(value, str) and "{" in value:
            value = f'''f"""{value}"""'''
            code = compile(value, "<string>", "eval")
            value = self.format_string(code)
        return value



    def eval_code(self, code):
        value = None
        try:
            allowed = self.get_symbols()
            value = eval(code, {"__builtins__": Mast.globals}, allowed)
        except:
            self.runtime_error(traceback.format_exc())
            self.end()
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
                g = Mast.globals | gbls
            else:
                g = Mast.globals
            exec(code, {"__builtins__": g}, allowed)
        except:
            self.runtime_error(traceback.format_exc())
            self.end()
        finally:
            pass
        

    def start_task(self, label = "main", inputs=None, task_name=None)->MastAsyncTask:
        inputs= self.inventory.collections|inputs if inputs else self.inventory.collections
        return self.main.start_task(label, inputs, task_name)
    
    def tick(self):
        restore = FrameContext.task
        FrameContext.task = self
        res = self.active_ticker.tick()
        FrameContext.task = restore
        if self.active_ticker.done:
            self.set_result(self.active_ticker.last_poll_result)
        return res
        

    def jump(self, label = "main", activate_cmd=0):
        if isinstance(label, str) or isinstance(label, Label):
            self.active_ticker = self.mast_ticker
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



# class MastBehaveTask(Agent):
#     def __init__(self):
#         super().__init__()
#         self.id = get_task_id()
#         self.add()

# class MastSequenceTask(MastBehaveTask):
#     def __init__(self, main, labels, conditional) -> None:
#         super().__init__()
#         self.task = None
#         self.main= main
#         self.labels = labels
#         self.conditional = conditional
#         self.current_label = 0
#         self.done = False
#         self.result = None

#     @property
#     def active_label(self):
#         self.task.active_label

#     def rewind(self):
#         self.current_label = 0
#         self.done = False
#         label = self.labels[self.current_label]
#         self.task.jump(label)
#         # The task was removed, re-add
#         self.main.tasks.append(self)
#         return PollResults.OK_JUMP

#     def tick(self) -> PollResults:
#         if self.conditional is not None and self.task.get_variable(self.conditional):
#             self.done = True
#             return PollResults.OK_END
#         self.result = self.task.tick()
#         if self.result == PollResults.OK_END:
#             self.current_label += 1
#             if self.current_label >= len(self.labels):
#                 self.done = True
#                 return PollResults.OK_END
#             # so if this fails as a sequence it reruns the sequence?
#             label = self.labels[self.current_label]
#             #TODO: I'm not sure why just jump didn't work
#             self.task.do_jump(label)
            
#             return PollResults.OK_JUMP
#         if self.result == PollResults.FAIL_END:
#                 self.done = True
#                 return PollResults.FAIL_END
#         return PollResults.OK_RUN_AGAIN
#     def run_event(self, event_name, event):
#         self.task.run_event(event_name, event)

# class MastFallbackTask(MastBehaveTask):
#     def __init__(self, main,  labels, conditional) -> None:
#         super().__init__()
#         self.task = None
#         self.main= main
#         self.labels = labels
#         self.conditional = conditional
#         self.current_selection = 0
#         self.done = False
#         self.result = None
        

#     @property
#     def active_label(self):
#         self.task.active_label

#     def rewind(self):
#         self.current_selection = 0
#         self.done = False
#         label = self.labels[self.current_selection]
#         self.task.do_jump(label)
#         self.main.tasks.append(self)
#         return PollResults.OK_JUMP

#     def tick(self) -> PollResults:
#         if self.conditional is not None and  self.task.get_variable(self.conditional):
#             self.done = True
#             return PollResults.OK_END
#         self.result = self.task.tick()
#         if self.result == PollResults.FAIL_END:
#             self.current_selection += 1
#             if self.current_selection >= len(self.labels):
#                 self.done = True
#                 return PollResults.FAIL_END
#             # so if this fails as a sequence it reruns the sequence?
#             label = self.labels[self.current_selection]
#             #TODO: I'm not sure why just jump didn't work
#             # 
#             self.task.do_jump(label)
#             #self.result = self.task.tick()
#             return PollResults.OK_JUMP
#         if self.result == PollResults.OK_END:
#             self.done = True
#             #print(f"Fallback ended {self.task.active_label}")
#             return PollResults.OK_END
#         return PollResults.OK_RUN_AGAIN
#     def run_event(self, event_name, event):
#         self.task.run_event(event_name, event)
    



class MastScheduler(Agent):
    runtime_nodes = {
        "End": EndRuntimeNode,
        "ReturnIf": ReturnIfRuntimeNode,
        "Fail": FailRuntimeNode,
        "Yield": YieldRuntimeNode,
        "Jump": JumpRuntimeNode,
        "IfStatements": IfStatementsRuntimeNode,
        "MatchStatements": MatchStatementsRuntimeNode,
        "LoopStart": LoopStartRuntimeNode,
        "LoopEnd": LoopEndRuntimeNode,
        "LoopBreak": LoopBreakRuntimeNode,
        "PyCode": PyCodeRuntimeNode,
        "FuncCommand": FuncCommandRuntimeNode,
        #"Behavior": BehaviorRuntimeNode,
#        "Parallel": ParallelRuntimeNode,
        "Assign": AssignRuntimeNode,
        "Await": AwaitRuntimeNode,
        "AwaitInlineLabel": AwaitInlineLabelRuntimeNode,
        "Button": ButtonRuntimeNode,
            "Change": ChangeRuntimeNode,
        #    "Timeout": TimeoutRuntimeNode,
        "EndAwait": EndAwaitRuntimeNode,
    }

    def __init__(self, mast: Mast, overrides=None):
        super().__init__()
        # Schedulers use task Id
        self.id = get_task_id()
        self.add()
        if overrides is None:
            overrides = {}
        self.nodes = MastScheduler.runtime_nodes | overrides
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
        

    def runtime_error(self, message):
        print("mast level runtime error:\n {message}")
        pass

    def get_seconds(self, clock):
        """ Gets time for a given clock default is just system """
        if clock == 'test':
            self.test_clock += 0.2
            return self.test_clock
        return time.time()

    def start_sequence_task(self, labels = "main", inputs=None, task_name=None, conditional=None)->MastSequenceTask:
        # if single label no need for any
        if not isinstance(labels, list):
            return self.start_task(labels, inputs, task_name)

        seq_task = MastSequenceTask(self, labels, conditional)    
        t = self._start_task(labels[0], inputs, None)
        t.jump(labels[0])
        seq_task.task = t

        #self.on_start_task(t)
        self.tasks.append(seq_task)
        if task_name is not None:
            self.active_task.set_value(task_name, seq_task, Scope.NORMAL)
        return seq_task

    def start_fallback_task(self, labels = "main", inputs=None, task_name=None, conditional=None)->MastFallbackTask:
        # if single label no need for any
        if not isinstance(labels, list):
            return self.start_task(labels, inputs, task_name)

        seq_task = MastFallbackTask(self, labels, conditional)    
        t = self._start_task(labels[0], inputs, None)
        t.jump(labels[0])
        seq_task.task = t

        #self.on_start_task(t)
        self.tasks.append(seq_task)
        if task_name is not None:
            self.active_task.set_value(task_name, seq_task, Scope.NORMAL)
        return seq_task


    def _start_task(self, label = "main", inputs=None, task_name=None)->MastAsyncTask:
        if self.inputs is None:
            self.inputs = inputs

        # if self.mast and self.mast.labels.get(label,  None) is None:
        #     raise Exception(f"Calling undefined label {label}")
        t= MastAsyncTask(self, inputs)
        return t


    def start_task(self, label = "main", inputs=None, task_name=None)->MastAsyncTask:
        t = self._start_task(label, inputs, task_name)
        if task_name is not None:
            t.set_value(task_name, t, Scope.NORMAL)
        t.jump(label)
        self.tasks.append(t)
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
            data.end()
            self.done.append(data)

    def is_running(self):
        if len(self.tasks) == 0:
            return False
        return True

    def get_value(self, key, defa=None):
        val = Mast.globals.get(key, None)
        if val is not None:
            return (val, Scope.SHARED)
        #val = self.mast.vars.get(key, None)
        val = Agent.SHARED.get_inventory_value(key, None)
        if val is not None:
            return (val, Scope.SHARED)
        #val = self.vars.get(key, defa)
        val = self.get_inventory_value(key, None)
        return (val, Scope.NORMAL)

    def get_variable(self, key):
        val = self.get_value(key)
        return val[0]
    
    def set_variable(self, key):
        val = self.get_value(key)
        return val[0]

    def tick(self):
        restore = FrameContext.task
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

        if len(self.tasks):
            return True
        else:
            return False

