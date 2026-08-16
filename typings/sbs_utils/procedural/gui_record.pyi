def _write (entry):
    ...
def command_line_get (key, default=None):
    """One `key=value` argument, or `default`.
    
    The key is matched case-insensitively and without surrounding spaces, because a launch
    argument is typed by a person or pasted from a script and `Map=` should not behave
    differently from `map=`."""
def gui_record_begin (event):
    """Start describing one interaction. Called before the event is dispatched."""
def gui_record_count ():
    """How many interactions have been recorded. Reset-ledger probe."""
def gui_record_enabled ():
    """Whether recording is on, resolved once.
    
    Enabled by `record=<name>` on the command line, or a `gui_record.enable` marker file in
    the mission - the same two ways the dev queue is enabled, so there is one convention to
    learn rather than two."""
def gui_record_end ():
    """Finish the interaction and write it. Called after the event is dispatched."""
def gui_record_note (event, widget):
    """The widget the event turned out to be for. Called from `Layout.on_message`.
    
    This is the whole value of recording from inside: the LABEL is stable across page
    edits in a way the tag is not."""
def gui_record_path ():
    """Where the transcript is being written, or None."""
def gui_record_reset ():
    """Drop state at a mission boundary. Registered with the reset ledger."""
