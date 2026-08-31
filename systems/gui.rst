GUI system
======================

The GUI System is for managing content that is displayed in the console selection screens e.g. the mission select screen for the server and the console select screen for clients.

Scripted GUIs are presented at various times. 

- Server during Mission selection and simulation pause
- Client during Console Select screen

At the low level, a mission script can handle HandlePresentGui, HandlePresentGUIMessage, HandleClientConnect to present a GUI.

At this low level this can get more complicated as you get multiple clients, and if the script needs more 'pages' of content to present.


Artemis Cosmos gui system
------------------------------
Artemis Cosmos calls the script function HandlePresentGUI when a console is in 'options' mode. For the server this is when selecting a mission or when the simulation is paused. For consoles this is when in the console select/options.

Artemis Cosmos calls the script function HandlePresentGUIMessage when change occur due to interacting with the GUI.


sbs_utils GUI system
----------------------

To use the sbs utils  GUI system 

- call :py:meth:`~sbs_utils.gui.Gui.present` in HandlePresentGUI 
- call :py:meth:`~sbs_utils.gui.Gui.on_message` in HandlePresentGUIMessage.
- call :py:meth:`~sbs_utils.gui.Gui.add_client` in HandleClientConnect.

 .. code-block:: python

   def HandlePresentGUI(sim):
      Gui.present(sim)

   def HandlePresentGUIMessage(sim, message_tag, clientID, data):
      Gui.on_message(sim, message_tag, clientID, data)

   def HandleClientConnect(sim, clientID):
      Gui.add_client(sim,clientID)



Importing the hookhandlers module it does by default.


 .. code-block:: python

      from sbs_utils.handlerhooks import *
      # no longer need to implement handlers in script.py



Creating a GUI page
---------------------

A :py:class:`~sbs_utils.gui.Page` is an abstract class used to create and organize a set of GUI components and react to changes to the GUI

 .. code-block:: python

      from lib.sbs_utils.gui import Page

      class MyPage(Page):
        def present(self, sim, CID):
           pass

        def on_message(self, sim, message_tag, clientID, data):
           pass

Creating a hello, world Page
------------------------------

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



Setting the start pages
-------------------------
The GUI needs somewhere to start this will be referred to as a start page.
The server has a start page shown in the mission select screen.
The client has a page in the console select screen.

A :py:class:`~sbs_utils.gui.Gui` is used to set start pages.
This should be done in script.py or as part of the initial loading of the mission.

:py:meth:`~sbs_utils.gui.Gui.server_start_page_class` is used to set the Page class to use for the server.
:py:meth:`~sbs_utils.gui.Gui.client_start_page_class` is used to set the Page class to use for clients.


 .. code-block:: python

      from sbs_utils.handlerhooks import *
      from lib.sbs_utils.gui import Gui

      Gui.server_start_page(MyPage)
      Gui.client_start_page(MyPage)

Calling these function should create the appropriate page at the proper time. For the server start page it will be created when the mission is selected in the mission selection screen.
This initial page will remain created throughout the running of the mission and would be called when the simulation is paused as well.

For clients it is created when the client connects. Each client will have their own copy/instance of the page class specified.



Navigating pages
-------------------

A GUI can have multiple pages. Only one page is displayed at a time.

The GUI system keeps a 'stack' of pages.
A Page can be navigated to by pushing an instance of a Page.
and the previous page can be returned to by 'popping' the current page off the stack.

Pushing pages
^^^^^^^^^^^^^^

For example, the start page can navigate to an Options page by pushing the option page on the stack.

.. code-block:: python

      from lib.sbs_utils.gui import Page

      class StartPage(Page):
        def present(self, sim, CID):
            sbs.send_gui_clear(CID)
            sbs.send_gui_button(CID, "Options", "options", 80,80, 99,89)
            sbs.send_gui_button(CID, "Start", "start", 80,90, 99,99)

        def on_message(self, sim, message_tag, clientID, data):
            if message_tag == 'options':
               if self.options is None:
                  self.options = Options()
               Gui.push(sim, clientID, self.options)

When the options button is pressed a Options page instances is 'pushed' on to the stack and it becomes the GUI that is presented.
The StartPage instance still exists, and is below the Options page on the stack.

.. image:: ../media/d/gui-push.png

Popping pages
^^^^^^^^^^^^^^


.. code-block:: python

      from lib.sbs_utils.gui import Page

      class Options(Page):
        def present(self, sim, CID):
            sbs.send_gui_clear(CID)
            sbs.send_gui_button(CID, "Back", "back", 80,90, 99,99)

        def on_message(self, sim, message_tag, clientID, data):
            if message_tag == 'back':
               Gui.pop(sim, clientID)

When the back button is pressed, the Option page is removed from the stack and the StartPage is then presented.


.. image:: ../media/d/gui-pop.png


Complex page hierarchies
^^^^^^^^^^^^^^^^^^^^^^^^^

The GUI systems's stack and navigating via push and pop can allow for deep and complex GUI screens.

For example a main StartPage could navigate to an Option page that can either navigate to a ship picker Page or an Avatar Editor.



.. image:: ../media/d/gui-complex.png

Reusable pages
---------------

There are a few reusable pages in sbs_utils:

- :py:class:`~sbs_utils.pages.start.StartPage` 
- :py:class:`~sbs_utils.pages.shippicker.ShipPicker`
- :py:class:`~sbs_utils.pages.avatar.AvatarEditor`



Page layout helpers
--------------------

The layout module helps layout a lot of components using generator that calculate the location for controls.

Currently the layout module supports the 'wrap' layout. which will build a table like layout by filling in columns and wrapping to a next row.




.. code-block:: python

      from lib.sbs_utils.gui import Page

      class Example(Page):
        def present(self, sim, CID):
            loc = layout.wrap(25, b, 15, 4,col=4, h_gutter = 1)
            for widget in widgets:
               sbs.send_gui_text(CID, widget.label, f"lab:{widget.label}", *next(loc))
               sbs.send_gui_slider(CID, f"value:{widget.label}",  widget["min"],widget["max"],self.cur[v], *next(loc), True)


.. raw:: html

   <video controls autostart loop width="640" height="480" src="../_static/gui_layout.mp4"></video>



Widgets
--------------------

Widgets provide a method to combine multiple components into a single reusable element.

For example the library has a ShipPicker widget :py:class:`~sbs_utils.widgets.shippicker.ShipPicker`

It combines a text title, a ship viewer, with next and previous buttons.

There is an example Page that shows two instances of the ShipPicker Widget. :py:class:`~sbs_utils.pages.shippicker.ShipPicker``





API: gui module
--------------------

.. automodule:: sbs_utils.gui
   :members:
   :undoc-members:
   :show-inheritance:


API: pages
--------------------

.. automodule:: sbs_utils.pages.avatar
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: sbs_utils.pages.shippicker
   :members: 
   :undoc-members:
   :show-inheritance:

.. automodule:: sbs_utils.pages.start
   :members:
   :undoc-members:
   :show-inheritance:



API: layout module
--------------------

.. automodule:: sbs_utils.layout
   :members:
   :undoc-members:
   :show-inheritance:


API: widgets
--------------------

.. automodule:: sbs_utils.widgets.shippicker
   :members:
   :undoc-members:
   :show-inheritance:



