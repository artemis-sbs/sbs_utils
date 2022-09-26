from sbs_utils.quests.quest import JUMP_CMD_REGEX,JUMP_ARG_REGEX, TIME_JUMP_REGEX, MIN_SECONDS_REGEX, TIMEOUT_REGEX, OPT_JUMP_REGEX, OPT_COLOR
from sbs_utils.quests.sbsquest import Comms
import re

print(JUMP_CMD_REGEX)
re.compile(JUMP_CMD_REGEX)

print(JUMP_ARG_REGEX)
re.compile(JUMP_ARG_REGEX)
print(OPT_JUMP_REGEX)
re.compile(OPT_JUMP_REGEX)

print(MIN_SECONDS_REGEX)
re.compile(MIN_SECONDS_REGEX)

print(TIME_JUMP_REGEX)
re.compile(TIME_JUMP_REGEX)



print(TIMEOUT_REGEX)
re.compile(TIMEOUT_REGEX)

print(OPT_JUMP_REGEX+TIMEOUT_REGEX)
re.compile(OPT_JUMP_REGEX+TIMEOUT_REGEX)

print(r'(?P<from_tag>\w+)\s+near\s+(?P<to_tag>\w+)\s*(?P<distance>\d+)'+OPT_JUMP_REGEX+TIMEOUT_REGEX)

print(r"""(?P<button>\*|\+|button|button\s+once)\s+["'](?P<message>.+?)["']"""+OPT_COLOR+JUMP_ARG_REGEX+r"""(\s+if(?P<if_exp>.+))?""")