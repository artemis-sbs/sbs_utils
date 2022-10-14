from enum import IntEnum
from .mast import *

class MastRuntimeNode:
    def enter(self, mast, runner, node):
        pass
    def leave(self, mast, runner, node):
        pass

    def poll(self, mast, runner, node):
        return PollResults.OK_ADVANCE_TRUE

class MastRuntimeError:
    def __init__(self, message, line_no):
        if isinstance(message, str):
            self.messages = [message]
        else:
            self.messages = message
        self.line_no = line_no


class MastAsync:
    pass

# Using enum.IntEnum 
class PollResults(IntEnum):
     OK_JUMP = 1
     OK_ADVANCE_TRUE = 2
     OK_ADVANCE_FALSE=3
     OK_RUN_AGAIN = 4
     OK_END = 99

class EndRunner(MastRuntimeNode):
    def poll(self, mast, thread, node:End):
        return PollResults.OK_END

class AssignRunner(MastRuntimeNode):
    def poll(self, mast, thread:MastAsync, node:Assign):
        try:
            value = thread.eval_code(node.code)
            if "." in node.lhs or "[" in node.lhs:
                locals = {"__mast_value": value} | thread.get_symbols()
                exec(f"""{node.lhs} = __mast_value""",{"__builtins__": Mast.globals}, locals)
            else:
                thread.set_value(node.lhs, value, node.scope)
        except:
            thread.main.runtime_error(f"assignment error {node.lhs}")
            return PollResults.OK_END

        return PollResults.OK_ADVANCE_TRUE

class PyCodeRunner(MastRuntimeNode):
    def poll(self, mast, thread:MastAsync, node:PyCode):
        def export():
            add_to = thread.main.vars
            def decorator(cls):
                add_to[cls.__name__] = cls
                return cls
            return decorator

        def export_var(name, value, shared=False):
            if shared:
                thread.main.mast.vars[name] = value
            else:
                thread.main.vars[name] = value

        locals = {"export": export, "export_var": export_var} | thread.get_symbols()
        exec(node.code,{"__builtins__": Mast.globals}, locals)

        # before = set(locals.items())
        # exec(node.code,{"__builtins__": Mast.globals}, locals)
        # after = set(locals.items())
        # new_vars = dict(before ^ after)
        # thread.main.vars = thread.main.vars | new_vars
        return PollResults.OK_ADVANCE_TRUE


class JumpRunner(MastRuntimeNode):
    def poll(self, mast, thread, node:Jump):
        if node.code:
            value = thread.eval_code(node.code)
            if not value:
                return PollResults.OK_ADVANCE_TRUE
        if node.push:
            thread.push_label(node.label)
        elif node.pop:
            thread.pop_label()
        else:
            thread.jump(node.label)
        return PollResults.OK_JUMP


class LoopStartRunner(MastRuntimeNode):
    def enter(self, mast, thread:MastAsync, node:LoopStart):
        scoped_val = thread.get_value(node.name, None)
        index = scoped_val[0]
        scope = scoped_val[1]
        scoped_val = thread.get_value(node.name+"__iter", None)
        _iter = scoped_val[0]
        iter_scope  = scoped_val[1]
        if index is None:
            index = 0
            scope = Scope.TEMP
            thread.set_value(node.name, index, scope)
        elif not node.iter:
            index+=1
            thread.set_value(node.name, index, scope)
        self.scope = scope

        # One time om start create iterator        
        if node.code is not None and node.iter is None:
            value = thread.eval_code(node.code)
            try:
                _iter = iter(value)
                node.iter = True
            except TypeError:
                node.iter = False

        # All the time if iterable
        if _iter is not None and node.iter:
            try:
                index = next(_iter)
                thread.set_value(node.name, index, Scope.TEMP)
                thread.set_value(node.name+"__iter", _iter, Scope.TEMP)
            except StopIteration:
                thread.set_value(node.name, None, Scope.TEMP)
                thread.set_value(node.name+"__iter", None, Scope.TEMP)
 

    def poll(self, mast, thread, node:LoopStart):
        value = True
        if node.iter:
            scoped_val = thread.get_value(node.name, None)
            index = scoped_val[0]
            if index is None:
                value = False
                node.iter = None
        elif node.code:
            value = thread.eval_code(node.code)
        if value == False:
            inline_label = f"{thread.active_label}:{node.name}"
            # End loop clear value
            thread.set_value(node.name, None, self.scope)
            thread.jump_inline_end(inline_label, False)
            return PollResults.OK_ADVANCE_TRUE
        return PollResults.OK_ADVANCE_TRUE

class LoopEndRunner(MastRuntimeNode):
    def poll(self, mast, thread, node:LoopEnd):
        inline_label = f"{thread.active_label}:{node.name}"
        if node.loop == True:
            thread.jump_inline_start(inline_label)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

class LoopBreakRunner(MastRuntimeNode):
    def enter(self, mast, thread:MastAsync, node:LoopStart):
        scoped_val = thread.get_value(node.name, None)
        index = scoped_val[0]
        scope = scoped_val[1]
        if index is None:
            scope = Scope.TEMP
        self.scope = scope

    def poll(self, mast, thread, node:LoopEnd):
        inline_label = f"{thread.active_label}:{node.name}"
        if node.op == 'break':
            thread.jump_inline_end(inline_label, True)
            # End loop clear value
            thread.set_value(node.name, None, self.scope)
            return PollResults.OK_JUMP
        elif node.op == 'continue':
            thread.jump_inline_start(inline_label)
            return PollResults.OK_JUMP
        return PollResults.OK_ADVANCE_TRUE

class IfStatementsRunner(MastRuntimeNode):
    def poll(self, mast, thread, node:IfStatements):
        """ """
        # if this is THE if, find the first true branch
        if node.if_op == "if":
            activate = self.first_true(thread, node)
            if activate is not None:
                thread.jump(thread.active_label, activate+1)
                return PollResults.OK_JUMP
        else:
            # Everything else jumps to past the endif
            activate = node.if_node.if_chain[-1]
            thread.jump(thread.active_label, activate+1)
            return PollResults.OK_JUMP

    def first_true(self, thread: MastAsync, node: IfStatements):
        cmd_to_run = None
        for i in node.if_chain:
            test_node = thread.cmds[i]
            if test_node.code:
                value = thread.eval_code(test_node.code)
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

class MatchStatementsRunner(MastRuntimeNode):
    def poll(self, mast, thread, node:MatchStatements):
        """ """
        # if this is THE if, find the first true branch
        if node.op == "match":
            activate = self.first_true(thread, node)
            if activate is not None:
                thread.jump(thread.active_label, activate+1)
                return PollResults.OK_JUMP
        else:
            # Everything else jumps to past the endif
            activate = node.match_node.chain[-1]
            thread.jump(thread.active_label, activate+1)
            return PollResults.OK_JUMP

    def first_true(self, thread: MastAsync, node: MatchStatements):
        cmd_to_run = None
        for i in node.chain:
            test_node = thread.cmds[i]
            if test_node.code:
                value = thread.eval_code(test_node.code)
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
        






class ParallelRunner(MastRuntimeNode):
    def enter(self, mast, thread, node:Parallel):
        vars = {} | thread.vars
        if node.code:
            inputs = thread.eval_code(node.code)
            vars = vars | inputs
        if node.if_code:
            value = thread.eval_code(node.if_code)
            if not value:
                return
        thread.start_thread(node.label, vars, thread_name=node.name)
    def poll(self, mast, thread, node:Parallel):
        return PollResults.OK_ADVANCE_TRUE

class AwaitRunner(MastRuntimeNode):
    def enter(self, mast, thread, node:Await):
        self.thread = None

        if node.if_code:
            value = thread.eval_code(node.if_code)
            if not value:
                return
        
        if node.spawn:
            vars = {} | thread.vars
            if node.code:
                inputs = thread.eval_code(node.code)
                vars = vars | inputs
            # spawn via thread to pass same inputs
            self.thread = thread.start_thread(node.label, vars)
        else:
            self.thread = thread.main.name_threads.get(node.label)

    def poll(self, mast, thread, node:Await):
        if self.thread is None:
            return PollResults.OK_ADVANCE_TRUE
        if self.thread.done:
            if self.thread.result == PollResults.OK_ADVANCE_FALSE:
                return PollResults.OK_ADVANCE_FALSE
            else:
                return PollResults.OK_ADVANCE_TRUE
        return PollResults.OK_RUN_AGAIN


class CancelRunner(MastRuntimeNode):
    def poll(self, mast, thread: MastAsync, node:Cancel):
        thread.main.cancel_thread(node.name)
        return PollResults.OK_ADVANCE_TRUE

    
class DelayRunner(MastRuntimeNode):
    def enter(self, mast, thread, node):
        self.timeout = node.minutes*60+node.seconds
        self.tag = None

    def poll(self, mast, thread, node):
        self.timeout -= 1
        if self.timeout <= 0:
            return PollResults.OK_ADVANCE_TRUE

        return PollResults.OK_RUN_AGAIN

class MastRunner:
    pass

class PushData:
    def __init__(self, label, active_cmd, data=None):
        self.label = label
        self.active_cmd = active_cmd
        self.data = data

class MastAsync:
    main: MastRunner
    
    def __init__(self, main: MastRunner, inputs=None):
        self.done = False
        self.runner = None
        self.main= main
        self.vars= inputs if inputs else {}
        self.result = None
        self.label_stack = []
        self.active_label = None

    def push_label(self, label, activate_cmd=0, data=None):
        if self.active_label:
            push_data = PushData(self.active_label, self.active_cmd, data)
            #print(f"PUSH DATA {push_data.label} {push_data.active_cmd}")
            self.label_stack.append(push_data)
        self.jump(label, activate_cmd)

    def pop_label(self):
        if len(self.label_stack)>0:
            push_data: PushData
            push_data = self.label_stack.pop()
            self.jump(push_data.label, push_data.active_cmd+1)

    def jump_inline_start(self, label_name):
        data = self.main.mast.inline_labels.get(label_name)
        if data and data.start is not None:
            self.jump(self.active_label, data.start)

    def jump_inline_end(self, label_name, break_op):
        data = self.main.mast.inline_labels.get(label_name)
        if data and data.end is not None:
            if break_op:
                self.jump(self.active_label, data.end+1)
            else:
                self.jump(self.active_label, data.end)

    def jump(self, label = "main", activate_cmd=0):
        self.call_leave()
        if label == "END":
            self.active_cmd = 0
            self.runner = None
            self.done = True
        else:
            label_runner = self.main.mast.labels.get(label)
            if label_runner is not None:
                if self.active_label == "main":
                    self.main.mast.prune_main()
                    
                self.cmds = self.main.mast.labels[label].cmds
                self.active_label = label
                self.active_cmd = activate_cmd
                self.runner = None
                self.done = False
                self.next()
            else:
                self.runtime_error(f"""Jump to label "{label}" not found""")
                self.active_cmd = 0
                self.runner = None
                self.done = True

    def get_symbols(self):
        m1 = self.main.mast.vars | self.main.vars
        m1 =  self.vars | m1
        for st in self.label_stack:
            data = st.data
            print(f"data -- {data}")
            if data is not None:
                m1 =  m1 | data
        return m1

    def set_value(self, key, value, scope):
        if scope == Scope.SHARED:
            self.main.mast.vars[key] = value
        elif scope == Scope.TEMP:
            self.vars[key] = value
        else:
            self.main.vars[key] = value

    def set_value_keep_scope(self, key, value):
        scoped_val = self.get_value(key, None)
        scope = scoped_val[1]
        if scope is None:
            scope = Scope.TEMP
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
        val = self.main.vars.get(key, defa)
        return (val, Scope.NORMAL)

    def call_leave(self):
        if self.runner:
            cmd = self.cmds[self.active_cmd]
            self.runner.leave(self.main.mast, self, cmd)
            self.runner = None

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

    def start_thread(self, label = "main", inputs=None, thread_name=None)->MastAsync:
        inputs= self.vars|inputs if inputs else self.vars
        return self.main.start_thread(label, inputs, thread_name)
    
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

                if self.runner:
                    cmd = self.cmds[self.active_cmd]
                    # Purged Assigned are seen as Comments
                    if cmd.__class__== "Comment":
                        self.next()
                        continue

                    result = self.runner.poll(self.main.mast, self, cmd)
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
            self.main.runtime_error(err)
            return PollResults.OK_END
                            

    def runtime_error(self, s):
        cmd = None
        logger = logging.getLogger("mast.runtime")
        logger.error(s)
        s = "mast SCRIPT ERROR\n"+ s
        if self.runner:
            cmd = self.cmds[self.active_cmd]
        s += f"\nlabel: {self.active_label}"
        if cmd is not None:
            s += f"\ncmd: {cmd.__class__.__name__}"
        logger = logging.getLogger("mast.runtime")
        logger.error(s)

        self.main.runtime_error(s)
        self.done = True


    def next(self):
        if self.runner:
            self.call_leave()
            cmd = self.cmds[self.active_cmd]
            self.active_cmd += 1
        
        if self.active_cmd >= len(self.cmds):
            self.done = True
            return len(self.cmds) > 0
        
        cmd = self.cmds[self.active_cmd]
        runner_cls = self.main.nodes.get(cmd.__class__.__name__, MastRuntimeNode)
        
        self.runner = runner_cls()
        #print(f"RUNNER {self.runner.__class__.__name__}")
        self.runner.enter(self.main.mast, self, cmd)
        return True



class MastRunner:
    runners = {
        "End": EndRunner,
        "Jump": JumpRunner,
        "IfStatements": IfStatementsRunner,
        "MatchStatements": MatchStatementsRunner,
        "LoopStart": LoopStartRunner,
        "LoopEnd": LoopEndRunner,
        "LoopBreak": LoopBreakRunner,
        "PyCode": PyCodeRunner,
        "Await": AwaitRunner,
        "Parallel": ParallelRunner,
        "Cancel": CancelRunner,
        "Assign": AssignRunner,
        "Delay": DelayRunner,
    }

    def __init__(self, mast: Mast, overrides=None):
        if overrides is None:
            overrides = {}
        self.nodes = MastRunner.runners | overrides
        self.mast = mast
        self.threads = []
        self.name_threads = {}
        self.inputs = None
        self.vars = {}
        self.done = []
        self.mast.add_runner(self)

    def runtime_error(self, message):
        pass

    def start_thread(self, label = "main", inputs=None, thread_name=None)->MastAsync:
        if self.inputs is None:
            self.inputs = inputs
        
        t= MastAsync(self, inputs)
        t.jump(label)
        self.on_start_thread(t)
        self.threads.append(t)
        if thread_name is not None:
            self.name_threads[thread_name] = t
        return t

    def on_start_thread(self, t):
        t.tick()
    def cancel_thread(self, name):
        t = self.name_threads.get(name)
        if t:
            self.done.append(t)

    def is_running(self):
        if len(self.threads) == 0:
            return False
        return True

    def get_value(self, key, defa=None):
        val = self.mast.vars.get(key, None)
        if val is not None:
            return (val, Scope.SHARED)
        val = self.vars.get(key, defa)
        return (val, Scope.NORMAL)

    def tick(self):
        for thread in self.threads:
            res = thread.tick()
            if res == PollResults.OK_END:
                self.done.append(thread)
        
        if len(self.done):
            for rem in self.done:
                self.threads.remove(rem)
            self.done = []

        if len(self.threads):
            return True
        else:
            return False

