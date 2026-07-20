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
    from sbs_utils.mast.maststory import MastStory
    from sbs_utils.mast_sbs.maststorypage import StoryPage
    from sbs_utils.gui import Gui

    # Wrap the design under its own label (not `main`, which the running mission
    # already owns) with a trailing await gui() to present it.
    label = "__gui_preview__"
    lines = str(code or "").replace("\r", "").split("\n")
    indented = "\n".join((("    " + ln) if ln.strip() else ln) for ln in lines)
    src = "=== " + label + "\n" + indented + "\n    await gui()\n"

    story = MastStory()
    errors = story.compile(src, "gui_preview", story)
    if errors:
        return errors

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
