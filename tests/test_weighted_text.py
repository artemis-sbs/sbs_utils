import unittest
from sbs_utils.mast.mast_node import DescribableNode


class _FakeTask:
    """Minimal task stand-in: evaluates a gate string against a scope."""
    def __init__(self, scope):
        self.scope = scope

    def eval_code(self, code, end_on_exception=True):
        try:
            return eval(code, {}, self.scope)
        except Exception:
            return None


class TestWeightedTextOptions(unittest.TestCase):
    def test_parse_weight_and_gate(self):
        n = DescribableNode()
        n.add_option("%", "a")
        n.add_option("%2", "b")
        n.add_option("%{honest>40}", "c")
        n.add_option("%3{kind>0}", "d")
        self.assertEqual(n.option_weights, [1, 2, 1, 3])
        self.assertEqual(n.option_gates, [None, None, "honest>40", "kind>0"])
        self.assertEqual(n.options, ["a", "b", "c", "d"])

    def test_plain_uniform_no_task(self):
        n = DescribableNode()
        n.add_option("%", "a")
        n.add_option("%", "b")
        self.assertIn(n.pick_option(None), ["a", "b"])

    def test_gate_filters_by_condition(self):
        n = DescribableNode()
        n.add_option("%{x>40}", "high")
        n.add_option("%", "base")
        self.assertEqual(
            set(n.pick_option(_FakeTask({"x": 50})) for _ in range(40)),
            {"high", "base"})
        self.assertEqual(
            set(n.pick_option(_FakeTask({"x": 10})) for _ in range(40)),
            {"base"})

    def test_all_gated_out_returns_none(self):
        n = DescribableNode()
        n.add_option("%{x>40}", "only")
        self.assertIsNone(n.pick_option(_FakeTask({"x": 10})))

    def test_quote_continuation_keeps_alignment(self):
        n = DescribableNode()
        n.add_option("%", "Hello ")
        n.append_text('"', "world")
        self.assertEqual(n.options, ["Hello world"])
        self.assertEqual(n.option_weights, [1])
        self.assertEqual(n.option_gates, [None])


if __name__ == "__main__":
    unittest.main()
