"""WebRenderSink - capture a web client's GUI render as browser wire commands.

Installed (in-engine) as Gui.web_render_sink. During a web client's present,
Gui swaps FrameContext.context.sbs to one of these shims; it records each
send_gui_* call as a wire dict (the SAME format cosmos_dev.mockgui emits, so
client.html renders it unchanged) and forwards everything else to the real sbs.

The captured frames are drained by a host-side proxy and forwarded to the
browser. Nothing here depends on the engine internals, so it is unit-testable
against the mock and works identically in the real engine.

Wire format mirrors cosmos_dev.mockgui.sbs._send:
    {"clientID": <id>, "cmd": <name>, **fields}
Keep this in sync with that module if the browser protocol changes.
"""


class WebRenderSink:
    """sbs shim for one web client. `frames` accumulates wire commands."""

    def __init__(self, client_id, real_sbs, out=None):
        self.client_id = client_id
        self._real = real_sbs
        # Optional callback(wire_dict) invoked as commands are produced (e.g. to
        # stream straight to a queue/file). If None, commands buffer in .frames.
        self._out = out
        self.frames = []

    # -- capture -----------------------------------------------------------
    def _emit(self, cmd, **fields):
        wire = {"clientID": self.client_id, "cmd": cmd, **fields}
        if self._out is not None:
            self._out(wire)
        else:
            self.frames.append(wire)

    def drain(self):
        """Return buffered frames and clear the buffer."""
        f = self.frames
        self.frames = []
        return f

    # -- buffer control ----------------------------------------------------
    def send_gui_clear(self, clientID, tag):
        self._emit("clear", tag=tag)

    def send_gui_complete(self, clientID, tag):
        self._emit("complete", tag=tag)

    # -- standard widgets (parent, tag, style, l, t, r, b) -----------------
    def _widget(self, cmd, clientID, parent, tag, style, left, top, right, bottom):
        self._emit(cmd, parent=parent, tag=tag, style=style,
                   left=left, top=top, right=right, bottom=bottom)

    def send_gui_button(self, *a):        self._widget("button", *a)
    def send_gui_checkbox(self, *a):      self._widget("checkbox", *a)
    def send_gui_clickregion(self, *a):   self._widget("clickregion", *a)
    def send_gui_colorbutton(self, *a):   self._widget("colorbutton", *a)
    def send_gui_colorcheckbox(self, *a): self._widget("colorcheckbox", *a)
    def send_gui_dropdown(self, *a):      self._widget("dropdown", *a)
    def send_gui_icon(self, *a):          self._widget("icon", *a)
    def send_gui_iconbutton(self, *a):    self._widget("iconbutton", *a)
    def send_gui_iconcheckbox(self, *a):  self._widget("iconcheckbox", *a)
    def send_gui_image(self, *a):         self._widget("image", *a)
    def send_gui_rawiconbutton(self, *a): self._widget("rawiconbutton", *a)
    def send_gui_sub_region(self, *a):    self._widget("sub_region", *a)
    def send_gui_text(self, *a):          self._widget("text", *a)
    def send_gui_typein(self, *a):        self._widget("typein", *a)

    # -- widgets with extra params -----------------------------------------
    def send_gui_face(self, clientID, parent, tag, face_string,
                      left, top, right, bottom):
        self._emit("face", parent=parent, tag=tag, face_string=face_string,
                   left=left, top=top, right=right, bottom=bottom)

    def send_gui_slider(self, clientID, parent, tag, current, style,
                        left, top, right, bottom):
        self._emit("slider", parent=parent, tag=tag, current=current,
                   style=style, left=left, top=top, right=right, bottom=bottom)

    def send_gui_hotkey(self, clientID, category, tag, keyType, description):
        self._emit("hotkey", category=category, tag=tag,
                   keyType=keyType, description=description)

    # -- ignored for web pages --------------------------------------------
    # Console widget lists drive 3d/2d gameplay views, which web pages don't
    # use. Swallow it so it doesn't reach the real engine transport.
    def send_client_widget_list(self, clientID, consoleType, widgetList):
        pass

    # -- everything else forwards to the real engine sbs -------------------
    def __getattr__(self, name):
        return getattr(self._real, name)


def make_sink_factory(out=None, sinks=None):
    """Build a factory suitable for Gui.web_render_sink.

    The factory returns one persistent WebRenderSink per client id (so frames
    accumulate across a tick's multiple presents). If `out` is given, each wire
    command is streamed to out(wire) as produced; otherwise frames buffer on the
    sink and can be read from the returned `sinks` dict. `sinks` may be passed in
    to share the registry with the caller.
    """
    if sinks is None:
        sinks = {}

    def factory(client_id, real_sbs):
        sink = sinks.get(client_id)
        if sink is None:
            sink = WebRenderSink(client_id, real_sbs, out=out)
            sinks[client_id] = sink
        else:
            # real_sbs can change frame-to-frame; keep it current
            sink._real = real_sbs
        return sink

    factory.sinks = sinks
    return factory
