"""Words lint called wrong that the game accepts, and words it was blind to.

Found by the author course (Classes 2, 3, 4 and 5).

FALSE WARNINGS, each on a line that works:

* `; discover gully` - on the frozen list - was `unknown-outcome-verb`, because the
  module that registers it had not been imported when lint asked which verbs exist;
* `earns guild honesty 30` was `earns-unknown-trait`: the game files a deed under an
  AXIS's own name exactly as it does under a trait's.

BLIND SPOTS, each clean in lint and dead in the game, and each reported only where it
cannot be wrong:

* a character's `Side:` that is no side; a side's `Values:` with a word that is no
  trait, a comma missing, or no numbers;
* `if learnt manifest`, `if knows manifest`; `%learned manifest ...` and
  `%standing >= 30 ...` with no curly brackets;
* a door's `Opens with:` in a shape the game skips; a key nothing gives; a signal
  nothing sends; `Talk scene:` naming no scene; `if holding` / `; take` of a thing
  nothing gives; `; calm` / `; reveal` of a key that is nothing;
* a ruin's `Barrier:` with no size, and an `Item:` in a mission where nothing is an item.

    python -m unittest tests.test_amd_lint_words
"""
import os
import re
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.procedural import amd_core
from sbs_utils.procedural import amd_lint as L
from sbs_utils.procedural.amd_lint import amd_lint


class _Mission(unittest.TestCase):
    STORY = ('shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"))\n'
             'boarding_ground_load(MISSION_DOC)\n')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, "MyAway")
        os.makedirs(self.root)
        self.write("story.json", '{"mastlib": []}\n')
        self.write("story.mast", self.STORY)

    def write(self, name, text):
        path = os.path.join(self.root, *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path

    def found(self, text=None, name="mission.amd", codes=None):
        if text is not None:
            self.write(name, text)
        amd, sources = [], []
        for folder, _dirs, names in os.walk(self.root):
            for n in sorted(names):
                path = os.path.join(folder, n)
                if n.endswith(".amd"):
                    amd.append(path)
                elif n.endswith((".mast", ".py")):
                    with open(path, encoding="utf-8") as f:
                        sources.append(f.read())
        keys = set()
        for path in amd:
            keys |= amd_core.parse(None, file_path=path).keys
        got = amd_lint(file_path=os.path.join(self.root, name), mast_sources=sources,
                       known_keys=keys)
        return [f for f in got if codes is None or f.code in codes]


# --- the verbs the library answers to ------------------------------------------------------

class TheLibrarysOutcomeVerbs(unittest.TestCase):
    def test_EVERY_MODULE_THAT_REGISTERS_A_VERB_IS_LOADED_BEFORE_LINT_JUDGES(self):
        """Read from the library's own source, so a verb added in a new module fails
        here instead of in a writer's lint output."""
        import sbs_utils.procedural as proc
        folder = os.path.dirname(proc.__file__)
        registering = set()
        for name in os.listdir(folder):
            if not name.endswith(".py") or name == "amd_dialogue.py":
                continue
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                if re.search(r"^\s*dialogue_register_outcome\(", f.read(), re.M):
                    registering.add(name[:-3])
        self.assertIn("boarding_tiles", registering)
        self.assertEqual(registering - set(L._OUTCOME_VERB_MODULES), set())

    def test_DISCOVER_IS_AN_OUTCOME_VERB(self):
        """Class 3, Lecture 12: `; discover cistern` works, and lint said nothing
        applies it."""
        text = """# [Kesh Relay](mission)

## [Scenes](scenes)

### [Pim](pim_talk)
% There is a way down, behind the pump house.
- [Mark it on the map.]() ; discover cistern
- [Leave it.]() ; dicover cistern
"""
        got = [f for f in amd_lint(content=text) if f.code == "unknown-outcome-verb"]
        self.assertEqual(len(got), 1)
        self.assertIn("`dicover`", got[0].message)
        self.assertIn("discover", got[0].message.split("Known:")[1])


# --- reputation ------------------------------------------------------------------------------

REP = """# [Mission](mission)

## [Sides](sides)

### [TSN](tsn)
---
Color: #07F
---
The crew's own.

### [Harbor Guild](guild)
---
Color: #0C6
Values: honest 40, generous 30
---
Pilots and tug crews.

## [Characters](characters)

### [Guildmaster Orla](orla)
---
Face: terran
Side: guild
Scene: orla_hail
---
She keeps the books.

## [Dialogue](dialogue)

### [Orla](orla_hail)
---
Speaker: orla
When: comms
---
%{standing >= 30} You are known here, captain.
%{standing < 30} State your business.
- [Report the wreck as it was](orla_hail) ; earns guild honest 30
- [Sign off]()
"""


class TheTraitsTheGameAccepts(unittest.TestCase):
    def rep(self, text):
        return [f for f in amd_lint(content=text) if f.code.startswith("earns-")]

    def test_the_lessons_file_is_clean(self):
        self.assertEqual(self.rep(REP), [])

    def test_AN_AXIS_NAME_IS_ACCEPTED_AS_THE_GAME_ACCEPTS_IT(self):
        """Class 2, Lecture 6: `earns guild honesty 30` moved the standing, and drew
        `earns-unknown-trait`."""
        from sbs_utils.procedural.reputation import (reputation_axis_names, _axis_sign)
        self.assertEqual(self.rep(REP.replace("earns guild honest 30",
                                              "earns guild honesty 30")), [])
        # What makes that true: the two words are filed in the same place.
        self.assertEqual(_axis_sign("honesty"), _axis_sign("honest"))
        for axis in reputation_axis_names():
            with self.subTest(axis=axis):
                self.assertEqual(self.rep(REP.replace("earns guild honest 30",
                                                      f"earns guild {axis} 30")), [])

    def test_a_word_that_is_neither_is_still_told(self):
        got = self.rep(REP.replace("earns guild honest 30", "earns guild honset 30"))
        self.assertEqual([f.code for f in got], ["earns-unknown-trait"])


class ACharactersSide(unittest.TestCase):
    def side(self, text):
        return [f for f in amd_lint(content=text, mast_sources=["# story\n"])
                if f.code == "dangling-side"]

    def test_a_side_that_is_declared_is_fine(self):
        self.assertEqual(self.side(REP), [])

    def test_A_CHARACTER_ON_A_SIDE_NOBODY_DECLARED(self):
        """Class 2, Lecture 6: `Side: gild` - standing reads 0 for good, lint clean."""
        got = self.side(REP.replace("Side: guild", "Side: gild"))
        self.assertEqual(len(got), 1)
        self.assertIn("`Side: gild`", got[0].message)
        self.assertIn("is not a side in this mission", got[0].message)
        self.assertIn("guild, tsn", got[0].message)

    def test_a_side_the_story_makes_counts(self):
        text = REP.replace("Side: guild", "Side: kralien")
        self.assertEqual(len(self.side(text)), 1)
        got = [f for f in amd_lint(content=text, mast_sources=['side_ensure("kralien")\n'])
               if f.code == "dangling-side"]
        self.assertEqual(got, [])

    def test_a_file_with_no_sides_is_not_judged(self):
        text = REP[:REP.index("## [Sides]")] + REP[REP.index("## [Characters]"):]
        self.assertEqual(self.side(text.replace("Side: guild", "Side: gild")), [])


class WhatASideValues(unittest.TestCase):
    def values(self, line):
        text = REP.replace("Values: honest 40, generous 30", line)
        return [f for f in amd_lint(content=text) if f.code.startswith("values-")]

    def test_the_lessons_line_is_clean(self):
        self.assertEqual(self.values("Values: honest 40, generous 30"), [])
        self.assertEqual(self.values("Values: By-the-Book 20, fearsome 10"), [])

    def test_an_axis_by_its_own_name_is_valued_too(self):
        self.assertEqual(self.values("Values: honesty 40"), [])

    def test_A_WORD_THAT_IS_NOT_A_TRAIT(self):
        got = self.values("Values: honset 40, generous 30")
        self.assertEqual([f.code for f in got], ["values-unknown-trait"])
        self.assertIn("`honset`", got[0].message)
        self.assertIn("is not a trait a side can value", got[0].message)

    def test_NO_COMMA_IS_ONE_TRAIT_WITH_A_LONG_NAME(self):
        got = self.values("Values: honest 40 generous 30")
        self.assertEqual([f.code for f in got], ["values-unknown-trait"])
        self.assertIn("Put a comma after each number", got[0].message)

    def test_NO_NUMBERS_IS_A_STANDING_OF_NOTHING(self):
        got = self.values("Values: honest, generous")
        self.assertEqual([f.code for f in got], ["values-no-weight", "values-no-weight"])
        self.assertIn("Values: honest 40", got[0].message)

    def test_a_universe_with_traits_of_its_own_is_not_judged(self):
        text = REP.replace("# [Mission](mission)\n", "# [Mission](mission)\n---\n"
                           "reputation:\n  axes:\n    - {axis: thrift, pos: frugal}\n---\n")
        text = text.replace("Values: honest 40, generous 30", "Values: frugal 40")
        self.assertEqual([f for f in amd_lint(content=text)
                          if f.code.startswith("values-")], [])
        text = REP.replace("Values: honest 40, generous 30",
                           "Axis: frugal / lavish\nValues: frugal 40")
        self.assertEqual([f for f in amd_lint(content=text)
                          if f.code.startswith("values-")], [])


# --- guards ----------------------------------------------------------------------------------

GUARDS = """# [The Customs House](customs)

## [Scenes](boarding)

### [The Counter](customs_counter)
% A clerk looks up.
- [Read the manifest](customs_counter) ; learn manifest
- [Ask about the Tern](customs_tern) if learned manifest
- [Leave]()

### [The Tern](customs_tern)
%{learned manifest} The clerk nods at the page you read.
% She went out light.
- [Leave]()
"""


class AGuardWordNothingAnswers(_Mission):
    CODES = ("guard-learned-word", "guard-no-braces")

    def test_the_lessons_file_is_clean(self):
        self.assertEqual(self.found(GUARDS, codes=self.CODES), [])

    def test_LEARNT_AND_KNOWS_ARE_NOT_THE_WORD(self):
        """Class 5, Lecture 10: `if learnt manifest` - never offered, lint clean."""
        for word in ("learnt", "knows", "learn"):
            with self.subTest(word=word):
                got = self.found(GUARDS.replace("if learned manifest", f"if {word} manifest"),
                                 codes=self.CODES)
                self.assertEqual([f.code for f in got], ["guard-learned-word"])
                self.assertIn(f"`if {word} manifest`", got[0].message)
                self.assertIn("Write `if learned manifest`", got[0].message)
                self.assertIn("never offered", got[0].message)

    def test_the_fact_may_be_learned_in_another_file(self):
        self.write("hails.amd", "# [Hail](h)\n---\nSpeaker: x\nWhen: comms\n---\n% Yes?\n"
                                "- [Take the page]() ; learn ledger page\n- [Read]() ; learn tally\n")
        got = self.found(GUARDS.replace("if learned manifest", "if knows tally"),
                         codes=self.CODES)
        self.assertEqual([f.code for f in got], ["guard-learned-word"])

    def test_A_FACT_OF_SEVERAL_WORDS(self):
        """Class 6, Lecture 2: `if learnt the gleaners broke a boat`, and the line
        `%learned the assay office buys salvage Entered.`"""
        text = GUARDS.replace("learn manifest", "learn the gleaners broke a boat") \
                     .replace("learned manifest", "learned the gleaners broke a boat")
        self.assertEqual(self.found(text, codes=self.CODES), [])
        got = self.found(text.replace("if learned the", "if knows the"), codes=self.CODES)
        self.assertEqual([f.code for f in got], ["guard-learned-word"])
        self.assertIn("Write `if learned the gleaners broke a boat`", got[0].message)
        got = self.found(text.replace("%{learned the gleaners broke a boat} The",
                                      "%learned the gleaners broke a boat The"),
                         codes=self.CODES)
        self.assertEqual([f.code for f in got], ["guard-no-braces"])
        self.assertIn("`%learned the gleaners broke a boat`", got[0].message)

    def test_a_second_word_that_is_no_fact_is_left_alone(self):
        """Two words that are not about a fact may be a role with a space in it."""
        self.assertEqual(self.found(GUARDS.replace("if learned manifest", "if chief engineer"),
                                    codes=self.CODES), [])

    def test_a_mission_that_gives_guards_a_word_of_its_own_is_not_judged(self):
        self.write("lp_world.py", 'boarding_metric_word("knows", _f)\n')
        self.assertEqual(self.found(GUARDS.replace("if learned manifest", "if knows manifest"),
                                    codes=self.CODES), [])

    def test_a_loose_file_is_not_judged(self):
        got = [f for f in amd_lint(content=GUARDS.replace("if learned manifest",
                                                          "if knows manifest"))
               if f.code in self.CODES]
        self.assertEqual(got, [])

    def test_A_LINE_WITH_ITS_CURLY_BRACKETS_MISSING(self):
        """Class 5, Lecture 10: `%learned manifest The clerk nods` is spoken aloud."""
        got = self.found(GUARDS.replace("%{learned manifest} The", "%learned manifest The"),
                         codes=self.CODES)
        self.assertEqual([f.code for f in got], ["guard-no-braces"])
        self.assertIn("`%learned manifest`", got[0].message)
        self.assertIn("%{learned manifest}", got[0].message)
        self.assertIn("spoken aloud", got[0].message)

    def test_a_sign_and_a_number_touching_the_percent(self):
        got = self.found(GUARDS.replace("% She went out light.",
                                        "%standing >= 30 She went out light."),
                         codes=self.CODES)
        self.assertEqual([f.code for f in got], ["guard-no-braces"])
        self.assertIn("`%standing >= 30`", got[0].message)

    def test_an_ordinary_line_is_an_ordinary_line(self):
        for line in ("% learned men say she went out light.",
                     "%learned men say she went out light.",       # `men` is no fact
                     "% She went out light, 30 >= 20 of them.",
                     "%She went out light."):
            with self.subTest(line=line):
                self.assertEqual(self.found(GUARDS.replace("% She went out light.", line),
                                            codes=self.CODES), [])


# --- the ground ------------------------------------------------------------------------------

GROUND = """# [Kesh Relay](mission)

## [Props](props)

### [Pump House Door](pump_door)
---
Area: yard
Mark: pump_door
Sprite: prop:door
Blocks: yes
Opens with: key pump_key, check engineering 8, cut
---
A steel door.

### [Sluice Gate](sluice)
---
Area: yard
Mark: sluice
Blocks: yes
Opens with: signal cistern_drained
---
A gate.

### [A Key on a Hook](key_hook)
---
Area: yard
Mark: hook
Item: pump_key
---
A key.

### [The Stash](stash)
---
Area: yard
Mark: stash
Hidden until: stash_shown
Item: tablet
---
Under a tarp.

### [Rubble](rubble)
---
Area: yard
Mark: rubble
Blocks: yes
---
A wall of it.

## [People](people)

### [Marrow](marrow)
---
Area: yard
Mark: marrow
Calm: yes
Talk scene: marrow_talk
---
The keeper.

### [The Sentry](sentry)
---
Area: yard
Mark: sentry
Drops: power_cell
---
A machine.

## [Scenes](scenes)

### [Marrow](marrow_talk)
% You came a long way.
- [Ask about the stash](marrow_talk) ; signal stash_shown
- [Hand over the tablet](marrow_talk) if holding tablet ; take tablet, give fuse
- [Have her drain the cistern](marrow_talk) ; signal cistern_drained
- [Talk the sentry down](marrow_talk) ; calm sentry
- [Leave]()
"""

GROUND_CODES = ("opens-with-shape", "item-nothing-gives", "ground-signal-unsent",
                "hidden-until-shape", "ground-verb-target", "dangling-scene")


class TheGround(_Mission):
    def g(self, old=None, new=None, codes=GROUND_CODES):
        text = GROUND if old is None else GROUND.replace(old, new)
        if old is not None:
            self.assertNotEqual(text, GROUND, old)
        return self.found(text, codes=codes)

    def test_the_lessons_file_is_clean(self):
        self.assertEqual(self.g(), [])

    def test_a_wall_is_not_a_door_with_something_missing(self):
        """`Blocks: yes` and no `Opens with:` is how rubble is written."""
        self.assertEqual([f for f in self.found(GROUND) if "rubble" in f.message.lower()], [])

    # -- Opens with -----------------------------------------------------------------
    def test_A_WAY_A_DOOR_DOES_NOT_OPEN(self):
        got = self.g("Opens with: key pump_key, check", "Opens with: kee pump_key, check")
        self.assertEqual([f.code for f in got], ["opens-with-shape"])
        self.assertIn("`kee` is not a way a door opens", got[0].message)

    def test_NO_COMMAS_LOSES_EVERYTHING_AFTER_THE_FIRST(self):
        got = self.g("key pump_key, check engineering 8, cut",
                     "key pump_key check engineering 8 cut")
        self.assertEqual([f.code for f in got], ["opens-with-shape"])
        self.assertIn("no comma before `check`", got[0].message)

    def test_A_CHECK_WITH_NO_NUMBER(self):
        for bad in ("check engineering", "check engineering eight", "check zero g 8"):
            with self.subTest(bad=bad):
                got = self.g("check engineering 8", bad)
                self.assertEqual([f.code for f in got], ["opens-with-shape"])
                self.assertIn("a skill and a number", got[0].message)

    def test_a_key_or_a_signal_with_no_name_and_a_key_of_two_words(self):
        self.assertEqual([f.code for f in self.g("key pump_key,", "key,")],
                         ["opens-with-shape"])
        self.assertEqual([f.code for f in self.g("signal cistern_drained", "signal")],
                         ["opens-with-shape"])
        got = self.g("key pump_key,", "key pump key,")
        self.assertEqual([f.code for f in got], ["opens-with-shape"])
        self.assertIn("`key pump_key`", got[0].message)

    # -- a key, a thing in a pack ----------------------------------------------------
    def test_A_KEY_NOTHING_GIVES(self):
        """Class 3, Lecture 10: the pickup renamed, the door not."""
        got = self.g("Opens with: key pump_key,", "Opens with: key brass_key,")
        self.assertEqual([f.code for f in got], ["item-nothing-gives"])
        self.assertIn("`Opens with: key brass_key`", got[0].message)
        self.assertIn("never opens with a key", got[0].message)
        self.assertIn("fuse, power_cell, pump_key, tablet", got[0].message)

    def test_a_key_somebody_drops_or_an_answer_gives_is_given(self):
        self.assertEqual(self.g("Opens with: key pump_key,", "Opens with: key power_cell,"), [])
        self.assertEqual(self.g("Opens with: key pump_key,", "Opens with: key fuse,"), [])

    def test_HOLDING_SOMETHING_NOTHING_GIVES(self):
        got = self.g("if holding tablet", "if holding tablt")
        self.assertEqual([f.code for f in got], ["item-nothing-gives"])
        self.assertIn("`if holding tablt`", got[0].message)
        self.assertIn("never offered", got[0].message)
        got = self.g("if holding tablet", "if party tablt >= 2")
        self.assertEqual([f.code for f in got], ["item-nothing-gives"])

    def test_TAKING_SOMETHING_NOTHING_GIVES(self):
        got = self.g("; take tablet,", "; take tablt,")
        self.assertEqual([f.code for f in got], ["item-nothing-gives"])
        self.assertIn("`; take tablt`", got[0].message)
        self.assertIn("refuses an answer", got[0].message)

    def test_needs_holding_on_a_thing(self):
        got = self.g("Item: tablet\n", "Item: tablet\nNeeds: holding crowbr\n")
        self.assertEqual([f.code for f in got], ["item-nothing-gives"])
        self.assertEqual(self.g("Item: tablet\n", "Item: tablet\nNeeds: holding pump_key\n"),
                         [])

    def test_a_thing_given_in_another_file_is_given(self):
        self.write("ship.amd", "# [Hail](h)\n---\nSpeaker: x\nWhen: comms\n---\n% Yes?\n"
                               "- [Take the crowbar]() ; give crowbar\n")
        self.assertEqual(self.g("if holding tablet", "if holding crowbar"), [])

    def test_code_that_fills_a_pack_makes_it_a_guess_so_nothing_is_said(self):
        self.write("probe.py", "def f(me):\n    boarding_give(me, 'tablt')\n")
        self.assertEqual(self.g("if holding tablet", "if holding tablt"), [])

    def test_a_loose_file_is_not_judged_for_what_is_in_a_pack(self):
        text = GROUND.replace("if holding tablet", "if holding tablt")
        self.assertEqual([f for f in amd_lint(content=text)
                          if f.code == "item-nothing-gives"], [])

    # -- signals ----------------------------------------------------------------------
    def test_A_DOOR_WAITING_ON_A_SIGNAL_NOTHING_SENDS(self):
        got = self.g("Opens with: signal cistern_drained", "Opens with: signal cistern_draind")
        self.assertEqual([f.code for f in got], ["ground-signal-unsent"])
        self.assertIn("`Opens with: signal cistern_draind`", got[0].message)

    def test_A_THING_HIDDEN_UNTIL_A_SIGNAL_NOTHING_SENDS(self):
        got = self.g("Hidden until: stash_shown", "Hidden until: stash_shwn")
        self.assertEqual([f.code for f in got], ["ground-signal-unsent"])
        self.assertIn("stays hidden for good", got[0].message)
        self.assertIn("; reveal stash", got[0].message)

    def test_a_thing_an_answer_reveals_by_its_key_is_not_hidden_for_good(self):
        text = GROUND.replace("Hidden until: stash_shown", "Hidden until: never_sent") \
                     .replace("; signal stash_shown", "; reveal stash")
        self.assertEqual(self.found(text, codes=GROUND_CODES), [])

    def test_a_signal_the_story_sends_counts(self):
        self.write("story.mast", self.STORY + 'signal_emit("cistern_draind")\n')
        self.assertEqual(self.g("Opens with: signal cistern_drained",
                                "Opens with: signal cistern_draind"), [])

    def test_a_signal_the_library_sends_counts(self):
        self.assertIn("relic_built", L._library_signal_names())
        self.assertEqual(self.g("Hidden until: stash_shown", "Hidden until: relic_built"), [])

    def test_hidden_until_takes_the_name_alone(self):
        got = self.g("Hidden until: stash_shown", "Hidden until: signal stash_shown")
        self.assertEqual([f.code for f in got], ["hidden-until-shape"])
        self.assertIn("Write `Hidden until: stash_shown`", got[0].message)

    # -- verbs and scenes --------------------------------------------------------------
    def test_A_VERB_AIMED_AT_NOBODY(self):
        got = self.g("; calm sentry", "; calm sentri")
        self.assertEqual([f.code for f in got], ["ground-verb-target"])
        self.assertIn("`; calm sentri` - nobody in this mission has the key `sentri`",
                      got[0].message)
        for verb in ("summon", "dismiss", "rouse"):
            with self.subTest(verb=verb):
                got = self.g("; calm sentry", f"; {verb} sentri")
                self.assertEqual([f.code for f in got], ["ground-verb-target"])

    def test_A_VERB_AIMED_AT_NOTHING(self):
        for verb in ("open", "reveal"):
            with self.subTest(verb=verb):
                got = self.g("; calm sentry", f"; {verb} stahs")
                self.assertEqual([f.code for f in got], ["ground-verb-target"])
                self.assertIn("nothing in this mission has the key `stahs`", got[0].message)
        self.assertEqual(self.g("; calm sentry", "; reveal stash"), [])
        self.assertEqual(self.g("; calm sentry", "; open pump_door"), [])

    def test_the_crew_a_boarded_ship_is_given_have_keys_no_file_holds(self):
        self.assertEqual(self.g("; calm sentry", "; calm deck_crew_2"), [])

    def test_code_that_puts_people_on_the_map_makes_it_a_guess(self):
        self.write("extra.py", "boarding_hostile_add('sentri', 'yard', (1, 1))\n")
        self.assertEqual(self.g("; calm sentry", "; calm sentri"), [])

    def test_A_TALK_SCENE_THAT_IS_NOT_THERE(self):
        got = self.g("Talk scene: marrow_talk", "Talk scene: marow_talk")
        self.assertEqual([f.code for f in got], ["dangling-scene"])
        self.assertIn("`marrow` Talk scene points at `marow_talk`", got[0].message)


# --- ruins ---------------------------------------------------------------------------------

RUIN = """# [The Hollow](mission)

## [Relics](relics)

### [The Hollow](hollow)
---
Walls: rock
Loc: 40000, 0, 40000
---

### [The Nave](nave)
---
Relic: hollow
Chamber: 0, 0, 0, 900
---

### [The Fallen Slab](slab)
---
Relic: hollow
Barrier: 300, 0, -110, 320
---

### [The Cache](cache)
---
Relic: hollow
Point: 100, 0, 100
Item: canister
---

## [Items](items)

### [Survey Canister](canister)
---
Art: container_1a
---
A sealed canister.
"""


class ARuinsParts(_Mission):
    STORY = 'relics_spawn(get_mission_dir_filename("mission.amd"))\n'

    def test_the_lessons_file_is_clean(self):
        self.assertEqual(self.found(RUIN, codes=("relic-short-part", "relic-unknown-item",
                                                 "relic-bad-radius")), [])

    def test_A_BARRIER_WITH_NO_SIZE(self):
        """Class 4, Lecture 8: `Barrier: x, y, z` - no barrier, nothing said."""
        got = self.found(RUIN.replace("Barrier: 300, 0, -110, 320", "Barrier: 300, 0, -110"),
                         codes=("relic-short-part",))
        self.assertEqual(len(got), 1)
        self.assertIn("'barrier' needs 4 numbers, got 3", got[0].message)
        self.assertIn("there is no barrier at all", got[0].message)

    def test_a_barrier_of_no_size(self):
        got = self.found(RUIN.replace("Barrier: 300, 0, -110, 320", "Barrier: 300, 0, -110, 0"),
                         codes=("relic-bad-radius",))
        self.assertEqual(len(got), 1)

    def test_AN_ITEM_IN_A_MISSION_WHERE_NOTHING_IS_AN_ITEM(self):
        """Class 4, Lecture 5: no Items section - a marker, and nothing to take."""
        text = RUIN[:RUIN.index("## [Items]")]
        got = self.found(text, codes=("relic-unknown-item",))
        self.assertEqual(len(got), 1)
        self.assertIn("`cache` holds `canister`, which is not a defined item", got[0].message)
        self.assertIn("## [Items](items)", got[0].message)

    def test_an_item_an_addon_makes_is_an_item(self):
        text = RUIN[:RUIN.index("## [Items]")]
        self.write("items.mast", "=== prefab_canister\nmetadata: ``` yaml\ntype: item/cargo\n"
                                 "key: canister\n```\n    ->END\n")
        self.assertEqual(self.found(text, codes=("relic-unknown-item",)), [])

    def test_an_item_written_in_another_file_is_an_item(self):
        text = RUIN[:RUIN.index("## [Items]")]
        self.write("things.amd", "# [Things](things_file)\n\n" + RUIN[RUIN.index("## [Items]"):])
        self.assertEqual(self.found(text, codes=("relic-unknown-item",)), [])

    def test_a_loose_file_is_not_judged(self):
        text = RUIN[:RUIN.index("## [Items]")]
        self.assertEqual([f for f in amd_lint(content=text)
                          if f.code == "relic-unknown-item"], [])


if __name__ == "__main__":
    unittest.main()
