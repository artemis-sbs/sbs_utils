from enum import IntEnum
from .quest import *

class QuestRuntimeNode:
    def enter(self, quest, runner, node):
        pass
    def leave(self, quest, runner, node):
        pass

    def poll(self, quest, runner, node):
        return PollResults.OK_ADVANCE_TRUE

class QuestRuntimeError:
    def __init__(self, message, line_no):
        if isinstance(message, str):
            self.messages = [message]
        else:
            self.messages = message
        self.line_no = line_no


class QuestAsync:
    pass

# Using enum.IntEnum 
class PollResults(IntEnum):
     OK_JUMP = 1
     OK_ADVANCE_TRUE = 2
     OK_ADVANCE_FALSE=3
     OK_RUN_AGAIN = 4
     OK_END = 99

class EndRunner(QuestRuntimeNode):
    def poll(self, quest, thread, node:End):
        return PollResults.OK_END

class AssignRunner(QuestRuntimeNode):
    def poll(self, quest, thread, node:Assign):
        value = thread.eval_code(node.code)
        locals = {"__quest_value": value} | thread.get_symbols()
        exec(f"""{node.lhs} = __quest_value""",{"__builtins__": {}}, locals)
        return PollResults.OK_ADVANCE_TRUE

class JumpRunner(QuestRuntimeNode):
    def poll(self, quest, thread, node:Jump):
        thread.jump(node.label)
        return PollResults.OK_JUMP

class ParallelRunner(QuestRuntimeNode):
    def enter(self, quest, thread, node:Parallel):
        thread.start_thread(node.label, thread_name=node.name)
    def poll(self, quest, thread, node:Parallel):
        return PollResults.OK_ADVANCE_TRUE

class AwaitRunner(QuestRuntimeNode):
    def enter(self, quest, thread, node:Await):
        self.thread = None
        if node.spawn:
            # spawn via thread to pass same inputs
            self.thread = thread.start_thread(node.label)
        else:
            self.thread = thread.name_threads.get(node.label)

    def poll(self, quest, thread, node:Await):
        if self.thread is None:
            return PollResults.OK_ADVANCE_TRUE
        if self.thread.done:
            if self.thread.result == PollResults.OK_ADVANCE_FALSE:
                return PollResults.OK_ADVANCE_FALSE
            else:
                return PollResults.OK_ADVANCE_TRUE
        return PollResults.OK_RUN_AGAIN


class CancelRunner(QuestRuntimeNode):
    def poll(self, quest, thread: QuestAsync, node:Cancel):
        thread.main.cancel_thread(node.name)
        return PollResults.OK_ADVANCE_TRUE

    
class DelayRunner(QuestRuntimeNode):
    def enter(self, quest, thread, node):
        self.timeout = node.minutes*60+node.seconds
        self.tag = None

    def poll(self, quest, thread, node):
        self.timeout -= 1
        if self.timeout <= 0:
            return PollResults.OK_ADVANCE_TRUE

        return PollResults.OK_RUN_AGAIN

class QuestRunner:
    pass

class QuestAsync:
    main: QuestRunner
    
    def __init__(self, main: QuestRunner, inputs=None):
        self.done = False
        self.runner = None
        self.main= main
        self.inputs= inputs if inputs else {}
        self.result = None
               

    def jump(self, label = "main"):
        self.call_leave()
        self.cmds = self.main.quest.labels[label].cmds
        self.active_label = label
        self.active_cmd = 0
        self.runner = None
        self.done = False
        self.next(True)

    def get_symbols(self):
        return self.inputs | self.main.vars

    def call_leave(self):
        if self.runner:
            cmd = self.cmds[self.active_cmd]
            self.runner.leave(self.main.quest, self, cmd)
            self.runner = None
        

    def eval_code(self, code):
        value = None
        try:
            allowed = {"math": math}| self.get_symbols()
            value = eval(code, {"__builtins__": {}}, allowed)
        finally:
            pass
        return value

    def start_thread(self, label = "main", inputs=None, thread_name=None)->QuestAsync:
        inputs= self.inputs|inputs if inputs else self.inputs
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
                    result = self.runner.poll(self.main.quest, self, cmd)
                    match result:
                        case PollResults.OK_ADVANCE_TRUE:
                            self.result = result
                            self.next()
                        case PollResults.OK_ADVANCE_FALSE:
                            self.result = result
                            self.next()
                        case PollResults.OK_END:
                            self.done = True
                        case PollResults.OK_RUN_AGAIN:
                            break
                        case PollResults.OK_JUMP:
                            break
            return PollResults.OK_RUN_AGAIN
        except BaseException as err:
            self.main.runtime_error("")
            return PollResults.OK_END
                            

    def runtime_error(self, s):
        if self.runner:
            cmd = self.cmds[self.active_cmd]
        s += f"label: {self.active_label}^"
        if cmd:
            s += f"cmd: {cmd.__class__.__name__}^"
            s += f"line: {cmd.gen()}^"
        self.main.runtime_error(s)
        self.done = True


    def next(self, first=False):
        if self.runner:
            self.call_leave()
            cmd = self.cmds[self.active_cmd]
            self.active_cmd += 1
        
        if self.active_cmd >= len(self.cmds):
            self.done = True
            return len(self.cmds) > 0
        
        cmd = self.cmds[self.active_cmd]
        runner_cls = self.main.nodes.get(cmd.__class__.__name__, QuestRuntimeNode)
        
        self.runner = runner_cls()
        self.runner.enter(self.main.quest, self, cmd)
        return True



class QuestRunner:
    runners = {
        "End": EndRunner,
        "Jump": JumpRunner,
        "Await": AwaitRunner,
        "Parallel": ParallelRunner,
        "Cancel": CancelRunner,
        "Assign": AssignRunner,
        "Delay": DelayRunner,
    }

    def __init__(self, quest: Quest, overrides=None):
        if overrides is None:
            overrides = {}
        self.nodes = QuestRunner.runners | overrides
        self.vars = {} | quest.vars
        self.quest = quest
        self.threads = []
        self.name_threads = {}
        self.inputs = None
        self.done = []

    def runtime_error(self, message):
        pass

    def start_thread(self, label = "main", inputs=None, thread_name=None)->QuestAsync:
        if self.inputs is None:
            self.inputs = inputs
            inputs = {} | inputs
        if inputs is None:
           inputs = {} | self.inputs

        t= QuestAsync(self, inputs)
        t.jump(label)
        self.threads.append(t)
        if thread_name is not None:
            self.name_threads[thread_name] = t
        return t

    def cancel_thread(self, name):
        t = self.name_threads.get(name)
        if t:
            self.done.append(t)

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




    
