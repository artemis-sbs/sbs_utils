from sbs_utils.agent import Agent
def _leads_of (agent_id):
    """Every ``Leads to:`` key of the ACTIVE quests an agent holds, nested ones too."""
def _norm (s):
    ...
def _person_worth (rec):
    ...
def _prop_worth (rec):
    """A prop nobody has touched yet that has something to it: a scene, an item, a
    lock, or just a description to read."""
def _where_key (key):
    """(area, x, y) of a prop or person key, or None when it is not on the map."""
def boarding_bearing (dx, dy):
    """A compass word for a map offset (y grows down the screen, so -y is north)."""
def boarding_go_to (client_id, key):
    """Walk to a prop or person and use or talk to it on arrival - the same as clicking
    it on the map. False when it is not in this crew member's area."""
def boarding_hint_badges (client_id, area):
    """What the tile view draws: ``{(x, y): atlas key}``, kinds with no sprite left
    out. This is what ``gui_tilemap(hints=...)`` is given."""
def boarding_hint_sprite (kind):
    ...
def boarding_hint_style (new=None, lead=None, way=None):
    """Name the atlas cells the map draws its hint badges with. ``None`` leaves a kind
    as it was; ``""`` turns it off."""
def boarding_hints (client_id, area):
    """``{(x, y): kind}`` for one area, as this console should see it. Only cells the
    party has explored; a lead wins over new, which wins over way."""
def boarding_hints_revision (client_id):
    """Moves when anything these lists show could have changed."""
def boarding_lead_places (client_id):
    """``[(key, name, where)]`` for this console's leads: ``where`` is the area's title,
    with a bearing when it is the area the crew member stands in, or a vaguer phrase
    when the party has not found that place yet."""
def boarding_leads (client_id):
    """The prop and person keys this console's open quests point at, not yet dealt
    with. Its own quests first, then the party's."""
def boarding_points_of_interest (client_id, reach=1):
    """What this crew member can see that is worth walking to, nearest first:
    ``[(kind, key, name, distance, bearing, hint)]``. ``kind`` is ``prop`` or ``talk``;
    ``hint`` is ``lead``, ``new`` or ``""``. Things already within ``reach`` are left
    out - the Look app lists those as buttons already. Scenery is never listed."""
def eva_leads (client_id):
    """The places in this console's relic its open quests point at (``Leads to:`` naming
    a relic point), not yet visited by it. Its own quests first, then the party's - the
    same order as `boarding_leads`, which answers the question for the ground."""
