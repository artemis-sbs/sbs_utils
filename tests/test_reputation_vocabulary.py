"""`Side:` on a Character is the library's word now - and Open Universe still declares it.

`amd_register_fields` RAISES on a re-declaration that disagrees, and
`load_mission_vocabulary` swallows what a vocabulary module raises (a module that needs
the engine simply does not contribute its words). So if the library's descriptor for a
character's `Side:` were anything but exactly the one Open Universe registers, importing
`universe_amd.py` would stop halfway and every mission built on Open Universe - from
source or from the RELEASED mastlib, which nobody can edit - would lose its vocabulary
without a word.

Vocabulary is process-global, so every case here is its own interpreter.

    python -m unittest tests.test_reputation_vocabulary
"""
import glob
import json
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MISSIONS = os.path.dirname(REPO)
LIB = os.path.join(MISSIONS, "__lib__")

# Runs in a child: load one mission's vocabulary and report what is declared.
_LOAD = r"""
import json, sys
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
from sbs_utils.procedural import amd_schema as S
{before}
from sbs_utils.procedural.amd_vocab import load_mission_vocabulary
loaded = load_mission_vocabulary(sys.argv[1])
life = S.ARCHETYPES.get("lifeform", {{}})
side = S.ARCHETYPES.get("side", {{}})
print("RESULT " + json.dumps({{
    "loaded": sorted(loaded),
    "side_on_character": life.get("side"),
    "character_flies": "flies" in life,
    "side_disposition": "disposition" in side,
    "landmark_relic": "relic" in S.ARCHETYPES.get("landmark", {{}}),
}}))
"""

# Runs in a child: import each vocabulary module of a mastlib with NOTHING swallowed.
_IMPORT_ZIP = r"""
import importlib, json, os, sys, zipfile
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
from sbs_utils.procedural import amd_schema as S
done = []
for addon in sys.argv[1:]:
    with zipfile.ZipFile(addon) as z:
        names = [n for n in z.namelist() if n.endswith("_amd.py") or n.endswith("_dialogue.py")]
    for n in sorted(names):
        sub = os.path.dirname(n)
        sys.path[:0] = [os.path.join(addon, sub) if sub else addon, addon]
        importlib.import_module(os.path.splitext(os.path.basename(n))[0])
        done.append(os.path.basename(n))
life = S.ARCHETYPES.get("lifeform", {})
print("RESULT " + json.dumps({"done": done, "side_on_character": life.get("side"),
                              "character_flies": "flies" in life}))
"""

SIDE = {"type": "ref", "ref": "node", "hint": "the side this person flies for"}


def _run(code, *args):
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO
    env.pop("COSMOS_SETTINGS", None)
    got = subprocess.run([sys.executable, "-c", code, *args], cwd=REPO, env=env,
                         capture_output=True, text=True, timeout=180)
    for line in got.stdout.splitlines():
        if line.startswith("RESULT "):
            res = json.loads(line[7:])
            # Open Universe catches its own clash and prints this; it is the one line
            # that says its vocabulary stopped halfway.
            res["refused"] = [l for l in got.stdout.splitlines()
                              if "vocabulary not declared" in l]
            return res, got
    return None, got


def _mission(name):
    path = os.path.join(MISSIONS, name)
    return path if os.path.isfile(os.path.join(path, "story.json")) else None


def _descriptor(d):
    """A field descriptor with only the keys that say what it is."""
    return {k: v for k, v in (d or {}).items() if v not in (None,)} if d else d


class TheLibraryDeclaresSide(unittest.TestCase):
    def test_with_no_mission_at_all(self):
        code = _LOAD.format(before="")
        res, got = _run(code, os.path.join(REPO, "tests"))     # a folder with no vocabulary
        self.assertIsNotNone(res, got.stderr)
        d = _descriptor(res["side_on_character"])
        for k, v in SIDE.items():
            self.assertEqual(d.get(k), v, d)


class EveryMissionKeepsItsVocabulary(unittest.TestCase):
    """`load_mission_vocabulary` for each mission that has words of its own."""

    def _load(self, name, before=""):
        path = _mission(name)
        if path is None:
            self.skipTest(f"{name} is not checked out beside sbs_utils")
        res, got = _run(_LOAD.format(before=before), path)
        self.assertIsNotNone(res, got.stderr)
        return res

    def test_open_universe_from_source(self):
        if not os.path.isfile(os.path.join(MISSIONS, "OpenUniverse", "universe_core",
                                           "universe_amd.py")):
            self.skipTest("OpenUniverse source is not here")
        res = self._load("OpenUniverse")
        self.assertIn("universe_amd", res["loaded"])
        self.assertIn("universe_dialogue", res["loaded"])
        self.assertEqual(res["refused"], [])
        self.assertTrue(res["character_flies"], "universe_amd.py stopped before `Flies:`")
        self.assertTrue(res["side_disposition"])
        self.assertTrue(res["landmark_relic"], "universe_amd.py did not run to its end")

    def test_storms_beacon_on_the_released_open_universe(self):
        # Storm's Beacon has no universe_core folder: its Open Universe is the mastlib
        # in __lib__, the released one.
        path = _mission("StormsBeacon")
        if path is None or os.path.isdir(os.path.join(path, "universe_core")):
            self.skipTest("StormsBeacon (on a packaged Open Universe) is not here")
        res = self._load("StormsBeacon")
        self.assertIn("universe_amd", res["loaded"])
        self.assertEqual(res["refused"], [])
        self.assertTrue(res["character_flies"], "the released universe_amd.py stopped "
                                                "before `Flies:`")
        self.assertTrue(res["landmark_relic"])

    def test_legendary_missions(self):
        res = self._load("LegendaryMissions")
        self.assertIn("lm_amd", res["loaded"])
        self.assertIn("casino_amd", res["loaded"])
        self.assertEqual(_descriptor(res["side_on_character"]).get("ref"), "node")

    def test_landing_party(self):
        res = self._load("LandingParty")
        self.assertEqual(_descriptor(res["side_on_character"]).get("ref"), "node")

    def test_the_test_can_fail(self):
        """A library descriptor that DISAGREES costs Open Universe its words - which is
        what every test above would then see."""
        if not os.path.isfile(os.path.join(MISSIONS, "OpenUniverse", "universe_core",
                                           "universe_amd.py")):
            self.skipTest("OpenUniverse source is not here")
        res = self._load("OpenUniverse",
                         before='S.LIFEFORM["side"] = S.ref("side")')
        self.assertTrue(res["refused"], "Open Universe did not notice the clash")
        self.assertFalse(res["character_flies"])
        self.assertFalse(res["landmark_relic"])


class TheReleasedOpenUniverseImportsClean(unittest.TestCase):
    """The RELEASED mastlibs, imported the way the loader imports them, with nothing
    swallowed: an exception here is the released product losing its vocabulary."""

    def test_every_vocabulary_module_in_the_released_mastlibs(self):
        zips = sorted(glob.glob(os.path.join(LIB, "artemis-sbs.OpenUniverse.*.mastlib")))
        if not zips:
            self.skipTest("no released OpenUniverse mastlib in __lib__")
        res, got = _run(_IMPORT_ZIP, *zips)
        self.assertIsNotNone(res, got.stderr[-2000:])
        self.assertEqual(got.returncode, 0, got.stderr[-2000:])
        self.assertIn("universe_amd.py", res["done"])
        self.assertEqual(res["refused"], [])
        self.assertTrue(res["character_flies"])
        d = _descriptor(res["side_on_character"])
        for k, v in SIDE.items():
            self.assertEqual(d.get(k), v, d)


if __name__ == "__main__":
    unittest.main()
