"""A map picker: choose one of a story's ``@map`` labels and start it.

WHY THIS IS IN THE LIBRARY. ``@map`` is the normal way a mission offers several entry
points, and until now it was unusable in a mission that loads only sbs_utils - both halves
of the machinery lived in LegendaryMissions. Its server console drew the selection screen,
so with sbs_utils alone the server page came up EMPTY with no way in, and the headless
runner's ``--map`` auto-start found nothing to start. A mission wanting its own maps had to
hand-roll a menu, which is the wrong shape for something every addon's test mission needs.

The pieces underneath were already generic and already here - ``maps_get_list``,
``map_get_properties``, ``gui_property_list_box`` and ``gui_list_box(carousel=True)``. This
is the ~100 lines of screen that were missing, and nothing more.

THE LIGHT TIER, DELIBERATELY. LegendaryMissions' console also does game codes and presets,
music selection, the player roster, operator mode and beam damage. Those stay there. This
is a carousel, a properties panel and a Start button - enough for a mission to offer its
maps, not a replacement for LM's console. Keep the line where it is.

    == main ==
        chosen = await gui_map_picker()
        map_start(chosen)
        ->END
"""
from ...futures import Promise
from ...mast.pollresults import PollResults
from ..maps import maps_get_list, map_get_properties, map_apply_defaults, map_apply_crew
from .listbox import gui_list_box
from .button import gui_button
from .text import gui_text
from .row import gui_row
from .message import gui_message_callback
from .property_listbox import gui_property_list_box, gui_properties_set
from .gui import gui
from ...helpers import gui_text_escape


class _MapPickerPromise(Promise):
    """Presents the picker, and resolves with the CHOSEN MAP.

    Two jobs in one object, because neither alone works:

      * Queued gui_* widgets are not presented until a GuiPromise is polled
        (GuiPromise.initial_poll -> set_button_layout -> swap_layout). Returning a bare
        Promise would build a page that never appears - a silent failure, no error.
      * The obvious `promise_any(gui(), prom)` presents correctly but resolves with a
        LIST indexed by promise position (PromiseAllAny.result), so the caller gets
        `[None, ButtonResult]` where it wanted a map label, and `map_start` then fails
        deep inside map_apply_defaults.

    So: poll the GuiPromise for presentation, and carry the map as this promise's own
    result. `done()` is inherited - it is true as soon as a result is set.
    """

    def __init__(self, gui_promise):
        super().__init__()
        self._gui = gui_promise

    def poll(self):
        if self._gui is not None:
            self._gui.poll()
        return PollResults.OK_RUN_AGAIN


def _map_item_template(item):
    """One carousel card: the map's display name over its description.

    gui_text_escape is not optional here. A description is free prose and a ``:`` or ``;``
    in it would otherwise be read as style properties, silently truncating the card.
    """
    gui_row("row-height: 1em+10px;padding:10px,10px,10px,0;")
    gui_text(f"$text:{gui_text_escape(getattr(item, 'display_name', str(item)))};"
             f"justify: left;font:gui-3;")
    gui_row("padding:10px,0,10px,3px;")
    gui_text(f"$text:{gui_text_escape(getattr(item, 'desc', ''))};"
             f"justify: left;color:#999;font:gui-2;")


def gui_map_picker(maps=None, properties=True, title=None, start_text="Start",
                   list_style="item-gap: 7em;"):
    """Build a map carousel plus a Start button; return an awaitable resolving to the choice.

    Pairs with ``map_start``: this one only CHOOSES, so a mission can do something else with
    the answer, or start a map it picked some other way.

        chosen = await gui_map_picker()
        map_start(chosen)

    Args:
        maps (list | None): Map labels to offer. Defaults to ``maps_get_list()``, which
            already hides maps whose ``if`` condition is false.
        properties (bool): Render the selected map's ``Properties:`` panel. On by default -
            it is two calls, and without it a map expecting ``PLAYER_COUNT`` starts with it
            unset, which is a silent wrong-behaviour trap rather than a missing feature.
        title (str | None): Listbox title. Defaults to a count of the maps.
        start_text (str): Label for the start button.
        list_style (str): Style string for the carousel.

    Returns:
        Promise: Resolves with the chosen map Label when Start is pressed. A story with no
        maps draws a message and returns a promise that never resolves, rather than raising.
    """
    maps = list(maps) if maps is not None else maps_get_list()
    # maps_get_list returns a placeholder DICT (not a Label) when a story has none.
    maps = [m for m in maps if hasattr(m, "path")]

    if not maps:
        gui_row("row-height: 2em;")
        gui_text("$text:`No maps found in this story.`;justify:center;")
        return gui()

    if title is None:
        title = "Select a mission." if len(maps) == 1 else f"Select a mission. {len(maps)} types."

    lb = gui_list_box(maps, list_style,
                      item_template=_map_item_template, title_template=title,
                      select=True, carousel=True)
    lb.set_selected_index(0)

    def _selected():
        sel = lb.get_value()
        return sel if hasattr(sel, "path") else maps[0]

    if properties:
        # Defaults are set-if-absent, so applying them per selection is safe and is what
        # makes the panel show the map's own starting values.
        map_apply_defaults(_selected())
        map_apply_crew(_selected())
        gui_property_list_box(name="Options")
        gui_properties_set(map_get_properties(_selected()))

        def _on_select(event, sender):
            # Handled in PYTHON, with no task in the path - the callback channel exists for
            # exactly this. LM repaints its panel by re-jumping its whole label, which a
            # library function cannot do; gui_properties_set already calls gui_represent
            # when it is not the first build, so the panel updates in place instead.
            sel = _selected()
            map_apply_defaults(sel)
            map_apply_crew(sel)
            gui_properties_set(map_get_properties(sel))

        gui_message_callback(lb, _on_select)

    gui_row("row-height: 2.4em;")
    # A plain label, the form LM uses (gui_button("ready")). Wrapping it in an explicit
    # $text: with gui_text_escape doubled the backticks in the rendered style string; the
    # widget builds its own $text: from a bare label.
    btn = gui_button(start_text)

    out = _MapPickerPromise(gui())
    # The press is handled in PYTHON on the callback channel - no task in the path, and no
    # MAST label needed. Resolving with _selected() is what makes `chosen` a map label
    # rather than a ButtonResult, so `map_start(chosen)` gets what it expects.
    gui_message_callback(btn, lambda event, sender: out.set_result(_selected()))
    return out
