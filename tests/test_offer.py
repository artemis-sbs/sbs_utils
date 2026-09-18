"""Tests for the offer registry - the "what is there for us?" primitive.

An offer is something the world has for you that you have not taken. Providers compute
them on demand; nothing is stored. These pin the contract the badge, the board, the comms
selection title and the digest all depend on - above all that ONE bad provider can never
cost the others their rows, because offers are computed on every tile of every build.

    python -m unittest tests.test_offer
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.procedural import offer as OF
from sbs_utils.procedural.offer import (
    offer_record, offer_register, offer_unregister, offer_providers,
    offer_mission_providers, offer_clear, offers, offer_count, offers_for_object,
    offer_generation, offer_touch)


def _one(title="Job", **kw):
    kw.setdefault("key", "t:" + title)
    return offer_record(title=title, **kw)


class OfferRegistryTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        offer_clear()

    def tearDown(self):
        offer_clear()

    # --- registration ---------------------------------------------------------
    def test_core_provider_is_installed(self):
        self.assertIn("quest", offer_providers())

    def test_register_and_unregister(self):
        offer_register("t", lambda ctx: [_one()])
        self.assertIn("t", offer_providers())
        self.assertTrue(offer_unregister("t"))
        self.assertNotIn("t", offer_providers())
        self.assertFalse(offer_unregister("t"))

    def test_identical_reregister_is_a_noop(self):
        """Re-running an addon's setup must not raise - the urge_register_condition rule."""
        fn = lambda ctx: []
        offer_register("t", fn)
        offer_register("t", fn)
        self.assertIn("t", offer_providers())

    def test_conflicting_reregister_raises(self):
        offer_register("t", lambda ctx: [])
        with self.assertRaises(ValueError):
            offer_register("t", lambda ctx: [])

    def test_a_name_is_required_and_must_be_callable(self):
        with self.assertRaises(ValueError):
            offer_register("  ", lambda ctx: [])
        with self.assertRaises(ValueError):
            offer_register("t", "not callable")

    # --- the guarantee that matters -------------------------------------------
    def test_a_raising_provider_costs_only_its_own_rows(self):
        def bad(ctx):
            raise RuntimeError("boom")
        offer_register("bad", bad)
        offer_register("good", lambda ctx: [_one("Good")])
        titles = [r.get("title") for r in offers()]
        self.assertEqual(titles, ["Good"])

    def test_a_raising_provider_is_reported_once(self):
        def bad(ctx):
            raise RuntimeError("boom")
        offer_register("bad", bad)
        for _ in range(5):
            offers()
        hits = [k for k in OF._OFFER_REPORTED if k[0] == "bad"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][1], "RuntimeError")

    def test_a_reentrant_provider_is_answered_not_reentered(self):
        """A provider is free to ask what the others offer. That is a cycle unless the
        asking one is short-circuited - the bug gui_app_badge measured at 332 entries."""
        seen = []

        def nosy(ctx):
            seen.append(1)
            offers()                       # ask again from inside
            return [_one("Nosy")]

        offer_register("nosy", nosy)
        rows = offers()
        self.assertEqual(len(seen), 1)
        self.assertIn("Nosy", [r.get("title") for r in rows])

    def test_a_provider_returning_none_is_tolerated(self):
        offer_register("n", lambda ctx: None)
        offer_register("g", lambda ctx: [_one("G")])
        self.assertEqual([r.get("title") for r in offers()], ["G"])

    def test_none_entries_are_dropped(self):
        offer_register("n", lambda ctx: [None, _one("Real"), None])
        self.assertEqual([r.get("title") for r in offers()], ["Real"])

    # --- counting and filtering -----------------------------------------------
    def test_count_excludes_pending(self):
        offer_register("t", lambda ctx: [
            _one("Takeable"),
            _one("Posted", pending=True),
        ])
        self.assertEqual(len(offers()), 2)
        self.assertEqual(offer_count(), 1)

    def test_kind_filter(self):
        offer_register("t", lambda ctx: [
            _one("A", kind="job"), _one("B", kind="trade")])
        self.assertEqual([r.get("title") for r in offers(kinds="trade")], ["B"])
        self.assertEqual(len(offers(kinds=["job", "trade"])), 2)

    def test_sorted_by_sort_then_title(self):
        offer_register("t", lambda ctx: [
            _one("Zeta", sort=1), _one("Alpha", sort=5), _one("Beta", sort=5)])
        self.assertEqual([r.get("title") for r in offers()],
                         ["Zeta", "Alpha", "Beta"])

    def test_context_reaches_the_provider(self):
        got = {}

        def p(ctx):
            got.update({"c": ctx.get("client_id"), "s": ctx.get("ship_id"),
                        "o": ctx.get("object_id"), "k": ctx.get("console")})
            return []

        offer_register("p", p)
        offers(client_id=7, ship_id=9, object_id=11, console="comms")
        self.assertEqual(got, {"c": 7, "s": 9, "o": 11, "k": "comms"})

    def test_offers_for_object_passes_the_id_through(self):
        offer_register("p", lambda ctx: (
            [_one("Mine")] if ctx.get("object_id") == 42 else []))
        self.assertEqual([r.get("title") for r in offers_for_object(42)], ["Mine"])
        self.assertEqual(offers_for_object(None), [])

    # --- generation -----------------------------------------------------------
    def test_generation_moves_on_touch_and_registration(self):
        g = offer_generation()
        offer_touch()
        self.assertNotEqual(g, offer_generation())
        g = offer_generation()
        offer_register("t", lambda ctx: [])
        self.assertNotEqual(g, offer_generation())

    def test_generation_moves_when_a_quest_does(self):
        from sbs_utils.procedural.quest import quest_add
        from sbs_utils.procedural.a2x.spawn import create_enemy
        from sbs_utils.procedural.query import to_id
        ship = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="P"))
        g = offer_generation()
        quest_add(ship, "j", "J", "")
        self.assertNotEqual(g, offer_generation())

    # --- reset ----------------------------------------------------------------
    def test_clear_drops_mission_providers_and_keeps_core(self):
        offer_register("mission_thing", lambda ctx: [])
        self.assertEqual(offer_mission_providers(), ["mission_thing"])
        offer_clear()
        self.assertEqual(offer_mission_providers(), [])
        self.assertIn("quest", offer_providers())

    def test_clear_drops_the_reported_set(self):
        offer_register("bad", lambda ctx: (_ for _ in ()).throw(RuntimeError("x")))
        offers()
        self.assertTrue(OF._OFFER_REPORTED)
        offer_clear()
        self.assertFalse(OF._OFFER_REPORTED)


class OfferRecordTests(unittest.TestCase):
    def test_defaults(self):
        r = offer_record("k", "Title")
        self.assertEqual(r.get("key"), "k")
        self.assertEqual(r.get("kind"), "job")
        self.assertFalse(r.get("pending"))
        self.assertEqual(r.get("detail"), "")
        self.assertEqual(r.get("data"), {})

    def test_none_text_becomes_empty_not_the_string_none(self):
        r = offer_record("k", "T", detail=None, where=None)
        self.assertEqual(r.get("detail"), "")
        self.assertEqual(r.get("where"), "")


class TheBoardUpdatesItDoesNotRepaintTests(unittest.TestCase):
    """The board builds ONCE and updates what moved.

    Three things were wrong at once and they had one cause - reaching for a rebuild:

    * selecting a row invoked the offer's `take`, so the list could not be browsed;
    * the route carried `on change offer_generation(): jump <label>`, which is the named
      anti-pattern verbatim - a repaint re-sends every widget over the wire per change,
      and two builds landing at once is what makes a board look scrambled;
    * the detail band was a refilled `gui_sub_section`, which leaves the previous fill
      painted underneath.

    Pinned at the source, because what matters is which code paths exist at all.
    """

    def _src(self):
        import inspect
        from sbs_utils.procedural.gui import offers_gui
        return inspect.getsource(offers_gui)

    def test_selecting_does_not_take(self):
        src = self._src()
        sel = src[src.index("def _select("):]
        self.assertNotIn('item["take"]', sel,
                         "selecting a row still invokes the offer's take")

    def test_there_is_a_take_button(self):
        self.assertIn("gui_button(_take_label(first), on_press=_take)", self._src())

    def test_the_button_binds_its_client_at_build_time(self):
        """MessageHandler calls a handler with NO arguments, so one that reads the
        ambient client works until the frame belongs to somebody else - and a job granted
        to the wrong client lands on nobody's Quests tab."""
        self.assertIn("def _take(_cid=cid):", self._src())

    def test_taking_updates_the_widgets_rather_than_repainting(self):
        src = self._src()
        take = src[src.index("def _take(_cid=cid):"):]
        self.assertIn("lb.items =", take)
        self.assertIn("detail.value =", take)
        self.assertIn("take_btn.update(", take)

    def test_nothing_rebuilds_a_section(self):
        """A refilled sub_section leaves the earlier fill painted underneath."""
        src = self._src()
        # The CALL, not the word - the docstrings explain why it is not used.
        self.assertNotIn("gui_rebuild(", src)
        self.assertNotIn("gui_sub_section(", src)

    def test_a_row_is_two_columns_not_three(self):
        """The objective used to share the row and wrapped one character wide."""
        src = self._src()
        row = src[src.index("def _row_template("):src.index("def _detail_text(")]
        self.assertNotIn("item.get('detail')", row)
        self.assertNotIn('item["detail"]', row)


class DetailLineTests(unittest.TestCase):
    """What the line under the list says - it is a VALUE pushed into a held widget."""

    def _row(self, **kw):
        base = {"title": "Picket Patrol", "detail": "Hold the picket",
                "where": "Hangar", "take": None, "can_take": False}
        base.update(kw)
        return base

    def test_nothing_selected_says_so(self):
        from sbs_utils.procedural.gui.offers_gui import _detail_text
        self.assertIn("Select", _detail_text(None))

    def test_it_shows_what_the_job_asks(self):
        from sbs_utils.procedural.gui.offers_gui import _detail_text
        self.assertIn("Hold the picket", _detail_text(self._row()))

    def test_it_says_WHERE_only_when_this_console_cannot_take_it(self):
        from sbs_utils.procedural.gui.offers_gui import _detail_text
        self.assertIn("Hangar", _detail_text(self._row()))
        takeable = self._row(take=lambda c, r: True, can_take=True)
        self.assertNotIn("Hangar", _detail_text(takeable),
                         "telling you to go where you already are")

    def test_the_button_label_is_ascii(self):
        from sbs_utils.procedural.gui.offers_gui import _take_label
        for item in (None, self._row(), self._row(take=lambda c, r: True,
                                                  can_take=True)):
            _take_label(item).encode("ascii")


class TheClientIsThePagesTests(unittest.TestCase):
    """Whose board this is: the PAGE's client, not the event's.

    A button handler runs under MessageHandler's frame and a watcher runs under the
    emitter's, while `FrameContext.page` is still correctly this console. Reading the
    event is how a job gets granted to the wrong client - or to none.
    """

    def test_it_prefers_the_pages_client(self):
        import inspect
        from sbs_utils.procedural import offer
        src = inspect.getsource(offer.offer_context_here)
        self.assertIn('getattr(page, "client_id", None)', src)


if __name__ == "__main__":
    unittest.main()
