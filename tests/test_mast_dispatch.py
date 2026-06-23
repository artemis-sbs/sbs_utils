"""Guards the compiler's first-char dispatch (mast.py) against under-claiming.

The compiler skips any node whose rule provably cannot match the current line's
first character. That is only correct if the first-char set for a node never
OMITS a character the rule can actually start with -- otherwise dispatch could
skip the true winning node and mis-parse. This test walks representative source
and asserts that for every token, the full-scan winner is also a dispatch
candidate (i.e. its first-char set is None or contains the line's first char).
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
import unittest

from sbs_utils.mast.mast import (
    first_non_whitespace_index,
    first_non_newline_index,
    first_newline_index,
    _node_first_chars,
)
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  populates MastNode.nodes
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.first_chars import first_chars_for_pattern

# A grab-bag exercising as many node types as practical. It does not need to be
# a runnable mission -- the test only inspects which node *wins* at each line.
SAMPLE = """
shared count = 0
default name = "ship"
x = 1 + 2
y += 3
# a comment
== a_label ==
    log("hi")
    if x > 1:
        count += 1
    elif x > 0:
        count += 2
    else:
        count += 3
    for i in range(3):
        count += i
    for v while count < 10:
        count += 1
    match name:
        case "ship":
            log("ship")
        case _:
            log("other")
    with content:
        log("inside")
    await delay_sim(5)
    await count > 5:
        log("done")
    on change count:
        log("changed")
    on signal go:
        log("signal")
    ~~ d = {"k": 1} ~~
    metadata: ``` yaml
    type: brain/npc
    ```
    yield success
    -> END
    jump a_label
---inline_pt
    break
//signal/enemy_spotted
    log("spotted")
//shared/signal/global_thing
    log("shared")
//comms
    + "Hail" //comms/sub
    * "One shot":
        log("clicked")
//spawn
    log("spawned")
=$ raider red, white
<< [green] "Title"
    % line one
    % line two
@map/secret "Secret Meeting"
    log("map")
@media/music/default "Music"
@console/helm !0 ^5 "Helm"
    gui_console("helm")
///enable
    log("inline route")
"""


def full_winner(src, pos):
    for nc in MastNode.nodes:
        mo = nc.parse(src, pos)
        if mo:
            return nc, mo.end
    return None, None


def walk_tokens(src):
    src = src.replace("\r", "")
    length = len(src)
    pos = 0
    while pos < length:
        ws = first_non_whitespace_index(src, pos)
        pos = ws[0]
        if pos >= length:
            break
        ch = src[pos]
        nc, end = full_winner(src, pos)
        yield pos, ch, nc
        if nc is None:
            nn = first_non_newline_index(src, pos)
            pos = nn if nn > pos else first_newline_index(src, pos) + 1
        else:
            pos = end if end > pos else pos + 1


class TestMastDispatch(unittest.TestCase):
    def test_no_under_claim_on_sample(self):
        violations = []
        winners = set()
        for pos, ch, nc in walk_tokens(SAMPLE):
            if nc is None:
                continue
            winners.add(nc.__name__)
            fc = _node_first_chars(nc)
            if fc is not None and ch not in fc:
                violations.append((pos, repr(ch), nc.__name__))
        self.assertEqual(violations, [], f"dispatch would skip true winner(s): {violations}")
        # Make sure the sample actually exercised a healthy spread of node types.
        self.assertGreaterEqual(len(winners), 15, f"sample too thin, only hit: {sorted(winners)}")

    def test_every_node_first_chars_is_set_or_none(self):
        for nc in MastNode.nodes:
            fc = _node_first_chars(nc)
            self.assertTrue(fc is None or isinstance(fc, set), f"{nc.__name__} -> {fc!r}")

    def test_analyzer_known_patterns(self):
        # Spot-check the analyzer on representative patterns.
        self.assertEqual(first_chars_for_pattern(r"metadata:"), {"m"})
        self.assertEqual(first_chars_for_pattern(r"//signal/x"), {"/"})
        self.assertEqual(first_chars_for_pattern(r"(if|elif)\s"), {"i", "e"})
        # optional leading group must union with the continuation, not replace it
        self.assertEqual(first_chars_for_pattern(r"(from\s+)?import\s+x"), {"f", "i"})
        # uncertain constructs collapse to None (match-anything / never skip)
        self.assertIsNone(first_chars_for_pattern(r".*=.*"))
        self.assertIsNone(first_chars_for_pattern(r"\w+"))


if __name__ == "__main__":
    unittest.main()
