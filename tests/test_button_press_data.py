"""A Python `on_press` gets the button's `data` - if it asks for it.

`MessageHandler.on_message` called a callable handler as `handler()`, flatly, and
`data=` reached MAST task variables only. So a Python handler could be GIVEN data and
had no way to read it: the obvious `def press(event=None, sender=None, **kw)` reading
`sender.data` got an empty dict and every value None, silently. That is how the xESS
shipped a FIRE app whose buttons did nothing and a Back that worked only sometimes -
"sometimes" because the handlers fell back to the ambient page for the client.

THE DISCRIMINATOR IS REQUIRED PARAMETERS, NEVER PARAMETER COUNT, and that is the whole
risk in this change. The house idiom for these handlers is a closure with BOUND
DEFAULTS - `lambda _cid=client_id: ...`, `def press(_mid=mid, _index=i, _seq=s)` -
because a no-argument call cannot tell one press from another, and every shipped caller
in the library and in LM is written that way. Those declare parameters; they just all
have defaults. Counting parameters would call them with an event and CLOBBER the values
they were binding, which would break every button in the game.

So the first class here is the backward-compatibility class, and it is the one that
matters.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from sbs_utils.procedural.gui.button import (call_press_handler,
                                             press_handler_arity)


class _Item:
    def __init__(self, data=None):
        self.data = data


class _Event:
    client_id = 7
    sub_tag = "x"


class EveryExistingCallerIsUNTOUCHED(unittest.TestCase):
    """Bound-default closures must keep being called with NOTHING."""

    def test_a_bare_lambda(self):
        seen = []
        call_press_handler(lambda: seen.append("ran"), _Item({"cid": 1}), _Event())
        self.assertEqual(["ran"], seen)

    def test_a_lambda_with_ONE_bound_default(self):
        """`lambda _cid=client_id: ...` - the shape `boarding_gui` ships."""
        seen = []
        call_press_handler(lambda _cid=99: seen.append(_cid), _Item({"cid": 1}),
                           _Event())
        self.assertEqual([99], seen, "the bound default was clobbered")

    def test_a_closure_with_THREE_bound_defaults(self):
        """`messages_gui._reply_strip`'s reply buttons, exactly."""
        seen = []

        def press(_mid=5, _index=2, _seq=9):
            seen.append((_mid, _index, _seq))

        call_press_handler(press, _Item({"cid": 1}), _Event())
        self.assertEqual([(5, 2, 9)], seen)

    def test_a_handler_that_takes_only_kwargs(self):
        """`**kwargs` alone requires nothing, so it is still called with nothing -
        which is deliberate. It is indistinguishable from a bound-default closure,
        and between breaking a shipped button and leaving one author to name a
        parameter, the shipped button wins."""
        seen = []
        call_press_handler(lambda **kw: seen.append(kw), _Item({"cid": 1}), _Event())
        self.assertEqual([{}], seen)

    def test_an_unintrospectable_callable_is_called_with_nothing(self):
        """Some C callables cannot be read at all - `inspect.signature(int)` raises
        ValueError. Those answer 0, which is what every caller had before this
        existed: being unable to read a handler is never a reason to change how it is
        called.

        NOT `print`, which the first version of this test used. Modern CPython reports
        a signature for it - `(*args, sep, end, ...)` - so it is introspectable and
        correctly answers 2. The test premise was wrong, not the rule."""
        self.assertEqual(0, press_handler_arity(int))


class AHandlerThatASKS_IS_GIVEN(unittest.TestCase):
    def test_one_required_parameter_gets_the_data(self):
        seen = []
        call_press_handler(lambda data: seen.append(data), _Item({"cid": 4}), _Event())
        self.assertEqual([{"cid": 4}], seen)

    def test_two_required_parameters_get_the_data_and_the_event(self):
        seen = []
        call_press_handler(lambda data, event: seen.append((data, event.client_id)),
                           _Item({"cid": 4}), _Event())
        self.assertEqual([({"cid": 4}, 7)], seen)

    def test_a_required_parameter_beside_bound_defaults(self):
        """Mixing the two is legal and reads the way it looks: one required, so one
        argument, and the defaults stay bound."""
        seen = []

        def press(data, _tag="t"):
            seen.append((data, _tag))

        call_press_handler(press, _Item({"cid": 4}), _Event())
        self.assertEqual([({"cid": 4}, "t")], seen)

    def test_star_args_gets_everything(self):
        seen = []
        call_press_handler(lambda *a: seen.append(len(a)), _Item({"cid": 4}), _Event())
        self.assertEqual([2], seen)

    def test_no_data_is_None_rather_than_an_error(self):
        seen = []
        call_press_handler(lambda data: seen.append(data), _Item(None), _Event())
        self.assertEqual([None], seen)

    def test_more_than_two_required_is_capped_at_two(self):
        """Rather than raising at click time, deep inside a GUI present. The handler
        will raise its own TypeError, which names the function and the arguments."""
        def press(a, b, c):
            pass
        self.assertEqual(2, press_handler_arity(press))


class TheArityIsCACHED(unittest.TestCase):
    def test_the_same_callable_answers_the_same_twice(self):
        def press(data):
            pass
        self.assertEqual(press_handler_arity(press), press_handler_arity(press))

    def test_a_bound_method_is_read_without_its_self(self):
        """`self` is already bound, so a method taking (self, data) requires one."""
        class Panel:
            def press(self, data):
                pass
        self.assertEqual(1, press_handler_arity(Panel().press))


if __name__ == "__main__":
    unittest.main()
