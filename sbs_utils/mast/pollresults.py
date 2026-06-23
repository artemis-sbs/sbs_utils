from enum import IntEnum
class PollResults(IntEnum):
    """Result of a runtime node ``poll()`` — tells the ticker what to do next.

    Flow results:
    - ``OK_JUMP``         — control moved (jump/pop applied); re-loop, don't advance.
    - ``OK_ADVANCE_TRUE`` / ``OK_ADVANCE_FALSE`` — step to the next command
      (the TRUE/FALSE distinction carries a condition outcome for the caller).
    - ``OK_RUN_AGAIN``    — keep polling this same node next tick.
    - ``OK_YIELD``        — advance, but the task yields this tick (see
      ``yields_once``).
    - ``OK_IDLE``         — behavior-tree "still running"; stop ticking this pass.

    Terminal results — NOTE the deliberate value aliasing (IntEnum collapses
    equal values, so the later names are *aliases* of the first):
    - ``OK_END == OK_SUCCESS == BT_SUCCESS == 99``  (success / normal end)
    - ``FAIL_END == BT_FAIL == 100``                 (failure end)
    The ``BT_*`` / ``*_SUCCESS`` spellings exist so behavior-tree code reads
    naturally; they are the same values as the flow ``*_END`` results.
    """
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

