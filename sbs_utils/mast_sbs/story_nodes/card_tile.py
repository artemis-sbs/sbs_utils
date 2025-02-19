from ...mast.mast_node import IF_EXP_REGEX, STRING_REGEX_NAMED, mast_node
from .card_base import CardLabelBase
import re

    
@mast_node()
class TileCardLabel(CardLabelBase):
    rule = re.compile(r'@tile/(?P<path>([\w/]+))[ /t]*'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name=None, q=None, if_exp=None, loc=None, compile_info=None):
        super().__init__("tile", path, display_name, if_exp, loc, compile_info)

    def generate_label_end_cmds(self, compile_info=None):
        super().generate_label_end_cmds(compile_info)
        #
        # Spawn any sub tasks
        #

    def apply_metadata(self, data):
        return super().apply_metadata(data)

