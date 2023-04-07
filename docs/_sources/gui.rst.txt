GUI system
======================
The GUI System is for managing content that is displayed in the console selection screens e.g. the mission select screen for the server and the console select screen for clients.


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

The contents of a page is created using the sbs module's GUI calls: e.g.

- send_gui_clear
- send_gui_text
- etc.


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

.. graphviz::

      digraph G {
         node [shape=box, fontname="Arial"];
         //constraint=false;
         rankdir="LR";
         //splines="ortho";
         
         subgraph cluster_tHREE {
            label="row3"
            a2;
            b2;
            c2;
            d2;
         }

         subgraph cluster_two {
            label="row2"
            a1;
            b1;
            c1;
            d1;
         }
         subgraph cluster_main {
            label="row1"
            a;
            b;
            c;
            d;
         }
         
         
         

         
         a [label=label];
         b [label=slider];
         c [label=label];
         d [label=slider];
         

         a -> b [style=invis];
         b -> c [style=invis];
         c -> d [style=invis];
         
         a1 [label=label];
         b1 [label=slider];
         c1 [label=label];
         d1 [label=slider];
         

         a1 -> b1 [style=invis];
         b1 -> c1 [style=invis];
         c1 -> d1 [style=invis];
         
         a2 [label=label];
         b2 [label=slider];
         c2 [label=label];
         d2 [label=slider];
         

         a2 -> b2 [style=invis];
         b2 -> c2 [style=invis];
         c2 -> d2 [style=invis];
         

         
      }



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



