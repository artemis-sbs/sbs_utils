"""The engine Options button, per client, remembered across page rebuilds.

`sbs.transparent_options_button(client_id, flag)` is a one-shot: it sets the
button's state and nothing records that it was asked for. `StoryPage.on_new_gui`
then restores the button on EVERY new GUI -- which fires from `add_tag`, on the
first tagged widget of a build -- so a mission that set it at the top of its
screen label had the setting taken away a moment later, every rebuild. The same
call worked in a cinematic only because no story page was being built.

So the intent is recorded here, and the page restores to the RECORDED value
rather than to a hardcoded 0. Default is 0, so a mission that never calls this
behaves exactly as before.
"""
from ...helpers import FrameContext


# client_id -> 1 (transparent) | 0 (normal). Absent means "never asked", which
# is 0 -- the behavior every existing mission already gets.
_OPTIONS_TRANSPARENT = {}


def gui_options_button(transparent=True, client_id=None):
    """Make the engine Options button transparent (or normal) for a client, and
    keep it that way across page rebuilds.

    Prefer this over calling ``sbs.transparent_options_button`` directly: the raw
    call is undone by the next page build.

    Args:
        transparent (bool, optional): ``True`` to make the button transparent,
            ``False`` to restore it. Defaults to ``True``.
        client_id (int, optional): The client to set it for. Defaults to the
            client of the current frame.

    Example:
        gui_options_button()            # this console's button, transparent
        gui_options_button(False)       # put it back
    """
    if client_id is None:
        client_id = FrameContext.client_id
    if client_id is None:
        return
    flag = 1 if transparent else 0
    _OPTIONS_TRANSPARENT[client_id] = flag
    ctx = FrameContext.context
    if ctx is not None:
        ctx.sbs.transparent_options_button(client_id, flag)


def gui_options_button_flag(client_id):
    """The flag a mission last asked for on this client, or 0 if it never did.

    Used by StoryPage.on_new_gui to restore the button to what the mission
    wanted rather than to a hardcoded 0.
    """
    return _OPTIONS_TRANSPARENT.get(client_id, 0)


def gui_options_button_clear(client_id=None):
    """Forget the recorded intent (all clients when client_id is None), so the
    button returns to the default on the next rebuild. For a client that
    disconnected, and for tests."""
    if client_id is None:
        _OPTIONS_TRANSPARENT.clear()
    else:
        _OPTIONS_TRANSPARENT.pop(client_id, None)
