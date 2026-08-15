import logging

from ...helpers import FrameContext
from ...futures import Trigger
from ...message_chain import MessageChain, message_cb_add

# Source sites already reported, so a button someone keeps pressing warns once
# instead of once per click. Keyed by the SITE, not the widget: a GUI rebuild
# hands out a fresh widget (and a fresh tag) on every repaint.
_dead_handler_sites = set()


def dead_handler_sites_clear():
    """Per-mission reset -- see handlerhooks.reset_mission_state."""
    _dead_handler_sites.clear()


def dead_handler_site_count():
    return len(_dead_handler_sites)


def gui_host_task(task):
    """The page's live GUI task -- who can tick a handler this task registered."""
    page = getattr(getattr(task, "main", None), "page", None)
    return getattr(page, "gui_task", None)


def host_handler_sub_task(builder, sub_task):
    """Give a handler sub-task a LIVE ticking parent when its builder has ended.

    A `gui_message(widget, label)` handler runs as a sub-task of the task that
    built the widget, and sub-tasks are only ever ticked by their parent's
    tick(). On a finished builder that is exactly one tick -- the
    tick_in_context() at the call site -- after which the handler stalls
    wherever it happens to be. Single-line handlers looked like they worked;
    anything that awaited did not.

    The page's gui_task takes over the TICKING only. root_task is deliberately
    left pointing at the builder, so the handler's variable scope is exactly
    what it is when the builder is alive.

    Returns True when the sub-task was re-hosted.
    """
    from ...mast.mastscheduler import MastAsyncTask
    if not MastAsyncTask.revive_ended_handlers:
        return False
    host = gui_host_task(builder)
    if host is None or host is builder or host.done():
        return False
    if sub_task in builder.sub_tasks:
        builder.sub_tasks.remove(sub_task)
    if sub_task not in host.sub_tasks:
        host.sub_tasks.append(sub_task)
    # Belongs to the GUI that owned the widget -- see StoryPage.on_new_gui.
    sub_task._revived_handler = True
    return True


def _handler_site(task, label, loc):
    try:
        from ...mast.mast import Mast
        lbl = task.main.mast.labels.get(label) if isinstance(label, str) else label
        cmd = lbl.cmds[loc]
        return (Mast.get_source_file_name(cmd.file_num), cmd.line_num)
    except Exception:
        return (None, f"{label}")


def warn_dead_handler(task, label, loc, kind):
    """Report a click that landed on a task which has already finished.

    Without this the failure is completely silent: the widget draws, the click
    dispatches, the handler is discarded, and nothing is logged anywhere. That
    silence is most of what made LM issue #707 hard to place.
    """
    site = _handler_site(task, label, loc)
    if site in _dead_handler_sites:
        return
    _dead_handler_sites.add(site)
    where = f"{site[0]} line {site[1]}" if site[0] else f"label {site[1]}"
    logging.getLogger("mast.runtime").warning(
        f"GUI handler ignored: the {kind} at {where} belongs to a task that has "
        f"already ended, so pressing it does nothing. Keep that task alive (end "
        f"it with `await gui()` or a loop instead of ->END / yield), or attach "
        f"the handler with gui_message_callback(widget, fn), which needs no task."
    )

class MessageTrigger(Trigger):
    def __init__(self, task, layout_item, label=None):
        # This will remap to include this as the message handler
        task.main.page.add_tag(layout_item, self)
        page = FrameContext.page 
        #
        # This is an outlier 
        # Your in a sub page 
        #
        if page is not task.main.page:
            page.add_tag(layout_item, self)

        self.task = task
        self.layout_item = layout_item
        # Needs to be set by Mast
        # Pure mast this is active Label
        # Python ith should be a callable
        self.label = label
        self.use_sub_task = False
        if label is None:
            self.label = task.active_label 
        else:
            self.use_sub_task = True
        # 0 for python the node loc of the on in Mast
        self.loc = 0



    def on_message(self, event):
        if not self.layout_item.is_message_for(event):
            return
        # A handler belongs to the task that BUILT the widget. The two forms
        # need different things from a builder that has finished: the inline
        # block IS that task's code, so the task itself must be woken; the
        # label form is a separate sub-task, which only needs someone alive to
        # tick it.
        was_dead = self.task.done() or self.task.active_ticker.done
        if not self.use_sub_task:
            if not self.task.revive_for_handler(gui_host_task(self.task)):
                # Stop HERE. push_inline_block would mutate the finished task
                # -- leaving pending_jump set and growing label_stack -- for a
                # jump that tick() returns before ever reading.
                warn_dead_handler(self.task, self.label, self.loc,
                                  "`on gui_message` block")
                return
        self.task.set_value_keep_scope("__ITEM__", self.layout_item)
        data = None
        if hasattr(self.layout_item, "data"):
            data = self.layout_item.data
        if not self.use_sub_task:
            self.task.push_inline_block(self.label, self.loc, data)
            self.task.tick_in_context()
        else:
            sub_task = self.task.start_sub_task(self.label, inputs=data, defer=True)
            if was_dead and not host_handler_sub_task(self.task, sub_task):
                # Not re-hosted, so this is the one free tick it has always had
                # on a dead parent -- kept because single-tick handlers depend
                # on it. It still stalls the moment it awaits.
                warn_dead_handler(self.task, self.label, self.loc,
                                  "gui_message handler")
            sub_task.tick_in_context()

def gui_message(layout_item, label=None):
    """Register a MAST label to run when a layout element receives a GUI event.

    Attaches a ``MessageTrigger`` to the current task so that when the engine
    fires a ``gui_message`` event matching ``layout_item``'s tag, the given
    label is pushed and executed inline. Used to respond to clicks on custom
    layout items (sections, regions, etc.) that are not plain buttons.

    Args:
        layout_item: The layout object whose tag to watch. Must expose
            ``is_message_for(event)`` (all standard layout items do).
        label (optional): MAST label or inline block to run on the event.
            Defaults to the current active label.

    Returns:
        MessageTrigger: The registered trigger object.

    Example:
        region = gui_region(style="area:10,10,50,50;")
        gui_message(region, on_region_click)
        ///on_region_click
            gui_text("Region clicked!")
    """
    task = FrameContext.task
    return MessageTrigger(task, layout_item, label)


def gui_message_callback(layout_item, cb):
    """Set a Python callable to invoke when a layout element receives a GUI event.

    Attaches a callback directly to the layout item's ``on_message_cb``
    attribute. The callback is called with the event and the layout item when
    the engine fires a ``gui_message`` event matching the item's tag.
    Use this for pure-Python handlers; use ``gui_message`` for MAST label
    handlers.

    Args:
        layout_item: The layout object to attach the callback to.
        cb (callable): Function called as ``cb(event, layout_item)`` on event.

    Example:
        btn = gui_button("Fire!", on_press=None)
        gui_message_callback(btn, lambda e, item: fire_torpedo(SHIP_ID))
    """
    return message_cb_add(layout_item, cb)


def gui_message_label(layout_item, label):
    """Schedule a MAST label as a sub-task when a layout element receives a GUI event.

    Similar to ``gui_message_callback`` but wraps the label in a
    ``gui_sub_task_schedule`` call, running it as an independent sub-task
    rather than inline in the current task.

    Args:
        layout_item: The layout object to attach the handler to.
        label: MAST label to schedule as a sub-task on event.

    Example:
        section = gui_sub_section(style="col-width:30%;")
        gui_message_label(section, handle_section_click)
    """
    from ..execution import gui_sub_task_schedule
    return message_cb_add(layout_item, lambda e, s: gui_sub_task_schedule(label))



def gui_message_clear(layout_item):
    """Drop EVERY gui_message handler attached to a widget, on both channels.

    Handlers accumulate now (LM #614), so replacing rather than adding takes an
    explicit step: clear, then register. Before #614 a plain re-registration
    did this implicitly, by throwing the previous handler away.

    Args:
        layout_item: the widget to detach every handler from.

    Returns:
        int: how many registrations were removed.
    """
    removed = 0
    cb = getattr(layout_item, "on_message_cb", None)
    if cb is not None:
        removed += len(cb) if isinstance(cb, MessageChain) else 1
        layout_item.on_message_cb = None

    task = FrameContext.task
    pages = [FrameContext.page, getattr(getattr(task, "main", None), "page", None)]
    seen = []
    for page in pages:
        if page is None or any(page is p for p in seen):
            continue
        seen.append(page)
        for name in ("tag_map", "pending_tag_map"):
            tag_map = getattr(page, name, None)
            if not tag_map:
                continue
            for tag, entry in list(tag_map.items()):
                if entry is None or entry[0] is not layout_item or entry[1] is None:
                    continue
                node = entry[1]
                removed += len(node) if isinstance(node, MessageChain) else 1
                tag_map[tag] = (layout_item, None)
    return removed
