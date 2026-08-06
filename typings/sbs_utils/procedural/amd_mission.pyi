def amd_chain (*handlers):
    """Compose several `amd_parse_facts` handlers into one. Each label is offered to the
    handlers in order; the first that consumes it (returns truthy) wins, otherwise it falls
    through to the default coercion. Lets a single parser understand SEVERAL vocabularies at
    once - e.g. quests + science scans + landmarks - so a mission can author all its content
    sections in ONE .amd file (parsed by document_get_amd_file with the chained parser) and
    hand each section to its own loader. Ordering matters only where two handlers claim the
    same label; keep the most specific first."""
def amd_landmark_facts ():
    """amd_parse_facts handler for landmark fences: kind/side/roles/art/behavior (text),
    loc (3 floats), system (2 ints). Unknown labels return None (chain / default coercion)."""
def amd_mission_data (text, aliases=None):
    """Parse one fence with the combined quest+scan+landmark vocabulary. Use as the
    ``data_parser`` for a consolidated mission .amd."""
def amd_mission_facts (aliases=None):
    """The chained handler: quest, then landmark vocabularies (scans are body-based)."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000011CF6E5F4C0>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def amd_quest_facts (aliases=None):
    """Return an ``amd_parse_facts`` handler for the shared quest vocabulary.
    
    Objective/flow labels: Scope / State / Goal / When / Then / Pays / Tier / Display.
    Quests-tab action gating: Accept On (consoles that may Accept/Abandon) and Engage On
    (consoles that may Engage) restrict a job to specific stations.
    End-game + mission-tree labels: Win / Lose (bare flag -> end_win/end_lose; prose ->
    also the win_text/lose_text reason), Parent, Required, Critical, and the fail
    triggers Fail on signal / Fail on all dead / Fail after, plus the timed-completion
    trigger Complete after (symmetric to Fail after; drives a reveal chain). These map to
    the data keys the LM quest end-game driver reads (parent aggregation, end_win/end_lose
    game-over, fail_on_signal/fail_on_all_dead/fail_after, complete_after).
    
    Unknown labels return None, so a mission with extra vocabulary chains its own
    handler after this one (or falls to amd_parse_facts's default coercion).
    ``aliases`` is forwarded to ``amd_trigger`` / role resolution."""
