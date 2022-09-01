from ..gui import Page
import sbs


class StartPage(Page):
    count = 0
    def __init__(self, description, callback) -> None:
        self.gui_state = 'options'
        self.desc = description
        self.callback = callback

    def present(self, sim, event):
        CID = event.client_id

        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
                    CID, self.desc, "text", 25, 30, 99, 90)
        
        sbs.send_gui_button(CID, "Start", "start", 80,90, 99,99)
        

    def on_message(self, sim, event):
        if event.sub_tag == 'start':
            self.callback
        

