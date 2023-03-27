from enum import IntEnum
class PollResults(IntEnum):
    OK_RUN_AGAIN=1
    OK_ADVANCE_TRUE =2
    OK_ADVANCE_FALSE=3
    OK_JUMP= 4
    OK_END = 99
    FAIL_END = 100
