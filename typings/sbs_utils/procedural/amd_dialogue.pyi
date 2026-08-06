from sbs_utils.mast.mast_node import MastDataObject
def _dlg_norm (s):
    ...
def _dlg_parse_choice (line):
    ...
def _dlg_parse_outcomes (s):
    """'costs 200 credits, earns ashfang selfish +5, signal paid' -> [(verb, *tokens), ...].
    Tokens are interpreted by the registered outcome handler (only `signal` is built in), so
    the grammar of costs/earns/etc. lives with the mission, not here."""
def dialogue_apply (agent_id, speaker, outcomes):
    """Apply a chosen line's outcomes: built-in `signal`, plus any registered verbs. Returns
    False if a handler refuses (e.g. a cost can't be afforded) - the pick is rejected."""
def dialogue_choices (scene, agent_id, speaker):
    """Choices whose guard passes, as MastDataObject (label/target/outcomes) so a mast comms
    route can render one button each."""
def dialogue_entry_for (scenes, speaker_key, when='comms'):
    """The entry scene key whose Speaker == speaker_key and When == `when` (default comms),
    or None. Used to open a character/faction's hail."""
def dialogue_get (scenes, key):
    ...
def dialogue_guard_ok (guard, agent_id, speaker):
    """Evaluate a simple `lhs op number` guard (no guard -> True). Safe: only a resolved
    metric, a comparison operator, and an integer - never arbitrary code."""
def dialogue_parse (node):
    """Parse one scene node into a plain dict: speaker, when, lines [(text, gate)], and
    choices [{label, target, guard, outcomes}]. Pure - no engine calls."""
def dialogue_pick_line (scene, agent_id, speaker):
    """A random NPC line whose gate passes (gates reuse the metric resolver). '' if the
    scene has no eligible line."""
def dialogue_register_outcome (verb, fn):
    """Register an outcome handler: fn(agent_id, speaker, tokens) - tokens are the words
    after the verb. Returning False refuses the pick. (`signal` is built in.)"""
def dialogue_scenes (section):
    """key -> scene node for every scene in a dialogue SECTION node (empty if None). The
    caller resolves the section (e.g. amd_section(doc, "dialogue"))."""
def dialogue_set_metric_resolver (fn):
    """Set the guard metric resolver: fn(name, agent_id, speaker) -> number."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
