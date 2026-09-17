from sbs_utils.helpers import FrameContext
def _esc (text):
    """Free prose in a style string. A `:` or `;` in a title or description would
    otherwise be read as style properties and silently truncate the widget - the same
    trap `gui_map_picker` documents on its cards."""
def _pane_build ():
    """The reading pane, built ONCE. A tick assigns to these four."""
def _pane_update (view, entry):
    """Show one reading. EVERY part of it, not only the interesting one.
    
    A pane that is right about the body and stale about the heading describes the
    previous reading, which is worse than a blank one."""
def _row (item, **kwargs):
    """One reading as a list row. Returns None, so the listbox sizes it.
    
    NEVER return a size from an item template: the listbox only calls
    `resize_to_content()` when the template returns None, and an item section starts at
    zero height - returning one leaves it degenerate, which kills selection and the
    click region with it."""
def _subject_of (item):
    """A node's name is `room:thing`; the room half is what a person calls it."""
def gui_app_chrome (title, subtitle=None):
    """An app's title bar. OPTIONAL - an app draws it when a title helps orient.
    
    ITS OWN BAND, 45px..109px, from `design/epadd/Spec.src`. It used to be a bare
    `gui_row` with no section of its own, so it landed in the ambient full-screen section
    at y=0 and painted over the engine's Options button. Every caller already reserved
    `area: 0, 109px, 100, 100` for its body, so the bar was always MEANT to own this
    band - it just never claimed it.
    
    45px is the console body top, the LM convention every tab body already follows, so
    this clears the tab strip as well as Options.
    
    NO HOME BUTTON. The strip's status region opens the PADD home already; a HOME here
    was a second control for the same thing. And no back: the one Back in the game is
    the console's, on the tab bar, declared by every PADD screen with
    `gui_tab_back(CONSOLE_SELECT)`.
    
    NOT EVERY APP WANTS ONE. Upgrades and the other list/detail screens use their whole
    sheet and read better for it, so this is opt-in rather than something every screen
    must remember to draw.
    
    Args:
        title (str): the screen's name.
        subtitle (str, optional): a second, dimmer line. Leave it out unless it says
            something the screen below does not - a board captioned with the count of
            what it is already listing says nothing.
    
            Pass "" rather than None for a line that is EMPTY NOW but will have text
            later: the widget is created either way, so a live screen can update it in
            place instead of rebuilding the page to make one appear.
    
    Returns:
        Text | None: the subtitle widget, so a caller can keep it and update it."""
def gui_survey_screen (title='Survey'):
    """Draw the log and the reading pane."""
def gui_survey_screen_tick ():
    """Refresh the log in place. What an `on change xess_log_revision()` should CALL.
    
    Never a jump back to the screen label: that re-sends every widget on the sheet over
    the network, and a watcher would do it forever.
    
    Returns:
        bool: False when the screen is gone - a handler can outlive the page."""
def survey_badge ():
    """The tile's badge: how many readings the party has taken.
    
    "" when there are none, which is the convention every PADD provider follows - an
    app with nothing to say says nothing rather than "0"."""
def survey_relevant ():
    """Whether this app is worth a tile.
    
    A mission with no boarding party in it has never filed a reading, and a tile that
    opens an empty page on every console is the noise the Boarding Party app's own
    condition exists to prevent."""
def xess_log_count (kind=None):
    """How many readings there are. What the tile's badge says."""
def xess_log_entries (kind=None, site=None):
    """Every reading, newest first. Filtered by kind or site when asked."""
def xess_log_revision ():
    ...
