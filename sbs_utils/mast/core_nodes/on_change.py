from ..mast_node import MastNode, mast_node, BLOCK_START, mast_compile
from .await_cmd import Await
import re



@mast_node()
class OnChange(MastNode):
    # val is lazy (`+?`) and allows colons so a `:` inside a quoted string
    # (e.g. on gui_message(gui_button("Test Upgrades:")):) doesn't get mistaken
    # for the block-start colon -- BLOCK_START requires the colon be followed by
    # end-of-line/comment, so lazy expansion walks past string colons to it.
    # (Matches how the `if` rule handles the same case.)
    rule = re.compile(r"on[ \t]+(change[ \t]+)?(?P<val>[ \t\S]+?)"+BLOCK_START)
    def __init__(self, end=None, val=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        self.value = val
        if val:
            self.value = mast_compile(val, "eval")

        self.is_end = False
        #
        # Check to see if this is embedded in an await
        #
        await_stack = compile_info.ctx.await_stack
        on_change_stack = compile_info.ctx.on_change_stack
        self.await_node = None
        if len(await_stack) > 0:
            self.await_node = await_stack[-1]
        self.end_node = None

        if end is not None:
            on_change_stack[-1].end_node = self
            self.is_end = True
            on_change_stack.pop()
        else:
            on_change_stack.append(self)

    def is_indentable(self):
        return True
    
    def mus_indent(self):
        return True

    def create_end_node(self, loc, dedent_obj, compile_info):
        """ cascade the dedent up to the start"""
        self.dedent_loc = loc
        end = OnChange("on_end", loc = loc, compile_info=compile_info)
        end.dedent_loc = loc+1
        return end

   
from ..pollresults import PollResults
from ..mast_runtime_node import MastRuntimeNode, mast_runtime_node
from ..mast import Scope
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..mast import Mast
    from ..mastscheduler import MastAsyncTask

from ...futures import Trigger

@mast_runtime_node(OnChange)
class OnChangeRuntimeNode(MastRuntimeNode):
    # Behavior flag: pop the inline block when it reaches its end node, instead
    # of only when this instance's is_running is set -- which it never is, see
    # poll(). Default OFF until the A/B conformance runs measure what it wakes.
    # See LM issue #707.
    pop_inline_block_on_end = True

    def enter(self, mast:'Mast', task:'MastAsyncTask', node: OnChange):
        self.task = task
        self.node = node
        self.is_running = False
        self.node_label = self.task.active_label
        if not node.is_end:
            self.value = task.eval_code(node.value)
            # Triggers handle things themselves
            if not isinstance(self.value, Trigger):  
                task.queue_on_change(self)
            # If the label is set don't override it
            # Python must have set it
            else:
                self.value.loc = node.loc+1
                self.value.label = task.active_label

            # TODO
            # Hmmm A little leakage that it uses PAGE
            # Move this to Task>
            #

    def test(self):
        prev = self.value
        self.is_running = False
        self.value = self.task.eval_code(self.node.value) 
        return prev!=self.value
    
    def run(self):
        # The block IS the builder's code, so it can only run on the builder --
        # exactly like an `on gui_message` inline block. If the builder has
        # ended, wake it the same way the click path does; push_inline_block on
        # a finished task only queues a jump that tick() returns before reading.
        # See LM #713.
        from ..mastscheduler import MastAsyncTask
        if self.task.done() or self.task.active_ticker.done:
            if not MastAsyncTask.rehost_gui_watchers:
                return
            if not self.task.revive_for_handler(self.task.gui_host_task()):
                from ...procedural.gui.message import warn_dead_handler
                warn_dead_handler(self.task, self.node_label, self.node.loc,
                                  "`on change` block")
                return
        self.is_running = True
        self.task.push_inline_block(self.node_label, self.node.loc+1)
        self.task.tick_in_context()

    def dequeue(self):
        pass

    def poll(self, mast:'Mast', task:'MastAsyncTask', node: OnChange):
        # The end node is only ever REACHED by running the block: normal flow
        # jumps over it from the start node below. So popping here is sound.
        #
        # `self.is_running` cannot be the gate: MastTicker.next() builds a fresh
        # runtime node for every command, so the instance that reaches the end
        # node is never the instance run() set is_running on. The pop was
        # therefore dead code, and a block that fell off its end left the task
        # parked on this node forever -- never resuming its await, never ending,
        # and growing label_stack once per trip through the block.
        if node.is_end and (OnChangeRuntimeNode.pop_inline_block_on_end
                            or self.is_running):
            self.task.pop_label(False)
            self.is_running = False
            # This is run again intentionally
            # The change aspect is done, no need to run anything 
            # again for this fork of the task 
            #
            return PollResults.OK_RUN_AGAIN
        if node.end_node:
            self.task.jump(self.node_label, node.dedent_loc+1)
            return PollResults.OK_JUMP
        return PollResults.OK_RUN_AGAIN


