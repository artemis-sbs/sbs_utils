"""An authored overlay directive must be TEMPORARY (PRM-8).

`On accept: toast Job accepted: X` reached overlay_kind() with no `seconds`, and
_show_transient only schedules a dismiss when it is given one - so the toast was
registered STICKY. It sat on every console for the rest of the mission, and restarting
the mission script was the only thing that cleared it. overlay_toast() had always
expired; this path never did.

    python -m unittest tests.test_quest_overlay_lifetime
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from sbs_utils.procedural import quest_driver as QD


class DirectiveLifetimeTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._real = QD.overlay_kind
        QD.overlay_kind = lambda kind, **kw: self.calls.append((kind, kw))

    def tearDown(self):
        QD.overlay_kind = self._real

    def test_a_toast_directive_is_given_a_lifetime(self):
        QD._fire_overlay_directive("toast Job accepted: Gunnery Qualification", None)
        kind, kw = self.calls[0]
        self.assertEqual("toast", kind)
        self.assertTrue(kw.get("seconds"),
                        "a toast with no lifetime is registered sticky and never clears")

    def test_every_kind_gets_one(self):
        """No directive should be able to pin an overlay up permanently."""
        for kind in ("toast", "banner", "hero", "lower_third"):
            self.calls.clear()
            QD._fire_overlay_directive(f"{kind} something happened", None)
            _, kw = self.calls[0]
            self.assertTrue(kw.get("seconds"), f"{kind} directive had no lifetime")

    def test_an_unknown_kind_still_gets_a_default(self):
        self.calls.clear()
        QD._fire_overlay_directive("wibble something happened", None)
        _, kw = self.calls[0]
        self.assertTrue(kw.get("seconds"), "unknown kinds must not default to sticky")

    def test_lifetimes_match_announce_for_the_same_kinds(self):
        """A directive and an announce of the same weight should agree."""
        from sbs_utils.procedural.announce import _LEVEL_SECONDS, LEVELS
        for level, (kind, _twin) in LEVELS.items():
            if kind in QD._DIRECTIVE_SECONDS:
                self.assertEqual(_LEVEL_SECONDS[level], QD._DIRECTIVE_SECONDS[kind],
                                 f"{kind}: directive and announce disagree")

    def test_an_authored_toast_directive_never_reaches_the_overlay_layer(self):
        """`On complete: toast ...` is a LOG line now (mkdocs build/messages.md). The directive
        stays valid - authored content must not start failing - but the corner card that
        needed its own scrim and its own lifetime is gone, and with it the bug where an
        authored toast registered STICKY.

        Goes through the REAL overlay_kind, since the retirement lives inside it."""
        from sbs_utils.procedural.gui import overlay as OV
        QD.overlay_kind = self._real
        shown = []
        real_show = OV._show_transient
        OV._show_transient = lambda *a, **k: shown.append(a)
        try:
            QD._fire_overlay_directive("toast Objective updated", None)
        finally:
            OV._show_transient = real_show
        self.assertEqual([], shown, "the toast retired into the log; nothing draws")
