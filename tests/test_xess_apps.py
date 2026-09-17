"""The xESS is a registry and four apps.

Every surface on the device is an app behind a tile - answering the scene and leaving the
surface included. That is the whole redesign: three of its functions used to be apps and
two were loose chrome stapled to the bottom of the column, in a band that never went away
and whose choices used select-a-row-then-press-ACT.

THREE THINGS HERE ARE LOAD-BEARING and each has its own class:

* **A badge provider never takes the device down.** It is called per tile per build AND
  by the revision the `on change` watches, so a provider that raises or recurses is not a
  cosmetic problem - it is the console going blank several times a second. Lifted from
  the ePADD, which learned it by entering one provider 332 times for one badge.
* **Auto-open records the beat even when it does not open.** Otherwise a beat somebody
  dismissed reopens on the next tick and cannot be got rid of.
* **Auto-open never fires while armed.** Yanking a crew member off a live weapon screen
  is the exact accident every other rule in FIRE exists to prevent, and it would happen
  at the worst possible moment - the one where something just started happening.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_site as B
from sbs_utils.procedural.gui import xess as X
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.spawn import npc_spawn, player_spawn

CID = 0x8000000000000001
OTHER = 0x8000000000000002


class _XessBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        # NO AMBIENT TASK. `boarding_site_build` restores damcons through
        # `prefab_spawn`, which is a no-op with no task context ("Invalid prefab label")
        # but RAISES `Calling undefined label` when some earlier test file has left a
        # live MAST scheduler whose story does not define that prefab. This file sorts
        # last under `discover`, so it inherits whatever the whole suite left behind -
        # it passed alone and errored 24 times in the full run, which is the shape every
        # ordering bug takes. A fixture that borrows shared state gives it back in the
        # same breath.
        # BOTH, and the page is the one that matters: `FrameContext.task` falls back to
        # `page.gui_task` when no task is set (`helpers.py:103`), so clearing the task
        # alone leaves a leftover page still supplying one - which is exactly what the
        # first version of this fixture did, and it cut the errors from 31 to 24 rather
        # than to 0.
        self.addCleanup(setattr, FrameContext, "task", FrameContext.task)
        self.addCleanup(setattr, FrameContext, "page", FrameContext.page)
        FrameContext.page = None
        FrameContext.task = None
        SpaceObject.clear()
        A.boarding_clear()
        B.boarding_site_clear()
        X.xess_clear()
        self.addCleanup(X.xess_clear)
        self.addCleanup(B.boarding_site_clear)
        for cid in (CID, OTHER):
            GuiClient(cid)
        self.ship = to_object(player_spawn(0, 0, 0, "Artemis", "tsn",
                                           "tsn_light_cruiser"))
        self.site = to_object(npc_spawn(3000, 0, 3000, "Kepler", "tsn",
                                        "tsn_destroyer", "behav_station"))
        B.boarding_site_build(self.site)
        self.who = lifeform_spawn("Lt Marek", "terran_male", "boarding,science")
        A.boarding_invite(self.ship, [self.who], title="Kepler")
        A.boarding_beam_down(CID, self.who)
        self.fig = B.boarding_figure_spawn(self.site, self.who, 3, 1)
        B.boarding_take(CID, self.fig, self.site)


class TheBuiltInsAreAllApps(_XessBase):
    def test_answering_the_scene_is_an_app(self):
        """It used to be a permanent band at the bottom of the column, which is what
        "why is it always active and not an app" was about."""
        self.assertIn(X.APP_ACT, X.xess_registered())

    def test_and_so_is_leaving_the_surface(self):
        self.assertIn(X.APP_CREW, X.xess_registered())

    def test_the_way_home_lives_in_the_CREW_app_and_nowhere_else(self):
        """It used to be a button under the choices on every screen, where a thumb
        rests. The ship is what brings you home, so it belongs on the ship's row.

        ASSERTS THE PLACE, NOT THE WORD. This used to look for the literal
        `gui_button("Beam up"` - which stopped being true when a second body model
        arrived: you do not beam up out of a suit, you fly back, so the label is chosen
        from what the console is wearing. The claim was never about the word.
        """
        import inspect
        self.assertIn("_leave_label(client_id)", inspect.getsource(X._caller_detail))
        self.assertIn("_leave(_cid)", inspect.getsource(X._caller_detail))
        for other in (X._act_app, X._scan_app, X._fire_app, X._nav_app, X._home):
            src = inspect.getsource(other)
            self.assertNotIn("Beam up", src)
            self.assertNotIn("_leave", src)

    def test_all_four_apps_are_offered_to_a_console_on_the_surface(self):
        """The guard on every sweep in this class: they walk `xess_apps(CID)`, so an
        empty list passes them all without measuring anything."""
        # NAV is not here: it is offered only to a console wearing a suit, and this
        # fixture is standing on a floor. `test_eva_console` covers the other case.
        self.assertEqual({X.APP_CREW, X.APP_ACT, X.APP_SCAN, X.APP_FIRE},
                         {a["key"] for a in X.xess_apps(CID)})

    def test_every_app_can_actually_draw_something(self):
        """A registration with no `draw` is a tile that does nothing when pressed - the
        PADD shipped that once and it was reported as "clicking the app does nothing"."""
        for app in X.xess_apps(CID):
            self.assertTrue(callable(app.get("draw")), app["key"])

    def test_a_clear_leaves_the_device_with_its_built_ins(self):
        """The mission reset clears the registry. A device with no apps is a blank
        screen with no way out of it."""
        X.xess_clear()
        self.assertTrue(X.xess_registered())

    def test_scan_and_fire_hide_when_there_is_no_floor_to_stand_on(self):
        """A tile that cannot do anything is a promise the device does not keep."""
        keys = [a["key"] for a in X.xess_apps(OTHER)]
        self.assertNotIn(X.APP_SCAN, keys)
        self.assertNotIn(X.APP_FIRE, keys)

    def test_but_crew_is_there_for_a_console_with_no_body(self):
        """Somebody watching still needs to see who is down there."""
        self.assertIn(X.APP_CREW, [a["key"] for a in X.xess_apps(OTHER)])


class OpeningAnAppIsPerConsole(_XessBase):
    def test_one_console_opening_an_app_does_not_open_it_on_another(self):
        X.xess_open(CID, X.APP_SCAN)
        self.assertEqual(X.APP_SCAN, X.xess_opened(CID))
        self.assertIsNone(X.xess_opened(OTHER))

    def test_home_is_None_not_a_key(self):
        X.xess_open(CID, X.APP_SCAN)
        X.xess_open(CID, None)
        self.assertIsNone(X.xess_opened(CID))

    def test_an_unknown_app_is_refused_rather_than_stored(self):
        """A stored key nothing registers would draw the tile sheet forever with no
        sign of why."""
        self.assertFalse(X.xess_open(CID, "nonesuch"))
        self.assertIsNone(X.xess_opened(CID))

    def test_leaving_FIRE_disarms(self):
        """Walking away from a live weapon with the gun still up is the same accident
        the disarm-on-shot rule prevents, one step earlier."""
        X.xess_open(CID, X.APP_FIRE)
        B.boarding_arm(CID)
        X.xess_open(CID, X.APP_SCAN)
        self.assertFalse(B.boarding_armed(CID))

    def test_going_home_from_FIRE_disarms_too(self):
        X.xess_open(CID, X.APP_FIRE)
        B.boarding_arm(CID)
        X.xess_open(CID, None)
        self.assertFalse(B.boarding_armed(CID))

    def test_opening_an_app_moves_the_revision(self):
        """Without this the device changes and nothing repaints - which is exactly how
        the old mode strip shipped as "the SCAN and FIRE tabs do nothing"."""
        before = X.xess_revision(CID)
        X.xess_open(CID, X.APP_SCAN)
        self.assertNotEqual(before, X.xess_revision(CID))


class ABadgeNeverTakesTheDeviceDown(_XessBase):
    def test_a_provider_that_raises_costs_its_own_tile_a_badge(self):
        def boom():
            raise ValueError("nope")
        X.xess_register("bad", draw=lambda cid: None, badge=boom)
        self.assertIsNone(X.xess_app_badge(X._APPS["bad"]))

    def test_and_the_other_tiles_still_have_theirs(self):
        def boom():
            raise ValueError("nope")
        X.xess_register("bad", draw=lambda cid: None, badge=boom)
        X.xess_register("good", draw=lambda cid: None, badge="3 here")
        self.assertEqual("3 here", X.xess_app_badge(X._APPS["good"]))

    def test_and_the_revision_still_answers(self):
        """The revision computes every badge, so one that raises would otherwise take
        the `on change` down with it - several times a second."""
        def boom():
            raise ValueError("nope")
        X.xess_register("bad", draw=lambda cid: None, badge=boom)
        self.assertIsNotNone(X.xess_revision(CID))

    def test_a_provider_asking_for_its_OWN_badge_terminates(self):
        """A provider is free to ask what the others are reporting, which includes
        itself - that is a cycle. The PADD found it by entering one provider 332 times
        for one badge, unwound only by Python's recursion limit."""
        seen = []

        def nosy():
            seen.append(1)
            return ",".join(str(X.xess_app_badge(a)) for a in X.xess_apps(CID))

        X.xess_register("nosy", draw=lambda cid: None, badge=nosy)
        self.assertIsNotNone(X.xess_app_badge(X._APPS["nosy"]))
        self.assertEqual(1, len(seen), "the provider was re-entered")

    def test_an_empty_badge_is_no_badge(self):
        """The convention every PADD provider follows: return "" for nothing to say."""
        X.xess_register("quiet", draw=lambda cid: None, badge=lambda: "  ")
        self.assertIsNone(X.xess_app_badge(X._APPS["quiet"]))

    def test_an_availability_that_raises_drops_ONE_tile(self):
        """A device that goes blank because one mission app asked an awkward question
        is worse than a device missing one tile."""
        def boom(cid):
            raise ValueError("nope")
        X.xess_register("bad", draw=lambda cid: None, available=boom)
        keys = [a["key"] for a in X.xess_apps(CID)]
        self.assertNotIn("bad", keys)
        self.assertIn(X.APP_CREW, keys)


class ABeatOpensTheActApp(_XessBase):
    """A beat nobody answers because nobody looked is a scene that did not happen."""

    #: The shape `dialogue_scenes()` produces: key -> node. Same as `test_boarding`'s
    #: fixture, so a change to the dialogue format breaks both rather than leaving this
    #: one quietly passing against a scene with no choices in it.
    SCENES = {
        "lab": {"key": "lab", "display_text": "lab",
                "description": ("% Containment on bench three has failed.\n"
                                "- [Examine the gel](corridor)\n"
                                "- [Read the manifest](corridor)\n"),
                "data": {"speaker": "outpost"}},
        "corridor": {"key": "corridor", "display_text": "corridor",
                     "description": "% You regroup.\n",
                     "data": {"speaker": "outpost"}},
    }

    def setUp(self):
        super().setUp()
        A.boarding_metric_install()

    def _open_a_beat(self):
        A.boarding_scene_begin(self.SCENES, "lab", speaker="outpost")
        # The guard on the guard: with no choices, auto-open correctly does nothing and
        # every test below would pass while measuring nothing.
        self.assertTrue(A.boarding_choices(CID), "fixture produced no choices")

    def test_a_new_beat_opens_ACT(self):
        self._open_a_beat()
        self.assertTrue(X._auto_open(CID))
        self.assertEqual(X.APP_ACT, X.xess_opened(CID))

    def test_it_does_not_reopen_after_it_is_dismissed(self):
        """THE TEST THAT MATTERS. Recording the seq only when the app is opened means a
        beat somebody closed pops straight back on the next tick, forever."""
        self._open_a_beat()
        X._auto_open(CID)
        X.xess_open(CID, None)
        self.assertFalse(X._auto_open(CID))
        self.assertIsNone(X.xess_opened(CID))

    def test_but_the_NEXT_beat_opens_it_again(self):
        self._open_a_beat()
        X._auto_open(CID)
        X.xess_open(CID, None)
        A.boarding_scene_end()
        self._open_a_beat()
        self.assertTrue(X._auto_open(CID))

    def test_it_NEVER_fires_while_the_weapon_is_armed(self):
        """The one place it must not happen, and the worst moment for it to - a crew
        member is aiming precisely because something is going on."""
        B.boarding_arm(CID, B.SETTING_CUT)
        X.xess_open(CID, X.APP_FIRE)
        self._open_a_beat()
        self.assertFalse(X._auto_open(CID))
        self.assertEqual(X.APP_FIRE, X.xess_opened(CID))

    def test_and_an_armed_console_is_not_ambushed_by_it_later(self):
        """Recording the seq while armed is what stops the beat springing out the
        instant the shot goes off."""
        B.boarding_arm(CID, B.SETTING_CUT)
        self._open_a_beat()
        X._auto_open(CID)
        B.boarding_disarm(CID)
        self.assertFalse(X._auto_open(CID))

    def test_nothing_opens_when_there_is_no_beat(self):
        self.assertFalse(X._auto_open(CID))
        self.assertIsNone(X.xess_opened(CID))


class TheScrollingBandsAreListboxes(unittest.TestCase):
    """A fixed row is NEVER scaled down, so past what fits it spills out over the map.
    That is not hypothetical - it is the bug the first version of the choices band
    shipped with. The container already handles wrapping, measurement and the scrollbar.
    """

    def test_the_choices_go_through_a_listbox(self):
        import inspect
        self.assertIn("gui_list_box(", inspect.getsource(X._act_app))

    def test_so_do_the_callers(self):
        import inspect
        self.assertIn("gui_list_box(", inspect.getsource(X._crew_app))

    def test_no_choice_button_is_built_in_a_loop(self):
        """The for-loop handler trap: a handler registered in a loop captures the loop
        variable at its LAST value, so every button would answer with the last choice.
        The listbox's own selection is the commitment instead - one press, no separate
        ACT button, which is what "the choice buttons are still weird" was about."""
        import inspect
        src = inspect.getsource(X._act_app)
        self.assertNotIn("for ", src[src.index("choices ="):])

    def test_the_item_templates_return_None(self):
        """The listbox only calls `resize_to_content()` when a template returns None; a
        returned size leaves the item section degenerate, which kills selection and the
        click region with it.

        Parsed rather than grepped - an earlier version of this test matched the word
        "returns" in the function's own docstring and passed on prose.
        """
        import ast
        import inspect
        import textwrap
        for template in (X._choice_row, X._caller_row):
            tree = ast.parse(textwrap.dedent(inspect.getsource(template)))
            returns = [n for n in ast.walk(tree)
                       if isinstance(n, ast.Return) and n.value is not None]
            self.assertEqual([], returns,
                             "%s must return None" % template.__name__)

    def test_the_prose_is_a_text_area_not_a_stack_of_rows(self):
        """A Control clears and scrolls its own region, which is what prose needs and
        what a column of `gui_text` rows can only imitate badly."""
        import inspect
        self.assertIn("gui_text_area(", inspect.getsource(X._act_app))
        self.assertIn("gui_text_area(", inspect.getsource(X._home))


class AChoiceCarriesItsBeat(_XessBase):
    """`boarding_answer` re-derives the choice list and indexes into it, so an index
    captured when the button was built is only valid for that beat."""

    def test_the_answer_passes_the_seq_it_was_built_with(self):
        import inspect
        src = inspect.getsource(X._act_app)
        self.assertIn("seq = boarding_seq()", src)
        self.assertIn("seq=seq", src)

    def test_and_the_agent_the_choice_belongs_to(self):
        """So the index is read back against the list the row came from rather than the
        merged one, which is a different list when a console holds two characters."""
        import inspect
        self.assertIn("agent=", inspect.getsource(X._act_app))


class ACoveringChoiceSaysSo(unittest.TestCase):
    """The attribute is `forwarded` - the guard text `boarding_orphan_choices` puts on a
    choice nobody present qualifies for. This read `covering` for its whole life, which
    NOTHING has ever set, so the mark has never once appeared on the crew console."""

    def test_a_forwarded_choice_is_marked(self):
        class _Ch:
            label = "Read the panel"
            forwarded = "Dr Sorel"
        self.assertIn("covering for Dr Sorel", X._choice_text(_Ch()))

    def test_an_ordinary_choice_is_just_its_label(self):
        class _Ch:
            label = "Read the panel"
            forwarded = None
        self.assertEqual("Read the panel", X._choice_text(_Ch()))


class TheCrewListIsStable(_XessBase):
    """`boarding_team` returns a SET. An unsorted roster reshuffles itself on every
    rebuild and nobody can find the same person twice."""

    def test_the_people_are_in_a_stable_order(self):
        for name in ("Zara Vale", "Ana Ruiz", "Marek Sol"):
            who = lifeform_spawn(name, "terran_male", "boarding,crewmate")
            A.boarding_assign_also(CID, who)
        first = [c["name"] for c in X._callers(CID)]
        second = [c["name"] for c in X._callers(CID)]
        self.assertEqual(first, second)
        people = first[1:-1]
        self.assertEqual(sorted(people, key=str.lower), people)

    def test_the_ship_is_first_and_everyone_is_last(self):
        callers = X._callers(CID)
        self.assertEqual("ship", callers[0]["id"])
        self.assertEqual("all", callers[-1]["id"])

    def test_you_are_marked_and_cannot_call_yourself(self):
        me = [c for c in X._callers(CID) if c.get("you")]
        self.assertEqual(1, len(me))
        import inspect
        self.assertIn('if item.get("you"):', inspect.getsource(X._caller_detail))

    def test_each_person_is_addressed_by_their_BODY(self):
        """Every boarded console reports the same console name, so a console-addressed
        message cannot tell two boarders apart."""
        for caller in X._callers(CID):
            if caller["id"] in ("ship", "all"):
                continue
            self.assertTrue(str(caller["to"]).startswith("crew:"), caller)


if __name__ == "__main__":
    unittest.main()
