try:
    import sbslibs
    from sbs_utils.handlerhooks import *
    from sbs_utils.gui import Gui
    from sbs_utils.mast.maststorypage import StoryPage
    from sbs_utils.mast.mast import Mast

    class SizzleStoryPage(StoryPage):
        story_file = "story.mast"

    # Runtime errors quote the offending MAST line. Worth the memory here: this
    # mission exists to be debugged.
    Mast.include_code = True

    # BOTH are required. Without them no page class is registered, so no server or
    # client page ever starts, Gui.clients stays EMPTY, and a client that launches
    # fine still never appears to the engine - which reads as "the client never
    # bound" and sends you looking at the binding code instead of at this file.
    Gui.server_start_page_class(SizzleStoryPage)
    Gui.client_start_page_class(SizzleStoryPage)
except Exception as e:
    message = e

    def cosmos_event_handler(sim, event):
        import sbs
        sbs.send_gui_clear(event.client_id, "")
        sbs.send_gui_text(
            event.client_id, "", "text",
            f"$text:sbs_utils runtime error^{message};", 0, 0, 80, 95)
        sbs.send_gui_complete(event.client_id, "")
