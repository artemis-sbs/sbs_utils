from enum import IntEnum

from ..tickdispatcher import TickDispatcher
from .mast import *
import sbs


class MastRuntimeNode:
    def enter(self, mast, scheduler, node):
        pass
    def leave(self, mast, scheduler, node):
        pass

    def poll(self, mast, scheduler, node):
        return PollResults.OK_ADVANCE_TRUE

class MastRuntimeError:
    def __init__(self, message, line_no):
        if isinstance(message, str):
            self.messages = [message]
        else:
            self.messages = message
        self.line_no = line_no


class MastAsyncTask:
    pass

# Using enum.IntEnum 
class PollResults(IntEnum):
     OK_JUMP = 1
     OK_ADVANCE_TRUE = 2
     OK_ADVANCE_FALSE=3
     OK_RUN_AGAIN = 4
     OK_END = 99

class EndRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:End):
        return PollResults.OK_END

class AssignRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task:MastAsyncTask, node:Assign):
        try:
            value = task.eval_code(node.code)
            if "." in node.lhs or "[" in node.lhs:
                locals = {"__mast_value": value} | task.get_symbols()
                exec(f"""{node.lhs} = __mast_value""",{"__builtins__": Mast.globals}, locals)
            elif node.scope: 
                task.set_value(node.lhs, value, node.scope)
            else:
                task.set_value_keep_scope(node.lhs, value)
                
        except:
            task.main.runtime_error(f"assignment error {node.lhs}")
            return PollResults.OK_END

        return PollResults.OK_ADVANCE_TRUE

class PyCodeRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task:MastAsyncTask, node:PyCode):
        def export():
            add_to = task.main.vars
            def decorator(cls):
                add_to[cls.__name__] = cls
                return cls
            return decorator

        def export_var(name, value, shared=False):
            if shared:
                task.main.mast.vars[name] = value
            else:
                task.main.vars[name] = value

        locals = {"export": export, "export_var": export_var} | task.get_symbols()
        try:
            exec(node.code,{"__builtins__": Mast.globals}, locals)
        except:
            task.runtime_error(f"""Embedded python failed""")
        return PollResults.OK_ADVANCE_TRUE


class JumpRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:Jump):
        if node.push:
            task.push_label(node.label)
        elif node.pop_jump:
            task.pop_label()
            task.jump(node.pop_jump)
        elif node.pop_push:
            task.pop_label()
            task.push_label(node.pop_push)
        elif node.pop:
            task.pop_label()
        else:
            task.jump(node.label)
        return PollResults.OK_JUMP


class LoopStartRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task:MastAsyncTask, node:LoopStart):
        scoped_val = task.get_value(node.name, None)
        index = scoped_val[0]
        scope = scoped_val[1]
        scoped_val = task.get_value(node.name+"__iter", None)
        _iter = scoped_val[0]
        iter_scope  = scoped_val[1]
        if index is None:
            index = 0
            scope = Scope.TEMP
            task.set_value(node.name, index, scope)
        elif not node.iter:
            index+=1
            task.set_value(node.name, index, scope)
        self.scope = scope

        # One time om start create iterator        
        if node.code is not None and node.iter is None:
            value = task.eval_code(node.code)
            try:
                _iter = iter(value)
                node.iter = True
            except TypeError:
                node.iter = False

        # All the time if iterable
        if _iter is not None and node.iter:
            try:
                index = next(_iter)
                task.set_value(node.name, index, Scope.TEMP)
                task.set_value(node.name+"__iter", _iter, Scope.TEMP)
            except StopIteration:
                task.set_value(node.name, None, Scope.TEMP)
                task.set_value(node.name+"__iter", None, Scope.TEMP)
 

    def poll(self, mast, task, node:LoopStart):
        value = True
        if node.iter:
            scoped_val = task.get_value(node.name, None)
            index = scoped_val[0]
            if index is None:
                value = False
                node.iter = None
        elif node.code:
            value = task.eval_code(node.code)
        if value == False:
            inline_label = f"{task.active_label}:{node.name}"
            # End loop clear value
            task.set_value(node.name, None, self.scope)
            task.jump(task.active_label, node.end.loc+1)
            #task.jump_inline_end(inline_label, False)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

class LoopEndRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task, node:LoopEnd):
        if node.loop == True:
            task.jump(task.active_label, node.start.loc)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

class LoopBreakRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task:MastAsyncTask, node:LoopStart):
        scoped_val = task.get_value(node.name, None)
        index = scoped_val[0]
        scope = scoped_val[1]
        if index is None:
            scope = Scope.TEMP
        self.scope = scope

    def poll(self, mast, task, node:LoopEnd):
        if node.op == 'break':
            #task.jump_inline_end(inline_label, True)
            task.jump(task.active_label, node.start.end.loc+1)
            # End loop clear value
            task.set_value(node.name, None, self.scope)
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
            test_node = task.cmds[i]
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
            test_node = task.cmds[i]
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
        






class ParallelRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task, node:Parallel):
        vars = {} | task.vars
        if node.code:
            inputs = task.eval_code(node.code)
            vars = vars | inputs
        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return
        task.start_task(node.label, vars, task_name=node.name)
    def poll(self, mast, task, node:Parallel):
        return PollResults.OK_ADVANCE_TRUE

class AwaitRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task, node:Await):
        self.task = None

        if node.if_code:
            value = task.eval_code(node.if_code)
            if not value:
                return
        
        if node.spawn:
            vars = {} | task.vars
            if node.code:
                inputs = task.eval_code(node.code)
                vars = vars | inputs
            # spawn via task to pass same inputs
            self.task = task.start_task(node.label, vars)
        else:
            named_task = task.get_value(node.label, None)
            if named_task is not None:
                self.task = named_task[0]

    def poll(self, mast, task, node:Await):
        if self.task is None:
            return PollResults.OK_ADVANCE_TRUE
        if self.task.done:
            if self.task.result == PollResults.OK_ADVANCE_FALSE:
                return PollResults.OK_ADVANCE_FALSE
            else:
                return PollResults.OK_ADVANCE_TRUE
        return PollResults.OK_RUN_AGAIN

class TimeoutRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task: MastAsyncTask, node:Timeout):
        if node.end_await_node:
            task.jump(task.active_label,node.end_await_node.loc+1)

class EndAwaitRuntimeNode(MastRuntimeNode):
    pass

class CancelRuntimeNode(MastRuntimeNode):
    def poll(self, mast, task: MastAsyncTask, node:Cancel):
        task.main.cancel_task(node.name)
        return PollResults.OK_ADVANCE_TRUE

class LogRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task: MastAsyncTask, node:Log):
        logger = logging.getLogger(node.logger)
        message = task.format_string(node.message)
        match node.level:
            case "info":
                logger.info(message)
            case "debug":
                logger.debug(message)
            case "warning":
                logger.warning(message)
            case "error":
                logger.error(message)
            case "critical":
                logger.critical(message)
            case _:
                logger.debug(message)

class LoggerRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task: MastAsyncTask, node:Logger):
        logger = logging.getLogger(node.logger)
        logging.basicConfig(level=logging.NOTSET)
        logger.setLevel(logging.NOTSET)
        # handler  = logging.StreamHandler()
        # handler.setFormatter(logging.Formatter("%(levelname)s|%(name)s|%(message)s"))
        # handler.setLevel(logging.NOTSET)
        # logger.addHandler(handler)

        if node.var is not None:
            streamer = StringIO()
            handler = logging.StreamHandler(stream=streamer)
            handler.setFormatter(logging.Formatter("%(message)s"))
            handler.setLevel(logging.NOTSET)
            logger.addHandler(handler)
            
            mast.vars[node.var] = streamer

        if node.name is not None:
            name = task.format_string(node.name)
            handler = logging.FileHandler(f'{name}',mode='w',)
            handler.setFormatter(logging.Formatter("%(message)s"))
            handler.setLevel(logging.NOTSET)
            logger.addHandler(handler)

    

class DelayRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task, node):
        if node.clock=="gui":
            self.timeout = sbs.app_seconds()+ (node.minutes*60+node.seconds)
            pass
        else:
            self.timeout = TickDispatcher.current + (node.minutes*60+node.seconds)*TickDispatcher.tps
        self.tag = None

    def poll(self, mast, task, node):
        match node.clock:
            case "gui":
                if self.timeout <= sbs.app_seconds():
                    return PollResults.OK_ADVANCE_TRUE
            case _:
                if self.timeout <= TickDispatcher.current:
                    return PollResults.OK_ADVANCE_TRUE

        return PollResults.OK_RUN_AGAIN

class EventRuntimeNode(MastRuntimeNode):
    def enter(self, mast, task:MastAsyncTask, node):
        if node.end is not None:
            task.add_event(node.event, node)

    def poll(self, mast, task, node):
        if node.end is not None:
            task.jump(task.active_label,node.end.loc+1)
            return PollResults.OK_JUMP
        else:
            task.pop_label(False)
            return PollResults.OK_JUMP



class AwaitConditionRuntimeNode(MastRuntimeNode):
    def enter(self, mast:Mast, task:MastAsyncTask, node: AwaitCondition):
        seconds = (node.minutes*60+node.seconds)
        if seconds == 0:
            self.timeout = None
        else:
            self.timeout = TickDispatcher.current + (node.minutes*60+node.seconds)*TickDispatcher.tps

    def poll(self, mast:Mast, task:MastAsyncTask, node: AwaitCondition):
        value = task.eval_code(node.code)
        if value:
            return PollResults.OK_ADVANCE_TRUE

        if self.timeout is not None and self.timeout <= TickDispatcher.current:
            print("CHOOSE timeout")
            if node.timeout_label:
                task.jump(task.active_label,node.timeout_label.loc+1)
                return PollResults.OK_JUMP
            elif node.end_await_node:
                task.jump(task.active_label,node.end_await_node.loc+1)
                return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN


#class MastScheduler:
#    pass

class PushData:
    def __init__(self, label, active_cmd, data=None):
        self.label = label
        self.active_cmd = active_cmd
        self.data = data


class MastAsyncTask:
    main: 'MastScheduler'
    
    def __init__(self, main: 'MastScheduler', inputs=None):
        self.done = False
        self.runtime_node = None
        self.main= main
        self.vars= inputs if inputs else {}
        self.result = None
        self.label_stack = []
        self.active_label = None
        self.events = {}
        self.vars["mast_task"] = self

    def push_label(self, label, activate_cmd=0, data=None):
        if self.active_label:
            push_data = PushData(self.active_label, self.active_cmd, data)
            #print(f"PUSH DATA {push_data.label} {push_data.active_cmd}")
            self.label_stack.append(push_data)
        self.jump(label, activate_cmd)

    def pop_label(self, inc_loc=True):
        if len(self.label_stack)>0:
            push_data: PushData
            push_data = self.label_stack.pop()
            #print(f"POP DATA {push_data.label} {push_data.active_cmd} len {len(self.label_stack)}")
            if inc_loc:
                self.jump(push_data.label, push_data.active_cmd+1)
            else:
                self.jump(push_data.label, push_data.active_cmd)

    def add_event(self, event_name, event):
        event_data = PushData(self.active_label, event.loc)
        self.events[event_name] = event_data

    def run_event(self, event_name, event):
        ev_data = self.events.get(event_name)
        if ev_data is not None:
            self.push_label(ev_data.label, ev_data.active_cmd+1, {"event": event})
            self.tick()
    
    def jump(self, label = "main", activate_cmd=0):
        self.call_leave()
        if label == "END":
            self.active_cmd = 0
            self.runtime_node = None
            self.done = True
        else:
            label_runtime_node = self.main.mast.labels.get(label)
            if label_runtime_node is not None:
                if self.active_label == "main":
                    self.main.mast.prune_main()
                    
                self.cmds = self.main.mast.labels[label].cmds
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

    def get_symbols(self):
        m1 = self.main.mast.vars | self.main.vars
        m1 =  self.vars | m1
        for st in self.label_stack:
            data = st.data
            if data is not None:
                m1 =  data | m1
        return m1

    def set_value(self, key, value, scope):
        if scope == Scope.SHARED:
            self.main.mast.vars[key] = value
        elif scope == Scope.TEMP:
            self.vars[key] = value
        else:
            self.main.vars[key] = value

    def set_value_keep_scope(self, key, value):
        scoped_val = self.get_value(key, value)
        scope = scoped_val[1]
        if scope is None:
            scope = Scope.TEMP
        # elif scope == Scope.UNKNOWN:
        #     scope = Scope.NORMAL
        self.set_value(key,value, scope)

    def get_value(self, key, defa):
        if len(self.label_stack) > 0:
            data = self.label_stack[-1].data
            if data is not None:
                val = data.get(key, None)
                if val is not None:
                    return (val, Scope.TEMP)
        val = self.vars.get(key, None)
        if val is not None:
            return (val, Scope.TEMP)
        val = self.main.mast.vars.get(key, None)
        if val is not None:
            return (val, Scope.SHARED)
        val = self.main.vars.get(key, Scope.UNKNOWN)
        if val == Scope.UNKNOWN:
            return (defa, Scope.NORMAL)
        return (val, Scope.NORMAL)

    def get_variable(self, key):
        value = self.get_value(key, None)
        return value[0]

    def call_leave(self):
        if self.runtime_node:
            cmd = self.cmds[self.active_cmd]
            self.runtime_node.leave(self.main.mast, self, cmd)
            self.runtime_node = None

    def format_string(self, message):
        if isinstance(message, str):
            return message
        allowed = self.get_symbols()
        value = eval(message, {"__builtins__": Mast.globals}, allowed)
        return value

    def eval_code(self, code):
        value = None
        try:
            allowed = self.get_symbols()
            value = eval(code, {"__builtins__": Mast.globals}, allowed)
        except:
            self.runtime_error("")
            self.done = True
        finally:
            pass
        return value

    def exec_code(self, code):
        try:
            allowed = self.get_symbols()
            eval(code, {"__builtins__": Mast.globals}, allowed)
        except:
            self.runtime_error("")
            self.done = True
        finally:
            pass
        

    def start_task(self, label = "main", inputs=None, task_name=None)->MastAsyncTask:
        inputs= self.vars|inputs if inputs else self.vars
        return self.main.start_task(label, inputs, task_name)
    
    def tick(self):
        cmd = None
        try:
            if self.done:
                # should unschedule
                return PollResults.OK_END

            count = 0
            while not self.done:
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

                    result = self.runtime_node.poll(self.main.mast, self, cmd)
                    match result:
                        case PollResults.OK_ADVANCE_TRUE:
                            self.result = result
                            self.next()
                        case PollResults.OK_ADVANCE_FALSE:
                            self.result = result
                            self.next()
                        case PollResults.OK_END:
                            self.done = True
                            return PollResults.OK_END
                        case PollResults.OK_RUN_AGAIN:
                            break
                        case PollResults.OK_JUMP:
                            continue
            return PollResults.OK_RUN_AGAIN
        except BaseException as err:
            self.main.runtime_error(str(err))
            return PollResults.OK_END
                            

    def runtime_error(self, s):
        cmd = None
        logger = logging.getLogger("mast.runtime")
        logger.error(s)
        s = "mast SCRIPT ERROR\n"+ s
        if self.runtime_node:
            cmd = self.cmds[self.active_cmd]
        s += f"\nlabel: {self.active_label}"
        if cmd is not None:
            s += f"\ncmd: {cmd.__class__.__name__} loc {cmd.loc}"
        logger = logging.getLogger("mast.runtime")
        logger.error(s)

        self.main.runtime_error(s)
        self.done = True


    def next(self):
        if self.runtime_node:
            self.call_leave()
            cmd = self.cmds[self.active_cmd]
            self.active_cmd += 1
        
        if self.active_cmd >= len(self.cmds):
            # move to the next label
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
        self.runtime_node.enter(self.main.mast, self, cmd)
        return True



class MastScheduler:
    runtime_nodes = {
        "End": EndRuntimeNode,
        "Jump": JumpRuntimeNode,
        "IfStatements": IfStatementsRuntimeNode,
        "MatchStatements": MatchStatementsRuntimeNode,
        "LoopStart": LoopStartRuntimeNode,
        "LoopEnd": LoopEndRuntimeNode,
        "LoopBreak": LoopBreakRuntimeNode,
        "PyCode": PyCodeRuntimeNode,
        "Await": AwaitRuntimeNode,
        "Parallel": ParallelRuntimeNode,
        "Cancel": CancelRuntimeNode,
        "Assign": AssignRuntimeNode,
        "AwaitCondition": AwaitConditionRuntimeNode,
        "Timeout": TimeoutRuntimeNode,
        "EndAwait": EndAwaitRuntimeNode,
        "Event": EventRuntimeNode,
        "Delay": DelayRuntimeNode,
        "Log": LogRuntimeNode,
        "Logger": LoggerRuntimeNode,
    }

    def __init__(self, mast: Mast, overrides=None):
        if overrides is None:
            overrides = {}
        self.nodes = MastScheduler.runtime_nodes | overrides
        self.mast = mast
        self.tasks = []
        self.name_tasks = {}
        self.inputs = None
        self.vars = {"mast_scheduler": self}
        self.done = []
        self.mast.add_scheduler(self)
        

    def runtime_error(self, message):
        pass

    def start_task(self, label = "main", inputs=None, task_name=None)->MastAsyncTask:
        if self.inputs is None:
            self.inputs = inputs

        if self.mast and self.mast.labels.get(label,  None) is None:
            return None
        
        t= MastAsyncTask(self, inputs)
        t.jump(label)
        self.on_start_task(t)
        self.tasks.append(t)
        if task_name is not None:
            self.active_task.set_value(task_name, t, Scope.NORMAL)
        return t

    def on_start_task(self, t):
        t.tick()
    def cancel_task(self, name):
        data = self.active_task.get_value(name, None)
        # Assuming its OK to cancel none
        if data is not None:
            self.done.append(data[0])

    def is_running(self):
        if len(self.tasks) == 0:
            return False
        return True

    def get_value(self, key, defa=None):
        val = self.mast.vars.get(key, None)
        if val is not None:
            return (val, Scope.SHARED)
        val = self.vars.get(key, defa)
        return (val, Scope.NORMAL)

    def get_variable(self, key):
        val = self.get_value(key)
        return val[0]

    def tick(self):
        for task in self.tasks:
            self.active_task = task
            res = task.tick()
            if res == PollResults.OK_END:
                self.done.append(task)
        
        if len(self.done):
            for rem in self.done:
                if rem in self.tasks:
                    self.tasks.remove(rem)
            self.done = []

        if len(self.tasks):
            return True
        else:
            return False

