from sbs_utils.helpers import FrameContext
def _esc (text):
    """Free prose in a style string. A `:` or `;` in a title or description would
    otherwise be read as style properties and silently truncate the widget - the same
    trap `gui_map_picker` documents on its cards."""
def _row_template (item):
    """One board row: the reading first, because that is what is being read.
    
    Sizes its ROW and returns None - a listbox only calls resize_to_content() when
    the template returns nothing."""
def epadd_console_name (console):
    """The name a script would use for a console, whatever the engine calls it."""
def gui_app_badge (app):
    """An app's live badge, as text.
    
    Never raises: a provider that throws costs its own tile a badge and nothing else.
    
    RE-ENTRANT PROVIDERS ARE ANSWERED, NOT RE-ENTERED. A provider is free to ask what
    the other apps are reporting - LM's Status tile does exactly that, counting the apps
    with something to say - and `status_rows` computes a badge for EVERY app, the asking
    one included. That is a cycle: the provider was entered 332 times for one badge
    (measured), unwound only when Python's own recursion limit tripped, and the
    RecursionError caught below was logged as "status provider for 'status' raised" on
    every badge computation, several times a second. The badge still came out right,
    which is why it read as noise rather than as a bug."""
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
def gui_app_list (console=None, client_id=None):
    """The apps this console should offer, in the order they should be drawn.
    
    Registered apps scoped to `console`. An entry whose `//gui/app/` route does not
    exist, or whose route condition is false right now, is left out - the route's own
    `if` is still the authority on whether a panel is available. A MISSING route is
    reported by name; it is almost always a typo or an unmigrated `//gui/tab`.
    
    Returns:
        list[dict]: each with tab, title, icon, group, sort, description, label."""
def gui_app_open (tab):
    """Open an app: send the GUI task to that app's label.
    
    The same two lines `TabControl.on_message` runs when a tab button is clicked, so
    an app opened from the PADD arrives exactly as a tab would have.
    
    Returns:
        bool: False when the app has no route or there is no GUI task to send."""
def gui_status_screen (title='Status'):
    """Draw the status board for this console."""
def status_rows (console=None):
    """The apps with something to say, in the order the PADD lays them out.
    
    Each row is the app record plus the badge text it produced, so a caller renders
    it without calling a provider a second time - a provider can be expensive and
    can change between calls, and a row that showed one value and opened on another
    would be worse than no row."""
