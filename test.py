from sbs_utils.mast.mast import Mast, PY_EXP_REGEX, IF_EXP_REGEX
from sbs_utils.mast.mastsbs import MastSbs



print(r"""((button\s+["'](?P<message>.+?)["'])(\s*data\s*=\s*(?P<data>"""+PY_EXP_REGEX+r"""))?"""+IF_EXP_REGEX+r")|(?P<end>end_button)")