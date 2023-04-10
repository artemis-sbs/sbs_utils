Adding Gui pages and using the Gui System
===========================================

Scripted GUIs are presented at various times. 

- Server during Mission selection and simulation pause
- Client during Console Select screen

At the low level, a mission script can handle HandlePresentGui, HandlePresentGUIMessage, HandleClientConnect to presnet a GUI.

At this low level this can get more complicated as you get multiple clients, and if the script needs more 'pages' of content to present.

sbs_utils GUI system
---------------------

The sbs_utils Gui system is provided to help manage multiple client and pages easily.

Clients are managed seamlessly and the focus is creating a Page and defining the start page for the server and clients.

Creating a Page
-----------------

A Page is a single class that allows the presentation and handling of messages in one place that can have data.

Below is the 'hello, world' of mission script using sbs_utils.

.. code-block:: python

    # enable sbs_utils systems and implement handlers
    from lib.sbs_utils.handlerhooks import *
    # bring in the Gui system and Page base class
    from lib.sbs_utils.gui import Page, Gui
    # the artemis cosmos engine
    import sbs

    class StartPage(Page):
        def present(self, sim, clientID):
            # clear the gui for the client
            sbs.send_gui_clear(clientID)
            # add a text box
            sbs.send_gui_text(
                        clientID, "Hello, GUI", "text", 25, 30, 99, 90)
            # add a button
            sbs.send_gui_button(clientID, "Start", "start", 80,90, 99,99)
            

        def on_message(self, sim, message_tag, clientID, _):
            # if the message_tag is 'start' the button is pressed
            if message_tag == 'start':
                # start the mission
                sbs.create_new_sim()
                sbs.resume_sim()
                start_mission(sim)

    def start_mission(sim):
        # create the world
        pass
    
    # Set the start page as the start page for the server
    Gui.server_start_page_class(StartPage)

With this script, selecting the mission in Artemis Cosmos will present the GUI and allow the mission to start. The world will be empty at this point.

Notice the clientID is passed to the page. Client id for the server is 0 and the id for other clients are non-zero. These client ids are managed by the gui system.

Also, the page's gui components are created in present using the engine's calls for this.

The engine (sbs) defines functions to 'send' to the GUI. The Artemis Cosmos 'data' folder has a file called script_documentation.txt which has the documentation for these functions.

The following are some of functions:

|    send_gui_clear(...)
|    send_gui_3dship(...)
|    send_gui_button(...)
|    send_gui_checkbox(...)
|    send_gui_face(...)
|    send_gui_slider(...)
|    send_gui_text(...)


Generally these functions take:

- A client ID - for which client
- Data for the control
- a 'message tag' which identifies the control
- it location - location is a percentage on the screen for left, top, right, bottom

So the following creates a text box with "Hello, GUI". The ID of the control is text. and is taking up the box from 25% from the left, 30% from the top, to 99% from the left, 90% from the top

.. code-block:: python

    sbs.send_gui_text(clientID, "Hello, GUI", "text", 25, 30, 99, 90)



Multiple Pages
-----------------

Pages can be used present a more complex set of screens. Like a stack of plates, or like apps on a phone a stack of pages can have multiple pages while only displaying the top page.
Removing the top page, the previous one becomes the top/active page.

The sbs_utils GUI system provides simple methods to manages multiple pages.

Call Gui. :py:meth:`~sbs_utils.gui.Gui.push` To place a new active Page 


.. graphviz::

      digraph G {
         node [shape=box, fontname="Arial"];
         constraint=false;
         rankdir="LR";
         //splines="ortho";
         
         sp [label="StartPage"];
         op [label="Options"];
         

         sp -> op [label="push"];
      }


Call Gui. :py:meth:`~sbs_utils.gui.Gui.pop` To deactivate an active Page and activate the previous page.


.. graphviz::

      digraph G {
         node [shape=box, fontname="Arial"];
         //constraint=false;
         rankdir="LR";
         ordering=in;
         splines="ortho";
         
         sp [label="StartPage"];
         op [label="Options"  style=dashed];
         
         sp -> op [weight=10;style=invis]
         op -> sp [label="pop"];
      }


Example Multiple Pages
---------------------------
The following example adds a New Sub Page class and modifies the start page to add activate the new sub page.

.. code-block:: python

    class StartPage(Page):
        def present(self, sim, clientID):
            sbs.send_gui_clear(clientID)
            sbs.send_gui_text(clientID, "Hello, GUI", "text", 25, 30, 99, 90)
            #added button to show a sub page
            sbs.send_gui_button(clientID, "Sub page", "subpage",  80, 90, 99, 94)        
            sbs.send_gui_button(clientID, "Start", "start", 80,95, 99,99)

        def on_message(self, sim, message_tag, clientID, _):
            if message_tag == 'start':
                # start the mission
                sbs.create_new_sim()
                sbs.resume_sim()
                start_mission(sim)
            # added button handler for sub page
            if message_tag == 'subpage':
                Gui.push(sim,clientID, SubPage())

The New subPage can stack multiple sub pages on top of each other.
The back button returns to the previous page.

.. code-block:: python

    class SubPage(Page):

        def present(self, sim, clientID):
            sbs.send_gui_clear(clientID)
            sbs.send_gui_text(
                        clientID, "Sub Page", "text", 25, 30, 99, 90)
            
            sbs.send_gui_button(clientID, "Back", "back",  80, 90, 99, 94)
            sbs.send_gui_button(clientID, "Another", "again",  80, 95, 99, 99)
            

        def on_message(self, sim, message_tag, clientID, _):
            if message_tag == 'back':
                Gui.pop(sim,clientID)
            if message_tag == 'again':
                Gui.push(sim,clientID, SubPage())

Complex page hierarchies
^^^^^^^^^^^^^^^^^^^^^^^^^

The GUI systems's stack and navigating via push and pop can allow for deep and complex GUI screens.

For example a main StartPage could navigate to an Option page that can either navigate to a ship picker Page or an Avatar Editor.



.. graphviz::

      digraph G {
         node [shape=box, fontname="Arial"];
         constraint=false;
         rankdir="LR";
         //splines="ortho";

         subgraph cluster_main {
            label="Main pages"
            sp;
            op;
         }
         subgraph cluster_pages {
            label="option sub pages";
            pick;
            av;
         }
         

         
         sp [label="StartPage"];
         op [label="Options"];
         av [label="Avatar Editor"];
         pick [label="ShipPicker"];
         

         sp -> op [label="push"];
         op -> sp [label="pop"];

         op -> pick [label="push"];
         pick -> op [label="pop"];
         
         
         
         av -> op [label="pop"];
         op -> av [label="push"];
      }





