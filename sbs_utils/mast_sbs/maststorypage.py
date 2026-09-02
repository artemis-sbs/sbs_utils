import logging
from ..gui import Gui, Page
from ..helpers import FakeEvent, FrameContext, FrameContextOverride
from ..message_chain import compose_handler
from ..procedural.inventory import get_inventory_value, set_inventory_value, has_inventory_value
from ..procedural.links import linked_to
from ..procedural.gui.navigation import gui_reroute_client
from ..procedural.style import apply_control_styles

from ..procedural.signal import signal_emit
from ..procedural.execution import log
from ..agent import Agent
#from ..pages.layout import layout
from ..pages.layout.layout import Layout
from ..pages.layout.row import Row
from ..pages.layout.text import Text
from ..pages.layout.icon import Icon
from ..helpers import gui_text_escape


def _is_main_screen(client_id, console):
    """Whether this console is the shared view rather than one person's station.

    The badge names the person at the console, and the main screen is the whole
    room's - a name on it is either wrong or somebody else's. The same test the away
    team already uses to decide the main screen takes no character.
    """
    if console and str(console).strip().lower() in ("mainscreen", "main_screen"):
        return True
    try:
        from ..procedural.roles import has_role
        return bool(has_role(client_id, "mainscreen"))
    except Exception:
        return False


def _console_identity(client_id, page_console):
    """Which console this client is on, for app scoping and the badge.

    What THIS BUILD declared wins, and the door's record fills in only when the build
    declared nothing. Both orders agree in the ordinary case; they part on a build that
    activates one console while the client's sticky CONSOLE_TYPE still names another,
    and there the screen being drawn is the honest answer.

    The fallback is the point, though. `gui_console_enter` - the one door - writes
    CONSOLE_TYPE and never touches `page.console`, so a console entered through it and
    nothing else reports `page.console == ""` for the rest of its life. The away screen
    is the shipped example (`gui_console_enter(cid, "away")`, no `@console/away`
    label), and reading the page alone answered "" for it - which left the away console
    scoped as if it were no console at all. The same mis-read cost three rounds on the
    messages app (2026-09-01), where it made `message_select` drop every pick in
    silence.

    NOT a test for "is this a console screen" - CONSOLE_TYPE is sticky, and nothing
    clears it when a client leaves one. See `_epadd_belongs_here`.
    """
    return page_console or get_inventory_value(client_id, "CONSOLE_TYPE", None)


def _identity_style(text, accent):
    """The badge's style string, in one place because two callers build it.

    ESCAPED, not hand-quoted: a crew member's name is authored content and a `;` or a
    backtick in it would otherwise end the style string early and draw the rest of it
    as text. `tests/test_gui_text_quoting` enforces this across the library.

    NOT CENTRED. The region is a percentage of the screen, so on a wide display it is
    a wide box - and a centred label in a wide box floats away from the glyph beside it,
    which is the growing gap the playtest caught on a larger screen. Left is the default
    and the column is content-sized, so the name sits against the glyph at any size.
    """
    return (f"$text:{gui_text_escape(text)};font:gui-1;color:{accent};"
            f"overflow:shrink;")
from ..pages.layout.blank import Blank
from ..pages.layout.dropdown import Dropdown
from..fs import get_mission_name, get_startup_mission_name, is_dev_build

from .story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel

from ..mast.maststory import  MastStory
from ..mast.mastscheduler import MastAsyncTask
from .maststoryscheduler import StoryScheduler

# Keep for runtime supprt
from . import story_nodes
#from .mastmission import MissionLabel, StateMachineLabel
from . import mast_sbs_procedural


class TabControl(Text):
    def __init__(self, tag, message, label, page) -> None:
        super().__init__(tag,message)
        self.page = page
        self.label = label
        apply_control_styles(None, "margin:1px,0,0,0;", self, page.task)

    def on_message(self, event):
        if event.sub_tag == self.click_tag:
            if self.label is not None:
                self.page.gui_task.jump(self.label)
                self.page.gui_task.tick_in_context()




#: The PADD's own glyph, from the engine's grid-icon-sheet - the same sheet the
#: engineering grid draws from. So the strip needs no word for it.
#:
#: Resolved through the NAME table rather than written as an index, so a mission that
#: re-skins `phone` with `gui_image_add_atlas` re-skins this too.
IDENTITY_ICON = "phone"

#: The strip spans x20..100. Seven slots across it, of which the PADD takes the left two
#: as ONE region - so the tab row starts where that region ends and its slots stay
#: exactly the width they would have been.
#: IN PIXELS, because the thing it has to sit beside is. The engine's Options button is
#: a fixed-pixel control, so a percentage only touches it at ONE resolution - 20% of 1024
#: is 205px, which is why this looked right at 1024x768 and opened a growing gap on
#: anything larger (playtest images, 2026-09-02). Converted per client instead.
STRIP_LEFT_PX = 205
#: The badge's own width, also in pixels and for the same reason. As a share of the
#: screen its click region grew with the display, so on a big monitor a press a long way
#: from the badge still opened the PADD.
IDENTITY_WIDTH_PX = 350
#: The percentages these used to be, kept as the fallback for a client that has not
#: reported its resolution yet, and as the reference the pixel numbers came from.
STRIP_LEFT = 20
STRIP_SLOTS = 7
#: THREE, not two. A PADD screen puts one tab on the bar - the way back to the console -
#: so the whole middle of the strip is empty while the name is squeezed against the
#: Options button. The extra slot costs a normal console nothing it was using: the tabs
#: divide what is left, and six of them still fit.
IDENTITY_SLOTS = 3
_SLOT_W = (100 - STRIP_LEFT) / STRIP_SLOTS
IDENTITY_RIGHT = STRIP_LEFT + IDENTITY_SLOTS * _SLOT_W

#: The status region's click tag, FIXED rather than derived.
#:
#: A Layout's default is `__click:{tag}`, and `tag` is a build-order ordinal that jumps
#: ~2100 every rebuild - so each visit to the PADD asked the engine for a NEW click
#: region and left the previous one live. A press answered by one of those reaches a
#: region belonging to a build that is gone: the handler correctly ignores it, but the
#: press is spent. Measured in a real session as `__click:68684` arriving while the
#: current region was `81284`.
#:
#: One region, one name, reused every build.
IDENTITY_CLICK_TAG = "epadd-status-region"

#: The strip's row height. The tab buttons declare `row-height:35px`, so this is how
#: tall the bar actually IS - and the click region has to match it or the hit target
#: stops short of the control it belongs to.
STRIP_ROW_PX = 35
#: The fallback when the client has not reported its resolution yet: 3% of a 768-high
#: screen is ~23px, short of the row, but it is the historic number and it is only ever
#: used for the first build or two.
STRIP_FALLBACK_PCT = 3


#: The strip's rect as an `area:` STYLE, in pixels.
#:
#: A style, not numbers, because `Layout.calc` re-resolves `bounds_style` against the
#: CURRENT aspect ratio on every layout pass - so a px area follows a window resize on
#: its own. Bounds passed to the constructor do not: they are frozen at whatever the
#: build computed, and a resize only sets `gui_state = "refresh"`, which re-presents the
#: EXISTING layouts rather than rebuilding them. Converting px to percent by hand at
#: build time therefore looked right until the window changed size, and then the badge
#: drifted off the Options button while the PADD's own screens - which do rebuild -
#: stayed correct (reported 2026-09-02).
def _strip_area(left_px, right="100"):
    """`area:` for a strip-height band starting at `left_px`."""
    return f"area: {left_px}px, 0, {right}, {STRIP_ROW_PX}px;"


def _pct_x(client_id, px, fallback):
    """A horizontal pixel measurement as the PERCENT a Layout's bounds want."""
    try:
        from ..procedural.gui.gui import gui_percent_from_pixels
        pct = gui_percent_from_pixels(client_id, px).x
        if pct and pct > 0:
            return pct
    except Exception:
        pass
    return fallback


def _strip_left(client_id):
    """Where the strip starts: just past the engine's Options button."""
    return _pct_x(client_id, STRIP_LEFT_PX, STRIP_LEFT)


def _identity_right(client_id):
    """Where the badge ends, and therefore where the tab row begins."""
    return _strip_left(client_id) + _pct_x(client_id, IDENTITY_WIDTH_PX,
                                           IDENTITY_SLOTS * _SLOT_W)


def _strip_bottom(client_id):
    """How far down the strip reaches, as the PERCENT a Layout's bounds want.

    A Layout's rect is a percentage while the row inside it is declared in PIXELS, so
    the two only agree at one resolution. They did not agree at the playtest's: the
    region was 3% (~32px at 1080) against a 35px row, so the press highlight stopped
    above the bottom of the bar and the badge read as floating in it.

    Converted per client, because that is what the percentage has to track.
    """
    try:
        from ..procedural.gui.gui import gui_percent_from_pixels
        pct = gui_percent_from_pixels(client_id, STRIP_ROW_PX).y
        if pct and pct > 0:
            return pct
    except Exception:
        pass
    return STRIP_FALLBACK_PCT

# CLICK_HIGHLIGHT lives with the other design tokens in procedural/gui/epadd.py.


def _identity_icon_props(accent):
    """The glyph's props, or None when nothing answers to that name.

    A missing icon draws nothing rather than some arbitrary index - a wrong glyph is
    worse than no glyph, because it looks deliberate.
    """
    from ..procedural.gui.icon_sheet import icon_resolve
    index, atlas_key = icon_resolve(IDENTITY_ICON)
    if index is None:
        return None                  # a re-skinned name needs an Image, not an Icon
    return f"icon_index:{index};color:{accent};"


# How many tabs the strip shows before the rest go into an overflow menu.
#
# The strip is a FIXED width (20%..100%) divided evenly, so it never dropped a tab and
# never scrolled - it just kept making them narrower. At 18 registered tabs that is 4.4%
# each, about 85px on a 1920 screen, and "engineering" needs roughly 130. The engine does
# not clip text, so the labels drew straight over their neighbours: the tabs were all
# present and all illegible, which is why adding tabs made EXISTING ones unreadable
# (PRM-26).
#
# Eight keeps every visible tab at 10% (~192px), comfortably wider than the longest label
# we ship.
TAB_MAX_VISIBLE = 8


class TabOverflow(Dropdown):
    """The tabs that did not fit, as a menu. Selecting one jumps to it exactly as
    clicking its tab would - the same two lines TabControl runs."""

    def __init__(self, tag, props, labels, page) -> None:
        super().__init__(tag, props)
        self.labels = labels
        self.page = page

    def on_message(self, event):
        if event.sub_tag == self.tag:
            label = self.labels.get(event.value_tag)
            if label is not None:
                self.page.gui_task.jump(label)
                self.page.gui_task.tick_in_context()
                return
        super().on_message(event)


class StoryPage(Page):
    tag = 0
    story_file = None
    inputs = None
    story = None
    def __init__(self) -> None:
        self.gui_state = 'repaint'
        self.story_scheduler = None
        self.layouts = []
        self.tag = 100
        self.rebuild_tag = 200
        self.is_processing_rebuild = False
        section = Layout(None, None, 0,0, 100, 90)
        section.tag = self.get_tag()
        self.pending_layouts = self.pending_layouts = []
        self.pending_row = self.pending_row = Row()
        self.pending_row.tag = self.get_tag()
        self.pending_tag_map = {}
        self.tag_map = {}
        # alias -> the layout item that claimed it, for THIS build only. Used solely
        # to notice two widgets asking for the same `tag:` name; the aliases
        # themselves live in tag_map beside the real tags.
        self.pending_alias_owner = {}
        self.pending_gui = True
        # Active gui_grid() contexts (a stack, so grids can nest). Each entry is
        # {"columns": N, "count": M}; add_content auto-breaks to a new row every N.
        self._grid_stack = []

        #self.aspect_ratio = sbs.vec2(1024,768)
        self.client_id = None
        self.sbs = None
        self.ctx = None
        self.console = ""
        self.widgets = ""
        self.pending_console = ""
        self.pending_widgets = ""
        # self.pending_on_change_items= []
        # self.on_change_items= []
        self.pending_on_click = []
        self.on_click = []
        self.gui_task = None
        # Optional overrides used by web-page sessions (Gui.web_page_open):
        # when set, start_story starts the GUI task at this label with these
        # variables instead of the default main/main_client label.
        self.start_label = None
        self.start_data = None
        self.web_path = None
        self.change_console_label = None
        self.main_screen_change_label = None
        self.disconnected = False
        self.gui_promise = None
        self.info_panel = None
        self.pending_info_panel = None
        # Overlay slots (drawn on top of the page, independent of the layout tree).
        # Lazily imported to avoid a circular import with procedural.gui.
        from ..procedural.gui.overlay import OverlayManager
        self.overlays = OverlayManager(self)

        
        self.errors = []
        self.compiler_errors = []

        cls = self.__class__
        
        if cls.story is None:
            if cls.story is  None:
                cls.story = MastStory()
                if cls.__dict__.get("story_file"):
                    # import time
                    # t = time.perf_counter()
                    self.errors =  cls.story.from_file(cls.story_file, None)
                    # elapsed_time = time.perf_counter() - t

                    self.compiler_errors = self.errors
                    cls.story.compiler_errors = self.errors
                    #if len(self.errors)>0:
                    #    cls.story = None
        
                    
        self.story = cls.story
        self.compiler_errors = self.story.compiler_errors
        self.main = cls.__dict__.get("main", "main")
        self.main_server = cls.__dict__.get("main_server", self.main)
        self.main_client = cls.__dict__.get("main_client", self.main)
        

    def start_story(self, client_id):
        if self.story_scheduler is not None:
            return
        cls = self.__class__
        self.client_id = client_id
        if len(self.compiler_errors)==0:
            self.story_scheduler = StoryScheduler(self.story)
            #
            # Get a label from the story class or us main
            # main should at least be an empty label
            label = self.__dict__.get("main", "main")
            # Look for server specific main
            if client_id == 0:
                label = self.__dict__.get("main_server", label)
            # Look for client specific main
            if client_id != 0:
                label = self.__dict__.get("main_client", label)

            # Web-page sessions start at a specific //web/<path> route label
            if self.start_label is not None:
                label = self.start_label

            self.story_scheduler.page = self
            #
            # signals need this to be set
            #
            FrameContext.mast = self.story
            #self.story_scheduler.set_inventory_value('sim', ctx.sim)
            self.story_scheduler.set_inventory_value('client_id', client_id)
            self.story_scheduler.set_inventory_value('IS_SERVER', client_id==0)
            self.story_scheduler.set_inventory_value('IS_CLIENT', client_id!=0)
            # self.set_inventory_value('STORY_PAGE', page)

            # Start task defer so we can set gui_task appropriately
            self.gui_task = self.story_scheduler.run(client_id, self, label, cls.inputs, None, True)
            self.gui_task.is_gui_task = True
            # Seed web-page query/data variables before the first tick
            if self.start_data:
                for k in self.start_data:
                    self.gui_task.set_variable(k, self.start_data[k])
            set_inventory_value(self.client_id, "GUI_TASK", self.gui_task)
            set_inventory_value(self.client_id, "GUI_PAGE", self)

            # Use a Fake event so the client_id and client page are correct
            e_restore = FrameContext.context.event
            e = FakeEvent(client_id, "__STORY_PAGE_INIT")
            FrameContext.context.event = e
            self.gui_task.tick_in_context()
            FrameContext.context.event = e_restore


    @property
    def task(self):
        return self.gui_task


    def tick_gui_task(self):
        #
        # Called by gui right before present
        #
        if self.story_scheduler:
            self.story_scheduler.story_tick_tasks(self.client_id)

    def swap_gui_promise(self, pending):
        if self.gui_promise is not None:
            self.gui_promise.cancel()
        self.gui_promise = pending

    def on_end_presenting(self):
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.on_end_presenting(self.client_id)

    def on_begin_presenting(self):
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.on_begin_presenting(self.client_id)


    @staticmethod
    def _retire_dropped_engine_widgets(prev, current, client_id, my_sbs):
        """Push offscreen any engine widget this console no longer declares -
        but ONLY the ones we know how to put back.

        An engine widget cannot be un-declared. The console's widget list is what
        the engine draws from, and it keeps what it was given, so sending a
        SHORTER list does not retire the ones that fell off - they carry on
        rendering at whatever rect they last had, against whatever object the
        console was last pointed at. When that object has been deleted, the
        engine walks freed memory: that is how a client died in
        ViewGridObjectListDraw two minutes after the mission ended, still drawing
        the Engineering grid list for a ship that no longer existed.

        Pushing the rect offscreen is the one thing that does work on a widget
        already shown - the same trick gui_widget_offscreen documents, applied
        automatically here so every console inherits it rather than each screen
        having to remember. Only runs when the list actually changes, which is
        rare (a console switch, or a jump to the results screen).

        WE CAN ONLY TAKE AWAY WHAT WE CAN GIVE BACK. Parking is permanent -
        re-declaring a widget in the list does not restore the rect it was pushed
        to - so a widget that comes back has to be sent a rect, and the only rect
        we can honestly send is one a script placed it at (``Gui.widget_rects``).
        A widget the ENGINE laid out has no such record, and guessing one wrecks
        the console: this used to un-park everything to the FULL CONSOLE, so
        clicking the Upgrades tab on Weapons and clicking back left all six
        engine-laid controls stacked over the whole screen. Helm and Weapons are
        the only LegendaryMissions consoles that leave anything to the engine,
        which is exactly where it was reported.

        So a widget with no placement record is left entirely alone - never
        parked, and therefore never stuck offscreen either. That is also what
        keeps the main screen's 3dview working: nothing places it, so the
        Tactical toggle can neither park nor lose it.
        """
        def names(pair):
            return {w for w in ((pair or ("", ""))[1] or "").split("^") if w}

        current_names = names(current)
        parked = Gui.widget_parked.setdefault(client_id, set())

        # PUT BACK ANYTHING WE PARKED THAT IS DECLARED AGAIN, where it was.
        #
        # A main screen toggles 3dview <-> 2dview every time the viewer goes
        # Tactical and back; a console switch drops the whole list and brings it
        # back. Without this a widget that returns stays offscreen - "it gets
        # stuck on tactical" - the same failure gui_widget_offscreen is documented
        # for, arrived at automatically.
        #
        # A widget whose record has since been dropped (its owner hid it - the
        # info panel puts ship_data away when the crew picks another tab) is
        # un-parked from our books but NOT moved: it is where its owner wants it.
        # A screen that wants somewhere else calls gui_layout_widget, whose
        # ConsoleWidget presents AFTER this and therefore wins.
        returning = parked & current_names
        for widget in returning:
            rect = Gui.widget_rect_of(client_id, widget)
            if rect is None:
                continue
            # Both rects, exactly as they were sent.
            my_sbs.send_client_widget_rects(client_id, widget, *rect)
        parked -= returning

        if not prev:
            return
        dropped = names(prev) - current_names
        if not dropped:
            return
        off = 100
        for widget in dropped:
            if Gui.widget_rect_of(client_id, widget) is None:
                # Engine-placed, or put away by its owner. Either way we have
                # nowhere to put it back, so we do not take it away.
                continue
            my_sbs.send_client_widget_rects(client_id, widget,
                                            off, off, off + 10, off + 10,
                                            off, off, off + 10, off + 10)
            parked.add(widget)

    @staticmethod
    def _forget_parked_widgets(client_id=None):
        """Drop the parking record - a client going away, a mission reset, a test."""
        if client_id is None:
            Gui.widget_parked.clear()
            Gui.widget_rects.clear()
        else:
            Gui.widget_parked.pop(client_id, None)
            Gui.widget_rects.pop(client_id, None)

    def _log_page_death(self, client_id):
        """Name the console and the last thing its GUI task was standing on.

        Called only from the non-dev branch that pops a page whose tasks have all
        finished. The screen going dark is the symptom a scripter reports; this
        is the one line that says which console and which label, so the report
        arrives with something to look at.
        """
        try:
            from ..procedural.gui.message import _handler_site
            task = self.gui_task
            where = "unknown"
            if task is not None:
                ticker = getattr(task, "active_ticker", None)
                site = _handler_site(task, task.active_label,
                                     getattr(ticker, "active_cmd", 0))
                where = f"{site[0]} line {site[1]}" if site[0] else f"label {site[1]}"
            logging.getLogger("mast.runtime").warning(
                f"console {self.console or '?'} (client {client_id}) has no tasks "
                f"left, so its page is being closed and the screen will go blank. "
                f"Last at {where}. A GUI task must park (`await gui()`) rather than "
                f"end - see handler-lifetime.md."
            )
        except Exception:
            # Diagnostics must never be the thing that takes a console down.
            pass

    def swap_layout(self):
        # self.on_change_items= self.pending_on_change_items
        # self.pending_on_change_items = []
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.on_end_presenting(self.client_id)


        self.gui_task.swap_on_change()
        self.gui_task.swap_inline_signals()
        self.on_click = self.pending_on_click
        self.pending_on_click = []
        #
        # Everything the OUTGOING build queued for an in-place redraw dies with
        # it. The incoming build is presented in full a moment from now, so the
        # queue can hold nothing but orphans -- and an orphan re-presents itself
        # at its OLD coordinates, over whatever replaced it. That is how the
        # console's log strip landed on the end-of-game results screen: the last
        # message of the game marked it dirty, the results screen replaced the
        # console in the same frame, and the post-present dirty pass drew the
        # strip on top of it.
        #
        from ..pages.layout.dirty import Dirty
        Dirty.clear_client(self.client_id)
        self.layouts = self.pending_layouts
        self.tag_map = self.pending_tag_map
        self.console = self.pending_console
        self.info_panel = self.pending_info_panel
        # This forces them is a certain order
        self.add_console_widget("")
        self.widgets = self.pending_widgets

        # TODO: this should be one thing
        # convert console tabs to procedural
        self.gui_queue_console_tabs()
        
        
        
        self.advance_tag_generation()
        
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.calc(self.client_id)
                layout_obj.on_begin_presenting(self.client_id)
            
            section = Layout(None, None, 0,0, 100, 90)
            section.tag = self.get_tag()
            self.pending_layouts = [section]
            self.pending_row = Row()
            self.pending_row.tag = self.get_tag()
            self.pending_tag_map = {}
            self.pending_alias_owner = {}
            self.pending_console = ""
            self.pending_widgets = ""
            self.pending_info_panel = None
            self.pending_gui = True
        
        self.gui_state = 'repaint'
        Gui.dirty(self.client_id)

    def on_new_gui(self):
        # print("NEW GUI")
        self.pending_gui = False
        from ..procedural.gui.property_listbox import gui_reset_variables
        gui_reset_variables(self.gui_task)
        # Restore the options button to what the MISSION asked for, not to a
        # hardcoded 0. This fires on every new GUI (from add_tag, on the first
        # tagged widget of a build), so a hardcoded restore made it impossible
        # for a story page to hold the button transparent -- the setting was
        # always taken away a moment after it was made. Defaults to 0, so a
        # mission that never calls gui_options_button() is unaffected.
        from ..procedural.gui.options_button import gui_options_button_flag
        FrameContext.context.sbs.transparent_options_button(
            self.client_id, gui_options_button_flag(self.client_id))
        # Whoever is running right now is the task PAINTING this build. It is
        # not a leftover of the build being replaced, and ending it here kills
        # it mid-paint: a re-hosted handler that repaints (press a button ->
        # draw the next screen) used to end itself on its own first tagged
        # widget, so it never reached its `await gui()` at all. This loop
        # cannot otherwise tell "the GUI that owned me is being replaced" from
        # "I am the one replacing it". See LM #714.
        building = FrameContext.task
        for sub_task in list(self.gui_task.sub_tasks):
            # A revived handler task (revive_for_handler) is parented here only
            # so it can be TICKED. It belongs to the GUI that owned the widget,
            # so it dies with that GUI -- an attribute, not a role, because any
            # role beyond __mast_task__ makes is_data_record() true and turns
            # dispose() into a no-op.
            if sub_task is building:
                continue
            if sub_task.has_role("end_on_new_gui") or getattr(
                    sub_task, "_revived_handler", False):
                sub_task.end()
        #
        # Clear tags
        #
        # Need to purge any "on signal" commands
        #
        # Only the handlers the PREVIOUS build registered. This fires on the first
        # tagged widget, which is partway through the new build -- so an
        # `on signal` written above that widget was already registered, and the
        # old wholesale purge took it out along with the ones it was aimed at
        # (LM #589). The new build's registrations are held in
        # pending_inline_signals until swap_layout promotes them.
        if MastAsyncTask.buffer_inline_signals:
            self.gui_task.purge_inline_signals()
        else:
            self.story.signal_unregister_all_inline(self.gui_task)



    def advance_tag_generation(self):
        """Move the widget-tag counters on to the next GUI build.

        The +2000 gap is what keeps a new build's tags clear of the build still
        on screen; only the previous build is ever live, so the numbers may
        safely wrap once they get large.

        The modulo used to be written `self.rebuild_tag + 100 % 100000`, which
        Python binds as `+ (100 % 100000)` == `+ 100` -- so the wrap never
        happened and the tags grew without bound. Measured against the engine, a
        GUI redrawn ten times was already handing it tags near 20,000.
        """
        self.tag = (self.rebuild_tag + 100) % 100000
        self.rebuild_tag = self.tag + 2000

    def get_tag(self):
        if self.is_processing_rebuild:
            self.rebuild_tag += 1
            return str(self.rebuild_tag)

        self.tag += 1
        return str(self.tag)

    def add_row(self):
        if not self.pending_layouts:
            self.pending_layouts = [Layout(self.get_tag(), None, 0,0, 100, 90)]
        if self.pending_row:
            if len(self.pending_row.columns):
                self.pending_layouts[-1].add(self.pending_row)
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
            self.pending_gui = True
        self.pending_row = Row()
        # Rows have tags for background and/or clickable
        self.pending_row.tag = self.get_tag()

    def add_tag(self, layout_item, runtime_node):
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
            self.pending_gui = True

        if self.pending_gui == True:
            # Registration is NOT free: the first add_tag of a build tears down
            # the previous build's inline `on signal` blocks. Nothing below may
            # move above this. (LM #589)
            self.on_new_gui()


        if hasattr(layout_item, 'tag'):
            tag = layout_item.tag
            if tag is None:
                # A gui_sub_section() has no tag until `with` enters it, so a
                # handler registered on the wrapper first would land under the
                # key None and be unreachable. Say so rather than pretending.
                if runtime_node is not None:
                    log("a gui_message handler was attached to a sub-section "
                        "before its `with` block, so it has no tag yet and "
                        "nothing can reach it. Register it inside the `with`.",
                        "gui", "warning")
            else:
                # compose, not assign: a widget can carry several handlers now,
                # so attaching a second one must not discard the first. (#614)
                self.pending_tag_map[tag] = compose_handler(
                    self.pending_tag_map.get(tag), layout_item, runtime_node)
        if hasattr(layout_item, 'click_tag'):
            if layout_item.click_tag is not None:
                click_tag = layout_item.click_tag
                self.pending_tag_map[click_tag] = compose_handler(
                    self.pending_tag_map.get(click_tag), layout_item, runtime_node)
        self.add_alias(layout_item, runtime_node)

    def add_alias(self, layout_item, runtime_node=None):
        """Register an author's `tag:` name so gui_update() can resolve it.

        An extra key in the SAME tag_map, exactly as click_tag has always earned a
        second entry -- so every consumer that resolves by tag_map (gui_update,
        message routing, the log panel's liveness check) picks it up with no further
        change. The engine keeps the library-managed tag (LM #349).

        Called from add_tag for widgets, and directly from gui_row/gui_section, which
        never reach add_tag -- which is why a named ROW was unreachable before.
        """
        alias = getattr(layout_item, "alias", None)
        if not alias:
            return
        prev = self.pending_alias_owner.get(alias)
        if prev is not None and prev is not layout_item:
            # A row template that names every row the same thing: only the last one
            # built is reachable. Say so rather than letting three of four rows
            # silently ignore an update.
            from ..procedural.execution import log
            log(f"tag '{alias}' was claimed by more than one widget in this layout. "
                f"Only the last one can be reached by gui_update -- make the name "
                f"unique, e.g. \"tag:{alias}-{{item}}\".", "gui", "warning")
        self.pending_alias_owner[alias] = layout_item
        self.pending_tag_map[alias] = compose_handler(
            self.pending_tag_map.get(alias), layout_item, runtime_node)

    def push_sub_section(self, style, layout_item, is_rebuild):
        #
        # If there is even an empty row, we need to cache it away for later
        #
        if is_rebuild:
            self.is_processing_rebuild = True

        if self.pending_row:
            if len(self.pending_layouts) != 0:
                self.pending_layouts[-1].add(self.pending_row)
            else:
                print("Lost main layout?")
            self.pending_row = None
        
        if layout_item is None:
            self.add_section()
            layout_item = self.get_pending_layout() 
            apply_control_styles(".section", style, layout_item, self.gui_task)
            self.add_row()
        else:
            self.pending_layouts.append(layout_item)
            rows = layout_item.rows
            if len(rows)>0:
                p_row = rows.pop()
                self.pending_row = p_row

        return layout_item
        

    def pop_sub_section(self, add_content, is_rebuild):
        if is_rebuild:
            self.is_processing_rebuild = False
            self.tag_map.update(self.pending_tag_map)
            self.pending_tag_map = {}
            self.pending_alias_owner = {}
            
            self.on_click.extend(self.pending_on_click)
            self.pending_on_click = []
        # Finish the layout for the sub section
        if self.pending_row:
            if len(self.pending_row.columns):
                self.pending_layouts[-1].add(self.pending_row)

        sub = self.pending_layouts.pop()
        p_row = None
        if len(self.pending_layouts)>0:
            rows = self.pending_layouts[-1].rows
            if len(rows)>0:
                p_row = rows.pop()
                if add_content:
                    p_row.add(sub)
                self.pending_row = p_row
                if add_content:
                    # A sub-section is added to its parent row HERE rather than
                    # through add_content, so this is the only place a grid can see
                    # one - and a grid of sub-sections is the common case
                    # (`with gui_grid(4): ... gui_sub_section()` per cell).
                    self._grid_note_cell()
                return
        # If get here started pretty much empty
        if add_content:
            self.add_content(sub, None)


    def add_content(self, layout_item, runtime_node):
        if self.pending_layouts is None:
            self.add_row()
        if self.pending_row is None:
            self.add_row()
        self.add_tag(layout_item, runtime_node)

        self.pending_row.add(layout_item)

        # gui_grid() auto-flow: after every N CELLS, break to a fresh row so items
        # lay out as an N-column grid. Inert unless a grid is active.
        self._grid_note_cell()

    def _grid_style_row(self):
        """Apply the grid's row style to the row it just started. A grid creates its
        own rows, so this is the only way an author can size them - and a row that
        declares nothing is 1fr, which stretches a short grid over the whole section.
        """
        if not self._grid_stack:
            return
        style = self._grid_stack[-1].get("row_style")
        if style and self.pending_row is not None:
            apply_control_styles(".row", style, self.pending_row, self.gui_task)

    def _grid_note_cell(self):
        """Count one grid cell, and break the row after every N.

        Only at the grid's OWN depth: anything a cell builds inside itself belongs to
        that cell, not to the grid.
        """
        if not self._grid_stack:
            return
        grid = self._grid_stack[-1]
        if grid.get("depth") != len(self.pending_layouts):
            return
        grid["count"] += 1
        if grid["count"] % grid["columns"] == 0:
            self.add_row()
            self._grid_style_row()

    def grid_begin(self, columns, row_style=None):
        """Enter a gui_grid() context: subsequent add_content()s flow into an
        ``columns``-wide grid, auto-breaking rows. Nestable."""
        columns = max(1, int(columns))
        self.add_row()                       # start the grid on a clean row
        # `depth` is what makes a CELL a cell. The counter used to run on every
        # add_content while a grid was open, including widgets nested inside a cell -
        # so a grid of sub-sections counted their CONTENTS and broke rows in the
        # middle of them. A tile of icon+title+description in a 4-column grid put its
        # second tile's icon on cell 4 and got a row break between the icon and its
        # own title, which read as "that one icon paints differently".
        self._grid_stack.append({"columns": columns, "count": 0,
                                 "depth": len(self.pending_layouts),
                                 "row_style": row_style})
        self._grid_style_row()

    def grid_end(self):
        """Leave the current gui_grid() context, padding the final row with Hole
        spacers so its columns stay aligned, then start a fresh row."""
        if not self._grid_stack:
            return
        grid = self._grid_stack.pop()
        row = self.pending_row
        if row is not None and 0 < len(row.columns) < grid["columns"]:
            from ..pages.layout.hole import Hole
            while len(row.columns) < grid["columns"]:
                row.add(Hole())
        self.add_row()                       # content after the grid isn't in it

    # def add_on_change(self, runtime_node):
    #     self.pending_on_change_items.append(runtime_node)

    def add_on_click(self, runtime_node):
        self.pending_on_click.append(runtime_node)


    def set_widget_list(self, console,widgets):
        self.pending_console = console
        self.pending_widgets = widgets

    def activate_console(self, console):
        self.pending_console = console

    def add_console_widget(self, widget):
        if  self.pending_widgets=="":
            self.pending_widgets = widget
        elif widget=="":
            pass
        else:
            self.pending_widgets += "^"+widget
        widgets = set(self.pending_widgets.split("^"))
        new_widgets = ""
        widgets_2d = ""
        widgets_3d = ""
        delim = ""
        for widget in set(widgets):
            if widget == "3dview":
                widgets_3d = widget+"^"
            elif widget in ["2dview","weapon_2d_view", "science_2d_view"]:
                widgets_2d = widget + delim + widgets_2d
                delim = "^"
            else:
                new_widgets = new_widgets + delim + widget
                delim = "^"
        self.pending_widgets = widgets_3d+ widgets_2d+new_widgets
    
    def add_section(self, tag= None):
        if tag is None:
            tag = self.get_tag()

        section = Layout(tag, None, 0,0, 100, 90)
        
        if not self.pending_layouts:
            self.pending_layouts = [section]
        else:
            self.add_row()
            self.pending_layouts.append(section)

    def get_pending_layout(self):
        if not self.pending_layouts:
            self.add_row()
        return self.pending_layouts[-1]

    def get_pending_row(self):
        if not self.pending_layouts:
            self.add_row()
        return self.pending_row

    def get_path(self):
        # The pending console is the one the gui is going to present
        return f"gui/{self.pending_console}"

    def set_button_layout(self, layout, gui_promise):
        if self.pending_row and self.pending_layouts:
            if self.pending_row:
                self.pending_layouts[-1].add(self.pending_row)
        
        if not self.pending_layouts:
            self.add_section()
        
        if layout:
            self.pending_layouts.append(layout)
        
        self.swap_layout()

    def _epadd_belongs_here(self, console, enabled_tabs):
        """Whether THIS build is a console screen the PADD belongs on.

        The PADD's shell route existing says the MISSION has one, not that this
        particular screen is a console. Without this test the button replaced the strip
        on every build that queued one - so it turned up on the start screen, on console
        select and on the game-results screen, and on the main screen, which is what the
        playtest reported (2026-09-01).

        Three signals, and none works alone:

        * **Being in the PADD** ends the question. An app screen declares no console and,
          since apps stopped calling `gui_tab_back`, no tabs either - so without this the
          status region would vanish the moment you opened an app, which is the one place
          it is most wanted.
        * `self.console` is PER BUILD - `pending_console` is reset after every swap - so
          it means "this screen activated a console", not "this client was ever on one".
          `gui_console()` sets it; console select, the results screen and the start
          screen never call it. But a MORPHED console does not call it either.
        * `enabled_tabs` is also per build, because drawing CONSUMES it. A morphed
          console declares its back tab and so has one; the three screens above declare
          nothing.

        CONSOLE_TYPE is deliberately not the test. It is sticky - nothing clears it when
        a client leaves a console - so the results screen still reports whatever station
        the player last sat at, and console select sets it outright.
        """
        from ..procedural.gui.console_tab import gui_app_get_active
        if _is_main_screen(self.client_id, console):
            return False          # the whole room's view, not one person's station
        return bool(gui_app_get_active(self.client_id)) or bool(self.console) or bool(enabled_tabs)

    def gui_queue_console_tabs(self):
        from ..procedural.gui.epadd import (epadd_console_name, SHELL_APP,
                                            CLICK_HIGHLIGHT)
        from ..procedural.gui.console_tab import gui_app_get_active
        from .story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
        # The normal_engi -> engineering table used to be computed here and then never
        # used. It lives in epadd.py now because app scoping needs it too, and there
        # must be exactly one of it.
        # WHO this console is, for app scoping and the badge - not WHETHER the PADD
        # belongs on this screen, which is `_epadd_belongs_here` below.
        console = epadd_console_name(_console_identity(self.client_id, self.console))
        # Cleared every build. A tab button subclasses Text, so "the badge" cannot be
        # found by walking the layouts for text - the page holds it directly.
        self.identity_badge = None
        #
        # tabs can be for all ships or single
        #
        enabled_tabs = get_inventory_value(self.client_id, "console_tabs", {})

        back_tab = get_inventory_value(self.client_id, "__back_tab__")

        # DECIDED FIRST, because the tab row's left edge depends on it: the PADD owns
        # the strip's left two slots as a region of its own, so the row of tabs starts
        # where that region ends.
        #
        # It falls back to the classic strip when the mission has no //gui/tab/epadd
        # route: turning the mode on without the route would otherwise leave the console
        # with a single button that does nothing.
        # NO MODE FLAG. The PADD draws wherever its shell route exists and the screen
        # is a console. It used to be gated on `gui_app_mode_is_on` as well, and that
        # went with the app/tab split: apps are `//gui/app` routes now, so suppressing
        # the PADD does not fall back to the classic strip - it leaves every app with no
        # way in. The route existing IS the mission's opt-in.
        epadd_label = GuiAppDecoratorLabel.all.get(SHELL_APP)
        show_epadd = (epadd_label is not None
                      and self._epadd_belongs_here(console, enabled_tabs))
        #
        # Ok we're on a ship, on a console
        #
        _left = (_identity_right(self.client_id) if show_epadd
                 else _strip_left(self.client_id))
        _left_px = (STRIP_LEFT_PX + IDENTITY_WIDTH_PX) if show_epadd else STRIP_LEFT_PX
        _layout = Layout(self.get_tag(), None, _left, 0, 100,
                         _strip_bottom(self.client_id))
        # The constructor bounds are the first frame's answer; the STYLE is what every
        # later calc uses, which is what makes this survive a resize.
        apply_control_styles(".section", _strip_area(_left_px), _layout, self.gui_task)
        _row = Row()
        #
        # MAKE the tab button 40px
        #
        apply_control_styles(".row", "row-height:35px", _row, self.gui_task)
        _layout.add(_row)

        # Collect FIRST, emit second. The strip has to know how many tabs there are before
        # it can decide which of them fit, and the old loop added each one as it went.
        entries = []          # (text, label) in registration order
        back_entry = None
        tabs = set()
        for tab in GuiTabDecoratorLabel.all:
            # Only use enabled tabs
            if not enabled_tabs.get(tab):
                continue
            tab_label = GuiTabDecoratorLabel.all[tab]
            # The back tab is still exempt from its own route's `if`: a tab's condition
            # answers "may this be picked from here", and the back tab answers "where
            # did you come from" - you demonstrably came from there.
            if tab != back_tab and isinstance(tab_label, GuiTabDecoratorLabel):
                if not tab_label.test(self.gui_task):
                    continue

            tab_text = tab
            if tab == back_tab:
                tab_text = back_tab
            if tab_text in tabs:
                continue
            tabs.add(tab_text)
            if tab_text == back_tab:
                back_entry = (tab_text, tab_label)
            else:
                entries.append((tab_text, tab_label))

        # A BACK TAB WITH NO ROUTE AT ALL is a mission bug, not a library one - there
        # is nothing to jump to - but it used to be a SILENT one, and the symptom is a
        # console you cannot leave. `//gui/tab/<console>` exists for the six standard
        # consoles; a mission's own console (the director, a custom station) has to
        # declare one too. Said once per page, so it names the gap without filling the
        # log every build.
        if back_tab and back_entry is None:
            warned = getattr(self, "_back_tab_warned", None)
            if warned is None:
                warned = self._back_tab_warned = set()
            if back_tab not in warned:
                warned.add(back_tab)
                log(f"no //gui/tab/{back_tab} or //gui/app/{back_tab} route - the Back "
                    f"button cannot be drawn, so this screen has no way back to it",
                    "gui", "warning")

        # NOTHING ABOUT THE PADD HERE. It declares its own back tab like any other
        # screen (`gui_tab_back(CONSOLE_SELECT)`), so the strip draws one the way it
        # always has. Synthesising one from the active tab is what kept breaking the
        # bar's own back button - the PADD sits ON TOP of the console, it does not
        # modify it.

        def _button(text, label, is_back):
            msg = f"justify:center;color:black;$text:{text};"
            button = TabControl(self.get_tag(), msg, label, self)
            button.click_text = text
            button.click_color = "#FFF"
            button.click_background = CLICK_HIGHLIGHT
            # A STABLE CLICK TAG, keyed by the tab's NAME. `get_tag()` is a build-order
            # ordinal that moves ~2100 every rebuild, so a fresh one per build asked the
            # engine for a NEW click region each time and left the previous one live -
            # and a press could then be answered by a region belonging to a build that
            # is gone. Measured in a real session: Back presses arriving as `9483` and
            # `70583` while the current build was at `15784` and `76884`, roughly three
            # builds stale, each doing nothing. That is the reported "Back takes several
            # presses": the ones that did nothing were answered by dead regions.
            #
            # The name is stable across builds and unique within one - a tab appears in
            # the strip once - which is exactly what a click tag needs to be. Prefixed so
            # it cannot collide with a generated ordinal.
            button.click_tag = f"console-tab:{text}"
            button.background_color = "#999" if is_back else "#333"
            return button

        # More than fits? Keep the first few and put the rest behind one menu. The BACK
        # tab is never overflowed - it is how you leave, so it stays where it always is.
        visible, overflow = entries, []
        reserved = (1 if back_entry else 0) + 1        # back tab + the menu itself
        if len(entries) + (1 if back_entry else 0) > TAB_MAX_VISIBLE:
            keep = max(1, TAB_MAX_VISIBLE - reserved)
            visible, overflow = entries[:keep], entries[keep:]

        for text, label in visible:
            _row.add_front(_button(text, label, False))
        if overflow:
            names = ", ".join(t for t, _ in overflow)
            menu = TabOverflow(self.get_tag(),
                               f"text: More ({len(overflow)}); list: {names}",
                               {t: l for t, l in overflow}, self)
            _row.add_front(menu)
        if back_entry:
            _row.add(_button(back_entry[0], back_entry[1], True))

        count = len(visible) + (1 if back_entry else 0) + (1 if overflow else 0)
        # Pad to six so a console with only a few tabs keeps them the size they have
        # always been rather than stretching each across the whole strip.
        spots = 6
        if show_epadd:
            # FIVE, because the PADD holds the other two - and it holds them as its own
            # region beside this row rather than as columns of it, so that the glyph and
            # the name are ONE click target instead of two that do the same thing.
            spots = STRIP_SLOTS - IDENTITY_SLOTS
        blanks = spots-count
        if blanks <0: blanks = 0
        for _ in range(blanks):
            _row.add_front(Blank())
        if show_epadd:
            self._queue_identity_region(console, epadd_label)

        #_layout.calc()
        self.pending_layouts.append(_layout)

        # Clear up tabs for the next GUI
        set_inventory_value(self.client_id, "console_tabs", {})
        set_inventory_value(self.client_id, "__back_tab__", None)




    #: How often the badge re-reads what is waiting. It is a THROTTLE, not a
    #: guarantee: reading it walks every app and calls each status provider, and
    #: `gui_app_revision` is no cheaper because it calls exactly the same ones. At the
    #: engine's tick rate this is a few times a second, which is far faster than a
    #: crew member can notice and a fraction of the per-frame cost.
    IDENTITY_REFRESH_TICKS = 8

    def _tick_identity_badge(self):
        """Keep the badge current while the console sits in `await gui()`.

        A SIGNAL DOES NOT WAKE `await gui()`, and a console parked on Helm all game
        never rebuilds - so without this the count is frozen at whatever it said when
        the screen was built, which is precisely the case the badge exists for.

        Updates the widget rather than the page: the dirty system re-renders a changed
        widget on its own, so nothing here repaints a screen.
        """
        label = getattr(self, "identity_label", None)
        if label is None:
            return
        try:
            ctx = FrameContext.context
            tick = int(getattr(ctx.sim, "time_tick_counter", 0) or 0)
        except Exception:
            return
        if tick - getattr(self, "_identity_tick", -999) < self.IDENTITY_REFRESH_TICKS:
            return
        self._identity_tick = tick
        from ..procedural.gui.epadd import (epadd_console_name, gui_app_identity_text,
                                            ACCENT)
        # The same identity read the build used - the door's record when the build
        # declared no console of its own, so a morphed console is not answered as "".
        console = epadd_console_name(_console_identity(self.client_id, self.console))
        if _is_main_screen(self.client_id, console):
            return
        try:
            text = gui_app_identity_text(client_id=self.client_id, console=console)
        except Exception:
            return                       # never let a badge take the console down
        if not text or text == getattr(self, "identity_text", None):
            return
        self.identity_text = text
        # THE LABEL GETS NO CLICK TEXT. Setting it gave the label its own click region on
        # top of the region the badge already had - a second hit target with different
        # bounds, painting the name over the strip on every press. The badge's Layout is
        # the one control here.
        label.update(_identity_style(text, ACCENT))

    def _queue_identity_region(self, console, epadd_label):
        """The PADD: the strip's left two slots, as ONE click target.

        It used to be a band of its own with an absolute pixel rect UNDER the strip,
        which put it over the ship-data panel and collided with its readouts (playtest,
        2026-09-01). It belongs on the strip, where every other control on that bar is.

        A REGION, NOT TWO COLUMNS. Built as its own `Layout` rather than as two columns
        of the tab row, because a Row gives each column its own click region - so a
        glyph and a name sitting side by side were two hit targets that did the same
        thing, and pressing either highlighted only its own half. One Layout emits one
        region over its whole bounds, which is what makes the status read as a single
        control.

        NO WORD FOR IT. The glyph is the engine's own `phone`, from the same
        grid-icon-sheet the engineering grid draws from, so the label is free to say who
        is sitting there instead of naming the button.
        """
        from ..procedural.gui.epadd import (gui_app_identity_text, ACCENT, PANEL,
                                            CLICK_HIGHLIGHT)
        text = gui_app_identity_text(client_id=self.client_id, console=console)

        # THE SAME BOTTOM AS THE TAB STRIP. Its rect is what the engine turns into the
        # click region, so a rect shorter than the row leaves the bottom of the badge
        # unclickable and the press highlight stopping mid-control (playtest image,
        # 2026-09-02).
        layout = Layout(self.get_tag(), None,
                        _strip_left(self.client_id), 0,
                        _identity_right(self.client_id),
                        _strip_bottom(self.client_id))
        apply_control_styles(".section",
                             _strip_area(STRIP_LEFT_PX,
                                         f"{STRIP_LEFT_PX + IDENTITY_WIDTH_PX}px"),
                             layout, self.gui_task)
        # NO CLICK TEXT ANYWHERE ON THIS CONTROL. A press must tint the region and
        # nothing else: the engine draws click text at its own size over the region's
        # whole rect, so the crew name came back oversized and centred, spilling up over
        # the topbar and reading as a second copy of the label. The region comes from the
        # TAG alone - see `Layout._post_present`.
        layout.click_background = CLICK_HIGHLIGHT
        # A STABLE TAG - see IDENTITY_CLICK_TAG. Set before `_open` closes over it.
        layout.click_tag = IDENTITY_CLICK_TAG

        # THE CALLBACK MUST CHECK THE TAG ITSELF. `Layout.on_message` calls
        # `on_message_cb` for EVERY event handed to it during the page's walk of the
        # layout tree, not only ones aimed at it - unlike `Column.on_message`, which
        # returns early on a tag miss. `StoryPage.on_message` walks every layout for
        # every event, and this region is in that list on every build.
        #
        # Unfiltered, it re-entered the PADD shell on somebody else's click: pressing a
        # tile ran the tile's own filtered handler AND then this one, so every click
        # produced two builds and the last one - always home - won. Reported from a real
        # engine run as "clicking an app just seems to run home again", with a Back that
        # needed several presses because each one rebuilt twice and the stale click was
        # dropped. `epadd._tile` carries the same guard and the same warning.
        def _open(event, sender, _label=epadd_label, _tag=layout.click_tag):
            if getattr(event, "sub_tag", None) != _tag:
                return
            self.gui_task.jump(_label)
            self.gui_task.tick_in_context()
        layout.on_message_cb = _open

        row = Row()
        # A ROW WITH A BACKGROUND NEEDS A TAG - `_pre_present` builds the backdrop's own
        # tag as "__bg:" + self.tag, and `Row()` starts with tag None.
        row.tag = self.get_tag()
        apply_control_styles(".row", "row-height:35px", row, self.gui_task)
        if text:
            # THE PANEL ONLY WHEN THERE IS SOMETHING IN IT. A mission using none of this
            # would otherwise get an empty box welded to every console.
            apply_control_styles(".row", f"background: {PANEL};", row, self.gui_task)

        # SIZED TO CONTENT, and the slack goes to a blank at the end. The region's rect
        # is a percentage - it has to be, to track the engine's Options button - so on a
        # bigger screen it is a wider box. A flexing label then stretched across it and
        # drifted away from the glyph; the gap grew with the display.
        props = _identity_icon_props(ACCENT)
        icon = Icon(self.get_tag(), props) if props else None
        if icon is not None:
            row.add(icon)                       # square: sized from the row, not the box
        label = Text(self.get_tag(), _identity_style(text or "", ACCENT))
        apply_control_styles(".text", "col-width: content;", label, self.gui_task)
        row.add(label)
        row.add(Blank())
        layout.add(row)
        self.pending_layouts.append(layout)

        self.identity_badge = layout
        self.identity_label = label
        self.identity_text = text
        # The build just computed it, so start the throttle here rather than letting the
        # next `present` in the SAME frame call every status provider again.
        try:
            self._identity_tick = int(
                getattr(FrameContext.context.sim, "time_tick_counter", 0) or 0)
        except Exception:
            self._identity_tick = 0

    def update_props_by_tag(self, tag, props, test):
        """Apply props to the widget registered under `tag`.

        Returns True when a widget was found and updated. A miss is not an error --
        the tag may name a listbox row that is currently scrolled out of view, and
        those are built only while visible -- but the caller can now tell, which it
        could not before.
        """
        # get item by tag
        item = self.tag_map.get(tag)
        present = True
        # call update
        if item is None:
            present = False
            item = self.pending_tag_map.get(tag)
        if item is None:
            return False

        #
        # Test allows one to pass values they need to be 
        # equal to 
        # Added for example to make sure the ship picker
        # only updates if the ship is the same
        #
        if test is not None:
            for k in test:
                expected = test.get(k)

                this = self.gui_task.get_variable(k)
                if this != expected:
                    return False

        item = item[0]
        item.update(props)
        #
        # A container that rebuilds its children from a template throws this update
        # away the next time it draws. Hand the props back to the owner so it can
        # re-apply them after the template runs (LM #349).
        #
        remember = getattr(getattr(item, "_alias_owner", None),
                           "remember_alias_props", None)
        if remember is not None:
            remember(tag, props)
        # present it
        if present:
            event = FakeEvent(self.client_id, "", "")
            item.present(event)
        return True

    
    def present(self, event):
        """ Present the gui """
        if self.client_id is None:
            self.client_id = event.client_id
        if self.gui_state == "errors":
            return
        if self.disconnected:
            return
        # SCOPED TO THIS PAGE. The ticker walks every app and calls every status
        # provider, and a provider resolves its console AMBIENTLY - `lm_epadd_reporting`
        # reaches `gui_app_list(None)`, `away_who()` reads `FrameContext.page.client_id`.
        # `present` runs before `story_tick_tasks` sets the page, so without this the
        # badge is computed against whatever page happens to be current: wrong words on
        # a multi-console bridge, and a `gui_app_revision` that MOVES when nothing has
        # changed, which repaints the PADD and eats the click that lands in that frame.
        # The same override the click path uses.
        with FrameContextOverride(self.gui_task, self):
            self._tick_identity_badge()
        #
        # Cache sbs this should not change
        # cache will be used in updates they only need sbs, ratio and client_id
        #
        my_sbs = FrameContext.context.sbs
        
        # for change in self.on_change_items:
        #     if change.test():
        #         change.run()
        #         return
        if len(self.compiler_errors) > 0:
            message = "".join(self.compiler_errors)
            message = message.replace(";", "~")
            message = "$text: Mast Compiler Errors\n" + message.replace(",", ".")
            Gui.root_clear(my_sbs, event.client_id)
            if event.client_id != 0:
                my_sbs.send_client_widget_list(event.client_id, "", "")
            my_sbs.send_gui_text(event.client_id,"", "error", message,  0,0,100,100)
            my_sbs.send_gui_button(event.client_id,"", "$Error$rerun", "$text:Attempt Rerun", 50, 90, 70, 99)
            my_sbs.send_gui_button(event.client_id,"", "$Error$startup", "$text:Run startup", 75, 90, 99, 99)
            self.gui_state = "errors"
            my_sbs.send_gui_complete(event.client_id,"")
            return
        

        if self.story_scheduler is None:
            self.start_story(event.client_id)
        else:
            if len(self.story_scheduler.errors) > 0:
                self.errors = self.story_scheduler.errors
                self.story_scheduler.errors = []
            else:
                if self.story_scheduler.paint_refresh:
                    if self.gui_state != "repaint":  
                        self.gui_state = "refresh"
                    self.story_scheduler.paint_refresh = False
                
                if not self.story_scheduler.story_tick_tasks(event.client_id):
                    #self.story_runtime_node.mast.remove_runtime_node(self)
                    if is_dev_build():
                        raise Exception("EDGE CASE: Did you set END or Yield the last GUI Task?")
                    else:
                        # The console's last task is gone, so this page is popped
                        # and the screen goes dark. In a dev build that is the
                        # exception above; in the ENGINE it used to be silent,
                        # which is how "all the controls vanished" reaches us
                        # with no error text to work from. Say where it died.
                        self._log_page_death(event.client_id)
                        Gui.pop(event.client_id)
                        return
            

        if len(self.errors) > 0:
            message = "".join(self.errors)
            message = message.replace(";", "~")
            message = "$text: Mast Compiler Errors\n" + message.replace(",", ".")
            Gui.root_clear(my_sbs, event.client_id)
            if event.client_id != 0:
                my_sbs.send_client_widget_list(event.client_id, "", "")
            my_sbs.send_gui_text(event.client_id,"", "error", message,  0,0,100,100)
            my_sbs.send_gui_button(event.client_id,"", "$Error$resume", "$text:Attempt Resume", 0, 90, 20, 99)
            my_sbs.send_gui_button(event.client_id,"", "$Error$pause", "$text:Attempt pause", 25, 90, 45, 99)
            my_sbs.send_gui_button(event.client_id,"", "$Error$rerun", "$text:Attempt Rerun", 50, 90, 70, 99)
            my_sbs.send_gui_button(event.client_id,"", "$Error$startup", "$text:Run startup", 75, 90, 99, 99)
            self.gui_state = "errors"
            my_sbs.send_gui_complete(event.client_id,"")
            return
        
        
        # An overlay slot holding content whose sub-region was revoked by a root
        # clear from outside this page's own repaint (a page pop, an error
        # screen). Only "repaint"/"refresh" run present_all, so any other state
        # would leave the card gone for the rest of its life.
        if (self.overlays.slots and self.gui_state not in ("repaint", "refresh")
                and self.overlays.needs_repaint()):
            self.gui_state = "repaint"

        match self.gui_state:

            case  "repaint":
                # Bumps the root epoch BEFORE present_all below, so the slots
                # establish into the epoch they will be checked against.
                Gui.root_clear(my_sbs, event.client_id)
                #
                # Only when it CHANGED. This call is how the ENGINE learns which
                # native widgets a console has, and acting on it means building
                # them (2d view, waterfall, ship_data, grid...). swap_layout sets
                # gui_state='repaint' on EVERY gui rebuild, so re-sending
                # unconditionally asked the engine to redo that work every time a
                # console's MAST screen rebuilt. Redundant either way; whether it
                # was also what made consoles slow to appear was NOT settled -
                # the cost may simply be having widgets up at all, which is the
                # engine's side of the line and not something we can send our
                # way out of.
                #
                # Safe to skip: send_gui_clear does NOT drop the engine's
                # widgets. The "refresh" branch below clears and re-presents
                # without ever re-sending the list, and consoles keep their
                # widgets across a resize, which is proof of it.
                #
                widget_list = (self.console, self.widgets)
                prev_widget_list = Gui.widget_list_sent.get(event.client_id)
                if prev_widget_list != widget_list:
                    Gui.widget_list_sent[event.client_id] = widget_list
                    my_sbs.send_client_widget_list(event.client_id, self.console, self.widgets)
                    self._retire_dropped_engine_widgets(
                        prev_widget_list, widget_list, event.client_id, my_sbs)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed

                for layout_obj in self.layouts:
                    layout_obj.present(event)
                # Overlays draw last (on top), re-emitted every repaint so they
                # survive the page's root clear.
                self.overlays.present_all(event)
                if len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"
                my_sbs.send_gui_complete(event.client_id,"")
            case  "refresh":
                Gui.root_clear(my_sbs, event.client_id)
                for layout_obj in self.layouts:
                    #layout_obj.calc(self.client_id)
                    layout_obj.invalidate_all()
                    layout_obj.represent(event)
                self.overlays.present_all(event)
                my_sbs.send_gui_complete(event.client_id,"")
                if len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"

    def on_message(self, event):
        if event.client_id != self.client_id:
            return

        message_tag = event.sub_tag
        if message_tag == "$Error$resume":
            self.errors = []
            FrameContext.context.sbs.resume_sim()
            self.gui_state = "paint"
            self.present(event)
            return
        
        if message_tag == "$Error$pause":
            self.errors = []
            FrameContext.context.sbs.pause_sim()
            self.gui_state = "paint"
            self.present(event)
            return
        
        if message_tag == "$Error$rerun":
            self.errors = []
            mission = get_mission_name()
            FrameContext.context.sbs.run_next_mission(mission)
            self.gui_state = "paint"
            self.present(event)
            return
        
        if message_tag == "$Error$startup":
            self.errors = []
            start_mission = get_startup_mission_name()
            if start_mission is not None:
                FrameContext.context.sbs.run_next_mission(start_mission)
            self.gui_state = "paint"
            self.present(event)
            return
            
        

        clicked = None
        # Process layout first
        with FrameContextOverride(self.gui_task, self):
            for section in self.layouts:
                section.on_message(event)

        clicked = Layout.clicked.get(self.client_id)

        runtime_node = self.tag_map.get(message_tag)

        refresh = False
        if runtime_node is not None and runtime_node[1] is not None:
            # tuple layout and runtime node
            runtime_node = runtime_node[1]
            with FrameContextOverride(self.gui_task, self):
                runtime_node.on_message(event)
          
        # for change in self.on_change_items:
        #     if change.test():
        #         change.run()
        #         return
        self.gui_task.run_on_change()
            
        if clicked is not None:
            Layout.clicked[self.client_id] = None
            # Every matching handler runs, the same rule gui_message now
            # follows (LM #614). This used to return on the first match, so a
            # catch-all gui_click() -- which matches everything -- silently
            # shadowed every handler registered after it.
            for click in list(self.on_click):
                click.click(clicked.click_tag)
            
        if refresh:
            self.gui_state = "refresh"
            self.present(event)

        

    def on_event(self, event):
        if event.client_id != self.client_id:
            return
        
        if self.story_scheduler is None:
            return
        
        if event.tag =="mast:client_disconnect":
            signal_emit("client_disconnect", {"client_id": self.client_id})
            self.disconnected = True
            self.tick_gui_task()
            # remove scheduler
            self.story_scheduler.mast.remove_scheduler(self.story_scheduler)
        elif event.tag == "client_change":
            if event.sub_tag == "change_console":
                if self.change_console_label:
                    # This is a bit of a hack to clear the properties
                    # List box
                    _ship = FrameContext.context.sbs.get_ship_of_client(self.client_id)
                    if _ship is not None and _ship != 0:
                        FrameContext.context.sbs.send_comms_selection_info(_ship, "", "white", "static")
                    # THE CLEAR. Overlays belong to the CONSOLE, and this jump does
                    # not make a new page - OverlayManager lives on the page and
                    # survives it - so without this the last screen's hero card, hail
                    # band or data column is re-drawn by present_all on whatever the
                    # console becomes, and the catch-up ticker puts it back if the
                    # mission clears it by hand.
                    #
                    # Only the overlays here, deliberately: what this console is
                    # BECOMING is not known at this point, and the rest of the
                    # transition (roles, CONSOLE_TYPE, the viewscreen claim, the crew
                    # seat) needs that name. gui_console_enter is the full door and
                    # belongs at the top of the console label, which does know.
                    from ..procedural.gui.overlay import overlay_clear_console
                    from ..procedural.gui.property_listbox import gui_reset_variables
                    with FrameContextOverride(self.gui_task, self):
                        overlay_clear_console(self.client_id)
                        gui_reset_variables(self.gui_task)
                        self.gui_task.jump(self.change_console_label)
                        self.gui_task.tick_in_context()
                        self.present(event)
        elif event.tag == "main_screen_change":
            if self.main_screen_change_label:
                # get_inventory_value(self.client_id,"assigned_ship")
                # viewscreen_home_ship, not get_ship_of_client: a console driving a
                # viewscreen shot is ASSIGNED TO THE SUBJECT, so the raw call answers
                # with the enemy being filmed and this would then look for the main
                # screens of the ENEMY's console list - which is empty, so some real
                # main screens never received the view change at all. Lazy import:
                # this module is deep in the import chain.
                from ..procedural.gui.viewscreen import viewscreen_home_ship
                _ship = viewscreen_home_ship(self.client_id)
                ms =  linked_to(_ship, "consoles") & (has_inventory_value("CONSOLE_TYPE", "mainscreen")) # | has_inventory_value("CONSOLE_TYPE", "normal_main"))
                # 3d_view, info, data - affects layout
                # front, left, right, back - engine controlled
                # 3d (chase, first_person, tracking) 2d (short, long) - engine controlled
                
                # THE SHIP, not the event fields. handlerhooks writes the crew's press
                # to the ship and THEN arbitrates it, and a story beat can refuse it and
                # put its own triple back - so the event still says what was pressed
                # while the ship says what actually won. Injecting the event's values
                # would hand a console a view the library declined to apply.
                #
                # The event cannot be re-stamped instead: it is a Pybind11 object from
                # the engine and its attributes are read-only.
                from ..procedural.gui.viewscreen import viewscreen_effective_state
                _ms = viewscreen_effective_state(_ship)
                if _ms is None:
                    _ms = (event.sub_tag, event.value_tag, event.extra_tag)
                for m in ms:
                    #t = get_inventory_value(m, "CONSOLE_TYPE", "not set")
                    #log(f"Got here {len(ms)} {t}", "mast:internal")
                    gui_reroute_client(m, self.main_screen_change_label, {
                        "MAIN_SCREEN_VIEW": _ms[0],
                        "MAIN_SCREEN_FACING": _ms[1],
                        "MAIN_SCREEN_MODE": _ms[2]
                    })

        elif event.tag == "screen_size":
            save = FrameContext.page
            FrameContext.page = self
            self.gui_state = "refresh"
            self.present(event)
            FrameContext.page = save
            
