from enum import IntEnum
class PollResults(IntEnum):
    OK_JUMP= 1
    OK_ADVANCE_TRUE =2
    OK_ADVANCE_FALSE=3
    OK_RUN_AGAIN=4
    OK_YIELD=5 # This will advance, but run again
    OK_END = 99
    OK_SUCCESS = 99
    BT_SUCCESS = 99
    FAIL_END = 100
    BT_FAIL = 100
    OK_IDLE = 999

