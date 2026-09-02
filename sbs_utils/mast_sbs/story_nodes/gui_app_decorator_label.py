from ...mast.mast_node import IF_EXP_REGEX, mast_node, mast_compile, EVAL_ERROR
from ...mast.core_nodes.decorator_label import DecoratorLabel
import re
from ...mast.core_nodes.inline_function import FuncCommand

@mast_node(append=False)
class GuiAppDecoratorLabel(DecoratorLabel):
    """A screen INSIDE the ePADD, as against a destination on the tab bar.

    The twin of `GuiTabDecoratorLabel`, and deliberately a separate kind rather than a
    flag on it, because the two answer different questions:

    * a TAB's `if` answers "may this be offered on the bar";
    * an APP's `if` answers "is this app available right now".

    One route kind doing both is what made the PADD's Back inherit a tab's condition -
    `//gui/tab/away if not gui_app_mode_is_on()` correctly hid away as a tab and deleted
    the way back to the away console with it.

    THE ACTIVATION KEY IS THE OTHER HALF. This injects `gui_app_activate`, which writes
    `__active_app__` and never touches `__active_tab__` - so the tab a player was on when
    they opened the PADD is still recorded, and that is what the PADD's single Back
    returns to. Nothing has to remember it.

    ORDER MATTERS AT IMPORT. `@mast_node(append=False)` inserts at the FRONT of the node
    list and the compiler takes the first match, so `story_nodes/__init__.py` has to
    import this AFTER `route_label` - otherwise `//gui/app/x` is swallowed by
    `RouteDecoratorLabel`'s `case ["gui", *b]` and becomes a navigation route.
    """
    rule = re.compile(r'(\/\/)gui/app/(?P<path>([\w]+))'+IF_EXP_REGEX)

    all = {}

    @classmethod
    def clear(cls):
        """Drop registered //gui/app labels (fresh mission / in-process recompile).

        Called from `reset_mission_state`. Without it the table carries two generations
        of routes across an in-process reload, and opening an app runs a label from the
        dead compile.
        """
        cls.all = {}

    def __init__(self, path, if_exp=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        self.label_weight = id
        name = f"gui/app/{path}/{id}"
        super().__init__(name, loc)

        self.path= path
        self.description = ""
        self.if_exp = if_exp

        GuiAppDecoratorLabel.all[path] = self

        # need to negate if
        self.code = None
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            try:
                self.code = mast_compile(self.if_exp, "eval")
            except:
                raise Exception(f"Syntax error '{if_exp}'")

        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self, parent):
        return False

    def generate_label_end_cmds(self, compile_info=None):
        # Allow this to follow into === labels
        pass

    def generate_label_begin_cmds(self, compile_info=None):
        cmd = FuncCommand(py_cmds=f'gui_app_activate("{self.path}")', compile_info=compile_info)
        cmd.file_num = self.file_num
        cmd.line_num = self.line_num
        cmd.line = f"gui_app_activate {self.name}"
        self.add_child(cmd)

    def test(self, task):
        if self.code is None:
            return True
        value = task.eval_code_checked(self.code)
        # A condition that RAISED is reported and read as "not shown" - it is
        # never quietly treated as true.
        return False if value is EVAL_ERROR else value
