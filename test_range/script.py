try:
    from sbs_utils.handlerhooks import *
    from sbs_utils.gui import Gui
    from sbs_utils.mast.maststorypage import StoryPage
    from sbs_utils.mast.mast import Mast

    class TestRangePage(StoryPage):
        story_file = "story.mast"

    Mast.include_code = True   # show MAST source in runtime errors (handy while iterating)

    Gui.server_start_page_class(TestRangePage)
    Gui.client_start_page_class(TestRangePage)
except Exception as e:
    message = e

    def cosmos_event_handler(sim, event):
        import sbs
        sbs.send_gui_clear(event.client_id, "")
        sbs.send_gui_text(event.client_id, "", "text",
                          f"$text:sbs_utils Test Range failed to load:\n{message};", 5, 5, 95, 95)
