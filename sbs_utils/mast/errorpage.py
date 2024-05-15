from ..gui import Gui, Page
import sbs

class ErrorPage(Page):
    def __init__(self, msg) -> None:
        self.gui_state = 'show'
        self.message = msg

    def present(self, event):
        match self.gui_state:
            case  "sim_on":
                self.gui_state = "blank"
                sbs.send_gui_clear(event.client_id, "")
                sbs.send_gui_complete(event.client_id, "")

            case  "show":
                sbs.send_gui_clear(event.client_id,"")
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                sbs.send_gui_text(
                    event.client_id, f"{self.message}", "text", 25, 20, 99, 90)
                sbs.send_gui_button(event.client_id, "back", "back", 80, 90, 99, 94)
                sbs.send_gui_button(event.client_id, "Resume Mission", "resume", 80, 95, 99, 99)
                sbs.send_gui_complete(event.client_id, "")

    def on_message(self, event):
        match event.sub_tag:
            case "back":
                Gui.pop(event.client_id)

            case "resume":
                Gui.pop(event.client_id)
                sbs.resume_sim()


