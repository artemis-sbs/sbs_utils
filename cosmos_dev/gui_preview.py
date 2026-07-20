"""Render arbitrary GUI MAST live in a running mock session — the GUI Editor's
pixel-faithful preview (dev-only).

The VS Code GUI Editor generates a block of ``gui_*`` MAST. `present_gui_code`
wraps it as a one-off story label and pushes it as a page on a client, so the
real engine lays it out and the real renderer draws it — nothing approximated.
Reuses the same compile+page pattern the web-page harness uses.

Wired to the runner's ``{"action": "gui_preview", "code": "..."}`` debug command.
"""


def present_gui_code(code, client_id=0):
    """Compile a GUI-editor code block and present it on ``client_id``.

    Returns a list of compile errors ([] on success). The page is pushed onto the
    client's stack, so popping/reloading returns to what was there before.
    """
    import re
    from sbs_utils.mast.maststory import MastStory
    from sbs_utils.mast_sbs.maststorypage import StoryPage
    from sbs_utils.gui import Gui

    code = str(code or "")
    m = re.match(r"^\s*===+\s*(\w+)", code)
    mw = re.match(r"^\s*//web/(\S+)", code)
    web_path = None
    if m:
        # The editor emits a complete `=== <label>` gui — compile as-is and start
        # at that label (never `main`).
        label = m.group(1)
        src = code if "await gui(" in code else code + "\n    await gui()"
    elif mw:
        # A web page — compile the `//web/<path>` route as-is; its label name is
        # generated, so resolve it from the compiled story below.
        web_path = mw.group(1)
        label = None
        src = code if "await gui(" in code else code + "\n    await gui()"
    else:
        # A bare block (e.g. hand-pasted) — wrap it in a preview label.
        label = "__gui_preview__"
        lines = code.replace("\r", "").split("\n")
        indented = "\n".join((("    " + ln) if ln.strip() else ln) for ln in lines)
        tail = "" if "await gui(" in code else "\n    await gui()"
        src = "=== " + label + "\n" + indented + tail
    if not src.endswith("\n"):
        src += "\n"                    # MAST needs a newline after the last statement

    story = MastStory()
    errors = story.compile(src, "gui_preview", story)
    if errors:
        return errors
    if web_path is not None:
        label = Gui._find_web_label(story, web_path)
        if label is None:
            return ["preview: no //web/%s route compiled" % web_path]

    class PreviewPage(StoryPage):
        pass
    PreviewPage.story = story

    page = PreviewPage()
    page.start_label = label
    # The preview browser is a web client (not an engine console), so exempt it
    # from Gui.present's console purge — same as a //web/ page.
    Gui.web_client_ids.add(client_id)
    Gui.push(client_id, page)
    return []
