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
from .mast_node import EVAL_ERROR, mast_expr_source
import logging
import sys

# Cached eval/exec globals wrapper. Variables resolve from the LOCALS arg
# (get_symbols()); this dict only carries __builtins__. MastGlobals.globals is
# mutated in place (never reassigned — runtime import_python edits land in the
# same object), so one shared wrapper stays current and spares us building a
# fresh {"__builtins__": ...} dict on every eval_code/format_string call (~one
# per expression eval, hundreds of thousands per second under load).
_EVAL_GLOBALS = {"__builtins__": MastGlobals.globals}

# `shared x = 1` is a SCOPE keyword plus a target; `shared = 1` therefore assigns
# to nothing at all, and the NameError lands on the line that READS the variable.
# See MAST_CLAUDE.md - it is a common enough trap to name in the error itself.
_SCOPE_KEYWORDS = ("shared", "assigned", "client", "temp")


def describe_eval_failure(code):
    """Header describing the live exception for a MAST eval/exec failure.

    Called from inside an ``except`` block, so ``sys.exc_info()`` is still live.
    Names the exception TYPE (a bare message hides whether it was a NameError or
    a TypeError), quotes the MAST expression the code object came from, and adds
    a hint for the scope-keyword trap.
    """
    err = sys.exc_info()[1]
    if err is None:
        return ""
    s = f"{type(err).__name__} in expression:"
    source = mast_expr_source(code)
    if source:
        for line in source.splitlines():
            s += f"\n     {line}"
    else:
        s += "\n     (source unavailable)"
    name = getattr(err, "name", None)
    if isinstance(err, NameError) and name in _SCOPE_KEYWORDS:
        s += (f"\n     hint: '{name}' is a MAST scope keyword, not a variable."
              f"\n           `{name} = value` assigns to NOTHING - it parses as the"
              f"\n           '{name}' scope with an empty target. Rename the variable.")
    return s


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
    # label_stack entry, allocated on every push_label / push_inline_block.
    # __slots__ drops the per-instance __dict__ (smaller, one fewer GC-tracked
    # container). Audited safe: 4 fixed fields, no subclasses, no dynamic attrs;
    # get_symbols() reads `.data`, which is still a slot.
    __slots__ = ("label", "active_cmd", "data", "runtime_node")

    def __init__(self, label, active_cmd, data=None, resume_node=None):
        self.label = label
        self.active_cmd = active_cmd
        self.data = data
        self.runtime_node = resume_node


class MastTicker:
    """Interpreter for one task's compiled `.mast` (BASIC-like linear flow).

    State
    -----
    - ``active_label`` / ``active_cmd`` / ``cmds`` — the current label name, the
      index of the current command within it, and that label's command list.
    - ``runtime_node`` — the live runtime instance for the current command
      (built in ``next()`` via ``enter()``, retired via ``leave()``).
    - ``last_poll_result`` — the most recent ``PollResults`` (drives the caller).
    - ``done`` — task finished.

    Control transfer is *deferred*: methods set ``pending_jump`` /
    ``pending_pop``, and ``tick()`` applies them at the top of its loop.
    **``pending_jump`` always wins over ``pending_pop``.**

    - ``jump(label, cmd)`` — request a jump (sets ``pending_jump``). A jump also
      unwinds any outstanding inline-block frames (see ``pop_on_jump``), because
      jumping out of an inline context abandons it.
    - ``do_jump(...)`` — performs the jump: resolves the target (label name,
      sub/inline label, or runtime node), repoints ``cmds`` /
      ``active_label`` / ``active_cmd``, then ``next()``.
    - ``do_resume(...)`` — re-enters a *saved* ``runtime_node`` (used when an
      inline block pops back to resume the very node that pushed it).

    label_stack (a list of ``PushData``) has two push styles:
    - ``push_label`` — a true "call": saves ``(active_label, active_cmd)`` and
      jumps; the matching ``pop_label`` returns to ``active_cmd + 1``.
    - ``push_inline_block`` — for buttons / dropdowns / event routes that run a
      block and then **resume the same runtime node** that was active when they
      fired. It saves the node too and bumps ``pop_on_jump``.

    ``pop_on_jump`` counts inline-block frames that must be auto-unwound the next
    time we ``jump`` (a jump escapes the inline context). ``pop_label`` chooses
    between resuming the saved node (``do_resume``) and treating the pop like a
    jump back to the caller's next command.
    """
    # Optional coverage/trace seam. When set to a callable, ``next()`` invokes
    # ``on_enter_node(active_label, cmd)`` once each time a command begins
    # executing. Default ``None`` → a single ``is not None`` check, no overhead.
    # Used by dev tooling (cosmos_dev) for MAST node coverage; never set in the
    # shipped library.
    on_enter_node = None

    def __init__(self, task, main):
        self.done = False
        # Set by runtime_error(). A task that CRASHED must never be revived to
        # run a GUI handler -- it stopped mid-statement, so its scope is
        # whatever the exception left behind.
        self.errored = False
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
                # NOTE: top-level `shared` assignments in `main` are pruned in
                # next() when main wraps (see prune_main there), NOT here on
                # jump-into-a-label. The disabled `prune_main()` below is left as
                # a historical marker of that decision.
                #if self.active_label == "main":
                #    self.main.mast.prune_main()

                self.cmds = label_runtime_node.cmds
                self.active_label = label
                self.active_cmd = activate_cmd
                self.runtime_node = None
                self.done = False
                # Inject the entered label's metadata as task variables on a
                # jump/reroute INTO the label (e.g. a GUI route). `_start_task`
                # separately seeds metadata at task creation for spawns, which is
                # needed because a spawned task may first enter at a non-zero
                # command (a brain/objective +++ sub-block) that this skips.
                # `has_metadata` gates this so labels without a metadata block pay
                # only one boolean check; only a top-of-label entry
                # (activate_cmd == 0) applies it. Defaults: a var already set
                # (passed data / live state) wins.
                if activate_cmd == 0 and getattr(label_runtime_node, "has_metadata", False):
                    _syms = self.task.get_symbols()
                    for _k, _v in label_runtime_node.inventory.collections.items():
                        if _k not in _syms:
                            self.task.set_value(_k, _v, Scope.NORMAL)
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

                # A runtime error can be raised by the node's enter(), which runs
                # inside the next()/do_jump above - INSIDE this iteration, after
                # the `while not self.done` test. Without this the errored node is
                # still polled, and it polls with whatever half-state enter() left
                # behind, producing a second error that hides the real one.
                if self.errored:
                    self.done = True
                    return PollResults.FAIL_END if is_sub_task else PollResults.OK_END

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
        except Exception as err:
            # Capture the live exception (file/line/traceback) while it is still
            # in sys.exc_info(); str(err) alone loses the Python location.
            self.runtime_error(format_exception(str(err), "Python exception:"))
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
        self.errored = True
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
            if MastTicker.on_enter_node is not None:
                # Coverage/trace seam (dev-only). Guarded so a hook failure never
                # breaks execution.
                try:
                    MastTicker.on_enter_node(self.active_label, cmd)
                except Exception:
                    pass
        except Exception as err:
            self.runtime_error(str(err))

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
                # NOTE: `fallthrough` is intentionally left True here and is
                # cleared ONLY on OK_END (below). A PyMAST label that yields
                # (suspends) and later runs off its end should still fall through
                # to the next @label, matching MAST `=== label` semantics.
                # (There was a `fallthrough - False` no-op typo here — it
                # computed a value and threw it away; "fixing" it to `= False`
                # would wrongly suppress fall-through after a yield.)
                if res is not None:
                    self.last_poll_result = res
                if res == PollResults.OK_RUN_AGAIN:
                    return self.last_poll_result
                elif res == PollResults.OK_JUMP:
                    break
                elif res == PollResults.OK_IDLE:
                    self.last_poll_result = res
                    return PollResults.OK_IDLE
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

        self.task.main.runtime_error(s)
        self.done = True



class MastAsyncTask(Agent, Promise):
    main: 'MastScheduler'
    dependent_tasks = {}
    # A task's variables are its local scope, not searchable game state. Keeping
    # them out of the global has_inventory() index avoids registering AND
    # unregistering every variable name on every task (the single biggest source
    # of registry traffic), keeps that index narrow for everyone else, and stops
    # a query like has_inventory("ship_id") returning task ids next to ships.
    _mirror_inventory = False

    # Behavior flag for revive_for_handler(). OFF means a GUI handler whose task
    # already ended is dropped exactly as it always was; ON means the task is
    # woken to run it. Off by default until the A/B conformance runs say what
    # flipping it wakes up. See LM issue #707.
    revive_ended_handlers = True

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

        # P2: get_symbols() cache, scoped strictly to a run_on_change() pass.
        # When _symbols_caching is True, the first get_symbols() build is stored
        # and reused by the remaining watcher test() evals (which only read).
        # Caching is disabled while a watcher's run() executes (it may mutate),
        # and cleared when the pass ends, so the main interpreter loop never
        # sees a cached value.
        self._symbols_caching = False
        self._symbols_cache = None


    def add_role(self, role: str):
        """Tagging a task makes it a discoverable RECORD, not just execution.

        procedural/prefab.py sets `prefab = FrameContext.task`, so a prefab IS its
        task: `prefab_torpedo_type` runs once and then tags itself
        ('torpedo_definition' + the torpedo key) so docking can resolve the type
        long after the label finished. Such a task must (a) survive disposal and
        (b) be findable by inventory key like any other agent - so joining the
        has_inventory index is backfilled here, once, rather than paid by every
        short-lived route/comms task that will never be looked up.
        """
        super().add_role(role)
        if not self._mirror_inventory and self.is_data_record():
            self._mirror_inventory = True      # instance attr shadows the class flag
            for k, v in self.inventory.collections.items():
                if v is not None:
                    Agent._has_inventory.add_to_collection(k, self.id)

    def queue_on_change(self, runtime_node):
        if self.is_gui_task:
            self.pending_on_change_items.append(runtime_node)
        else:
            self.on_change_items.append(runtime_node)

    def run_on_change(self):
        any_ran = False
        # P2: reuse one get_symbols() build across the watcher test() evals.
        self._symbols_caching = True
        self._symbols_cache = None
        for change in self.on_change_items:
            if change.test():
                # The watcher fired: its block runs with LIVE (uncached)
                # symbols and may mutate state, so disable caching for run(),
                # then re-enable + clear so the next test() rebuilds.
                self._symbols_caching = False
                self._symbols_cache = None
                change.run()
                self._symbols_caching = True
                self._symbols_cache = None
                any_ran = True
        self._symbols_caching = False
        self._symbols_cache = None
        for st in self.sub_tasks:
            if st.run_on_change():
                any_ran = True
        return any_ran
            
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

    
    def is_data_record(self):
        """True when this task has been tagged for DISCOVERY, so it must outlive
        its own execution.

        A MastAsyncTask is an Agent, and missions legitimately use one as a
        persistent data record: the label runs once to populate it, then tags it
        with roles so other code can find it later. LegendaryMissions registers
        every torpedo type this way (`prefab_torpedo_type` -> roles
        'torpedo_definition' + 'homing'/'nuke'/'beacon'/...), and docking's rearm
        step resolves the type through that role set long after the task ended.
        Disposing such a task deletes the registry.

        A role beyond the built-in __mast_task__ is the signal: nothing adds one
        unless it intends the task to be found.
        """
        return bool(set(getattr(self, "_own_roles", ())) - {"__mast_task__"})

    def dispose(self):
        """Drop a FINISHED task from the Agent registries.

        A task is an Agent: __init__ calls self.add(), which registers it in
        Agent.all, in Agent.roles under __MAST_TASK__, and in Agent._has_inventory
        under EVERY variable name it holds (start_task(inherit=True) copies the
        whole parent scope, so that is a lot of names).  Dropping the task from the
        scheduler's `tasks` list left all of that behind, so a busy mission grew
        Agent.all without bound -- ~150 dead tasks a sim-second on LM, 47k agents
        of which 92% were finished tasks.

        Idempotent, and safe to call while the task object is still referenced:
        this only unregisters the id, it does not invalidate live references
        (`mast_task`, an awaited promise's result).  A task that is later revived
        via jump_restart_task re-registers itself there.
        """
        if self.is_data_record():
            return                # tagged for discovery - it outlives its code
        for st in list(self.sub_tasks):
            st.dispose()          # sub-tasks share the parent's lifecycle
        self.sub_tasks = []
        self.remove()

    # NOTE on reclamation: unregistering is enough for the OBJECT to die too, but
    # only via Python's CYCLIC collector - a task references itself four ways (the
    # "mast_task" inventory value, mast_ticker, py_ticker, root_task), so refcounting
    # alone never frees it. One task per scheduler also stays pinned by
    # `scheduler.active_task` until the next task ticks; that pointer is deliberately
    # NOT cleared here, because callers read it after a run to fetch results.

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
        # P2: within a run_on_change() pass, reuse the built namespace across the
        # watcher test() evals (see __init__/run_on_change). Outside that pass
        # _symbols_caching is False, so this always rebuilds (unchanged behavior).
        if self._symbols_caching and self._symbols_cache is not None:
            return self._symbols_cache
        if self.root_task != self:
            m1 = self.root_task.get_symbols()
            #
            # Sub task can have a small set of overrides
            #
            m1 =   m1 | self.inventory.collections
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
        if self._symbols_caching:
            self._symbols_cache = m1
        return m1

    def set_value(self, key, value, scope):
        if scope == Scope.SUB_TASK_LOCAL and self.is_sub_task:
            self.set_inventory_value(key, value)
            return scope
        elif self.root_task != self:
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
        if self.is_sub_task and self.get_inventory_value(key) is not None:
            self.set_inventory_value(key, value)
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
        if val is None and self.is_sub_task and self.root_task != self:
            return self.root_task.get_value(key, defa)

        if val is not None:
            return (val, Scope.NORMAL)
        val = self.main.get_value(key, defa)
        if val[1] != Scope.UNKNOWN:
            return val
        return (defa, Scope.NORMAL)
    
    def get_scoped_value(self, key, defa, scope):
        if scope == Scope.TEMP or scope == Scope.SUB_TASK_LOCAL:
            data = None
            # if self.redirect:
            #     data = self.redirect.data
            if len(self.label_stack) > 0:
                data = self.label_stack[-1].data
            if data is not None:
                val = data.get(key, None)
                if val is not None:
                    return val
            val = self.get_inventory_value(key)
            if val is not None:
                return val
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
        """
        Check if the provided variable keys are defined in this task.
        Args:
            keys (str): A comma-separated list of the keys.
        Returns:
            bool: True if all variables are defined, otherwise False.
        """
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
            value = eval(message, _EVAL_GLOBALS, allowed)
            return value
        except Exception as err:
            # `message` here is a CODE OBJECT, so printing it directly says only
            # "<code object <module> ...>". Quote the template text instead.
            s = f"FORMAT String error:\n\t{mast_expr_source(message) or message}\n"
            s += f"{type(err).__name__}: {err}"
            self.runtime_error(s)
        return ""
        
    
    def compile_and_format_string(self, value):
        if isinstance(value, str) and "{" in value:
            from .mast_node import compile_format_string
            code = compile_format_string(value)
            value = self.format_string(code)
        return value



    def eval_code_checked(self, code, end_on_exception=True):
        """Evaluate a MAST expression, returning EVAL_ERROR if it raised.

        Prefer this over ``eval_code`` anywhere the VALUE is used: ``None`` is a
        legal MAST value, so it cannot carry "this blew up" - see EVAL_ERROR.
        """
        try:
            allowed = self.get_symbols()
            return eval(code, _EVAL_GLOBALS, allowed)
        except Exception:
            err = format_exception(describe_eval_failure(code), "Mast eval level Runtime Error:")
            if end_on_exception:
                self.runtime_error(err)
                self.end()
            else:
                # Non-fatal path: still report it. A bare print() never reaches
                # mast.runtime.log, which is where everyone looks.
                logging.getLogger("mast.runtime").warning(err)
            return EVAL_ERROR

    def eval_code(self, code, end_on_exception=True):
        """Backward-compatible wrapper: a failed expression still returns None.

        Kept so every existing caller (including mission code) behaves exactly as
        before. Library nodes use eval_code_checked so they can stop instead.
        """
        value = self.eval_code_checked(code, end_on_exception)
        return None if value is EVAL_ERROR else value

    def exec_code(self, code, vars, gbls):
        try:
            if vars is not None:
                allowed = vars | self.get_symbols()
            else:
                allowed = self.get_symbols()
            if gbls is not None:
                exec(code, {"__builtins__": MastGlobals.globals | gbls}, allowed)
            else:
                exec(code, _EVAL_GLOBALS, allowed)
        except Exception:
            err = format_exception(describe_eval_failure(code), "Mast exec level Runtime Error:")
            self.runtime_error(err)
            self.end()


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
        
        t= MastAsyncTask(self.main, None, task_name)
        #
        # Sub tasks Share Scope
        #
        if inputs is not None:
            for k in inputs:
                t.set_value(k, inputs[k], Scope.SUB_TASK_LOCAL)

        t.is_sub_task = True
        t.root_task = self
        if task_name is not None:
            self.set_value(task_name, t, Scope.NORMAL)

                # 
        # Look for sub label
        #
        if isinstance(label, str) and active_cmd == 0:
            label_obj = self.active_label_object 
            if label_obj is not None and isinstance(label_obj, Label):
                sub_label = label_obj.labels.get(label)
                if sub_label is not None:
                    label = label_obj
                    active_cmd = sub_label.loc
            
        t.jump(label,active_cmd)
        self.sub_tasks.append(t)
        if not defer:
            t.tick_in_context()
        return t
    
    def remove_sub_task(self, t):
        t.end()

    def remove_all_sub_tasks(self):
        for t in list(self.sub_tasks):
            t.end()

    
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
                    rem.dispose()   # finished: unregister it from the Agent registries
            done = []

    def jump_restart_task(self, label = "main", activate_cmd=0):
        """
        Used by the mission runner to run multiple labels
        """
        self.set_result(None)
        self.active_ticker.done = False
        # An explicit restart re-arms the task, crash and all: the caller is asking
        # for a DIFFERENT label to run. (revive_for_handler deliberately refuses an
        # errored task; this is the other case.) Without this the ticker's
        # errored-bail would end the restarted task before it ran a command.
        self.active_ticker.errored = False
        # Revive: if this task already finished it was disposed out of Agent.all,
        # so re-register before it runs again (add() is keyed by id, so a task
        # that was never disposed just re-registers itself harmlessly).
        self.add()
        self.jump(label, activate_cmd)
        self.tick_in_context()

    def revive_for_handler(self, host=None):
        """Wake a task that ENDED NORMALLY so a GUI handler it registered can run.

        A widget's handler is owned by the task that BUILT the widget: an
        `on gui_message(w):` block is an inline block in that task's label, and
        `on_press=<label>` is a jump on that task. When the builder was
        scheduled and then ended (->END / yield success) the handler had no way
        to run at all -- push_inline_block only queues pending_jump, and tick()
        returns at its leading `if self.done:` before ever reading it. The click
        was discarded silently. See LM issue #707.

        Returns True when the task is runnable afterwards.

        Reviving in place rather than spawning a fresh task keeps the builder's
        own scope, active_label and identity, so the block still closes over the
        locals its author wrote it against -- and, with the inline block pop
        fixed, the woken task pops back to its own ->END and finishes again.

        `host` is the task that will TICK the revived one (the page's gui_task),
        so a handler that awaits still gets ticks. It is a ticking parent only:
        is_sub_task/root_task are deliberately left alone, because changing them
        would change variable scoping.
        """
        ticker = self.active_ticker
        if not (self.done() or ticker.done):
            return True                      # still live -- nothing to do
        if not MastAsyncTask.revive_ended_handlers:
            return False
        if self.canceled() or getattr(ticker, "errored", False):
            # Deliberately killed, or crashed. Neither should come back.
            return False
        # A task is a Promise, and both MastScheduler.tick and tick_subtasks
        # drop it on done(); clearing the result is what makes it schedulable
        # again. jump_restart_task does the same three things for the same
        # reason -- add() re-registers it after dispose() unregistered it.
        self.set_result(None)
        ticker.done = False
        self.add()
        self._revived_handler = True
        if host is not None and host is not self and self not in host.sub_tasks:
            host.sub_tasks.append(self)
        return True

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
    def sweep_finished(cls):
        """Backstop: dispose any FINISHED task still sitting in the registries.

        Disposing at the two points where a task leaves `tasks` / `sub_tasks`
        catches the common case, but tasks are started from a dozen places
        (routes, comms, science, overlays) and some run to completion outside
        those lists -- notably a sub-task whose parent never ticks again, which
        leaves it done-but-registered forever. This sweep is creation-site
        agnostic: if it is done, it does not belong in the registries.

        Cheap: it walks the __mast_task__ role set, not all of Agent.all, and
        runs on the GarbageCollector cadence rather than every frame. dispose()
        is idempotent, and a task revived later by jump_restart_task re-registers.
        """
        ids = Agent.roles.collection_set("__mast_task__")
        if not ids:
            return 0
        swept = 0
        for tid in list(ids):
            t = Agent.all.get(tid)
            if t is not None and t.done() and not t.is_data_record():
                t.dispose()
                swept += 1
        return swept

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
    # Optional verdict/trace seam. When set to a callable, every reported MAST
    # runtime error invokes ``on_runtime_error(message)``. Default ``None`` → a
    # single ``is not None`` check, no overhead; never set in the shipped library.
    # Used by dev tooling (cosmos_dev) to turn a headless run into a pass/fail.
    # Fired from both this base ``runtime_error`` and the story-scheduler override.
    on_runtime_error = None

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
        if MastScheduler.on_runtime_error is not None:
            try:
                MastScheduler.on_runtime_error(message)
            except Exception:
                pass
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
        # Merge the label's metadata as the task's base variables (passed data
        # overrides). do_jump ALSO injects metadata, but only on a top-of-label
        # (activate_cmd == 0) entry; a spawned task may begin inside a sub-block
        # (e.g. a brain/objective +++ block) at a non-zero command, which do_jump
        # skips - so the spawn path must seed metadata here.
        if hasattr(label, "inventory"):
            if inputs is None:
                inputs = label.inventory.collections.copy()
            else:
                inputs = label.inventory.collections.copy() | inputs
        t= MastAsyncTask(self, inputs, task_name)
        return t


    def start_task(self, label = "main", inputs=None, task_name=None, defer=False, unscheduled=False, loc=0)->MastAsyncTask:
        t = self._start_task(label, inputs, task_name)
        if task_name is not None:
            t.set_value(task_name, t, Scope.NORMAL)

        restore = FrameContext.task
        FrameContext.task = t
        t.jump(label, loc)
        FrameContext.task = restore
        if not unscheduled:
            self.tasks.append(t)
        if not defer:
            self.on_start_task(t)

        return t

    def schedule(self, task):
        self.tasks.append(task)


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
                    rem.dispose()   # finished: unregister it from the Agent registries
            self.done = []

        for task in self.tasks:
            task.run_on_change()

        if len(self.tasks):
            return True
        else:
            return False


