from sbs_utils.mast.mast_node import MastDataObject
def _csv (value):
    """A comma-separated fact as a list. Already-a-list passes through."""
def _declared_kind (section):
    """The kind noun the fence actually declared, or ""."""
def _hull_known (hull):
    ...
def _is_crew_section (node, section, allow_key=True):
    """Is this node a roster?
    
    Two ways to say so, and they are NOT equal. A bare ``crew`` noun on the fence is the AMD
    idiom and is definitive. A section merely KEYED ``crew``/``rosters`` is a guess, kept
    because ``## [Crew](crew)`` reads naturally and an author should not have to say it
    twice - but it is only consulted when nothing in the file declared the noun outright.
    
    That ordering is load-bearing. A file whose root heading is ``# [Rosters](rosters)``
    holding two real ``crew`` sections would otherwise match on the ROOT, and every actual
    roster in it would be read as one of its members."""
def _lower (data):
    ...
def amd_crew_data (text):
    """Parse one crew fence into a data dict."""
def amd_crew_facts ():
    """``amd_parse_facts`` handler for a crew fence.
    
    Unknown labels return None so they fall through to the field registry and then to the
    numeric default, exactly as every other domain reader does - a mission may declare extra
    fields on crew and read them off ``record.data``."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x000002741D0E0540>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def amd_read_text (path):
    """The text of one .amd (or any AMD-adjacent source), decoded the same way a
    mastlib read decodes it.
    
    UTF-8 first (with a BOM tolerated, since editors add one), falling back to
    cp1252 for a legacy file that predates that convention, and finally to a
    replacing UTF-8 decode - because a file that cannot be decoded should still
    parse into something an author can look at and fix, not vanish."""
def crew_from_core (section):
    """The same, from an ``amd_core`` node - the model the LINTER parses into.
    
    Two readers exist because the linter needs spans and the runtime does not; they share
    the record builders above so the two can never disagree about what a fact means."""
def crew_from_document (doc):
    """Every roster in a document. A file with no crew section yields nothing rather than
    complaining, so a mission may keep its rosters in a file beside anything else."""
def crew_from_section (node):
    """Roster records from one ``## [Name](key)`` crew section of an ``amd_document``."""
def crew_member_record (section, data, key, name=None, roster_key=None):
    """One crew member from the section's facts and their own.
    
    Section-level ``Race``/``Portraits``/``Cell``/``Grid`` are the member's defaults, which
    is what lets a member be a ``Console:`` line and a ``Face:`` line."""
def crew_read_amd (file_path):
    """Read a MISSION-relative ``.amd`` file and return its roster records.
    
    Mission-relative, so an ADDON CANNOT USE THIS. An addon reads its own file out of its
    mastlib and calls :func:`sbs_utils.procedural.crew.crew_declare_amd`."""
def crew_roster_record (key, section, name=None, desc=None, members=None):
    """One roster from its section fence.
    
    ``By:`` defaults to ``console`` because a cast is the common case and the one that needs
    no player input; a group has to say so."""
def crew_sections (doc):
    """Every crew section in a document, AT ANY DEPTH.
    
    `amd_document` wraps a file's sections under a single root heading, and a mission is
    free to nest its rosters under one of its own - so this walks rather than looking one
    level down. A node that IS a roster is not descended into: its children are its members,
    not more rosters."""
def crew_validate (records, check_files=True):
    """Problems a mission would otherwise meet as a blank name plate.
    
    Returns a list of ``(key, severity, code, message)``.
    
    A ``Console:`` no ``@console`` label registers is a WARNING, never an error: console
    types are registered at runtime from decorator labels, so a mod's own console genuinely
    may not exist at lint time and refusing it would make the linter wrong about correct
    files."""
