"""Let a widget carry MORE THAN ONE gui_message handler (LM issue #614).

Before this, every registration was a plain `=`, so the second handler attached
to a widget silently discarded the first. There are two independent slots and
both had the problem:

  * Channel 1 -- the page's `tag_map`, `{tag: (layout_item, runtime_node)}`.
    Written by `on gui_message(w):`, `gui_message(w, label)` and
    `gui_button(on_press=...)`.
  * Channel 2 -- `layout_item.on_message_cb`. Written by
    `gui_message_callback()` and `gui_message_label()`.

`MessageChain` holds several handlers and answers to BOTH protocols -- Channel
1 calls `on_message(event)`, Channel 2 calls the object -- so neither side of
the library needs to learn about multiplicity. Everything that reads a tag_map
entry (`gui_update`, the log panel's liveness check, the exerciser, the handler
audit, the tests) keeps working unchanged.

Three rules make this backward compatible, and each is load-bearing:

1. A LONE handler is never wrapped. `entry[1]` stays the raw MessageTrigger /
   MessageHandler when there is only one, because real consumers read through
   it by type and by attribute (`entry[1].task`, `getattr(rn, "handler", None)`,
   `isinstance(node, (MessageTrigger, MessageHandler))`).
2. An INERT handler is not a link. `gui_button()` builds a `MessageHandler`
   even when there is no `on_press`, and that one has nothing to run --
   see `MessageHandler.is_inert`.
3. Growing an existing chain returns the SAME tuple object, so the listbox's
   retraction check (`tag_map.get(k) is v`) still recognizes what it merged.

Ordering is registration order, which is source order. Note that Channel 2
always fires before Channel 1: `StoryPage.on_message` walks the layouts before
it looks the tag up.
"""

import logging
import traceback


class MessageChain:
    """An ordered list of gui_message handlers that looks like a single one.

    Callable as `chain(event, item)` (Channel 2) and as `chain.on_message(event)`
    (Channel 1), so it can sit in either slot.
    """

    # A Channel-1 runtime node: `node.on_message(event)`.
    NODE = "node"
    # A Channel-2 callback: `cb(event, item)`.
    CB = "cb"

    # Re-raise instead of continuing. The isolation below exists so that one
    # author's broken handler cannot silence another's -- flip this in one
    # place when you want the old propagate-and-stop behavior back.
    stop_on_error = False

    def __init__(self):
        self._entries = []

    @staticmethod
    def kind_of(handler):
        return MessageChain.NODE if hasattr(handler, "on_message") else MessageChain.CB

    def add(self, handler, kind=None):
        """Append a handler. Returns False if this exact object is already in."""
        if handler is None:
            return False
        for existing, _ in self._entries:
            if existing is handler:
                return False
        self._entries.append((handler, kind or self.kind_of(handler)))
        return True

    def remove(self, handler):
        for i, (existing, _) in enumerate(self._entries):
            if existing is handler:
                del self._entries[i]
                return True
        return False

    def clear(self):
        self._entries = []

    @property
    def handlers(self):
        return tuple(h for h, _ in self._entries)

    def __len__(self):
        return len(self._entries)

    def __iter__(self):
        return iter(self.handlers)

    def __bool__(self):
        # A chain always counts as present, even the moment it is emptied --
        # `if self.on_message_cb is not None` is the real presence test.
        return True

    def __contains__(self, handler):
        return any(existing is handler for existing, _ in self._entries)

    def on_message(self, event, item=None):
        self._fire(event, item)

    def __call__(self, event, item=None):
        self._fire(event, item)

    def _fire(self, event, item):
        # Snapshot: a handler is allowed to reroute and rebuild the GUI, which
        # can register or drop handlers while we are still walking.
        for handler, kind in tuple(self._entries):
            try:
                if kind == self.NODE:
                    handler.on_message(event)
                else:
                    _call_cb(handler, event, item)
            except Exception:
                if self.stop_on_error:
                    raise
                # Keep going. Stopping here would put us back where #614
                # started: a handler that never runs, for a reason nobody
                # attached to this widget can see.
                logging.getLogger("mast.runtime").error(
                    "A gui_message handler raised; the remaining handlers on "
                    "this widget still ran.\n" + traceback.format_exc()
                )


def _call_cb(cb, event, item):
    """Invoke a Channel-2 callback.

    `Layout` has always called this slot as `cb.on_message(event, item)` while
    `Column` called it as `cb(event, item)`, and both forms are in the wild, so
    accept either. (That split is why attaching a plain function -- which is all
    gui_message_callback ever assigns -- to a gui_section() used to raise
    AttributeError on the first click.)
    """
    fn = getattr(cb, "on_message", None)
    if fn is not None:
        fn(event, item)
    else:
        cb(event, item)


def _is_inert(node):
    """True for a runtime node with nothing to run.

    Duck-typed on purpose: importing procedural.gui.button from here would drag
    in the whole procedural GUI surface and close an import cycle.
    """
    fn = getattr(node, "is_inert", None)
    return bool(fn is not None and fn())


def compose_handler(existing, layout_item, runtime_node):
    """Return the `(layout_item, node)` tuple a tag_map key should now hold.

    Replaces, exactly as before, unless there is a real handler already
    registered for this same widget -- then the two are chained.
    """
    if runtime_node is None:
        # Every widget except gui_button registers None. Unchanged.
        return (layout_item, None)
    if existing is None:
        return (layout_item, runtime_node)

    old_item, old_node = existing
    if old_item is not layout_item:
        # A different widget claimed this tag: a rebuild reusing the number, or
        # an author-supplied `tag:` name used twice. Last one wins, as before.
        return (layout_item, runtime_node)
    if old_node is None or _is_inert(old_node):
        return (layout_item, runtime_node)
    if old_node is runtime_node:
        return existing
    if isinstance(old_node, MessageChain):
        old_node.add(runtime_node)
        # The SAME tuple, so identity-based cleanup elsewhere still matches.
        return existing

    chain = MessageChain()
    chain.add(old_node)
    chain.add(runtime_node)
    return (layout_item, chain)


def message_cb_add(layout_item, cb):
    """Register a Channel-2 callback WITHOUT dropping any already attached.

    Direct assignment (`item.on_message_cb = fn`) still means replace -- that is
    what the layout classes themselves do, and it is the only predictable
    meaning for `=`. This is the append form.
    """
    existing = getattr(layout_item, "on_message_cb", None)
    if existing is None:
        # One callback stays a bare callable, so the single-handler shape --
        # and anything comparing `item.on_message_cb is my_fn` -- is untouched.
        layout_item.on_message_cb = cb
        return cb
    if existing is cb:
        return existing
    if isinstance(existing, MessageChain):
        existing.add(cb, MessageChain.CB)
        return existing

    chain = MessageChain()
    chain.add(existing, MessageChain.CB)
    chain.add(cb, MessageChain.CB)
    layout_item.on_message_cb = chain
    return chain


def invoke_message_cb(cb, event, item):
    """Call whatever is in an `on_message_cb` slot: chain, object, or function."""
    if cb is None:
        return
    if isinstance(cb, MessageChain):
        cb(event, item)
        return
    _call_cb(cb, event, item)


def message_handlers(node):
    """Flatten a tag_map runtime node into the handlers it will actually run.

    For tooling and tests that inspect handlers by type -- without this a
    chained handler is invisible to them.
    """
    if node is None:
        return ()
    if isinstance(node, MessageChain):
        return node.handlers
    return (node,)
