from ..gui import Page, Gui
from .. import layout as layout
from .. import faces as faces
from ..helpers import FrameContext, gui_text_escape


#: Button tag -> race. The tags are the historical three-letter spellings this page has
#: always used; note "xim", which is NOT the atlas alias ("zim"). Kept as-is because they
#: are only widget tags, and renaming them would change nothing anybody can see.
_RACE_BY_TAG = {
    "arv": "arvonian", "kra": "kralien", "ska": "skaraan",
    "ter": "terran", "tor": "torgoth", "xim": "ximni",
}


class AvatarEditor(Page):
    """A minimal face builder, driven entirely by `faces.FACE_FEATURES`.

    This page used to carry its OWN table of per-race controls - the fourth independent
    copy of that data in the tree - and it had drifted badly: it listed controls for two
    of the six races, and the Kralien entry offered "Eyes" and "Hair Tone" for a race
    whose sheet has no hair at all. Reading the library's recipe instead means the page
    cannot disagree with the art, and it picked up the features the 2026-09 redraw added
    without being edited.

    The in-engine editor is LegendaryMissions' `avatar_editor` addon, which is what
    players actually see. This one backs the library's own demo `script.py`.
    """

    def __init__(self) -> None:
        self.gui_state = "arv"
        self.race = "arvonian"
        self.values = []
        self.enables = []
        self._reset_for_race()

    # --- state ---------------------------------------------------------------

    def _features(self):
        return faces.FACE_FEATURES.get(self.race, [])

    def _reset_for_race(self):
        """Start every control at its minimum and every optional feature switched off.

        Sized from the feature list rather than from a fixed-length buffer: the races no
        longer have anything like the same number of controls (Arvonian has four, Terran
        eleven), so a shared 12-slot list quietly mixed one race's values into another's.
        """
        feats = self._features()
        self.values = [0] * len(feats)
        self.enables = [not f.get("optional", False) for f in feats]
        self._rebuild()

    def _rebuild(self):
        self.face = faces.build_face(self.race, self.values, self.enables)

    # --- drawing -------------------------------------------------------------

    def present(self, event):
        CID = event.client_id
        SBS = FrameContext.context.sbs

        if self.gui_state == "presenting":
            return
        SBS.send_gui_clear(CID)
        SBS.send_gui_text(0, "title", "$text:Avatar Editor", 25, 5, 99, 9)
        SBS.send_gui_face(CID, "face", self.face, 35, 0, 65, 1)

        l1 = layout.wrap(25, 50, 19, 4, col=3)
        for tag, race in _RACE_BY_TAG.items():
            SBS.send_gui_button(CID, tag, f"$text: {race.capitalize()}", *next(l1))

        w = layout.wrap(99, 99, 19, 4, col=1, v_dir=-1, h_dir=-1)
        SBS.send_gui_button(CID, "back", "$text:back", *next(w))

        # Bottom of the race buttons, so the controls start below them.
        (_l, t, _r, b) = next(l1)
        feats = self._features()
        l2 = layout.wrap(25, b, 15, 4, col=4, h_gutter=1)
        for i, widget in enumerate(feats):
            label = widget["label"]
            loc = next(l2)
            if widget.get("optional"):
                on = self.enables[i]
                SBS.send_gui_checkbox(
                    CID, f"op:{i}",
                    f"$text: {gui_text_escape(label)};state: {'on' if on else 'off'}",
                    *loc)
                if on and widget["max"] > 0:
                    SBS.send_gui_slider(CID, f"{i}", self.values[i],
                                        f"low: 0; high: {widget['max']}", *next(l2))
                else:
                    next(l2)
            else:
                SBS.send_gui_text(CID, label, f"$text:{gui_text_escape(label)}", *loc)
                SBS.send_gui_slider(CID, f"{i}", self.values[i],
                                    f"low: 0; high: {widget['max']}; show_number: no",
                                    *next(l2))
        SBS.send_gui_complete(CID)
        self.gui_state = "presenting"

    # --- input ---------------------------------------------------------------

    def on_message(self, event):
        tag = event.sub_tag
        if tag == "back":
            Gui.pop(event.client_id)
            return

        if tag.startswith("op:"):
            try:
                i = int(tag[3:])
            except ValueError:
                return
            if 0 <= i < len(self.enables):
                self.enables[i] = not self.enables[i]
                self._rebuild()
        elif tag in _RACE_BY_TAG:
            self.race = _RACE_BY_TAG[tag]
            self._reset_for_race()
        else:
            try:
                i = int(tag)
            except ValueError:
                return
            if 0 <= i < len(self.values):
                self.values[i] = round(event.sub_float)
                self._rebuild()

        self.gui_state = self.race
        self.present(event)
