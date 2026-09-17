from sbs_utils.helpers import FrameContext
def _come_back_word (client_id):
    """The way home, and it must match the way out.
    
    A console that suited up has a SHIP to be deleted and a different console type to be
    put back; `boarding_go_up` knows about neither, so sending an EVA console through it
    would leave the suit drifting in the ruin and the console on a dead 3D view.
    
    Two spellings of the same word, because the two surfaces shout differently: the PADD
    labels its one big commitment in caps, the device's buttons are sentence case. Doing
    it with `.title()` at the call site gets "Beam Up", which is neither.
    
    Returns:
        tuple: ``(padd_label, device_label, door)``."""
def _down_here (client_id, held):
    """What a console on the surface sees: who it is, and the way back."""
def _esc (text):
    """Free prose in a style string. A `:` or `;` in a title or description would
    otherwise be read as style properties and silently truncate the widget - the same
    trap `gui_map_picker` documents on its cards."""
def _give_a_body (client_id, host):
    """Put this console's character on the interior, and hand the console that body.
    
    Idempotent: a console that already has a figure keeps it, so a second beam-down (a
    reconnect, a move between sites) does not leave an abandoned body standing on the
    floor for the rest of the mission."""
def _go_word ():
    """What the button says, and which door it opens.
    
    ONE BRANCH, in one place, because there are two kinds of place to board now. A ship's
    interior is a floor, so you beam down onto it; a relic has no floor, so you suit up
    and fly it. The party, the roster and the reservation are identical either way - only
    the body differs - so the whole difference is which door the button calls.
    
    Returns:
        tuple: ``(label, going_to_phrase, door)``."""
def _going_as (client_id, lifeform):
    """A place held for this console: who they already are, and one button.
    
    No picker. The crew member has BEEN this person all evening - the party was
    derived from the bridge, not cast - so asking them to choose themselves off a list
    is a step that can only be got wrong. What they need to see is the face and the
    job words the scene guards will read."""
def _roster_template (item):
    """One character on offer. Sizes its ROW and returns None."""
def _who_is_down ():
    """The rest of the party, so nobody is alone down there by accident."""
def boarding_beam_down (client_id, lifeform=None):
    """Take a place in the landing party.
    
    Args:
        client_id: the console volunteering.
        lifeform (optional): who to play. Defaults to the first character still free,
            so a console can simply say yes.
    
    Returns:
        The lifeform taken, or None when the invitation is closed or nobody is left -
        which a caller shows as "the party is full" rather than treating as an error."""
def boarding_beam_up (client_id):
    """Leave the surface. The console's own screen is the caller's business - this
    releases the character so somebody else could take them."""
def boarding_client_of (lifeform):
    """Which client is playing this character, or None. The reverse of :func:`boarding_me`."""
def boarding_clients ():
    """Every client currently controlling a character."""
def boarding_go_down (client_id, host=None):
    """Morph this console into the character it just took, and show it where it is.
    
    The PADD stays open across it - the crew pressed a button on a screen and that
    screen is still there, now saying who they are. That is the whole reason identity
    lives in the bar rather than in an app.
    
    **`gui_console_enter` is given the console's OWN ship, never the host**, and the
    assignment to the host is a separate line afterwards. That split is not tidiness; it
    is the difference between a player keeping their name and losing it. The door
    re-asserts the crew seat with `crew_assign(client_id, home, console_type)`, and
    `own_pick` is None for anybody auto-named - so handing it the host resolves the seat
    against the HOST's roster and hull and, failing both, autonames from
    `_complement_key(host, slot)`. `crew_resolve`'s own docstring says it outright:
    moving seats RENAMES an auto-named player. The crew would beam across and arrive as
    strangers.
    
    So the seat and the camera stay home; only the interior view follows the host.
    
    Args:
        client_id: the console going down.
        host (optional): the ship or station whose interior it will walk. Without one
            this is the old dialogue-only morph, which is still a valid way to play.
    
    Returns:
        bool: False when this console is not holding anybody."""
def boarding_go_up (client_id):
    """Put this console back at the post it left.
    
    The character is released first, so somebody still down there could take them.
    Where the console goes next is the mission's business - `boarding_came_back` is how it
    is told - but the console TYPE is restored here, because leaving a crew member
    wearing `away` is what the role-strip bug was."""
def boarding_held (client_id):
    """Every character this console speaks for, primary first."""
def boarding_home_ship (client_id):
    """The ship this console BELONGS to, even while it is looking at a boarded interior.
    
    `viewscreen_home_ship` cannot answer once a console is boarded: it falls back to
    `sbs.get_ship_of_client`, and boarding has just pointed that at the site. So the real
    answer is captured on the way down and kept here."""
def boarding_invitation ():
    """The open invitation, or None."""
def boarding_invite_site ():
    """The interior this party is boarding, or None for a dialogue-only party."""
def boarding_invite_title ():
    ...
def boarding_is_open ():
    """True while a beat is open and answerable."""
def boarding_job_text (lifeform, default=''):
    """:func:`boarding_jobs` as one line, ready for a widget. ``default`` when there is none."""
def boarding_label (lifeform):
    """A character as a person: their name and what they are for.
    
    The job words are not decoration - the scene guards read exactly these - so a crew
    member choosing a character is reading the same thing the story will."""
def boarding_me (client_id):
    """The character this client is playing - the PRIMARY, when it holds several.
    
    Stays the answer to "whose face and name is on this screen", which is what every
    caller wants it for. :func:`boarding_held` is the whole list."""
def boarding_open_roster (client_id=None):
    """The characters this console may still take, in the order they were offered.
    
    A body RESERVED for another console is not on offer - a crew-derived party knows
    who everybody is, and offering Lt Marek to the person who is not Lt Marek is how
    two consoles end up fighting over one body. Asked without a console, this is the
    unreserved remainder, which is what "who is still free" means to a script."""
def boarding_relevant (client_id=None):
    """Whether the Boarding Party app has anything to offer this console.
    
    True when a party is forming, or when this console is already down there. A
    mission with no landing parties in it has neither, and the tile is then pure
    noise on every console - which is what a playtest reported: six screens each
    carrying a button that says "No landing party".
    
    Put this on the ROUTE (`//gui/tab/boarding_team if boarding_relevant()`) rather than
    inventing a visibility flag: a route's own condition is already what ePADD tests
    when it builds the app list, and it is how `casino` and `brain` gate themselves."""
def boarding_reserved (client_id):
    """The character held for this console, or None."""
def boarding_set_who (client_id, lifeform):
    """Which of this console's characters is acting."""
def boarding_team ():
    """Every character currently under a console's control, as a set of ids.
    
    A set rather than a list: callers intersect it with role queries, and the same character
    must never appear twice however many clients were bound to it."""
def boarding_who (client_id=None):
    """The character this console is playing, or None.
    
    A console holding several has an ACTIVE one - the roster picker sets it - because
    four characters' readings side by side is a dozen buttons and no sense of who is
    doing what."""
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
def gui_boarding_screen (title='Boarding Party'):
    """Draw the join/leave screen for this console."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
