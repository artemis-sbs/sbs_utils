"""Does `typings/sbs/__init__.pyi` still describe the engine that is installed?

WHY THIS EXISTS. On 2026-08-15 a new exe changed `add_extra_ship_data` from
`(name, folder)` to `(fully_pathed_file)`. Nothing noticed. pybind answers a wrong-arity
call with a TypeError, `add_extra` logs it and carries on by design, and the LIBRARY still
merges every stat - so every headless run, every unit test and every lookup saw the ships,
and only the engine did not. The bill arrived as `MemoryError: bad allocation` from a
spawn, minutes later, in code that never mentions ship data. Every LegendaryMissions
monster and turret was unspawnable in the meantime.

This compares the stub against the engine's OWN generated documentation, which Cosmos
rewrites on every launch. On a machine with the install it turns red in under a second the
first time a new exe is run. That is the whole feature: a signature drift should be a
failing test, not an afternoon.

QUIET WITH NO INSTALL. `data/script_documentation.txt` lives in the Artemis install, not
in this repo, so CI has nothing to compare against - the same reasoning `_art_that_is_not_there`
already uses for art. A check that reported every signature as wrong because it could not
find the game would be worse than no check.
"""
import os
import re
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils import fs


def _engine_doc():
    path = os.path.join(fs.get_artemis_data_dir(), "script_documentation.txt")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def _stub_path():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(here, "typings", "sbs", "__init__.pyi")


# `    name(arg0: str, arg1: int) -> None` inside the module's FUNCTIONS block. The engine
# prints a `name(...)` line first for every function, which carries no types - skipped.
_ENGINE_SIG = re.compile(r'^\s{4,}(\w+)\((.*?)\)\s*->\s*(.+)$', re.M)
_STUB_SIG = re.compile(r'^def (\w+)\((.*?)\)\s*->\s*(.*?):', re.M)


def _arity(args):
    """Parameter names, in order. Types are ignored: the engine prints `arg0: str` for an
    unnamed parameter and the stub copies that, so names ARE the contract here, and a
    changed count is what actually breaks a caller."""
    args = args.strip()
    if not args:
        return []
    return [a.split(":")[0].split("=")[0].strip() for a in args.split(",")]


class TestEngineApiConformance(unittest.TestCase):
    def setUp(self):
        self.doc = _engine_doc()
        if self.doc is None:
            self.skipTest("no Artemis install here - nothing to compare the stub against")

    def test_every_stubbed_function_matches_the_installed_engine(self):
        engine = {}
        for m in _ENGINE_SIG.finditer(self.doc):
            engine.setdefault(m.group(1), set()).add(tuple(_arity(m.group(2))))

        with open(_stub_path(), "r", encoding="utf-8") as f:
            stub_src = f.read()

        wrong = []
        for m in _STUB_SIG.finditer(stub_src):
            name, args = m.group(1), m.group(2)
            if name not in engine:
                continue                    # a class method or a name the doc spells elsewhere
            got = tuple(_arity(args))
            if got not in engine[name]:
                wrong.append("  %s\n     stub  : (%s)\n     engine: %s"
                             % (name, ", ".join(got),
                                " | ".join("(%s)" % ", ".join(s) for s in sorted(engine[name]))))

        self.assertEqual(wrong, [], "typings/sbs/__init__.pyi disagrees with the installed "
                                    "engine. The engine changed under us; update the stub, "
                                    "the mock in cosmos_dev/mock/sbs.py, and every caller:\n"
                                    + "\n".join(wrong))


if __name__ == "__main__":
    unittest.main()
