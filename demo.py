from ..gui import Gui, Page
import sbs


class StartPage(Page):
    def present(self, sim, CID):
        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
                    CID, "Hello, GUI", "text", 25, 30, 99, 90)
        
        sbs.send_gui_button(CID, "Start", "start", 80,90, 99,99)
        

    def on_message(self, sim, message_tag, clientID, _):
        if message_tag == 'start':
            # start the mission
            sbs.create_new_sim()
            sbs.resume_sim()
            start_mission(sim)
            
            
def start_mission(sim):
    pass

Gui.server_start_page_class(StartPage)
Gui.client_start_page_class(StartPage)








class StartPage(Page):
    def present(self, sim, CID):
        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
                    CID, "Hello, GUI", "text", 25, 30, 99, 90)

        sbs.send_gui_button(CID, "Sub page", "subpage",  85, 90, 99, 94)        
        sbs.send_gui_button(CID, "Start", "start", 80,95, 99,99)
        

    def on_message(self, sim, message_tag, clientID, _):
        if message_tag == 'start':
            # start the mission
            sbs.create_new_sim()
            sbs.resume_sim()
            start_mission(sim)
        if message_tag == 'subpage':
            Gui.push(sim,clientID, SubPage())
            
            
def start_mission(sim):
    pass





class SubPage(Page):

    def present(self, sim, CID):
        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
                    CID, "Sub Page", "text", 25, 30, 99, 90)
        
        sbs.send_gui_button(CID, "Back", "back",  85, 90, 99, 94)
        sbs.send_gui_button(CID, "Another", "again",  85, 95, 99, 99)
        

    def on_message(self, sim, message_tag, clientID, _):
        if message_tag == 'back':
            Gui.pop(sim,clientID)
        if message_tag == 'again':
            Gui.push(sim,clientID, SubPage())


