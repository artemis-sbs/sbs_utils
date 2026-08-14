"""`//overlay/<kind>` — author a custom overlay builder as a MAST route.

The route body builds the card with the usual gui_* verbs; the content fields passed
to overlay_show(slot, "<kind>", ...) arrive as task variables. At load the route
registers itself as the builder for `<kind>` (via overlay_register_label), so there is
no separate registration call — the MAST-native, sugar form of overlay_register_label::

    //overlay/hero_card
        gui_row("row-height: content;")
        gui_text(f"$text:{gui_text_escape(title)};justify:center;font:gui-6")

    # then anywhere: overlay_show("center_hero", "hero_card", title="CHAPTER TWO")

Mirrors the //signal route node: a hidden label whose body is the route, plus a
FuncCommand injected into main that registers it once.
"""
import re
import ast
from ...mast.mast_node import mast_node, IF_EXP_REGEX
from ...mast.core_nodes.decorator_label import DecoratorLabel
from ...mast.core_nodes.yield_cmd import Yield
from ...mast.core_nodes.inline_function import FuncCommand


@mast_node(append=False)
class OverlayRouteDecoratorLabel(DecoratorLabel):
    rule = re.compile(r'//overlay/(?P<kind>(\w[\w\/]*))' + IF_EXP_REGEX)

    def __init__(self, kind, if_exp=None, loc=None, compile_info=None):
        id = DecoratorLabel.next_label_id()
        kind = kind.strip('/')
        name = f"__overlay__{kind.replace('/', '_')}__{id}__"
        super().__init__(name, loc)
        self.label_weight = id
        self.kind = kind
        self.if_exp = if_exp.strip() if if_exp else None
        if self.if_exp is not None:
            self.if_exp = ast.unparse(ast.parse(self.if_exp))   # strip comments / catch errors
        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self, p):
        return False

    def generate_label_begin_cmds(self, compile_info=None):
        # Register this label as the builder for `kind`, once, on the first run of
        # main. overlay_register_label accepts the label NAME (start_task resolves it).
        cmd = FuncCommand(
            py_cmds=f'overlay_register_label("{self.kind}", "{self.name}")',
            compile_info=compile_info)
        cmd.file_num = self.file_num
        cmd.line_num = self.line_num
        cmd.line = f"overlay_register_label in main for {self.name}"
        compile_info.main.add_child(cmd)

    def generate_label_end_cmds(self, compile_info=None):
        # A builder is build-only: end after building so the one-shot tick completes.
        p = compile_info.label if compile_info is not None else None
        if not self.can_fallthrough(p):
            cmd = Yield('success', compile_info=compile_info)
            cmd.file_num = self.file_num
            cmd.line_num = self.line_num
            cmd.line = f"yield success at end of {self.name}"
            self.add_child(cmd)
